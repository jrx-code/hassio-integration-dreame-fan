"""Raw property sensors for a Dreame fan.

The MF10 has no published MIoT spec and none of its 28 properties have been
identified yet, so every one is exposed as a diagnostic sensor. That is
deliberate: watching which entity moves while the fan is operated from its app
or its buttons is how the properties get named. Once a property's meaning is
established it should graduate to a real entity (fan, switch, number) and drop
off this list.
"""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DreameFanConfigEntry
from .const import CONFIRMED_PROPERTIES, KNOWN_WRITABLE, PROPERTY_KEYS
from .coordinator import DreameFanCoordinator
from .entity import DreameFanEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DreameFanConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up one sensor per known property."""
    coordinator = entry.runtime_data
    async_add_entities(
        DreameFanPropertySensor(coordinator, key)
        for key in PROPERTY_KEYS
        if key not in CONFIRMED_PROPERTIES
    )


class DreameFanPropertySensor(DreameFanEntity, SensorEntity):
    """One unidentified MIoT property, shown raw."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: DreameFanCoordinator, key: str) -> None:
        super().__init__(coordinator)
        self._key = key
        self._attr_translation_key = "property"
        self._attr_translation_placeholders = {"key": key}
        self._attr_name = f"Property {key}"
        self._attr_unique_id = f"{coordinator.did}_prop_{key.replace('.', '_')}"

    @property
    def native_value(self) -> int | str | None:
        raw = self.coordinator.data.get(self._key)
        if raw is None:
            return None
        try:
            return int(raw)
        except (TypeError, ValueError):
            return raw

    @property
    def available(self) -> bool:
        return super().available and self._key in self.coordinator.data

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        siid, piid = self._key.split(".")
        return {
            "siid": int(siid),
            "piid": int(piid),
            "writable": self._key in KNOWN_WRITABLE,
        }
