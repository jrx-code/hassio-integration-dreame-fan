"""Diagnostics for the Dreame Fan integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant

from . import DreameFanConfigEntry

TO_REDACT = {CONF_USERNAME, CONF_PASSWORD, "mac", "sn", "masterUid", "ssid"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: DreameFanConfigEntry
) -> dict[str, Any]:
    """Return the raw property map, which is the useful part for this device."""
    coordinator = entry.runtime_data
    return {
        "entry": async_redact_data(dict(entry.data), TO_REDACT),
        "device": async_redact_data(coordinator.device_info_raw, TO_REDACT),
        "properties": coordinator.data,
    }
