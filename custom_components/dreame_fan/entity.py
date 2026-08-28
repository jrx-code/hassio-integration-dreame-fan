"""Shared entity base for Dreame fan entities."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import DreameFanCoordinator


class DreameFanEntity(CoordinatorEntity[DreameFanCoordinator]):
    """Base class tying entities to the physical fan."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: DreameFanCoordinator) -> None:
        super().__init__(coordinator)
        raw = coordinator.device_info_raw
        info = raw.get("deviceInfo") or {}
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.did)},
            manufacturer="Dreame",
            model=info.get("displayName") or raw.get("model"),
            model_id=raw.get("model"),
            name=raw.get("customName") or info.get("displayName") or "Dreame Fan",
            sw_version=raw.get("ver"),
            serial_number=raw.get("sn"),
            connections={("mac", raw["mac"])} if raw.get("mac") else set(),
        )
