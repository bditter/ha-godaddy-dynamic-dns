"""GoDaddy Dynamic DNS integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import DynamicDnsApi
from .const import (
    CONF_API_KEY,
    CONF_API_SECRET,
    CONF_FIREWALL_BASE_URL,
    CONF_FIREWALL_CA_PATH,
    CONF_FIREWALL_INTERFACE,
    CONF_GODADDY_API_URL,
    CONF_VERIFY_SSL,
    PLATFORMS,
)
from .coordinator import DynamicDnsCoordinator

type DynamicDnsConfigEntry = ConfigEntry[DynamicDnsCoordinator]


async def async_setup_entry(
    hass: HomeAssistant, entry: DynamicDnsConfigEntry
) -> bool:
    """Set up GoDaddy Dynamic DNS from a config entry."""
    api = DynamicDnsApi(
        async_get_clientsession(hass),
        firewall_base_url=entry.data[CONF_FIREWALL_BASE_URL],
        firewall_ca_path=entry.data.get(CONF_FIREWALL_CA_PATH, ""),
        firewall_username=entry.data[CONF_USERNAME],
        firewall_password=entry.data[CONF_PASSWORD],
        firewall_interface=entry.data[CONF_FIREWALL_INTERFACE],
        verify_ssl=entry.data[CONF_VERIFY_SSL],
        godaddy_api_url=entry.data[CONF_GODADDY_API_URL],
        api_key=entry.data[CONF_API_KEY],
        api_secret=entry.data[CONF_API_SECRET],
    )
    coordinator = DynamicDnsCoordinator(hass, entry, api)
    await coordinator.async_load_state()
    if coordinator.state.godaddy_api_available is None:
        coordinator.state.godaddy_api_available = True
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: DynamicDnsConfigEntry
) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
