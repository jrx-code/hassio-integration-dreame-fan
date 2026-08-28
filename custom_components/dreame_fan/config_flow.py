"""Config flow for the Dreame Fan integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME

from .cloud import DreameAuthError, DreameCloudError, DreameHomeCloud
from .const import (
    CONF_COUNTRY,
    CONF_DID,
    COUNTRIES,
    DEFAULT_COUNTRY,
    DOMAIN,
    SUPPORTED_MODELS,
)

ACCOUNT_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Required(CONF_COUNTRY, default=DEFAULT_COUNTRY): vol.In(COUNTRIES),
    }
)


class DreameFanConfigFlow(ConfigFlow, domain=DOMAIN):
    """Ask for the Dreamehome account, then which fan on it to add."""

    VERSION = 1

    def __init__(self) -> None:
        self._account: dict[str, Any] = {}
        self._fans: dict[str, dict] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            cloud = DreameHomeCloud(
                user_input[CONF_USERNAME],
                user_input[CONF_PASSWORD],
                user_input[CONF_COUNTRY],
            )
            try:
                await self.hass.async_add_executor_job(cloud.login)
                devices = await self.hass.async_add_executor_job(cloud.get_devices)
            except DreameAuthError:
                errors["base"] = "invalid_auth"
            except DreameCloudError:
                errors["base"] = "cannot_connect"
            else:
                self._fans = {
                    device["did"]: device
                    for device in devices
                    if device.get("model") in SUPPORTED_MODELS
                }
                if not self._fans:
                    return self.async_abort(reason="no_supported_devices")
                self._account = user_input
                return await self.async_step_device()

        return self.async_show_form(
            step_id="user", data_schema=ACCOUNT_SCHEMA, errors=errors
        )

    async def async_step_device(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            did = user_input[CONF_DID]
            await self.async_set_unique_id(f"{DOMAIN}_{did}")
            self._abort_if_unique_id_configured()

            device = self._fans[did]
            info = device.get("deviceInfo") or {}
            title = device.get("customName") or info.get("displayName") or device["model"]
            return self.async_create_entry(
                title=title, data={**self._account, CONF_DID: did}
            )

        choices = {}
        for did, device in self._fans.items():
            info = device.get("deviceInfo") or {}
            label = device.get("customName") or info.get("displayName") or device["model"]
            choices[did] = f"{label} ({device['model']})"

        return self.async_show_form(
            step_id="device",
            data_schema=vol.Schema({vol.Required(CONF_DID): vol.In(choices)}),
        )
