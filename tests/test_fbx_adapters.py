from __future__ import annotations

import pathlib
import sys
import tempfile
import types
import unittest

from tests._support import (
    CASCADEUR_SITE_ROOT,
    SRC_ROOT,
    CallRecorder,
    installed_modules,
    load_module,
    make_module,
    make_package,
)


class MayaFbxTests(unittest.TestCase):
    def _load(self):
        statements = []
        removed_namespaces = CallRecorder()
        cmds = make_module(
            "maya.cmds",
            playbackOptions=lambda **kwargs: 1 if kwargs.get("animationStartTime") else 24,
            upAxis=lambda **kwargs: "y",
        )
        mel = make_module("maya.mel", eval=lambda statement: statements.append(statement))
        maya = make_package("maya", cmds=cmds, mel=mel)
        cg3dguru = make_package("cg3dguru")
        utils = make_module(
            "cg3dguru.utils", remove_namespaces=removed_namespaces
        )
        cg3dguru.utils = utils
        modules = {
            "maya": maya,
            "maya.cmds": cmds,
            "maya.mel": mel,
            "cg3dguru": cg3dguru,
            "cg3dguru.utils": utils,
        }
        return modules, statements, removed_namespaces

    def test_export_is_selection_only_and_honours_media_and_children(self):
        modules, statements, unused_remove = self._load()
        with installed_modules(modules):
            module = load_module("_test_maya_fbx", SRC_ROOT / "core" / "fbx.py")
            try:
                module.export(
                    pathlib.Path(r"C:\temp\character.fbx"),
                    include_children=False,
                    embed_media=True,
                )
            finally:
                sys.modules.pop("_test_maya_fbx", None)

        self.assertIn("FBXExportEmbeddedTextures -v true;", statements)
        self.assertIn("FBXExportIncludeChildren -v false;", statements)
        self.assertIn(
            'FBXExport -s -f "C:/temp/character.fbx";', statements
        )
        self.assertFalse(any(item.startswith("FBXExport -f") for item in statements))

    def test_namespace_cleanup_runs_only_when_requested_and_file_exists(self):
        modules, unused_statements, remove_namespaces = self._load()
        with tempfile.TemporaryDirectory() as directory:
            target = pathlib.Path(directory) / "character.fbx"
            target.write_text("fbx", encoding="utf-8")
            with installed_modules(modules):
                module = load_module(
                    "_test_maya_fbx_cleanup", SRC_ROOT / "core" / "fbx.py"
                )
                try:
                    module.export(target, remove_namespaces=True)
                finally:
                    sys.modules.pop("_test_maya_fbx_cleanup", None)
        self.assertEqual([((target,), {})], remove_namespaces.calls)

    def test_import_uses_merge_mode_and_normalized_path(self):
        modules, statements, unused_remove = self._load()
        with installed_modules(modules):
            module = load_module(
                "_test_maya_fbx_import", SRC_ROOT / "core" / "fbx.py"
            )
            try:
                module.import_fbx(pathlib.Path(r"C:\temp\animation.fbx"))
            finally:
                sys.modules.pop("_test_maya_fbx_import", None)
        self.assertIn('FBXImportMode -v "merge";', statements)
        self.assertIn('FBXImport -f "C:/temp/animation.fbx";', statements)


class FakeCascadeurLoader:
    def __init__(self, modern_selected=True):
        self.calls = []
        self.settings = []
        self.modern_selected = modern_selected
        if not modern_selected:
            self.export_scene_selected_objects = None

    def set_settings(self, settings):
        self.settings.append(settings)

    def _call(self, name, path):
        self.calls.append((name, path))
        return name

    def import_scene(self, path):
        return self._call("import_scene", path)

    def import_model(self, path):
        return self._call("import_model", path)

    def import_animation(self, path):
        return self._call("import_animation", path)

    def import_animation_to_selected_objects(self, path):
        return self._call("import_selected", path)

    def import_animation_to_selected_frames(self, path):
        return self._call("import_frames", path)

    def export_all_objects(self, path):
        return self._call("export_all", path)

    def export_model(self, path):
        return self._call("export_model", path)

    def export_scene_selected_objects(self, path):
        return self._call("export_selected", path)

    def export_scene_selected(self, path):
        return self._call("export_selected_legacy", path)

    def export_joints(self, path):
        return self._call("export_joints", path)


class CascadeurFbxTests(unittest.TestCase):
    def _load(self, loader):
        current_scene = types.SimpleNamespace(unwrap=lambda: "view")
        tool = types.SimpleNamespace(get_fbx_loader=lambda view: loader)
        manager = types.SimpleNamespace(get_tool=lambda name: tool)
        application = types.SimpleNamespace(get_tools_manager=lambda: manager)
        csc = make_module(
            "csc",
            app=types.SimpleNamespace(get_application=lambda: application),
            fbx=types.SimpleNamespace(FbxLoader=object, FbxSettings=object),
        )
        pycsc = make_module(
            "pycsc",
            get_current_scene=lambda: current_scene,
            new_scene=CallRecorder(),
        )
        modules = {"csc": csc, "pycsc": pycsc}
        with installed_modules(modules):
            module = load_module(
                "_test_cascadeur_fbx",
                CASCADEUR_SITE_ROOT / "cg3dmaya" / "fbx.py",
            )
        return module, pycsc

    def test_every_import_filter_routes_to_the_matching_loader_method(self):
        loader = FakeCascadeurLoader()
        module, pycsc = self._load(loader)
        try:
            cases = {
                module.FbxFilterType.SCENE: "import_scene",
                module.FbxFilterType.MODEL: "import_model",
                module.FbxFilterType.ANIMATION: "import_animation",
                module.FbxFilterType.SELECTED: "import_selected",
                module.FbxFilterType.FRAMES: "import_frames",
            }
            for filter_type, expected in cases.items():
                with self.subTest(filter=filter_type):
                    loader.calls.clear()
                    settings = object()
                    module.import_fbx("input.fbx", filter_type, True, settings)
                    self.assertEqual([(expected, "input.fbx")], loader.calls)
                    self.assertIs(settings, loader.settings[-1])
            self.assertEqual(len(cases), len(pycsc.new_scene.calls))
        finally:
            sys.modules.pop("_test_cascadeur_fbx", None)

    def test_every_export_filter_routes_to_the_matching_loader_method(self):
        loader = FakeCascadeurLoader()
        module, unused_pycsc = self._load(loader)
        try:
            cases = {
                module.FbxFilterType.SCENE: "export_all",
                module.FbxFilterType.MODEL: "export_model",
                module.FbxFilterType.SELECTED: "export_selected",
                module.FbxFilterType.ANIMATION: "export_joints",
            }
            for filter_type, expected in cases.items():
                with self.subTest(filter=filter_type):
                    loader.calls.clear()
                    module.export_fbx("output.fbx", filter_type, object())
                    self.assertEqual([(expected, "output.fbx")], loader.calls)
        finally:
            sys.modules.pop("_test_cascadeur_fbx", None)

    def test_invalid_filters_fail_loudly(self):
        loader = FakeCascadeurLoader()
        module, unused_pycsc = self._load(loader)
        try:
            with self.assertRaises(ValueError):
                module.import_fbx("input.fbx", module.FbxFilterType.SKIP)
            with self.assertRaises(ValueError):
                module.export_fbx("output.fbx", module.FbxFilterType.AUTO)
        finally:
            sys.modules.pop("_test_cascadeur_fbx", None)


if __name__ == "__main__":
    unittest.main()
