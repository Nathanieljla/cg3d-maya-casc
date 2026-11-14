from __future__ import annotations

import pathlib
import sys
import tempfile
import types
import unittest
from unittest import mock

from tests._support import (
    SRC_ROOT,
    CallRecorder,
    installed_modules,
    load_module,
    make_module,
    make_package,
)


class Identifier:
    def __init__(self, value=""):
        self.value = value
        self.operations = []

    def get(self):
        return self.value

    def set(self, value):
        self.operations.append(("set", value))
        self.value = value

    def unlock(self):
        self.operations.append(("unlock",))

    def lock(self):
        self.operations.append(("lock",))


class ExportData:
    def __init__(self, identifier=""):
        self.cscDataId = Identifier(identifier)


class FakeCommands(types.ModuleType):
    def __init__(self):
        super().__init__("maya.cmds")
        self.loaded = False
        self.scene_sets = []
        self.assembly_results = []
        self.plugin_loads = []
        self.set_calls = []
        self.renames = []

    def pluginInfo(self, *args, **kwargs):
        return self.loaded

    def loadPlugin(self, name):
        self.loaded = True
        self.plugin_loads.append(name)

    def ls(self, **kwargs):
        if kwargs.get("type") == "objectSet":
            return list(self.scene_sets)
        if kwargs.get("assemblies"):
            return list(self.assembly_results.pop(0))
        return []

    def rename(self, node, name):
        self.renames.append((node, name))
        return name

    def sets(self, members, **kwargs):
        self.set_calls.append((list(members), kwargs))

    def error(self, message):
        raise RuntimeError(message)


class MayaImportTests(unittest.TestCase):
    def _load(self, existing_exports=None):
        existing_exports = existing_exports or []
        cmds = FakeCommands()
        maya = make_package("maya", cmds=cmds)
        hik_set = CallRecorder()
        hik = make_module(
            "_maya_import_host.hik",
            SourceType=types.SimpleNamespace(NONE="none"),
            set_character_source=hik_set,
        )
        pigeons = make_module("wingcarrier.pigeons")
        wingcarrier = make_package("wingcarrier", pigeons=pigeons)
        utils_class = types.SimpleNamespace(
            get_nodes_with_data=lambda nodes, data_class: list(existing_exports)
        )
        cg_udata = make_module("cg3dguru.udata", Utils=utils_class)
        cg_utils = make_module("cg3dguru.utils")
        cg3dguru = make_package("cg3dguru", udata=cg_udata, utils=cg_utils)

        created_data = ExportData()

        class CascExportData:
            @classmethod
            def create_node(cls, **kwargs):
                return "newSet", created_data

            @classmethod
            def get_data(cls, node):
                return created_data

        host = make_package("_maya_import_host")
        udata = make_module(
            "_maya_import_host.udata", CascExportData=CascExportData
        )
        server_send = CallRecorder()
        server = make_module("_maya_import_host.server", send_to_casc=server_send)
        character = object()
        common = make_module(
            "_maya_import_host.common",
            get_character_node=lambda data: character,
        )
        import_fbx = CallRecorder()
        fbx = make_module("_maya_import_host.fbx", import_fbx=import_fbx)
        modules = {
            "maya": maya,
            "maya.cmds": cmds,
            "wingcarrier": wingcarrier,
            "wingcarrier.pigeons": pigeons,
            "cg3dguru": cg3dguru,
            "cg3dguru.udata": cg_udata,
            "cg3dguru.utils": cg_utils,
            "_maya_import_host": host,
            "_maya_import_host.hik": hik,
            "_maya_import_host.udata": udata,
            "_maya_import_host.server": server,
            "_maya_import_host.common": common,
            "_maya_import_host.fbx": fbx,
        }
        with installed_modules(modules):
            module = load_module(
                "_maya_import_host.casc_import",
                SRC_ROOT / "core" / "casc_import.py",
            )
        return (
            module,
            cmds,
            server_send,
            import_fbx,
            hik_set,
            created_data,
            character,
        )

    def test_import_command_requests_animation_from_cascadeur(self):
        module, unused_cmds, send, unused_fbx, unused_hik, unused_data, unused_char = self._load()
        try:
            module.import_from_casc()
        finally:
            sys.modules.pop("_maya_import_host.casc_import", None)
        self.assertEqual(
            [(("cg3dmaya.export_maya_animation()",), {})], send.calls
        )

    def test_temp_files_are_grouped_by_export_name_and_extension(self):
        module, unused_cmds, unused_send, unused_fbx, unused_hik, unused_data, unused_char = self._load()
        try:
            with tempfile.TemporaryDirectory() as directory:
                mayacasc = pathlib.Path(directory) / "mayacasc"
                mayacasc.mkdir()
                (mayacasc / "SET.uuid.fbx").write_bytes(b"fbx")
                (mayacasc / "SET.uuid.fbm").mkdir()
                with mock.patch.object(
                    module.tempfile, "gettempdir", return_value=directory
                ):
                    files = module.get_import_files()
            self.assertEqual({"fbx", "fbm"}, set(files["SET.uuid"]))
        finally:
            sys.modules.pop("_maya_import_host.casc_import", None)

    def test_existing_export_set_receives_animation_and_disables_hik_source(self):
        existing = ExportData("uuid")
        module, cmds, unused_send, import_fbx, hik_set, unused_data, character = self._load(
            [existing]
        )
        cmds.scene_sets = ["existingSet"]
        cmds.assembly_results = [["root"], ["root"]]
        module.get_import_files = lambda: {
            "SET.uuid": {"fbx": "animation.fbx"}
        }
        try:
            module.import_fbx()
        finally:
            sys.modules.pop("_maya_import_host.casc_import", None)
        self.assertEqual([((character, "none"), {})], hik_set.calls)
        self.assertEqual([(("animation.fbx",), {})], import_fbx.calls)
        self.assertEqual([], cmds.set_calls)

    def test_unknown_export_id_creates_set_for_new_roots(self):
        module, cmds, unused_send, import_fbx, unused_hik, created, unused_char = self._load()
        cmds.assembly_results = [["oldRoot"], ["oldRoot", "newRoot"]]
        module.get_import_files = lambda: {
            "NEW_SET.new-uuid": {"fbx": "new.fbx"}
        }
        try:
            module.import_fbx()
        finally:
            sys.modules.pop("_maya_import_host.casc_import", None)
        self.assertEqual([(("new.fbx",), {})], import_fbx.calls)
        self.assertEqual(
            [(["newRoot"], {"addElement": "NEW_SET"})], cmds.set_calls
        )
        self.assertEqual(
            [("unlock",), ("set", "new-uuid"), ("lock",)],
            created.cscDataId.operations,
        )


if __name__ == "__main__":
    unittest.main()
