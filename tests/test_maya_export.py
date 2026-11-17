from __future__ import annotations

import json
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


class CascExportData:
    @classmethod
    def get_data(cls, value):
        return value

    @classmethod
    def references_textures(cls, value):
        return value.reference


class MayaExportTests(unittest.TestCase):
    def _load(self):
        cmds = make_module(
            "maya.cmds",
            objectType=lambda node, **kwargs: str(node).endswith("Shape"),
        )
        maya = make_package("maya", cmds=cmds)
        pigeons = make_module("wingcarrier.pigeons")
        wingcarrier = make_package("wingcarrier", pigeons=pigeons)
        udata = make_module("cg3dguru.udata", Attribute=type("Attribute", (), {}))
        cg_utils = make_module("cg3dguru.utils")
        cg3dguru = make_package("cg3dguru", udata=udata, utils=cg_utils)

        host = make_package("_maya_export_host")
        hik = make_module("_maya_export_host.hik")
        preferences = make_module("_maya_export_host.preferences")
        cg3dcasc = make_package("cg3dcasc", preferences=preferences)
        udata_module = make_module(
            "_maya_export_host.udata",
            CascExportData=CascExportData,
            QRigData=type("QRigData", (), {}),
        )
        server_send = CallRecorder()
        server = make_module("_maya_export_host.server", send_to_casc=server_send)
        common = make_module("_maya_export_host.common", get_export_nodes=lambda: [])
        casc_qrt = make_module("_maya_export_host.casc_qrt")
        fbx = make_module("_maya_export_host.fbx")
        build_material = CallRecorder(result={"id": "export-id"})
        materials = make_module(
            "_maya_export_host.materials",
            MATERIAL_INFO_FILE="material_info.json",
            build_export_data=build_material,
            material_document=lambda exports: {"version": 1, "exports": exports},
        )
        mayautil = make_module(
            "_maya_export_host.maya",
            parent=lambda node: None,
            descendants=lambda nodes: set(),
        )
        modules = {
            "maya": maya,
            "maya.cmds": cmds,
            "wingcarrier": wingcarrier,
            "wingcarrier.pigeons": pigeons,
            "cg3dguru": cg3dguru,
            "cg3dguru.udata": udata,
            "cg3dguru.utils": cg_utils,
            "cg3dcasc": cg3dcasc,
            "cg3dcasc.preferences": preferences,
            "_maya_export_host": host,
            "_maya_export_host.hik": hik,
            "_maya_export_host.preferences": preferences,
            "_maya_export_host.udata": udata_module,
            "_maya_export_host.server": server,
            "_maya_export_host.common": common,
            "_maya_export_host.casc_qrt": casc_qrt,
            "_maya_export_host.fbx": fbx,
            "_maya_export_host.materials": materials,
            "_maya_export_host.maya": mayautil,
        }
        with installed_modules(modules):
            module = load_module(
                "_maya_export_host.casc_export",
                SRC_ROOT / "core" / "casc_export.py",
            )
        return module, cmds, mayautil, server_send, build_material

    def test_trimmed_export_branch_keeps_only_paths_to_content(self):
        module, cmds, mayautil, unused_send, unused_build = self._load()
        parents = {
            "meshShape": "mesh",
            "mesh": "geo",
            "geo": "root",
            "root": None,
        }
        mayautil.parent = lambda node: parents[node]
        mayautil.descendants = lambda seeds: {"meshShape"} if "mesh" in seeds else set()
        cmds.objectType = lambda node, **kwargs: node == "meshShape"
        try:
            result = module.get_export_branches({"root"}, {"meshShape"})
            self.assertEqual({"root", "geo", "mesh", "meshShape"}, result)
            self.assertNotIn("unrelatedSibling", result)
        finally:
            sys.modules.pop("_maya_export_host.casc_export", None)

    def test_temp_cleanup_removes_files_and_fbm_directories(self):
        module, unused_cmds, unused_maya, unused_send, unused_build = self._load()
        try:
            with tempfile.TemporaryDirectory() as directory:
                export_dir = pathlib.Path(directory)
                (export_dir / "old.fbx").write_bytes(b"fbx")
                media = export_dir / "old.fbm"
                media.mkdir()
                (media / "texture.png").write_bytes(b"png")
                module._clear_export_directory(export_dir)
                self.assertEqual([], list(export_dir.iterdir()))
        finally:
            sys.modules.pop("_maya_export_host.casc_export", None)

    def test_reference_export_rebuilds_sidecar_before_dispatch(self):
        module, unused_cmds, unused_maya, send, build_material = self._load()
        export_data = types.SimpleNamespace(reference=True)
        module.cascadeur_available = lambda: True
        module._export_data = CallRecorder(result={"mesh"})
        try:
            with tempfile.TemporaryDirectory() as directory:
                temp = pathlib.Path(directory) / "mayacasc"
                temp.mkdir()
                (temp / "stale.json").write_text("stale", encoding="utf-8")
                stale_media = temp / "stale.fbm"
                stale_media.mkdir()
                with mock.patch.object(
                    module.tempfile, "gettempdir", return_value=directory
                ):
                    self.assertTrue(
                        module.export(
                            export_set=export_data,
                            cmd="cg3dmaya.update_textures()",
                            only_textures=True,
                        )
                    )
                document = json.loads(
                    (temp / "material_info.json").read_text(encoding="utf-8")
                )
                self.assertEqual(
                    {"version": 1, "exports": [{"id": "export-id"}]}, document
                )
                self.assertFalse((temp / "stale.json").exists())
                self.assertFalse(stale_media.exists())
            self.assertEqual(1, len(build_material.calls))
            self.assertEqual(
                [(("cg3dmaya.update_textures()",), {})], send.calls
            )
        finally:
            sys.modules.pop("_maya_export_host.casc_export", None)

    def test_embed_export_intentionally_writes_no_sidecar(self):
        module, unused_cmds, unused_maya, send, build_material = self._load()
        export_data = types.SimpleNamespace(reference=False)
        module.cascadeur_available = lambda: True
        module._export_data = CallRecorder(result={"mesh"})
        try:
            with tempfile.TemporaryDirectory() as directory:
                with mock.patch.object(
                    module.tempfile, "gettempdir", return_value=directory
                ):
                    module.export(
                        export_set=export_data,
                        cmd="cg3dmaya.update_textures()",
                        only_textures=True,
                    )
                self.assertFalse(
                    (pathlib.Path(directory) / "mayacasc" / "material_info.json").exists()
                )
            self.assertEqual([], build_material.calls)
            self.assertEqual(1, len(send.calls))
        finally:
            sys.modules.pop("_maya_export_host.casc_export", None)

    def test_update_commands_dispatch_the_expected_modes(self):
        module, unused_cmds, unused_maya, unused_send, unused_build = self._load()
        export = CallRecorder(result=True)
        module.export = export
        try:
            self.assertTrue(module.update_textures())
            module.update_animations()
            module.update_models()
            module.smart_export()
            module.export_scene(True)
        finally:
            sys.modules.pop("_maya_export_host.casc_export", None)
        self.assertEqual(
            [
                ((), {"cmd": "cg3dmaya.update_textures()", "only_textures": True}),
                ((), {"cmd": "cg3dmaya.update_animations()", "textures": False}),
                ((), {"cmd": "cg3dmaya.update_models()"}),
                ((), {"cmd": "cg3dmaya.smart_import()"}),
                ((), {"cmd": "cg3dmaya.import_scene(True)"}),
            ],
            export.calls,
        )


if __name__ == "__main__":
    unittest.main()
