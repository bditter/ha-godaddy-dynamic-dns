"""Button platform for GoDaddy Dynamic DNS."""

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DynamicDnsConfigEntry
from .entity import DynamicDnsEntity

BUTTONS = (
    ButtonEntityDescription(
        key="check_now",
        translation_key="check_now",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    ButtonEntityDescription(
        key="force_update",
        translation_key="force_update",
        entity_category=EntityCategory.CONFIG,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DynamicDnsConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up buttons."""
    async_add_entities(
        DynamicDnsButton(entry.runtime_data, description)
        for description in BUTTONS
    )


class DynamicDnsButton(DynamicDnsEntity, ButtonEntity):
    """A dynamic DNS action button."""

    entity_description: ButtonEntityDescription

    def __init__(self, coordinator, description: ButtonEntityDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    async def async_press(self) -> None:
        """Run the selected action."""
        if self.entity_description.key == "force_update":
            await self.coordinator.async_force_update()
        else:
            await self.coordinator.async_request_refresh()
