"""Sensors for the Dreame MF10.

Named sensors for the properties whose meaning is established, plus one raw
diagnostic sensor per property that is still unidentified. The raw ones are the
tool for naming the rest: watch which entity moves while the fan is operated one
control at a time, then promote it here.
"""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DreameFanConfigEntry
from .const import (
    CONFIRMED_PROPERTIES,
    KNOWN_WRITABLE,
    PROP_FILTER_DAYS,
    PROP_FILTER_PERCENT,
    PROP_TEMPERATURE,
    PROPERTY_KEYS,
)
from .coordinator import DreameFanCoordinator
from .entity import DreameFanEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DreameFanConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    entities: list[SensorEntity] = [
        DreameFanTemperature(coordinator),
        DreameFanFilterDays(coordinator),
        DreameFanFilterPercent(coordinator),
    ]
    entities.extend(
        DreameFanPropertySensor(coordinator, key)
        for key in PROPERTY_KEYS
        if key not in CONFIRMED_PROPERTIES
    )
    async_add_entities(entities)


class DreameFanTemperature(DreameFanEntity, SensorEntity):
    """Ambient temperature, property 3.2.

    3.3 always carries the same number and moves with it; nothing observed so
    far tells the two apart, so only one is exposed as a named sensor and 3.3
    stays available as a raw property if that ever changes.
    """

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_translation_key = "temperature"

    def __init__(self, coordinator: DreameFanCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.did}_temperature"

    @property
    def native_value(self) -> int | None:
        raw = self.coordinator.data.get(PROP_TEMPERATURE)
        try:
            return int(raw)
        except (TypeError, ValueError):
            return None


class DreameFanFilterPercent(DreameFanEntity, SensorEntity):
    """Pre-filter life left, property 4.7. The app shows it as a percentage."""

    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "filter_percent"

    def __init__(self, coordinator: DreameFanCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.did}_filter_percent"

    @property
    def native_value(self) -> int | None:
        raw = self.coordinator.data.get(PROP_FILTER_PERCENT)
        try:
            return int(raw)
        except (TypeError, ValueError):
            return None


class DreameFanFilterDays(DreameFanEntity, SensorEntity):
    """Days until the pre-filter needs cleaning, property 4.8.

    The app words it as "Szac. pozostało N dni do czyszczenia" - cleaning, not
    replacement.
    """

    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTime.DAYS
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "filter_days"

    def __init__(self, coordinator: DreameFanCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.did}_filter_days"

    @property
    def native_value(self) -> int | None:
        raw = self.coordinator.data.get(PROP_FILTER_DAYS)
        try:
            return int(raw)
        except (TypeError, ValueError):
            return None


class DreameFanPropertySensor(DreameFanEntity, SensorEntity):
    """One still-unidentified MIoT property, shown raw.

    Disabled by default: these exist to identify the remaining properties, not
    for everyday use, and eleven nameless numbers would only clutter a dashboard.
    Enable the ones you want in the entity registry, watch which moves while you
    operate the fan, and report what you find.
    """

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: DreameFanCoordinator, key: str) -> None:
        super().__init__(coordinator)
        self._key = key
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
