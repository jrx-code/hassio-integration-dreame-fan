"""Helpers for device registry entry ids across Home Assistant versions."""

from __future__ import annotations


def config_entry_ids_for_device(device) -> list[str]:
    """Return config entry ids for a device registry entry.

    HA 2026.10+ exposes ``config_entry_id`` (one primary entry) and deprecates
    ``config_entries``. Older cores only have ``config_entries``. Prefer the
    new attribute when present so custom integrations avoid the deprecation
    warning logged from 2026.11.
    """
    entry_id = getattr(device, "config_entry_id", None)
    if entry_id:
        return [entry_id]
    return list(device.config_entries)
