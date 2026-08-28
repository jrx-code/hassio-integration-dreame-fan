"""Sleep timer for the Dreame MF10."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.const import EntityCategory, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DreameFanConfigEntry
from .const import PROP_TIMER_HOURS
from .coordinator import DreameFanCoordinator
from .entity import DreameFanEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DreameFanConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities([DreameFanTimer(entry.runtime_data)])


class DreameFanTimer(DreameFanEntity, NumberEntity):
    """Sleep timer in hours, property 6.8. Zero is off.

    The upper bound has not been checked against the device - the app was only
    ever stepped as far as 1 hour - so 12 is a placeholder. Verify it by
    stepping the app's timer to its maximum and reading 6.8 back.
    """

    _attr_entity_category = EntityCategory.CONFIG
    _attr_translation_key = "timer"
    _attr_native_min_value = 0
    _attr_native_max_value = 12
    _attr_native_step = 1
    _attr_native_unit_of_measurement = UnitOfTime.HOURS
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator: DreameFanCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.did}_timer"

    @property
    def native_value(self) -> float | None:
        raw = self.coordinator.data.get(PROP_TIMER_HOURS)
        try:
            return float(raw)
        except (TypeError, ValueError):
            return None

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_set_property(PROP_TIMER_HOURS, int(value))
