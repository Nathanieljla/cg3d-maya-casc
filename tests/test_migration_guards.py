from __future__ import annotations

import ast
import pathlib
import unittest

from tests._support import REPO_ROOT, SRC_ROOT


OLD_PACKAGE_NAMES = {"cg3dcasc_v2", "cg3dguru_v2", "cg3dmaya_v2"}


class MigrationGuardTests(unittest.TestCase):
    def test_runtime_source_does_not_import_pymel(self):
        imports = []
        for path in SRC_ROOT.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    names = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom):
                    names = [node.module or ""]
                else:
                    continue
                if any(name == "pymel" or name.startswith("pymel.") for name in names):
                    imports.append(path.relative_to(REPO_ROOT).as_posix())

        self.assertEqual([], imports)

    def test_package_metadata_does_not_install_pymel(self):
        metadata = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8").lower()
        self.assertNotIn('"pymel', metadata)
        self.assertNotIn("'pymel", metadata)

    def test_runtime_source_has_no_v2_package_references(self):
        references = []
        for path in SRC_ROOT.rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            names = sorted(name for name in OLD_PACKAGE_NAMES if name in text)
            if names:
                references.append((path.relative_to(REPO_ROOT).as_posix(), names))

        self.assertEqual([], references)


if __name__ == "__main__":
    unittest.main()
