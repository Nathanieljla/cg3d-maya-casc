from __future__ import annotations

import pathlib
import sys
import types
import unittest

from tests._support import (
    SRC_ROOT,
    CallRecorder,
    installed_modules,
    load_module,
    make_module,
    make_package,
)


class FakeCommands(types.ModuleType):
    def __init__(self):
        super().__init__("maya.cmds")
        self.connections = {}
        self.skin_calls = []
        self.set_calls = []
        self.connected = []
        self.parent_constraints = []
        self.warnings = []

    def about(self, **kwargs):
        return True

    def setAttr(self, plug, *args, **kwargs):
        self.set_calls.append((plug, args, kwargs))

    def skinCluster(self, cluster, **kwargs):
        self.skin_calls.append((cluster, kwargs))
        if kwargs.get("query") and kwargs.get("influence"):
            return ["proxyJoint"]
        return []

    def listConnections(self, plug, **kwargs):
        result = self.connections.get(plug, [])
        return list(result) if isinstance(result, list) else result

    def dagPose(self, influences, **kwargs):
        return "newBindPose"

    def connectAttr(self, source, destination, **kwargs):
        self.connected.append((source, destination, kwargs))

    def parentConstraint(self, source, destination, **kwargs):
        self.parent_constraints.append((source, destination, kwargs))

    def warning(self, message):
        self.warnings.append(message)

    def waitCursor(self, **kwargs):
        return None

    def ls(self, **kwargs):
        return ["selectedMesh"] if kwargs.get("selection") else []


