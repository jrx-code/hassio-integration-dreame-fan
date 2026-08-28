"""Polling coordinator for a Dreame fan."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .cloud import DreameAuthError, DreameCloudError, DreameHomeCloud
from .const import (
    DOMAIN,
    PROPERTY_KEYS,
    UPDATE_INTERVAL_SECONDS,
    WRITE_RECONCILE_SECONDS,
)

_LOGGER = logging.getLogger(__name__)


class DreameFanCoordinator(DataUpdateCoordinator[dict[str, str]]):
    """Keeps the cached property values fresh.

    Reads go through the cloud's REST property store rather than the device
    RPC. The RPC path returns wrong values for some keys without reporting an
    error (see cloud.py), so it is used only for writes.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        cloud: DreameHomeCloud,
        did: str,
        device_info: dict,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} {did}",
            update_interval=timedelta(seconds=UPDATE_INTERVAL_SECONDS),
            config_entry=entry,
        )
        self.cloud = cloud
        self.did = did
        self.device_info_raw = device_info
        self.host = device_info.get("bindDomain", "")

    async def _async_update_data(self) -> dict[str, str]:
        try:
            return await self.hass.async_add_executor_job(
                self.cloud.get_properties, self.did, list(PROPERTY_KEYS)
            )
        except DreameAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except DreameCloudError as err:
            raise UpdateFailed(str(err)) from err

    async def async_set_property(self, key: str, value: int) -> bool:
        """Write one property, applying an acknowledged write optimistically.

        Refreshing straight after a write reads a stale value: the cloud's
        cached view trails the device by tens of seconds. So a write the device
        acknowledged is reflected immediately and reconciled by a later poll,
        which will correct the state if the device did something else with it.
        """
        siid, piid = (int(part) for part in key.split("."))
        result = await self.hass.async_add_executor_job(
            self.cloud.set_property, self.did, self.host, siid, piid, value
        )
        if result:
            self.async_set_updated_data({**(self.data or {}), key: str(value)})
            async_call_later(self.hass, WRITE_RECONCILE_SECONDS, self._async_reconcile)
        return result

    @callback
    def _async_reconcile(self, _now) -> None:
        """Re-read after a write, once the cloud has caught up."""
        self.hass.async_create_task(self.async_request_refresh())
