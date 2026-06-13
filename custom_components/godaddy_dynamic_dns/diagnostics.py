"""Diagnostics for GoDaddy Dynamic DNS."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from . import DynamicDnsConfigEntry
from .const import CONF_API_KEY, CONF_API_SECRET

TO_REDACT = {
    CONF_API_KEY,
    CONF_API_SECRET,
    "password",
    "username",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: DynamicDnsConfigEntry
) -> dict[str, Any]:
    """Return redacted config and coordinator state."""
    return {
        "config": async_redact_data(dict(entry.data), TO_REDACT),
        "options": dict(entry.options),
        "state": entry.runtime_data.state.to_store(),
    }
