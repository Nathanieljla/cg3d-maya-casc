from __future__ import annotations

import contextlib
import importlib.util
import pathlib
import sys
import types


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src" / "cg3dcasc"
MAYA_MENU_ROOT = SRC_ROOT / "menu"
CASCADEUR_SITE_ROOT = SRC_ROOT / "casc-site"
CASCADEUR_COMMAND_ROOT = CASCADEUR_SITE_ROOT / "cg3dcmds"


def make_module(name, **attributes):
    module = types.ModuleType(name)
    for attribute, value in attributes.items():
        setattr(module, attribute, value)
    return module


def make_package(name, path=None, **attributes):
    module = make_module(name, **attributes)
    module.__path__ = [] if path is None else [str(path)]
    return module


@contextlib.contextmanager
def installed_modules(modules):
    missing = object()
    previous = {name: sys.modules.get(name, missing) for name in modules}
    sys.modules.update(modules)
    try:
        yield
    finally:
        for name, value in previous.items():
            if value is missing:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = value


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError("Cannot load {} from {}".format(name, path))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(name, None)
        raise
    return module


class CallRecorder:
    def __init__(self, result=None):
        self.calls = []
        self.result = result

    def __call__(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return self.result
