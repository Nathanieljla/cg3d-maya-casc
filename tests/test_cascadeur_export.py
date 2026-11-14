from __future__ import annotations

import pathlib
import sys
import tempfile
import types
import unittest
from unittest import mock

from tests._support import (
    CASCADEUR_SITE_ROOT,
    CallRecorder,
    installed_modules,
    load_module,
    make_module,
    make_package,
)


class Data:
    def __init__(self, value):
        self.value = value

    def get(self):
        return self.value


class DataCollection:
    def __init__(self, values):
        self.values = values

    def get_by_name(self, name):
        return self.values.get(name, [])


class Scene:
    def __init__(self):
        self.selection = []
        self.errors = []
        self.warnings = []

    def select(self, selection):
        self.selection = list(selection)

    def edit(self, title, function, *args):
        function(self, *args)
        return True

    def error(self, message):
        self.errors.append(message)

    def warning(self, message):
        self.warnings.append(message)


class CascadeurExportTests(unittest.TestCase):
    def _load(self, scene=None):
        scene = scene or Scene()
        export_fbx = CallRecorder()
        send_to_maya = CallRecorder()
        settings_instances = []

        class FbxSettings:
            def __init__(self):
                self.bake_animation = None
                settings_instances.append(self)

        csc = make_module(
            "csc",
            fbx=types.SimpleNamespace(FbxSettings=FbxSettings),
            view=types.SimpleNamespace(),
        )
        pycsc = make_module(
            "pycsc", get_current_scene=lambda: types.SimpleNamespace(ds=scene)
        )
        hierarchy = make_module(
            "common.hierarchy",
            get_object_branch_inclusive=lambda root, unused_scene: [
                root,
                root.name + "_child",
            ],
        )
        common_package = make_package("common", hierarchy=hierarchy)
        host = make_package("_cascadeur_export_host")
        common = make_module(
            "_cascadeur_export_host.common",
            MAYA_ROOTS="Maya Roots",
            MAYA_BEHAVIOUR_NAME="Maya Data",
            BAKE_ANIMATION="Bake Animation",
            _active_port_number=6000,
            _add_export_settings=lambda behaviour: None,
        )
        server = make_module(
            "_cascadeur_export_host.server", send_to_maya=send_to_maya
        )
        fbx = make_module(
            "_cascadeur_export_host.fbx",
            FbxFilterType=types.SimpleNamespace(SELECTED=5),
            export_fbx=export_fbx,
        )
        modules = {
            "csc": csc,
            "pycsc": pycsc,
            "common": common_package,
            "common.hierarchy": hierarchy,
            "_cascadeur_export_host": host,
            "_cascadeur_export_host.common": common,
            "_cascadeur_export_host.server": server,
            "_cascadeur_export_host.fbx": fbx,
        }
        with installed_modules(modules):
            module = load_module(
                "_cascadeur_export_host.maya_export",
                CASCADEUR_SITE_ROOT / "cg3dmaya" / "maya_export.py",
            )
        return module, scene, export_fbx, send_to_maya, settings_instances

    def test_cleanup_removes_files_and_fbm_directories(self):
        module, unused_scene, unused_export, unused_send, unused_settings = self._load()
        try:
            with tempfile.TemporaryDirectory() as directory:
                export_dir = pathlib.Path(directory) / "mayacasc"
                export_dir.mkdir()
                (export_dir / "character.fbx").write_bytes(b"fbx")
                media = export_dir / "character.fbm"
                media.mkdir()
                (media / "texture.png").write_bytes(b"png")
                module.temp_dir = export_dir
                with mock.patch.object(module.tempfile, "gettempdir", return_value=directory):
                    module._clean_export_location()
                self.assertEqual([], list(export_dir.iterdir()))
        finally:
            sys.modules.pop("_cascadeur_export_host.maya_export", None)

    def test_cleanup_refuses_to_delete_outside_the_temp_root(self):
        module, unused_scene, unused_export, unused_send, unused_settings = self._load()
        try:
            with tempfile.TemporaryDirectory() as directory:
                module.temp_dir = pathlib.Path(directory) / "nested" / "mayacasc"
                with mock.patch.object(module.tempfile, "gettempdir", return_value=directory):
                    with self.assertRaises(RuntimeError):
                        module._clean_export_location()
        finally:
            sys.modules.pop("_cascadeur_export_host.maya_export", None)

    def test_cleanup_errors_are_reported_without_running_export(self):
        module, scene, unused_export, unused_send, unused_settings = self._load()
        determine = CallRecorder()
        module.determine_export_action = determine
        module._clean_export_location = mock.Mock(
            side_effect=PermissionError("locked .fbm")
        )
        try:
            self.assertFalse(module.export_maya_animation())
            self.assertEqual([], determine.calls)
            self.assertIn("locked .fbm", scene.errors[0])
        finally:
            sys.modules.pop("_cascadeur_export_host.maya_export", None)

    def test_export_selects_each_branch_and_dispatches_to_maya(self):
        module, scene, export_fbx, send_to_maya, settings_instances = self._load()
        try:
            root = types.SimpleNamespace(name="root", scene="scene")
            root_reference = types.SimpleNamespace(object=root)
            roots_property = types.SimpleNamespace(get=lambda: [root_reference])
            maya_id = Data("uuid")
            bake = Data(True)
            maya_behaviour = types.SimpleNamespace(
                datasWithSameNamesReadonly=DataCollection({"maya_id": [maya_id]}),
                datasWithSameNames=DataCollection({"Bake Animation": [bake]}),
            )
            root_behaviour = types.SimpleNamespace(
                object=types.SimpleNamespace(name="casc:CSC_EXPORT"),
                behaviours=roots_property,
                get_siblings_by_name=lambda name: [maya_behaviour],
            )
            export_set = types.SimpleNamespace(
                get_behaviour_by_name=lambda name: root_behaviour
            )
            with tempfile.TemporaryDirectory() as directory:
                module.temp_dir = pathlib.Path(directory)
                module._export(scene, [export_set])

            self.assertEqual([root, "root_child"], scene.selection)
            self.assertEqual(1, len(export_fbx.calls))
            export_path, export_filter, settings = export_fbx.calls[0][0]
            self.assertTrue(str(export_path).endswith("casc_CSC_EXPORT.uuid.fbx"))
            self.assertEqual(5, export_filter)
            self.assertTrue(settings.bake_animation)
            self.assertIs(settings, settings_instances[0])
            self.assertEqual(
                [((6000, "cg3dcasc.core.import_fbx()"), {})], send_to_maya.calls
            )
        finally:
            sys.modules.pop("_cascadeur_export_host.maya_export", None)


if __name__ == "__main__":
    unittest.main()