class ProxyUtilityTests(unittest.TestCase):
    def _load(self):
        cmds = FakeCommands()
        mel = make_module("maya.mel", eval=lambda statement: None)
        open_maya = make_module(
            "maya.api.OpenMaya",
            MGlobal=types.SimpleNamespace(displayInfo=lambda message: None),
            MTransformationMatrix=object,
            MSpace=types.SimpleNamespace(kWorld=0),
        )
        maya_api = make_package("maya.api", OpenMaya=open_maya)
        maya = make_package("maya", cmds=cmds, mel=mel)
        qt_widgets = make_module(
            "PySide2.QtWidgets",
            QInputDialog=type("QInputDialog", (), {}),
            QMessageBox=type("QMessageBox", (), {}),
        )
        pyside = make_package("PySide2")

        cg3dguru = make_package("cg3dguru")
        cg_ui = make_module(
            "cg3dguru.ui", Window=types.SimpleNamespace(mayaWindow=None)
        )
        cg_udata = make_module(
            "cg3dguru.udata", Utils=types.SimpleNamespace(get_nodes_with_data=lambda *args, **kwargs: [])
        )
        cg_maya = make_module(
            "cg3dguru.maya",
            Node=lambda value: value,
            node_name=str,
            nodes=lambda values: list(values),
        )
        cg3dguru.ui = cg_ui
        cg3dguru.udata = cg_udata

        preferences = make_module(
            "cg3dcasc.preferences",
            CopyWeightType=types.SimpleNamespace(SWAP="swap"),
        )
        cg3dcasc = make_package("cg3dcasc", preferences=preferences)
        host = make_package("_proxy_test_host")
        common = make_module("_proxy_test_host.common")
        hik = make_module("_proxy_test_host.hik")
        materials = make_module("_proxy_test_host.materials")
        server = make_module("_proxy_test_host.server")
        disconnect = CallRecorder()
        mayautil = make_module(
            "_proxy_test_host.maya",
            names=lambda values: list(values),
            disconnect=disconnect,
        )
        udata = make_module(
            "_proxy_test_host.udata",
            CascExportData=type("CascExportData", (), {}),
            ProxyData=type("ProxyData", (), {}),
            ProxyRoot=type("ProxyRoot", (), {}),
        )
        modules = {
            "maya": maya,
            "maya.cmds": cmds,
            "maya.mel": mel,
            "maya.api": maya_api,
            "maya.api.OpenMaya": open_maya,
            "PySide2": pyside,
            "PySide2.QtWidgets": qt_widgets,
            "cg3dguru": cg3dguru,
            "cg3dguru.ui": cg_ui,
            "cg3dguru.udata": cg_udata,
            "cg3dguru.maya": cg_maya,
            "cg3dcasc": cg3dcasc,
            "cg3dcasc.preferences": preferences,
            "_proxy_test_host": host,
            "_proxy_test_host.common": common,
            "_proxy_test_host.hik": hik,
            "_proxy_test_host.materials": materials,
            "_proxy_test_host.server": server,
            "_proxy_test_host.maya": mayautil,
            "_proxy_test_host.udata": udata,
        }
        with installed_modules(modules):
            module = load_module(
                "_proxy_test_host.utils", SRC_ROOT / "core" / "utils.py"
            )
        return module, cmds, mayautil, materials

    def test_skin_weights_keep_original_index_and_swap_in_proxy_plugs(self):
        module, cmds, mayautil, unused_materials = self._load()
        replace = CallRecorder()
        module._replace = replace
        module._influence_indices = lambda unused_cluster: {
            "originalJoint": 3,
            "proxyJoint": 8,
        }
        cmds.connections["skin.bindPose"] = []
        cmds.connections["originalJoint"] = [
            "originalJoint.worldMatrix[0]",
            "skin.matrix[3]",
        ]
        try:
            module._copy_swap(
                "proxyMesh",
                "skin",
                {"originalJoint": "proxyJoint"},
                ["originalJoint"],
                ["proxyJoint"],
            )
        finally:
            sys.modules.pop("_proxy_test_host.utils", None)

        self.assertEqual(
            [
                ((8, 3, "skin", "bindPreMatrix"), {}),
                ((8, 3, "skin", "matrix"), {}),
            ],
            replace.calls,
        )
        self.assertIn(
            (("originalJoint.worldMatrix[0]", "skin.matrix[3]"), {}),
            mayautil.disconnect.calls,
        )
        self.assertIn(
            ("newBindPose.message", "skin.bindPose", {"force": True}),
            cmds.connected,
        )

    def test_convert_textures_only_converts_unsupported_extensions(self):
        module, unused_cmds, mayautil, materials = self._load()
        convert = CallRecorder()
        materials.SUPPORTED_TEXTURE_EXTENSIONS = {".jpg", ".jpeg", ".png"}
        materials.convert_texture = convert
        materials.get_textures = lambda objects: {
            "mesh": ["albedo.jpg", "normal.tif", "mask.exr"]
        }
        mayautil.ls = lambda **kwargs: ["mesh"]
        mayautil.top_parent = lambda item: item
        mayautil.descendants = lambda roots: ["meshShape"]
        try:
            module.convert_textures()
        finally:
            sys.modules.pop("_proxy_test_host.utils", None)
        self.assertEqual(
            [
                ((pathlib.Path("normal.tif"),), {}),
                ((pathlib.Path("mask.exr"),), {}),
            ],
            convert.calls,
        )

    def test_create_proxy_command_creates_export_set_only_after_success(self):
        module, unused_cmds, unused_maya, unused_materials = self._load()
        create = CallRecorder()
        module.create_export_set = create
        module.QInputDialog.getText = staticmethod(
            lambda *args, **kwargs: ("CASC", True)
        )
        try:
            module._derig_selection = lambda: False
            module.derig_selection()
            self.assertEqual([], create.calls)
            module._derig_selection = lambda: True
            module.derig_selection()
        finally:
            sys.modules.pop("_proxy_test_host.utils", None)
        self.assertEqual(
            [
                (
                    ("CASC:CASC_CSC_EXPORT",),
                    {"auto_add_selected": True},
                )
            ],
            create.calls,
        )

    def test_constrain_proxy_uses_nodes_returned_by_udata_query_directly(self):
        module, cmds, mayautil, unused_materials = self._load()

        class Value:
            def __init__(self, value):
                self.value = value

            def get(self):
                return self.value

        class Message:
            def __init__(self, values):
                self.values = values

            def inputs(self):
                return self.values

        class HostNode:
            def __init__(self, name):
                self._name = name

            def name(self):
                return self._name

        source = HostNode("sourceJoint")
        root = HostNode("proxyRoot")
        root.rootType = Value(1)
        proxy = HostNode("proxyJoint")
        proxy.proxySource = Message([source])
        descendants = CallRecorder([proxy])
        mayautil.descendants = descendants
        module.preferences.get = lambda: types.SimpleNamespace(
            derig_maintain_offset=True
        )
        module.cg3dguru.udata.Utils.get_nodes_with_data = (
            lambda *args, **kwargs: (
                [root] if kwargs.get("data_class") is module.ProxyRoot else [proxy]
            )
        )

        try:
            module.constrain_proxy()
        finally:
            sys.modules.pop("_proxy_test_host.utils", None)

        self.assertEqual([(([root],), {})], descendants.calls)
        self.assertEqual(
            [
                (
                    "sourceJoint",
                    "proxyJoint",
                    {"maintainOffset": True},
                )
            ],
            cmds.parent_constraints,
        )


if __name__ == "__main__":
    unittest.main()
