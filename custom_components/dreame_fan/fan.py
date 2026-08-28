"""Fan entity for the Dreame MF10."""

from __future__ import annotations

import math
from typing import Any

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util.percentage import (
    percentage_to_ranged_value,
    ranged_value_to_percentage,
)

from . import DreameFanConfigEntry
from .const import (
    MODE_SPEED_WANDERS,
    MODE_VALUES,
    MODES,
    POWER_ON,
    PROP_MODE,
    PROP_OSCILLATION,
    PROP_POWER,
    PROP_SPEED,
    SPEED_MAX,
    SPEED_MIN,
)
from .coordinator import DreameFanCoordinator
from .entity import DreameFanEntity

SPEED_RANGE = (SPEED_MIN, SPEED_MAX)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DreameFanConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities([DreameFan(entry.runtime_data)])


class DreameFan(DreameFanEntity, FanEntity, RestoreEntity):
    """The fan itself.

    Power is deliberately not wired up. The device reports its power state in
    2.1 but refuses every write to it, including the value the app itself
    produces, while every other control accepts writes. Rather than pretend,
    turn_on and turn_off say so.
    """

    _attr_name = None
    _attr_supported_features = (
        FanEntityFeature.SET_SPEED
        | FanEntityFeature.OSCILLATE
        | FanEntityFeature.PRESET_MODE
    )
    _attr_preset_modes = list(MODE_VALUES)
    _attr_speed_count = SPEED_MAX

    def __init__(self, coordinator: DreameFanCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.did}_fan"
        # The value `percentage` reports while the fan is varying its own
        # airflow; see there. Seeded from the restored state, then from any
        # mode that holds a steady number, then from the user's own setting.
        self._steady_speed: int | None = None

    async def async_added_to_hass(self) -> None:
        """Carry the held speed across a restart.

        Without this, a Home Assistant that starts while the fan is already in
        natural mode has nothing to hold on to and the slider goes back to
        following the fan's own variation.
        """
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        if last is None:
            return
        try:
            percentage = int(last.attributes["percentage"])
        except (KeyError, TypeError, ValueError):
            return
        if percentage > 0:
            self._steady_speed = math.ceil(
                percentage_to_ranged_value(SPEED_RANGE, percentage)
            )

    def _value(self, key: str) -> int | None:
        raw = self.coordinator.data.get(key)
        try:
            return int(raw)
        except (TypeError, ValueError):
            return None

    @property
    def is_on(self) -> bool | None:
        power = self._value(PROP_POWER)
        return None if power is None else power == POWER_ON

    @property
    def percentage(self) -> int | None:
        """Airflow, held steady while the fan is varying it on purpose.

        2.4 is what the fan is blowing right now, not a stored setpoint. In
        natural mode it walks 0-4 every few seconds by design (measured: 121
        polls, five different values), and a slider that moves on its own every
        poll is a broken control - it fights the user and fills the recorder.
        So in natural mode this reports the last value seen in any other mode,
        and everywhere else it reports the live number, which the mode holds
        steady anyway (strong 10, night 1, auto its own choice, custom exactly
        what was set). `sensor.*_airflow` always carries the live value.
        """
        speed = self._value(PROP_SPEED)
        if speed is None:
            return None
        if not self.is_on:
            # 2.4 freezes at whatever the fan last blew, so it is a fair seed
            # for the held value even though the entity itself reports zero.
            if speed > 0:
                self._steady_speed = speed
            return 0
        if self._value(PROP_MODE) in MODE_SPEED_WANDERS:
            # First sample in natural mode with nothing remembered: freeze on it
            # rather than follow the variation from here on.
            if self._steady_speed is None and speed > 0:
                self._steady_speed = speed
            if self._steady_speed is not None:
                speed = self._steady_speed
        else:
            self._steady_speed = speed
        return ranged_value_to_percentage(SPEED_RANGE, speed)

    @property
    def preset_mode(self) -> str | None:
        mode = self._value(PROP_MODE)
        return MODES.get(mode) if mode is not None else None

    @property
    def oscillating(self) -> bool | None:
        value = self._value(PROP_OSCILLATION)
        return None if value is None else bool(value)

    async def async_set_percentage(self, percentage: int) -> None:
        if percentage == 0:
            raise HomeAssistantError(
                "This fan cannot be switched off over the cloud API. Set a speed "
                "instead, or use the app or the fan's own button."
            )
        if not self.is_on:
            # Verified: the device acknowledges a speed write while off but does
            # not apply it, so reporting success here would be a lie.
            raise HomeAssistantError(
                "The fan is off and ignores speed changes until it is switched on."
            )
        speed = math.ceil(percentage_to_ranged_value(SPEED_RANGE, percentage))
        # Keep the slider where the user put it: the next poll in natural mode
        # would otherwise read back whatever the fan happens to be blowing.
        self._steady_speed = speed
        await self.coordinator.async_set_property(PROP_SPEED, speed)

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        if preset_mode not in MODE_VALUES:
            raise HomeAssistantError(f"Unknown mode {preset_mode}")
        # Selecting a mode also moves 2.4, in the same poll: strong pins it to
        # 10, night to 1, auto picks its own, natural starts varying it, and
        # custom restores the value it had when it was last left.
        await self.coordinator.async_set_property(PROP_MODE, MODE_VALUES[preset_mode])

    async def async_oscillate(self, oscillating: bool) -> None:
        await self.coordinator.async_set_property(
            PROP_OSCILLATION, 1 if oscillating else 0
        )

    async def async_turn_on(self, **kwargs: Any) -> None:
        raise HomeAssistantError(
            "This fan cannot be switched on over the cloud API. It reports its "
            "power state but rejects every write to it; use the app or the "
            "fan's own button."
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        raise HomeAssistantError(
            "This fan cannot be switched off over the cloud API. It reports its "
            "power state but rejects every write to it; use the app or the "
            "fan's own button."
        )
