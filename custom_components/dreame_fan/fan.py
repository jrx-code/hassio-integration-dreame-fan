"""Fan entity for the Dreame MF10."""

from __future__ import annotations

import math
from typing import Any

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util.percentage import (
    percentage_to_ranged_value,
    ranged_value_to_percentage,
)

from . import DreameFanConfigEntry
from .const import (
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


class DreameFan(DreameFanEntity, FanEntity):
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
        speed = self._value(PROP_SPEED)
        if speed is None:
            return None
        if not self.is_on:
            return 0
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
        await self.coordinator.async_set_property(PROP_SPEED, speed)

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        if preset_mode not in MODE_VALUES:
            raise HomeAssistantError(f"Unknown mode {preset_mode}")
        # Selecting a mode also moves the speed: night drops it to 1, natural to
        # 2, strong to 10. Auto varies it - observed at both 3 and 5.
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
