from __future__ import annotations

import sys
import unittest

from tests._support import (
    SRC_ROOT,
    CallRecorder,
    installed_modules,
    load_module,
    make_module,
    make_package,
)


class HikSourceTests(unittest.TestCase):
    def test_none_source_targets_character_without_ui_menu_lookup(self):
        class Node:
            def __init__(self, name):
                self._name = name

            def name(self):
                return self._name

        option_menu = CallRecorder()
        cmds = make_module(
            "maya.cmds",
            nodeType=lambda unused_node: "HIKCharacterNode",
            optionMenuGrp=option_menu,
        )
        mel_eval = CallRecorder()
        mel = make_module("maya.mel", eval=mel_eval)
        maya = make_package("maya", cmds=cmds, mel=mel)
        cg_maya = make_module(
            "cg3dguru.maya",
            Node=Node,
            node_name=lambda node: node.name(),
        )
        cg3dguru = make_package("cg3dguru", maya=cg_maya)
        modules = {
            "maya": maya,
            "maya.cmds": cmds,
            "maya.mel": mel,
            "cg3dguru": cg3dguru,
            "cg3dguru.maya": cg_maya,
        }
        with installed_modules(modules):
            module = load_module(
                "_hik_source_test",
                SRC_ROOT / "core" / "hik.py",
            )
        module.load_hik = CallRecorder()

        try:
            module.set_character_source(
                Node("character1"),
                module.SourceType.NONE,
            )
        finally:
            sys.modules.pop("_hik_source_test", None)

        self.assertEqual([], option_menu.calls)
        self.assertEqual(1, len(module.load_hik.calls))
        statement = mel_eval.calls[0][0][0]
        self.assertIn('hikSetCurrentCharacter("character1")', statement)
        self.assertIn('hikEnableCharacter("character1", 2)', statement)


if __name__ == "__main__":
    unittest.main()
