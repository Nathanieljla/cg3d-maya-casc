"""dispatcher.py - Wing Carrier dispatcher for Antigravity IDE

This script is the Antigravity equivalent of the Wing IDE dispatcher. It is
invoked by a VS Code task (see antigravity_action.md) which passes the active
file path as a command-line argument, since Antigravity has no Python API for
reading the active editor state directly.

Usage:
    python dispatcher.py <file_path>

Where <file_path> is the absolute path to the file currently open in the
Antigravity editor, typically provided via the ${file} VS Code task variable.
"""

import sys
import os
from pathlib import Path


# ---------------------------------------------------------------------------
# Bootstrap: add the wingcarrier package to sys.path so we can import pigeons.
# ---------------------------------------------------------------------------
# This script lives at:  3rdparty/antigravity/dispatcher.py
# pigeons lives at:      ../../pigeons/  (relative to this file)
_this_dir = os.path.dirname(os.path.abspath(__file__))           # .../3rdparty/antigravity
_3rdparty_dir = os.path.dirname(_this_dir)                        # .../3rdparty
_wingcarrier_dir = os.path.dirname(_3rdparty_dir)                 # .../wingcarrier (src root)
_src_dir = os.path.dirname(_wingcarrier_dir)                      # .../src

if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

import pigeons
import pigeons.maya
import pigeons.cascadeur

sys.path.remove(_src_dir)


# ---------------------------------------------------------------------------
# Carrier registry – mirrors the CARRIERS list in wing/wing_ide_hotkeys/dispatcher.py
# ---------------------------------------------------------------------------
CARRIERS = [
    pigeons.maya.MayaPigeon(),
    pigeons.cascadeur.CascadeurPigeon(),
]


def _get_module_info(file_path: str):
    """Resolve the Python module namespace for *file_path* by walking parent
    directories and checking for ``__init__.py`` files.

    This mirrors the ``_get_module_info()`` function in the Wing IDE
    dispatcher.  The walk stops as soon as a parent directory without
    ``__init__.py`` is encountered (meaning the package boundary has been
    reached).

    Args:
        file_path (str): Absolute path to the Python source file.

    Returns:
        tuple[str, str]: ``(module_name, file_path)`` where *module_name* is
        the dotted import path (e.g. ``"mypkg.subpkg.mymodule"``) and
        *file_path* is the original path with backslashes replaced by forward
        slashes.
    """

    def _add_parent_module(name, path):
        """Attempt to prepend the parent package name to *name*.

        Returns:
            tuple[bool, str, Path]: (found, updated_name, updated_path)
        """
        parent_init = os.path.join(path.parent, '__init__.py')
        if os.path.exists(parent_init):
            path = path.parent
            name = os.path.basename(path) + '.' + name
            return True, name, path
        return False, name, path

    name = os.path.basename(file_path).split('.')[0]
    path = Path(file_path)

    loop = True
    count = 0
    while loop and count < 20:
        count += 1
        loop, name, path = _add_parent_module(name, path)

    # Special case: executing an __init__.py directly refers to the package.
    if name.endswith('.__init__'):
        name = name.removesuffix('.__init__')

    return name, file_path.replace('\\', '/')


def _get_doc_type(file_path: str) -> str:
    """Infer a MIME-like document type from the file extension.

    Args:
        file_path (str): Path to the file.

    Returns:
        str: ``"python"`` for ``.py`` files, ``"mel"`` for ``.mel`` files,
        or an empty string for anything else.
    """
    ext = os.path.splitext(file_path)[1].lower()
    if ext == '.py':
        return 'python'
    if ext == '.mel':
        return 'mel'
    return ''


def _find_best_carrier():
    """Return the first carrier that reports it can currently dispatch.

    Returns:
        Pigeon | None: A ready carrier pigeon, or None if none are available.
    """
    for carrier in CARRIERS:
        if carrier.can_dispatch():
            return carrier
    return None


def dispatch(file_path: str, highlighted_text: str = ''):
    """Collect document metadata and send it to the best available carrier.

    This is the Antigravity equivalent of ``dispatch_carrier()`` in the Wing
    IDE dispatcher.  Because Antigravity (VS Code) has no Python API to read
    selected text from the editor, *highlighted_text* is accepted as an
    optional parameter but will typically be empty when invoked via a VS Code
    task.

    Args:
        file_path (str): Absolute path to the active document.
        highlighted_text (str): Currently selected text, if any. Defaults to
            an empty string.
    """
    carrier = _find_best_carrier()
    if carrier is None:
        print('wing-carrier [antigravity]: No application available to dispatch to!')
        return

    module_path, norm_file_path = _get_module_info(file_path)
    doc_type = _get_doc_type(file_path)

    print('wing-carrier [antigravity]: module_path={!r}  file_path={!r}  doc_type={!r}'.format(
        module_path, norm_file_path, doc_type))

    carrier.send(highlighted_text, module_path, norm_file_path, doc_type)


# ---------------------------------------------------------------------------
# Entry point – called by the VS Code task
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python dispatcher.py <file_path> [highlighted_text]')
        sys.exit(1)

    _file_path = sys.argv[1]
    _highlighted_text = sys.argv[2] if len(sys.argv) > 2 else ''

    dispatch(_file_path, _highlighted_text)
