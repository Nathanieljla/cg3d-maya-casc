from __future__ import annotations

import enum
import json
import pathlib
import sys
import tempfile
import types
import unittest
from unittest import mock

from tests._support import (
    CASCADEUR_SITE_ROOT,
    installed_modules,
    load_module,
    make_module,
    make_package,
)


class FbxFilterType(enum.IntEnum):
    SKIP = 0
    AUTO = 1
    SCENE = 2
    MODEL = 3
    ANIMATION = 4


class Property:
    def __init__(self, value=None, data_id=None):
        self.value = value
        self.id = data_id

    def get(self):
        return self.value


class Material:
    def __init__(self, name, slot):
        self.name = name
        self.slot = slot

    def get_property(self, field):
        if field == "name":
            return Property(self.name, (self.slot, field))
        return Property(data_id=(self.slot, field))


class MeshBehaviour:
    def __init__(self, materials):
        self.materials = materials

    def get_property(self, name):
        if name != "materials":
            raise KeyError(name)
        return Property(self.materials, "materials")


class PathName:
    def __init__(self, value):
        self.value = value

    def to_string(self):
        return self.value


class MeshObject:
    def __init__(self, name, path, materials):
        self.name = name
        self.path = path
        self.materials = materials

    def get_path_name(self):
        return PathName(self.path)

    def get_behaviour_by_name(self, name):
        return MeshBehaviour(self.materials) if name == "MeshObject" else None

    def has_behaviour(self, name):
        return name == "MeshObject"


class DataEditor:
    def __init__(self):
        self.values = {}

    def set_data_value(self, data_id, value):
        self.values[data_id] = value


class SceneUpdater:
    def __init__(self):
        self.updates = 0

    def generate_update(self):
        self.updates += 1


class Scene:
    def __init__(self):
        self.de = DataEditor()
        self.su = SceneUpdater()
        self.warnings = []
        self.edits = []

    def edit(self, title, function, *args, **kwargs):
        self.edits.append(title)
        function(self, *args)
        return True

    def warning(self, message):
        self.warnings.append(message)


