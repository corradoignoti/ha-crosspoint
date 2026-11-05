"""Base entities for the CrossPoint integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import CrossPointDeviceCoordinator
from .library import LibraryCoordinator

if TYPE_CHECKING:
    from . import CrossPointConfigEntry


def device_info(entry: CrossPointConfigEntry) -> DeviceInfo:
    """Device registry info shared by all entities of one e-reader."""
    runtime = entry.runtime_data
    data = runtime.coordinator.data
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name=runtime.model.name,
        model=runtime.model.name,
        sw_version=(data.status.get("version") if data else None),
        configuration_url=f"http://{runtime.client.host}/",
    )


class CrossPointDeviceEntity(CoordinatorEntity[CrossPointDeviceCoordinator]):
    """An entity that follows the device reachability coordinator."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: CrossPointDeviceCoordinator, key: str) -> None:
        super().__init__(coordinator)
        entry = coordinator.config_entry
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = device_info(entry)


class CrossPointLibraryEntity(CoordinatorEntity[LibraryCoordinator]):
    """An entity that follows the library scan."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: LibraryCoordinator, key: str) -> None:
        super().__init__(coordinator)
        entry = coordinator.config_entry
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = device_info(entry)
