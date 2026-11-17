from __future__ import annotations

import ast
import os
import pathlib
import shutil
import tempfile
import unittest
from unittest import mock

from tests._support import REPO_ROOT


INSTALLER_PATH = REPO_ROOT / "installer" / "maya_casc_installer.py"


def _load_preflight_and_installer_method():
    """Load the pure preflight and real pre_install method without Maya/Qt."""
    tree = ast.parse(
        INSTALLER_PATH.read_text(encoding="utf-8"), filename=str(INSTALLER_PATH)
    )
    preflight = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "_cascadeur_install_preflight"
    )
    installer_class = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "MyInstaller"
    )
    pre_install = next(
        node
        for node in installer_class.body
        if isinstance(node, ast.FunctionDef) and node.name == "pre_install"
    )

    class BaseInstaller:
        def __init__(self, module_path):
            self.module_path = str(module_path)
            self.failure_reason = ""
            self.base_pre_install_called = False

        def pre_install(self):
            self.base_pre_install_called = True
            return True

    harness = ast.ClassDef(
        name="InstallerHarness",
        bases=[ast.Name(id="BaseInstaller", ctx=ast.Load())],
        keywords=[],
        body=[pre_install],
        decorator_list=[],
    )
    module = ast.fix_missing_locations(
        ast.Module(body=[preflight, harness], type_ignores=[])
    )
    namespace = {
        "BaseInstaller": BaseInstaller,
        "os": os,
        "pathlib": pathlib,
        "shutil": shutil,
    }
    exec(compile(module, str(INSTALLER_PATH), "exec"), namespace)
    return namespace["_cascadeur_install_preflight"], namespace["InstallerHarness"]


class InstallerPreflightTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        preflight, cls.installer_type = _load_preflight_and_installer_method()
        cls.preflight = staticmethod(preflight)

    def test_missing_cascadeur_setup_explains_first_launch_requirement(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ready, nekki_dir, settings_file, reason = self.preflight(temp_dir)

        self.assertFalse(ready)
        self.assertEqual(
            pathlib.Path(temp_dir) / "Nekki Limited" / "Cascadeur", nekki_dir
        )
        self.assertEqual(nekki_dir / "settings.json", settings_file)
        self.assertIn("Install and launch Cascadeur once", reason)
        self.assertIn(str(settings_file), reason)

    def test_missing_cascadeur_setup_does_not_clear_existing_module(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = pathlib.Path(temp_dir)
            module_path = temp_path / "maya-module"
            module_path.mkdir()
            sentinel = module_path / "keep-me.txt"
            sentinel.write_text("existing install", encoding="utf-8")
            installer = self.installer_type(module_path)

            with mock.patch.dict(os.environ, {"LOCALAPPDATA": temp_dir}):
                result = installer.pre_install()

            self.assertFalse(result)
            self.assertTrue(sentinel.is_file())
            self.assertFalse(installer.base_pre_install_called)
            self.assertIn("Install and launch Cascadeur once", installer.failure_reason)

    def test_existing_settings_file_passes_preflight(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            settings_file = (
                pathlib.Path(temp_dir)
                / "Nekki Limited"
                / "Cascadeur"
                / "settings.json"
            )
            settings_file.parent.mkdir(parents=True)
            settings_file.write_text("{}", encoding="utf-8")

            ready, _, actual_settings_file, reason = self.preflight(temp_dir)

        self.assertTrue(ready)
        self.assertEqual(settings_file, actual_settings_file)
        self.assertEqual("", reason)


if __name__ == "__main__":
    unittest.main()