class CascadeurImportTests(unittest.TestCase):
    def _load(self, scene=None, branch=None, export_set=None):
        scene = scene or Scene()
        branch = branch or []
        export_set = export_set or object()
        root = types.SimpleNamespace(scene="scene")
        hierarchy = make_module(
            "common.hierarchy",
            get_object_branch_inclusive=lambda unused_root, unused_scene: branch,
        )
        common_package = make_package("common", hierarchy=hierarchy)
        csc = make_module("csc", model=types.SimpleNamespace(DataMode=types.SimpleNamespace(Static=0)))
        pycsc = make_module(
            "pycsc", get_current_scene=lambda: types.SimpleNamespace(ds=scene)
        )
        rig_mode = make_package("rig_mode")
        rig_mode_on = make_module("rig_mode.on", run_raw=lambda *args: None)
        host = make_package("_cascadeur_import_host")
        common = make_module(
            "_cascadeur_import_host.common",
            MAYA_BEHAVIOUR_NAME="Maya Data",
            get_export_sets=lambda unused_scene: ({export_set}, set()),
            get_ids=lambda unused_sets: {"export-id": export_set},
            get_set_members=lambda unused_set: [root],
        )
        fbx = make_module(
            "_cascadeur_import_host.fbx",
            FbxFilterType=FbxFilterType,
        )
        modules = {
            "csc": csc,
            "pycsc": pycsc,
            "common": common_package,
            "common.hierarchy": hierarchy,
            "rig_mode": rig_mode,
            "rig_mode.on": rig_mode_on,
            "_cascadeur_import_host": host,
            "_cascadeur_import_host.common": common,
            "_cascadeur_import_host.fbx": fbx,
        }
        with installed_modules(modules):
            module = load_module(
                "_cascadeur_import_host.maya_import",
                CASCADEUR_SITE_ROOT / "cg3dmaya" / "maya_import.py",
            )
        return module, scene, common

    def test_auto_filter_chooses_scene_skip_or_animation(self):
        module, unused_scene, unused_common = self._load()
        try:
            self.assertEqual(
                FbxFilterType.SCENE,
                module._get_modified_filter(None, "", FbxFilterType.AUTO),
            )
            self.assertEqual(
                FbxFilterType.SKIP,
                module._get_modified_filter(object(), "rig.qrigcasc", FbxFilterType.AUTO),
            )
            self.assertEqual(
                FbxFilterType.ANIMATION,
                module._get_modified_filter(object(), "", FbxFilterType.AUTO),
            )
            self.assertEqual(
                FbxFilterType.SKIP,
                module._get_modified_filter(None, "", FbxFilterType.ANIMATION),
            )
            self.assertEqual(
                FbxFilterType.MODEL,
                module._get_modified_filter(None, "", FbxFilterType.MODEL),
            )
        finally:
            sys.modules.pop("_cascadeur_import_host.maya_import", None)

    def test_duplicate_mesh_names_use_path_and_material_to_disambiguate(self):
        material_a = Material("materialA", 0)
        material_b = Material("materialB", 1)
        mesh_a = MeshObject("ns:mesh", "rootA/ns:mesh", [material_a])
        mesh_b = MeshObject("ns:mesh", "rootB/ns:mesh", [material_b])
        module, unused_scene, unused_common = self._load(branch=[mesh_a, mesh_b])
        try:
            matched = module._match_mesh(
                [mesh_a, mesh_b],
                {
                    "name": "ns:mesh",
                    "path": "|rootB|ns:mesh",
                    "materials": [{"name": "materialB"}],
                },
                set(),
            )
            self.assertIs(mesh_b, matched)
        finally:
            sys.modules.pop("_cascadeur_import_host.maya_import", None)

    def test_material_name_is_preferred_and_slot_is_a_fallback(self):
        materials = [Material("first", 0), Material("second", 1)]
        mesh = MeshObject("mesh", "mesh", materials)
        module, scene, unused_common = self._load(branch=[mesh])
        try:
            applied = module._apply_mesh_materials(
                scene,
                mesh,
                {
                    "materials": [
                        {
                            "name": "renamed_in_fbx",
                            "slot": 1,
                            "properties": {"roughness": 0.25},
                        }
                    ]
                },
            )
            self.assertEqual(1, applied)
            self.assertEqual(0.25, scene.de.values[(1, "roughness")])
        finally:
            sys.modules.pop("_cascadeur_import_host.maya_import", None)

    def test_each_sidecar_is_a_fresh_snapshot_and_clears_old_maps(self):
        material = Material("skin", 0)
        mesh = MeshObject("mesh", "mesh", [material])
        module, scene, unused_common = self._load(branch=[mesh])
        try:
            with tempfile.TemporaryDirectory() as directory:
                mayacasc = pathlib.Path(directory) / "mayacasc"
                mayacasc.mkdir()
                sidecar = mayacasc / "material_info.json"

                def write(properties):
                    sidecar.write_text(
                        json.dumps(
                            {
                                "version": 1,
                                "exports": [
                                    {
                                        "id": "export-id",
                                        "set_name": "SET",
                                        "meshes": [
                                            {
                                                "name": "mesh",
                                                "path": "|mesh",
                                                "materials": [
                                                    {
                                                        "name": "skin",
                                                        "slot": 0,
                                                        "properties": properties,
                                                    }
                                                ],
                                            }
                                        ],
                                    }
                                ],
                            }
                        ),
                        encoding="utf-8",
                    )

                with mock.patch.object(
                    module.tempfile, "gettempdir", return_value=directory
                ):
                    write(
                        {
                            "base_color_map": "old.png",
                            "roughness_map": "packed.png",
                            "roughness_channel": 2,
                        }
                    )
                    module._load_materials(scene)
                    self.assertEqual("old.png", scene.de.values[(0, "base_color_map")])
                    self.assertEqual(2, scene.de.values[(0, "roughness_channel")])

                    write({"base_color": [0.1, 0.2, 0.3]})
                    module._load_materials(scene)

                self.assertEqual("", scene.de.values[(0, "base_color_map")])
                self.assertEqual("", scene.de.values[(0, "roughness_map")])
                self.assertEqual(0, scene.de.values[(0, "roughness_channel")])
                self.assertEqual([0.1, 0.2, 0.3], scene.de.values[(0, "base_color")])
                self.assertEqual(2, scene.su.updates)
        finally:
            sys.modules.pop("_cascadeur_import_host.maya_import", None)

    def test_embed_mode_without_a_sidecar_is_a_noop(self):
        module, scene, unused_common = self._load()
        try:
            with tempfile.TemporaryDirectory() as directory:
                with mock.patch.object(
                    module.tempfile, "gettempdir", return_value=directory
                ):
                    self.assertIsNone(module._load_materials(scene))
            self.assertEqual([], scene.edits)
        finally:
            sys.modules.pop("_cascadeur_import_host.maya_import", None)


if __name__ == "__main__":
    unittest.main()
