"""Blade speed selector for the Dreame MF10."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DreameFanConfigEntry
from .const import BLADE_SPEED_VALUES, BLADE_SPEEDS, PROP_BLADE_SPEED
from .coordinator import DreameFanCoordinator
from .entity import DreameFanEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DreameFanConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities([DreameFanBladeSpeed(entry.runtime_data)])


class DreameFanBladeSpeed(DreameFanEntity, SelectEntity):
    """How fast the blades travel, property 6.30.

    Distinct from the 1-10 airflow speed: this is the app's "Prędkość łopatek",
    standard or fast.
    """

    _attr_entity_category = EntityCategory.CONFIG
    _attr_translation_key = "blade_speed"
    _attr_options = list(BLADE_SPEED_VALUES)

    def __init__(self, coordinator: DreameFanCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.did}_blade_speed"

    @property
    def current_option(self) -> str | None:
        raw = self.coordinator.data.get(PROP_BLADE_SPEED)
        try:
            return BLADE_SPEEDS.get(int(raw))
        except (TypeError, ValueError):
            return None

    async def async_select_option(self, option: str) -> None:
        if option not in BLADE_SPEED_VALUES:
            raise HomeAssistantError(f"Unknown blade speed {option}")
        await self.coordinator.async_set_property(
            PROP_BLADE_SPEED, BLADE_SPEED_VALUES[option]
        )
