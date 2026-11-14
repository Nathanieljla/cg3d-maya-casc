from __future__ import annotations

import sys
import types
import unittest

from tests._support import (
    CASCADEUR_SITE_ROOT,
    CallRecorder,
    installed_modules,
    load_module,
    make_module,
    make_package,
)


class DialogButton:
    def __init__(self, label, callback=None):
        self.label = label
        self.callback = callback


class DialogManager:
    def __init__(self):
        self.dialogs = []

    def show_buttons_dialog(self, title, message, buttons):
        self.dialogs.append((title, message, buttons))


class Scene:
    def __init__(self):
        self.errors = []
        self.successes = []

    def error(self, message):
        self.errors.append(message)

    def success(self, message):
        self.successes.append(message)


class Item:
    def __init__(self, name, parent=None):
        self.name = name
        self.parent = parent
        self.handle = object()

    def __repr__(self):
        return "Item({})".format(self.name)


class CascadeurExportSetTests(unittest.TestCase):
    def _load(self, scene=None):
        scene = scene or Scene()
        dialogs = DialogManager()
        csc = make_module(
            "csc",
            model=types.SimpleNamespace(DataMode=types.SimpleNamespace(Static=0)),
            update=types.SimpleNamespace(Object=type("UpdateObject", (), {})),
            domain=types.SimpleNamespace(Tool_object_id=type("ToolObject", (), {})),
            view=types.SimpleNamespace(
                DialogButton=DialogButton,
                StandardButton=types.SimpleNamespace(Cancel="Cancel"),
                DialogManager=types.SimpleNamespace(instance=lambda: dialogs),
            ),
            fbx=types.SimpleNamespace(
                FbxSettingsAxis=types.SimpleNamespace(X="x", Y="y", Z="z")
            ),
        )
        pycsc = make_module(
            "pycsc", get_current_scene=lambda: types.SimpleNamespace(ds=scene)
        )
        host = make_package("_cascadeur_sets_host")
        client = make_module("_cascadeur_sets_host.client", data_to_maya=CallRecorder())
        server = make_module(
            "_cascadeur_sets_host.server", send_and_listen=CallRecorder()
        )
        modules = {
            "csc": csc,
            "pycsc": pycsc,
            "_cascadeur_sets_host": host,
            "_cascadeur_sets_host.client": client,
            "_cascadeur_sets_host.server": server,
        }
        with installed_modules(modules):
            module = load_module(
                "_cascadeur_sets_host.common",
                CASCADEUR_SITE_ROOT / "cg3dmaya" / "common.py",
            )
        return module, scene, dialogs, client, server

    def test_root_filter_walks_selected_children_to_top_level(self):
        module, unused_scene, unused_dialogs, unused_client, unused_server = self._load()
        try:
            root = Item("root")
            child = Item("child", root)
            grandchild = Item("grandchild", child)
            self.assertEqual({root}, module._get_roots_from_selected({child, grandchild}))
        finally:
            sys.modules.pop("_cascadeur_sets_host.common", None)

    def test_add_selected_uses_the_single_available_export_set(self):
        module, scene, unused_dialogs, unused_client, unused_server = self._load()
        try:
            root = Item("root")
            export_set = Item("set")
            add = CallRecorder()
            module._get_filtered_selection = lambda *args: {root}
            module.get_export_sets = lambda unused_scene: ({export_set}, set())
            module.remove_export_sets = lambda unused_scene, roots: roots
            module._add_to_set = add
            module.add_selection_to(False)
            self.assertEqual([((scene, {root}, export_set), {})], add.calls)
        finally:
            sys.modules.pop("_cascadeur_sets_host.common", None)

    def test_add_selected_dialog_buttons_keep_their_own_target_set(self):
        module, scene, dialogs, unused_client, unused_server = self._load()
        try:
            root = Item("root")
            set_a = Item("A")
            set_b = Item("B")
            add = CallRecorder()
            module._get_filtered_selection = lambda *args: {root}
            module.get_export_sets = lambda unused_scene: ({set_a, set_b}, set())
            module.remove_export_sets = lambda unused_scene, roots: roots
            module._add_to_set = add
            module.add_selection_to(False)
            buttons = dialogs.dialogs[0][2][:-1]
            for button in buttons:
                button.callback()
            self.assertEqual({set_a, set_b}, {call[0][2] for call in add.calls})
        finally:
            sys.modules.pop("_cascadeur_sets_host.common", None)

    def test_select_members_dialog_buttons_keep_their_own_target_set(self):
        module, scene, dialogs, unused_client, unused_server = self._load()
        try:
            set_a = Item("A")
            set_b = Item("B")
            select = CallRecorder(result=True)
            module.get_export_sets = lambda unused_scene: ({set_a, set_b}, set())
            module._select_set_members = select
            module.select_set_members()
            buttons = dialogs.dialogs[0][2][:-1]
            for button in buttons:
                button.callback()
            self.assertEqual({set_a, set_b}, {call[0][1] for call in select.calls})
        finally:
            sys.modules.pop("_cascadeur_sets_host.common", None)

    def test_sync_requires_one_maya_id_and_one_selected_set(self):
        module, scene, unused_dialogs, unused_client, unused_server = self._load()
        try:
            module.get_selected_maya_set_ids = lambda: {"one", "two"}
            module.get_export_sets = lambda unused_scene: (set(), set())
            module.sync_selected_set_ids()
            self.assertIn("Select exactly one", scene.errors[0])
        finally:
            sys.modules.pop("_cascadeur_sets_host.common", None)

    def test_sync_confirmation_targets_the_selected_export_set(self):
        module, scene, dialogs, unused_client, unused_server = self._load()
        try:
            export_set = Item("set")
            sync = CallRecorder()
            module.get_selected_maya_set_ids = lambda: {"maya-id"}
            module.get_export_sets = lambda unused_scene: ({export_set}, {export_set})
            module.get_ids = lambda unused_sets: {}
            module._sync_id = sync
            module.sync_selected_set_ids()
            yes = dialogs.dialogs[0][2][0]
            yes.callback()
            self.assertEqual([((scene, "maya-id", export_set), {})], sync.calls)
        finally:
            sys.modules.pop("_cascadeur_sets_host.common", None)


if __name__ == "__main__":
    unittest.main()
