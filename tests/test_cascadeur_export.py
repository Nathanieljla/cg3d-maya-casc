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


class Item:
    def __init__(self, name, parent=None):
        self.name = name
        self.parent = parent

    def __repr__(self):
        return "Item({})".format(self.name)


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

    def get_behaviours(self, name):
        return []


class CascadeurExportTests(unittest.TestCase):
    def _load(self, scene=None):
        scene = scene or Scene()
        export_fbx = CallRecorder()

        def write_export(*args, **kwargs):
            export_fbx(*args, **kwargs)
            pathlib.Path(args[0]).write_bytes(b"fbx")
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
            get_export_sets=lambda unused_scene: (set(), set()),
            get_set_members=lambda unused_set: set(),
        )
        server = make_module(
            "_cascadeur_export_host.server", send_to_maya=send_to_maya
        )
        fbx = make_module(
            "_cascadeur_export_host.fbx",
            FbxFilterType=types.SimpleNamespace(SELECTED=5),
            export_fbx=write_export,
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

    def test_export_selection_includes_required_parent_transforms(self):
        module, unused_scene, unused_export, unused_send, unused_settings = self._load()
        container = Item("container")
        mesh_parent = Item("mesh", parent=container)
        mesh = Item("mesh", parent=mesh_parent)
        joint = Item("root", parent=container)
        try:
            self.assertEqual(
                [container, mesh_parent, mesh, joint],
                module._with_required_ancestors([mesh, joint]),
            )
        finally:
            sys.modules.pop("_cascadeur_export_host.maya_export", None)

    def test_export_does_not_dispatch_when_fbx_file_is_missing(self):
        module, scene, unused_export, send_to_maya, unused_settings = self._load()
        root = types.SimpleNamespace(name="root", scene="scene")
        root_reference = types.SimpleNamespace(object=root)
        maya_id = Data("uuid")
        maya_behaviour = types.SimpleNamespace(
            datasWithSameNamesReadonly=DataCollection({"maya_id": [maya_id]}),
            datasWithSameNames=DataCollection({"Bake Animation": [Data(False)]}),
        )
        root_behaviour = types.SimpleNamespace(
            object=types.SimpleNamespace(name="CHAR_CSC_EXPORT"),
            behaviours=types.SimpleNamespace(get=lambda: [root_reference]),
            get_siblings_by_name=lambda name: [maya_behaviour],
        )
        export_set = types.SimpleNamespace(
            get_behaviour_by_name=lambda name: root_behaviour
        )
        module.fbx.export_fbx = lambda *args, **kwargs: None
        try:
            with tempfile.TemporaryDirectory() as directory:
                module.temp_dir = pathlib.Path(directory)
                self.assertFalse(module._export(scene, [export_set]))
            self.assertEqual([], send_to_maya.calls)
            self.assertIn("no file was created", scene.errors[-1])
        finally:
            sys.modules.pop("_cascadeur_export_host.maya_export", None)

    def test_character_export_rejects_multiple_rig_infos(self):
        module, scene, unused_export, unused_send, unused_settings = self._load()
        scene.get_behaviours = lambda name: [object(), object()] if name == "RigInfo" else []
        try:
            self.assertFalse(module.export_character_and_rig())
            self.assertIn("multiple Rig Info", scene.errors[0])
        finally:
            sys.modules.pop("_cascadeur_export_host.maya_export", None)

    def test_character_export_requires_one_rig_info_with_valid_qrt(self):
        module, scene, unused_export, unused_send, unused_settings = self._load()
        try:
            self.assertFalse(module.export_character_and_rig())
            self.assertIn("no Rig Info", scene.errors[-1])

            rig_info = types.SimpleNamespace(
                object=Item("Rig"),
                qrt_json=Data("not-json"),
            )
            scene.get_behaviours = (
                lambda name: [rig_info] if name == "RigInfo" else []
            )
            self.assertFalse(module.export_character_and_rig())
            self.assertIn("qrt_json is invalid", scene.errors[-1])
        finally:
            sys.modules.pop("_cascadeur_export_host.maya_export", None)

    def test_proto_spline_ik_is_serialized_in_rig_mode(self):
        module, scene, unused_export, unused_send, unused_settings = self._load()
        joint_a = Item("spine_01")
        joint_b = Item("spine_02")
        proto = types.SimpleNamespace(
            joints=Data(
                [
                    types.SimpleNamespace(object=joint_a),
                    types.SimpleNamespace(object=joint_b),
                ]
            )
        )
        scene.get_behaviours = (
            lambda name: [proto] if name == "ProtoSplineIk" else []
        )
        try:
            self.assertEqual(
                [["spine_01", "spine_02"]],
                module._spline_ik_chains(scene, {joint_a, joint_b}),
            )
        finally:
            sys.modules.pop("_cascadeur_export_host.maya_export", None)

    def test_character_export_reuses_an_exactly_matching_export_set(self):
        module, scene, unused_export, unused_send, unused_settings = self._load()
        rig_info = types.SimpleNamespace(object=Item("UnrealRig"))
        joint = Item("pelvis")
        mesh = Item("bodyMesh")
        matching = Item("UnrealRig_CSC_EXPORT")
        different = Item("Other_CSC_EXPORT")
        module.common.get_export_sets = lambda unused_scene: (
            {different, matching},
            set(),
        )
        module.common.get_set_members = lambda export_set: (
            {joint, mesh} if export_set is matching else {joint}
        )
        create_set = CallRecorder(Item("newSet"))
        module._new_rig_export_set = create_set
        try:
            result = module._get_or_create_rig_export_set(
                scene,
                rig_info,
                {joint, mesh},
            )
            self.assertIs(matching, result)
            self.assertEqual([], create_set.calls)
        finally:
            sys.modules.pop("_cascadeur_export_host.maya_export", None)

    def test_character_export_writes_qrt_spline_map_and_influenced_mesh(self):
        module, scene, unused_export, unused_send, unused_settings = self._load()
        joint_a = Item("pelvis")
        joint_b = Item("spine_01")
        mesh = Item("bodyMesh")
        rig_info = types.SimpleNamespace(
            object=Item("UnrealRig"),
            qrt_json=Data('{"Document": []}'),
            related_joints=Data([joint_a, joint_b]),
        )
        mesh_behaviour = types.SimpleNamespace(
            object=mesh,
            linked_objects=Data([joint_b]),
        )
        spline = types.SimpleNamespace(
            joints=Data(
                [
                    types.SimpleNamespace(object=joint_a),
                    types.SimpleNamespace(object=joint_b),
                ]
            )
        )
        scene.get_behaviours = lambda name: {
            "RigInfo": [rig_info],
            "MeshObject": [mesh_behaviour],
            "SplineIk": [spline],
        }.get(name, [])
        maya_data = types.SimpleNamespace(
            datasWithSameNamesReadonly=DataCollection({"maya_id": [Data("uuid")]})
        )
        export_set = Item("UnrealRig_CSC_EXPORT")
        export_set.get_behaviour_by_name = lambda name: maya_data
        create_set = CallRecorder(export_set)
        export = CallRecorder()
        module._new_rig_export_set = create_set
        module._export = export
        module._clean_export_location = CallRecorder()

        try:
            with tempfile.TemporaryDirectory() as directory:
                module.temp_dir = pathlib.Path(directory)
                self.assertTrue(module.export_character_and_rig())
                qrig = module.temp_dir / "UnrealRig_CSC_EXPORT.uuid.qrigcasc"
                hikmap = module.temp_dir / "UnrealRig_CSC_EXPORT.uuid.hikmap"
                self.assertTrue(qrig.is_file())
                self.assertTrue(hikmap.is_file())
                mapping = __import__("json").loads(hikmap.read_text(encoding="utf-8"))
            self.assertEqual([["pelvis", "spine_01"]], mapping["spline_ik_chains"])
            self.assertEqual(
                {joint_a, joint_b, mesh},
                create_set.calls[0][0][2],
            )
            self.assertEqual([((scene, {export_set}), {})], export.calls)
        finally:
            sys.modules.pop("_cascadeur_export_host.maya_export", None)


if __name__ == "__main__":
    unittest.main()
