"""Sensor platform for GoDaddy Dynamic DNS."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DynamicDnsConfigEntry
from .entity import DynamicDnsEntity
from .models import DynamicDnsState


@dataclass(frozen=True, kw_only=True)
class DynamicDnsSensorDescription(SensorEntityDescription):
    """Describe a dynamic DNS sensor."""

    value_fn: Callable[[DynamicDnsState], str | int | datetime | None]


SENSORS = (
    DynamicDnsSensorDescription(
        key="wan_ip",
        translation_key="wan_ip",
        value_fn=lambda state: state.wan_ip,
    ),
    DynamicDnsSensorDescription(
        key="previous_wan_ip",
        translation_key="previous_wan_ip",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda state: state.previous_wan_ip,
    ),
    DynamicDnsSensorDescription(
        key="dns_record_ip",
        translation_key="dns_record_ip",
        value_fn=lambda state: state.dns_record_ip,
    ),
    DynamicDnsSensorDescription(
        key="last_update_time",
        translation_key="last_update_time",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda state: state.last_update_time,
    ),
    DynamicDnsSensorDescription(
        key="last_update_result",
        translation_key="last_update_result",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda state: state.last_update_result,
    ),
    DynamicDnsSensorDescription(
        key="last_ip_change_time",
        translation_key="last_ip_change_time",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda state: state.last_ip_change_time,
    ),
    DynamicDnsSensorDescription(
        key="records_updated",
        translation_key="records_updated",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda state: state.records_updated,
    ),
    DynamicDnsSensorDescription(
        key="total_updates_performed",
        translation_key="total_updates_performed",
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda state: state.total_updates_performed,
    ),
    DynamicDnsSensorDescription(
        key="public_ip_source",
        translation_key="public_ip_source",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda state: state.public_ip_source,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DynamicDnsConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensors."""
    async_add_entities(
        DynamicDnsSensor(entry.runtime_data, description)
        for description in SENSORS
    )


class DynamicDnsSensor(DynamicDnsEntity, SensorEntity):
    """A dynamic DNS sensor."""

    entity_description: DynamicDnsSensorDescription

    def __init__(
        self,
        coordinator,
        description: DynamicDnsSensorDescription,
    ) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self):
        """Return the current sensor value."""
        return self.entity_description.value_fn(self.coordinator.data)
