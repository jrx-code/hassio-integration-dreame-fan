"""The Dreame Fan integration."""

from __future__ import annotations

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers import device_registry as dr

from .cloud import DreameAuthError, DreameCloudError, DreameHomeCloud
from .const import (
    ATTR_PROPERTY,
    ATTR_VALUE,
    CONF_COUNTRY,
    CONF_DID,
    DEFAULT_COUNTRY,
    DOMAIN,
    SERVICE_SET_PROPERTY,
)
from .coordinator import DreameFanCoordinator

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.FAN,
    Platform.SELECT,
    Platform.NUMBER,
    Platform.SENSOR,
    Platform.SWITCH,
]

SET_PROPERTY_SCHEMA = vol.Schema(
    {
        vol.Required("device_id"): vol.All(cv.ensure_list, [cv.string]),
        vol.Required(ATTR_PROPERTY): cv.matches_regex(r"^\d+\.\d+$"),
        vol.Required(ATTR_VALUE): vol.Coerce(int),
    }
)

type DreameFanConfigEntry = ConfigEntry[DreameFanCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: DreameFanConfigEntry) -> bool:
    """Set up a Dreame fan from a config entry."""
    cloud = DreameHomeCloud(
        entry.data[CONF_USERNAME],
        entry.data[CONF_PASSWORD],
        entry.data.get(CONF_COUNTRY, DEFAULT_COUNTRY),
    )
    did = entry.data[CONF_DID]

    try:
        await hass.async_add_executor_job(cloud.login)
        device_info = await hass.async_add_executor_job(cloud.get_device_info, did)
        # device/info returns sn as null; the serial only appears in the device
        # list, so pull it from there when the info call did not carry one.
        if not device_info.get("sn"):
            devices = await hass.async_add_executor_job(cloud.get_devices)
            for device in devices:
                if str(device.get("did")) == str(did) and device.get("sn"):
                    device_info["sn"] = device["sn"]
                    break
    except DreameAuthError as err:
        raise ConfigEntryAuthFailed(str(err)) from err
    except DreameCloudError as err:
        raise ConfigEntryNotReady(str(err)) from err

    coordinator = DreameFanCoordinator(hass, entry, cloud, did, device_info)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    _async_register_services(hass)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: DreameFanConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


def _async_register_services(hass: HomeAssistant) -> None:
    """Register the raw property write service, once."""
    if hass.services.has_service(DOMAIN, SERVICE_SET_PROPERTY):
        return

    async def handle_set_property(call: ServiceCall) -> None:
        registry = dr.async_get(hass)
        targeted = False

        for device_id in call.data["device_id"]:
            device = registry.async_get(device_id)
            if device is None:
                raise ValueError(f"Unknown device {device_id}")

            for entry_id in device.config_entries:
                entry = hass.config_entries.async_get_entry(entry_id)
                if entry and entry.domain == DOMAIN and hasattr(entry, "runtime_data"):
                    await entry.runtime_data.async_set_property(
                        call.data[ATTR_PROPERTY], call.data[ATTR_VALUE]
                    )
                    targeted = True
                    break

        if not targeted:
            raise ValueError("No Dreame fan among the targeted devices")

    hass.services.async_register(
        DOMAIN, SERVICE_SET_PROPERTY, handle_set_property, schema=SET_PROPERTY_SCHEMA
    )
