from __future__ import annotations

import contextlib
import pathlib
import sys
import tempfile
import types
import unittest

from tests._support import SRC_ROOT, installed_modules, load_module, make_module, make_package


class FakeMayaCommands(types.ModuleType):
    def __init__(self, project=None):
        super().__init__("maya.cmds")
        self.project = pathlib.Path(project).resolve() if project else None
        self.connections = {}
        self.filepaths = {}
        self.warnings = []
        self.workspace_calls = []

    def workspace(self, **kwargs):
        self.workspace_calls.append(kwargs)
        if "expandName" in kwargs:
            return str(self.project / kwargs["expandName"])
        if kwargs.get("query") and kwargs.get("rootDirectory"):
            return str(self.project)
        raise RuntimeError(kwargs)

    def warning(self, message):
        self.warnings.append(message)

    def listConnections(self, plug, **kwargs):
        source = self.connections.get(plug)
        if not source:
            return []
        return [source] if kwargs.get("plugs") else [source.partition(".")[0]]

    def nodeType(self, node):
        return "file" if node in self.filepaths else "standardSurface"

    def listHistory(self, *args, **kwargs):
        return []

    def getAttr(self, plug, **kwargs):
        node, separator, attribute = plug.partition(".")
        if attribute == "fileTextureName":
            return self.filepaths[node]
        return 0.0


@contextlib.contextmanager
def material_modules(cmds):
    maya = make_package("maya", cmds=cmds)
    maya_api = make_package("maya.api")
    open_maya = make_module("maya.api.OpenMaya")
    maya_api.OpenMaya = open_maya
    cg3dguru = make_package("cg3dguru")
    cg3dguru_maya = make_module("cg3dguru.maya", node_name=str)
    cg3dcasc = make_package("cg3dcasc", SRC_ROOT)
    host_package = make_package("_material_test_core", SRC_ROOT / "core")
    host_maya = make_module("_material_test_core.maya", set_members=lambda unused: [])
    modules = {
        "maya": maya,
        "maya.cmds": cmds,
        "maya.api": maya_api,
        "maya.api.OpenMaya": open_maya,
        "cg3dguru": cg3dguru,
        "cg3dguru.maya": cg3dguru_maya,
        "cg3dcasc": cg3dcasc,
        "_material_test_core": host_package,
        "_material_test_core.maya": host_maya,
    }
    loaded = []
    with installed_modules(modules):
        try:
            material_data = load_module(
                "cg3dcasc.material_data", SRC_ROOT / "material_data.py"
            )
            loaded.append("cg3dcasc.material_data")
            maya_material_data = load_module(
                "_material_test_core.maya_material_data",
                SRC_ROOT / "core" / "maya_material_data.py",
            )
            loaded.append("_material_test_core.maya_material_data")
            materials = load_module(
                "_material_test_core.materials", SRC_ROOT / "core" / "materials.py"
            )
            loaded.append("_material_test_core.materials")
            yield material_data, maya_material_data, materials
        finally:
            for name in reversed(loaded):
                sys.modules.pop(name, None)


class TexturePathTests(unittest.TestCase):
    def test_project_relative_paths_are_exported_as_absolute_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            project = pathlib.Path(directory)
            sourceimages = project / "sourceimages"
            sourceimages.mkdir()
            texture = sourceimages / "Torso_low_Normal_OpenGL.png"
            texture.write_bytes(b"png")
            cmds = FakeMayaCommands(project)
            with material_modules(cmds) as (_, _, materials):
                expected = texture.resolve()
                for maya_path in (
                    "sourceimages/Torso_low_Normal_OpenGL.png",
                    "/sourceimages/Torso_low_Normal_OpenGL.png",
                ):
                    with self.subTest(path=maya_path):
                        exported = pathlib.Path(
                            materials.prepare_texture_path(maya_path)
                        )
                        self.assertEqual(expected, exported)
                        self.assertTrue(exported.is_absolute())

    def test_custom_location_copies_once_and_does_not_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            source = root / "source.jpg"
            target = root / "textures"
            source.write_bytes(b"first")
            cmds = FakeMayaCommands(root)
            with material_modules(cmds) as (_, _, materials):
                copied = pathlib.Path(materials.prepare_texture_path(source, target))
                self.assertEqual(b"first", copied.read_bytes())
                source.write_bytes(b"second")
                materials.prepare_texture_path(source, target)
                self.assertEqual(b"first", copied.read_bytes())

    def test_missing_texture_still_serializes_an_absolute_path(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            cmds = FakeMayaCommands(root)
            with material_modules(cmds) as (_, _, materials):
                result = pathlib.Path(
                    materials.prepare_texture_path("sourceimages/missing.png")
                )
                self.assertTrue(result.is_absolute())
                self.assertEqual(1, len(cmds.warnings))


class PackedChannelTests(unittest.TestCase):
    def test_rgba_outputs_map_to_cascadeur_channel_indices(self):
        cmds = FakeMayaCommands(pathlib.Path.cwd())
        cmds.filepaths["packedFile"] = "C:/textures/packed.png"
        plugs = {
            "roughness": ("outColorG", 1),
            "metallic": ("outColorB", 2),
            "reflectance": ("outColorR", 0),
            "ambientOcclusion": ("outAlpha", 3),
        }
        with material_modules(cmds) as (_, maya_data, materials):
            attributes = {}
            for attribute, (output, expected_channel) in plugs.items():
                cmds.connections["shader." + attribute] = "packedFile." + output
                entry = maya_data.MayaMaterialData._read_attribute(
                    "shader", attribute
                )
                self.assertEqual(expected_channel, entry["channel"])
                attributes[attribute] = entry

            materials.prepare_texture_path = lambda path, location: path
            result = materials._cascadeur_material(attributes, "")
            self.assertEqual(1, result["roughness_channel"])
            self.assertEqual(2, result["metallic_channel"])
            self.assertEqual(0, result["reflectance_channel"])
            self.assertEqual(3, result["ambient_occlusion_channel"])
            self.assertEqual(
                {"C:/textures/packed.png"},
                {
                    result["roughness_map"],
                    result["metallic_map"],
                    result["reflectance_map"],
                    result["ambient_occlusion_map"],
                },
            )

    def test_full_color_output_defaults_scalar_maps_to_red(self):
        cmds = FakeMayaCommands(pathlib.Path.cwd())
        cmds.filepaths["packedFile"] = "C:/textures/packed.png"
        cmds.connections["shader.roughness"] = "packedFile.outColor"
        with material_modules(cmds) as (_, maya_data, materials):
            entry = maya_data.MayaMaterialData._read_attribute(
                "shader", "roughness"
            )
            self.assertNotIn("channel", entry)
            materials.prepare_texture_path = lambda path, location: path
            result = materials._cascadeur_material({"roughness": entry}, "")
            self.assertEqual(0, result["roughness_channel"])

    def test_material_document_is_versioned(self):
        cmds = FakeMayaCommands(pathlib.Path.cwd())
        with material_modules(cmds) as (_, _, materials):
            self.assertEqual(
                {"version": 1, "exports": [{"id": "one"}]},
                materials.material_document([{"id": "one"}]),
            )


if __name__ == "__main__":
    unittest.main()
