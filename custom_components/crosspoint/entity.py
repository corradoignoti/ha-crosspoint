"""Base entity for the CrossPoint integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import CrossPointDeviceCoordinator


class CrossPointDeviceEntity(CoordinatorEntity[CrossPointDeviceCoordinator]):
    """An entity attached to the CrossPoint e-reader device."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: CrossPointDeviceCoordinator, key: str) -> None:
        super().__init__(coordinator)
        entry = coordinator.config_entry
        model = entry.runtime_data.model
        status = coordinator.data.status if coordinator.data else {}
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=model.name,
            model=model.name,
            sw_version=status.get("version"),
            configuration_url=f"http://{coordinator.client.host}/",
        )
