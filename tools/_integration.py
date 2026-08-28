"""Load `cloud.py` / `const.py` out of the integration without importing HA.

Putting `custom_components/dreame_fan` on `sys.path` is the obvious way to do
this and it is a trap: the integration ships `select.py` (the HA select
platform), which then shadows the standard library's `select` module. Anything
importing `requests` later — urllib3 does, one level down — pulls in that file
instead and dies on `No module named 'homeassistant'`.

So load the two dependency-free modules by file path instead, and leave
`sys.path` alone.
"""

from __future__ import annotations

import importlib.util
import pathlib
import sys
from types import ModuleType

COMPONENT = (
    pathlib.Path(__file__).resolve().parent.parent / "custom_components" / "dreame_fan"
)


def load(name: str) -> ModuleType:
    """Import `<component>/<name>.py` as a standalone module."""
    path = COMPONENT / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"dreame_fan_{name}", path)
    if (
        spec is None or spec.loader is None
    ):  # pragma: no cover - unreachable in practice
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module
