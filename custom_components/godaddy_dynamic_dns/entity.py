"""Base entity for GoDaddy Dynamic DNS."""

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import DynamicDnsCoordinator


class DynamicDnsEntity(CoordinatorEntity[DynamicDnsCoordinator]):
    """Base coordinator entity."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: DynamicDnsCoordinator, key: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.entry.entry_id)},
            name=f"Dynamic DNS {coordinator.entry.data['target_domain']}",
            manufacturer="Local",
            model="GoDaddy Dynamic DNS",
        )
