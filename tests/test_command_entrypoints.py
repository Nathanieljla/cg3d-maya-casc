from __future__ import annotations

import pathlib
import sys
import unittest

from tests._support import (
    CASCADEUR_COMMAND_ROOT,
    MAYA_MENU_ROOT,
    CallRecorder,
    installed_modules,
    load_module,
    make_module,
    make_package,
)


MAYA_COMMANDS = {
    "add_to/current_scene.py": ("export_scene", (False,)),
    "add_to/new_scene.py": ("export_scene", (True,)),
    "editor.py": ("editor.run", ()),
    "import.py": ("import_from_casc", ()),
    "preferences.py": ("preferences.editor.run", ()),
    "quick_export.py": ("smart_export", ()),
    "update/update_animations.py": ("update_animations", ()),
    "update/update_models.py": ("update_models", ()),
    "update/update_textures.py": ("update_textures", ()),
    "utils/constrain_proxy.py": ("utils.constrain_proxy", ()),
    "utils/convert_textures.py": ("utils.convert_textures", ()),
    "utils/create_proxy_rig.py": ("utils.derig_selection", ()),
    "utils/hik_from_proxy.py": ("utils.hik_def_from_proxy", ()),
    "utils/sync_casc_id.py": ("utils.sync_casc_id", ()),
}

CASCADEUR_COMMANDS = {
    "add_selected.py": ("Maya.Export Sets.Add Selected", "add_selection_to", (False,)),
    "create_new_set.py": ("Maya.Export Sets.Create New Set", "add_selection_to", (True,)),
    "export_animation.py": ("Maya.Export Animation", "export_maya_animation", ()),
    "export_character_and_rig.py": (
        "Maya.Export Character and Rig",
        "export_character_and_rig",
        (),
    ),
    "remove_selected.py": ("Maya.Export Sets.Remove Selected", "remove_selection_from", ()),
    "select_set_members.py": ("Maya.Export Sets.Select Set Members", "select_set_members", ()),
    "sync_ids.py": ("Maya.Export Sets.Sync Maya ID", "sync_selected_set_ids", ()),
}


def _python_files(root):
    return {
        path.relative_to(root).as_posix()
        for path in root.rglob("*.py")
        if path.name != "__init__.py"
    }


class MayaMenuCommandTests(unittest.TestCase):
    def test_every_menu_command_has_an_explicit_routing_test(self):
        expected = set(MAYA_COMMANDS) | {"connect.py"}
        self.assertEqual(expected, _python_files(MAYA_MENU_ROOT))

    def test_menu_commands_route_to_the_expected_workflow(self):
        for index, (relative_path, (target, expected_args)) in enumerate(
            sorted(MAYA_COMMANDS.items())
        ):
            with self.subTest(command=relative_path):
                recorder = CallRecorder()
                root = make_package("cg3dcasc")
                editor = make_module("cg3dcasc.editor")
                preferences = make_package("cg3dcasc.preferences")
                preferences_editor = make_module("cg3dcasc.preferences.editor")
                utils = make_module("cg3dcasc.utils")

                owner = root
                pieces = target.split(".")
                if pieces[0] == "editor":
                    owner = editor
                    root.editor = editor
                elif pieces[:2] == ["preferences", "editor"]:
                    owner = preferences_editor
                    root.preferences = preferences
                    preferences.editor = preferences_editor
                elif pieces[0] == "utils":
                    owner = utils
                    root.utils = utils
                setattr(owner, pieces[-1], recorder)

                modules = {
                    "cg3dcasc": root,
                    "cg3dcasc.editor": editor,
                    "cg3dcasc.preferences": preferences,
                    "cg3dcasc.preferences.editor": preferences_editor,
                    "cg3dcasc.utils": utils,
                }
                module_name = "_test_maya_menu_{}".format(index)
                with installed_modules(modules):
                    module = load_module(
                        module_name, MAYA_MENU_ROOT / pathlib.Path(relative_path)
                    )
                    try:
                        module.command("ignored", value="ignored")
                    finally:
                        sys.modules.pop(module_name, None)

                self.assertEqual([(expected_args, {})], recorder.calls)

    def test_connect_reports_success_only_after_dispatch(self):
        for dispatched, expected_messages in ((True, 1), (False, 0)):
            with self.subTest(dispatched=dispatched):
                send = CallRecorder(result=dispatched)
                display = CallRecorder()
                root = make_package("cg3dcasc")
                root.server = make_module("cg3dcasc.server", send_to_casc=send)
                open_maya = make_module(
                    "maya.api.OpenMaya",
                    MGlobal=type("MGlobal", (), {"displayInfo": display}),
                )
                maya = make_package("maya")
                maya_api = make_package("maya.api", OpenMaya=open_maya)
                modules = {
                    "cg3dcasc": root,
                    "maya": maya,
                    "maya.api": maya_api,
                    "maya.api.OpenMaya": open_maya,
                }
                module_name = "_test_connect_{}".format(dispatched)
                with installed_modules(modules):
                    module = load_module(module_name, MAYA_MENU_ROOT / "connect.py")
                    try:
                        module.command()
                    finally:
                        sys.modules.pop(module_name, None)

                self.assertEqual([(("cg3dmaya.report_port_number()",), {})], send.calls)
                self.assertEqual(expected_messages, len(display.calls))


class CascadeurCommandTests(unittest.TestCase):
    def test_every_cascadeur_command_has_an_explicit_routing_test(self):
        self.assertEqual(set(CASCADEUR_COMMANDS), _python_files(CASCADEUR_COMMAND_ROOT))

    def test_command_names_and_workflow_routing(self):
        for index, (filename, (command_name, target, expected_args)) in enumerate(
            sorted(CASCADEUR_COMMANDS.items())
        ):
            with self.subTest(command=filename):
                recorder = CallRecorder()
                cg3dmaya = make_module("cg3dmaya", **{target: recorder})
                module_name = "_test_cascadeur_command_{}".format(index)
                with installed_modules({"cg3dmaya": cg3dmaya}):
                    module = load_module(
                        module_name, CASCADEUR_COMMAND_ROOT / filename
                    )
                    try:
                        self.assertEqual(command_name, module.command_name())
                        self.assertEqual(command_name, module.name())
                        module.run(object())
                    finally:
                        sys.modules.pop(module_name, None)

                self.assertEqual([(expected_args, {})], recorder.calls)


if __name__ == "__main__":
    unittest.main()
