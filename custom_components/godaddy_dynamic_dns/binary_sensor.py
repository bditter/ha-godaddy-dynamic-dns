"""Binary sensor platform for GoDaddy Dynamic DNS."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DynamicDnsConfigEntry
from .entity import DynamicDnsEntity
from .models import DynamicDnsState


@dataclass(frozen=True, kw_only=True)
class DynamicDnsBinaryDescription(BinarySensorEntityDescription):
    """Describe a dynamic DNS binary sensor."""

    value_fn: Callable[[DynamicDnsState], bool | None]


BINARY_SENSORS = (
    DynamicDnsBinaryDescription(
        key="dns_in_sync",
        translation_key="dns_in_sync",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        value_fn=lambda state: state.dns_in_sync,
    ),
    DynamicDnsBinaryDescription(
        key="internet_available",
        translation_key="internet_available",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        value_fn=lambda state: state.internet_available,
    ),
    DynamicDnsBinaryDescription(
        key="firewall_available",
        translation_key="firewall_available",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda state: state.firewall_available,
    ),
    DynamicDnsBinaryDescription(
        key="godaddy_api_available",
        translation_key="godaddy_api_available",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda state: state.godaddy_api_available,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DynamicDnsConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up binary sensors."""
    async_add_entities(
        DynamicDnsBinarySensor(entry.runtime_data, description)
        for description in BINARY_SENSORS
    )


class DynamicDnsBinarySensor(DynamicDnsEntity, BinarySensorEntity):
    """A dynamic DNS binary sensor."""

    entity_description: DynamicDnsBinaryDescription

    def __init__(self, coordinator, description: DynamicDnsBinaryDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        """Return the binary state."""
        return self.entity_description.value_fn(self.coordinator.data)
