"""Sensors for the CrossPoint integration."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import SIGNAL_STRENGTH_DECIBELS_MILLIWATT, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import CrossPointConfigEntry
from .entity import CrossPointDeviceEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: CrossPointConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up CrossPoint sensors."""
    async_add_entities([CrossPointSignalSensor(entry.runtime_data.coordinator)])


class CrossPointSignalSensor(CrossPointDeviceEntity, SensorEntity):
    """Wi-Fi signal strength reported by the e-reader."""

    _attr_device_class = SensorDeviceClass.SIGNAL_STRENGTH
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = SIGNAL_STRENGTH_DECIBELS_MILLIWATT
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False
    _attr_translation_key = "rssi"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "rssi")

    @property
    def available(self) -> bool:
        """Only meaningful while the device is online."""
        return super().available and self.coordinator.online

    @property
    def native_value(self) -> int | None:
        """Return the RSSI in dBm."""
        value = self.coordinator.data.status.get("rssi")
        return int(value) if isinstance(value, (int, float)) else None
