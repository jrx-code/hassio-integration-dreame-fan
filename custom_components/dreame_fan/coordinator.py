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
    CONF_SCENE_OFF,
    CONF_SCENE_ON,
    DOMAIN,
    POWER_OFF,
    POWER_ON,
    PROP_POWER,
    PROPERTY_KEYS,
    SCENE_COMMAND_SWITCH,
    SCENE_NAME_OFF,
    SCENE_NAME_ON,
    SCENE_VALUE_OFF,
    SCENE_VALUE_ON,
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
        self.model = device_info.get("model", "")
        info = device_info.get("deviceInfo") or {}
        self.device_name = (
            device_info.get("customName") or info.get("displayName") or self.model or str(did)
        )

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

    # --- power, via scenes ---------------------------------------------------

    async def async_set_power(self, on: bool) -> None:
        """Switch the fan, by running the scene that holds that command.

        The property API refuses 2.1 outright, so the two scenes below are the
        mechanism. They are created once, on first use, and their ids are kept
        in the config entry so later starts are a single call.
        """
        scene_id = await self._async_scene_id(on)
        await self.hass.async_add_executor_job(self.cloud.start_scene, scene_id)
        # The cloud's cached view lags; show the intent and reconcile on a poll.
        self.async_set_updated_data(
            {**(self.data or {}), PROP_POWER: str(POWER_ON if on else POWER_OFF)}
        )
        async_call_later(self.hass, WRITE_RECONCILE_SECONDS, self._async_reconcile)

    async def _async_scene_id(self, on: bool) -> str:
        """The scene for this direction: from the entry, the account, or new."""
        key = CONF_SCENE_ON if on else CONF_SCENE_OFF
        entry = self.config_entry
        stored = entry.data.get(key)
        if stored:
            return stored

        name = (SCENE_NAME_ON if on else SCENE_NAME_OFF).format(name=self.device_name)
        home_id = await self._async_home_id()
        scenes = await self.hass.async_add_executor_job(self.cloud.get_scenes, home_id)
        found = next((s for s in scenes if s.get("sceneName") == name), None)
        if found is None:
            await self.hass.async_add_executor_job(
                self.cloud.create_manual_scene,
                home_id, name, self.did, self.model,
                SCENE_COMMAND_SWITCH,
                SCENE_VALUE_ON if on else SCENE_VALUE_OFF,
                "On" if on else "Off",
            )
            scenes = await self.hass.async_add_executor_job(self.cloud.get_scenes, home_id)
            found = next((s for s in scenes if s.get("sceneName") == name), None)
            if found is None:
                raise DreameCloudError(f"Scene {name!r} was created but is not listed")
            _LOGGER.info("Created Dreame scene %r for power control", name)

        scene_id = str(found["sceneId"])
        self.hass.config_entries.async_update_entry(
            entry, data={**entry.data, key: scene_id}
        )
        return scene_id

    async def _async_home_id(self) -> str:
        """The home holding this device. One account may have several."""
        homes = await self.hass.async_add_executor_job(self.cloud.get_homes)
        if not homes:
            raise DreameCloudError("The account has no home, so it can hold no scenes")
        return str(homes[0]["homeId"])

    @callback
    def _async_reconcile(self, _now) -> None:
        """Re-read after a write, once the cloud has caught up."""
        self.hass.async_create_task(self.async_request_refresh())
