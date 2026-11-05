"""Unit tests for set_property device → config entry resolution."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

_HELPER = (
    Path(__file__).resolve().parents[1]
    / "custom_components"
    / "dreame_fan"
    / "device_entry.py"
)
_SPEC = importlib.util.spec_from_file_location("dreame_fan_device_entry", _HELPER)
assert _SPEC and _SPEC.loader
_MOD = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MOD)
config_entry_ids_for_device = _MOD.config_entry_ids_for_device


def test_single_device_prefers_config_entry_id() -> None:
    """HA 2026.10+ DeviceEntry: use config_entry_id, ignore deprecated set."""
    device = SimpleNamespace(
        config_entry_id="entry-new",
        config_entries={"entry-old-should-not-win", "other"},
    )
    assert config_entry_ids_for_device(device) == ["entry-new"]


def test_single_device_falls_back_to_config_entries() -> None:
    """Older HA DeviceEntry without config_entry_id keeps iterating the set."""
    device = SimpleNamespace(config_entries={"only-entry"})
    assert config_entry_ids_for_device(device) == ["only-entry"]


def test_config_entry_id_none_falls_back() -> None:
    """Explicit None on config_entry_id must not be treated as a valid id."""
    device = SimpleNamespace(config_entry_id=None, config_entries={"legacy"})
    assert config_entry_ids_for_device(device) == ["legacy"]
