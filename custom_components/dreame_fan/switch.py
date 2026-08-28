"""Switches for the Dreame MF10: child lock and the two blades."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DreameFanConfigEntry
from .const import (
    BLADE_LEFT,
    BLADE_RIGHT,
    PROP_BLADES,
    PROP_CHILD_LOCK,
    PROP_DIRECTION_ALTERNATE,
    PROP_DIRECTION_SYNC,
    PROP_KEY_SOUND,
    PROP_LED_DISPLAY,
)
from .coordinator import DreameFanCoordinator
from .entity import DreameFanEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DreameFanConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        [
            DreameFanChildLock(coordinator),
            DreameFanBlade(coordinator, "left", BLADE_LEFT),
            DreameFanBlade(coordinator, "right", BLADE_RIGHT),
            DreameFanFlag(coordinator, "direction_sync", PROP_DIRECTION_SYNC),
            DreameFanFlag(coordinator, "direction_alternate", PROP_DIRECTION_ALTERNATE),
            DreameFanFlag(coordinator, "led_display", PROP_LED_DISPLAY),
            DreameFanFlag(coordinator, "key_sound", PROP_KEY_SOUND),
        ]
    )


class DreameFanChildLock(DreameFanEntity, SwitchEntity):
    """Child lock, property 6.10."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_translation_key = "child_lock"

    def __init__(self, coordinator: DreameFanCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.did}_child_lock"

    @property
    def is_on(self) -> bool | None:
        raw = self.coordinator.data.get(PROP_CHILD_LOCK)
        return None if raw is None else raw != "0"

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_property(PROP_CHILD_LOCK, 1)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_property(PROP_CHILD_LOCK, 0)


class DreameFanBlade(DreameFanEntity, SwitchEntity):
    """One of the two blades.

    Both live in property 2.8 as a bitmask - 1 is the left blade, 2 the right,
    3 both - so switching one has to preserve the other's bit.
    """

    def __init__(
        self, coordinator: DreameFanCoordinator, side: str, bit: int
    ) -> None:
        super().__init__(coordinator)
        self._bit = bit
        self._attr_translation_key = f"blade_{side}"
        self._attr_unique_id = f"{coordinator.did}_blade_{side}"

    def _mask(self) -> int | None:
        raw = self.coordinator.data.get(PROP_BLADES)
        try:
            return int(raw)
        except (TypeError, ValueError):
            return None

    @property
    def is_on(self) -> bool | None:
        mask = self._mask()
        return None if mask is None else bool(mask & self._bit)

    async def _async_apply(self, enable: bool) -> None:
        mask = self._mask()
        if mask is None:
            return
        new = mask | self._bit if enable else mask & ~self._bit
        if new != mask:
            await self.coordinator.async_set_property(PROP_BLADES, new)

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._async_apply(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._async_apply(False)


class DreameFanFlag(DreameFanEntity, SwitchEntity):
    """A plain 0/1 property exposed as a switch.

    The app offers direction sync and alternating direction as alternatives -
    picking one replaces the other in its UI - but the device accepts both set
    at once, and then the app renders a mixed state it cannot produce itself.
    They are independent flags here, which is what the device actually does.
    """

    def __init__(
        self, coordinator: DreameFanCoordinator, key: str, prop: str
    ) -> None:
        super().__init__(coordinator)
        self._prop = prop
        self._attr_translation_key = key
        self._attr_unique_id = f"{coordinator.did}_{key}"

    @property
    def is_on(self) -> bool | None:
        raw = self.coordinator.data.get(self._prop)
        return None if raw is None else raw != "0"

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_property(self._prop, 1)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_property(self._prop, 0)
