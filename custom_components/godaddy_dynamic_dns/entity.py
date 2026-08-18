"""Base entity for GoDaddy Dynamic DNS."""

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import DynamicDnsCoordinator
from .helpers import records_from_config


class DynamicDnsEntity(CoordinatorEntity[DynamicDnsCoordinator]):
    """Base coordinator entity."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: DynamicDnsCoordinator, key: str) -> None:
        super().__init__(coordinator)
        first_record = records_from_config(
            coordinator.entry.data.get("target_domain", ""),
            coordinator.entry.data.get("primary_record_type", "A"),
            coordinator.entry.data.get("primary_record_name", ""),
            coordinator.entry.options.get(
                "additional_records",
                coordinator.entry.data.get("additional_records", ""),
            ),
        )[0]
        if first_record.name == "@":
            device_name = first_record.domain
        else:
            device_name = f"{first_record.name}.{first_record.domain}"
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.entry.entry_id)},
            name=f"Dynamic DNS {device_name}",
            manufacturer="Local",
            model="GoDaddy Dynamic DNS",
        )
