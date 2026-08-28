"""Read-only flags for the Dreame MF10."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DreameFanConfigEntry
from .const import PROP_MONITORING
from .coordinator import DreameFanCoordinator
from .entity import DreameFanEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DreameFanConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities([DreameFanMonitoring(entry.runtime_data)])


class DreameFanMonitoring(DreameFanEntity, BinarySensorEntity):
    """Continuous monitoring, property 2.15.

    A binary sensor rather than a switch on purpose: the setting is toggleable
    in the app, but the cloud property API answers 80001 to every write, the
    same as it does for power. Exposing it as a switch would offer a control
    that cannot work.
    """

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "monitoring"

    def __init__(self, coordinator: DreameFanCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.did}_monitoring"

    @property
    def is_on(self) -> bool | None:
        raw = self.coordinator.data.get(PROP_MONITORING)
        return None if raw is None else raw != "0"
