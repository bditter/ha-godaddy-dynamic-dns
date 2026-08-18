"""Config flow for GoDaddy Dynamic DNS."""

from __future__ import annotations

import asyncio
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithReload,
)
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import (
    DynamicDnsApi,
    DynamicDnsApiError,
    DynamicDnsAuthError,
    DynamicDnsCertificateError,
)
from .const import (
    CONF_ADDITIONAL_RECORDS,
    CONF_API_KEY,
    CONF_API_SECRET,
    CONF_CONFIG_SCHEMA_VERSION,
    CONF_FIREWALL_BASE_URL,
    CONF_FIREWALL_CA_PATH,
    CONF_FIREWALL_INTERFACE,
    CONF_GODADDY_API_URL,
    CONF_PRIMARY_RECORD_NAME,
    CONF_PRIMARY_RECORD_TYPE,
    CONF_SCAN_INTERVAL,
    CONF_TARGET_DOMAIN,
    CONF_TTL,
    CONF_VERIFY_SSL,
    DEFAULT_GODADDY_API_URL,
    DEFAULT_PRIMARY_RECORD_TYPE,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TTL,
    DEFAULT_VERIFY_SSL,
    DOMAIN,
    CONFIG_SCHEMA_FQDN_RECORDS,
)
from .helpers import format_config_records_for_display, parse_fqdn_records


def _text_password() -> selector.TextSelector:
    return selector.TextSelector(
        selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
    )


def _required(
    key: str, defaults: dict[str, Any], fallback: Any | None = None
) -> vol.Required:
    """Create a required field without inserting private setup defaults."""
    if key in defaults:
        return vol.Required(key, default=defaults[key])
    if fallback is not None:
        return vol.Required(key, default=fallback)
    return vol.Required(key)


def _optional(key: str, defaults: dict[str, Any]) -> vol.Optional:
    """Create an optional field populated only when a value already exists."""
    if key in defaults:
        return vol.Optional(key, default=defaults[key])
    return vol.Optional(key)


def _data_schema(defaults: dict[str, Any]) -> vol.Schema:
    """Build the setup/reconfigure schema."""
    return vol.Schema(
        {
            _required(CONF_FIREWALL_BASE_URL, defaults): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.URL)
            ),
            _required(CONF_USERNAME, defaults): selector.TextSelector(),
            _required(CONF_PASSWORD, defaults): _text_password(),
            _required(CONF_FIREWALL_INTERFACE, defaults): selector.TextSelector(),
            _required(
                CONF_VERIFY_SSL, defaults, DEFAULT_VERIFY_SSL
            ): selector.BooleanSelector(),
            _optional(CONF_FIREWALL_CA_PATH, defaults): selector.TextSelector(),
            _required(
                CONF_GODADDY_API_URL, defaults, DEFAULT_GODADDY_API_URL
            ): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.URL)
            ),
            _required(CONF_API_KEY, defaults): _text_password(),
            _required(CONF_API_SECRET, defaults): _text_password(),
            _required(CONF_ADDITIONAL_RECORDS, defaults): selector.TextSelector(
                selector.TextSelectorConfig(multiline=True)
            ),
            _required(
                CONF_SCAN_INTERVAL, defaults, DEFAULT_SCAN_INTERVAL
            ): vol.All(vol.Coerce(int), vol.Range(min=60, max=86400)),
            _required(CONF_TTL, defaults, DEFAULT_TTL): vol.All(
                vol.Coerce(int), vol.Range(min=600, max=86400)
            ),
        }
    )


def _options_schema(defaults: dict[str, Any]) -> vol.Schema:
    """Build the existing-entry maintenance schema."""
    return vol.Schema(
        {
            _required(CONF_FIREWALL_BASE_URL, defaults): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.URL)
            ),
            _required(CONF_USERNAME, defaults): selector.TextSelector(),
            _required(CONF_PASSWORD, defaults): _text_password(),
            _required(CONF_FIREWALL_INTERFACE, defaults): selector.TextSelector(),
            _required(
                CONF_VERIFY_SSL, defaults, DEFAULT_VERIFY_SSL
            ): selector.BooleanSelector(),
            _optional(CONF_FIREWALL_CA_PATH, defaults): selector.TextSelector(),
            _required(
                CONF_GODADDY_API_URL, defaults, DEFAULT_GODADDY_API_URL
            ): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.URL)
            ),
            _required(CONF_API_KEY, defaults): _text_password(),
            _required(CONF_API_SECRET, defaults): _text_password(),
            _required(CONF_ADDITIONAL_RECORDS, defaults): selector.TextSelector(
                selector.TextSelectorConfig(multiline=True)
            ),
            _required(
                CONF_SCAN_INTERVAL, defaults, DEFAULT_SCAN_INTERVAL
            ): vol.All(vol.Coerce(int), vol.Range(min=60, max=86400)),
            _required(CONF_TTL, defaults, DEFAULT_TTL): vol.All(
                vol.Coerce(int), vol.Range(min=600, max=86400)
            ),
        }
    )


def _maintenance_data(
    entry: ConfigEntry, user_input: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Split maintenance form input into config data and options."""
    existing = {**entry.data, **entry.options}
    merged = {**existing, **user_input}
    merged[CONF_CONFIG_SCHEMA_VERSION] = CONFIG_SCHEMA_FQDN_RECORDS

    data_keys = {
        CONF_CONFIG_SCHEMA_VERSION,
        CONF_FIREWALL_BASE_URL,
        CONF_USERNAME,
        CONF_PASSWORD,
        CONF_FIREWALL_INTERFACE,
        CONF_VERIFY_SSL,
        CONF_FIREWALL_CA_PATH,
        CONF_GODADDY_API_URL,
        CONF_API_KEY,
        CONF_API_SECRET,
    }
    option_keys = {CONF_ADDITIONAL_RECORDS, CONF_SCAN_INTERVAL, CONF_TTL}
    return (
        {key: merged[key] for key in data_keys if key in merged},
        {key: merged[key] for key in option_keys if key in merged},
    )


def _first_record_title(records_value: str) -> str:
    """Return a title from the first configured FQDN."""
    record = parse_fqdn_records(records_value)[0]
    if record.name == "@":
        return record.domain
    return f"{record.name}.{record.domain}"


async def _validate_input(hass: HomeAssistant, data: dict[str, Any]) -> None:
    """Validate the firewall, record syntax, and GoDaddy credentials."""
    records = parse_fqdn_records(data.get(CONF_ADDITIONAL_RECORDS, ""))
    primary_record = records[0]
    api = DynamicDnsApi(
        async_get_clientsession(hass),
        firewall_base_url=data[CONF_FIREWALL_BASE_URL],
        firewall_ca_path=data.get(CONF_FIREWALL_CA_PATH, ""),
        firewall_username=data[CONF_USERNAME],
        firewall_password=data[CONF_PASSWORD],
        firewall_interface=data[CONF_FIREWALL_INTERFACE],
        verify_ssl=data[CONF_VERIFY_SSL],
        godaddy_api_url=data[CONF_GODADDY_API_URL],
        api_key=data[CONF_API_KEY],
        api_secret=data[CONF_API_SECRET],
    )
    firewall_result, godaddy_result = await asyncio.gather(
        api.async_get_firewall_ip(),
        api.async_get_record(
            primary_record.domain,
            primary_record.record_type,
            primary_record.name,
        ),
        return_exceptions=True,
    )
    if isinstance(godaddy_result, DynamicDnsAuthError):
        raise godaddy_result
    if isinstance(firewall_result, DynamicDnsCertificateError):
        raise firewall_result
    if isinstance(firewall_result, Exception):
        raise DynamicDnsApiError(str(firewall_result))
    if isinstance(godaddy_result, Exception):
        raise DynamicDnsApiError(str(godaddy_result))


class DynamicDnsConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle setup and reconfiguration."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                await _validate_input(self.hass, user_input)
            except DynamicDnsAuthError:
                errors["base"] = "invalid_auth"
            except DynamicDnsCertificateError:
                errors["base"] = "invalid_firewall_certificate"
            except ValueError:
                errors["base"] = "invalid_records"
            except DynamicDnsApiError:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(
                    _first_record_title(user_input[CONF_ADDITIONAL_RECORDS]).lower()
                )
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=_first_record_title(user_input[CONF_ADDITIONAL_RECORDS]),
                    data={
                        **user_input,
                        CONF_CONFIG_SCHEMA_VERSION: CONFIG_SCHEMA_FQDN_RECORDS,
                        CONF_TARGET_DOMAIN: "",
                        CONF_PRIMARY_RECORD_TYPE: DEFAULT_PRIMARY_RECORD_TYPE,
                        CONF_PRIMARY_RECORD_NAME: "",
                    },
                )
        return self.async_show_form(
            step_id="user",
            data_schema=_data_schema(user_input or {}),
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                await _validate_input(self.hass, user_input)
            except DynamicDnsAuthError:
                errors["base"] = "invalid_auth"
            except DynamicDnsCertificateError:
                errors["base"] = "invalid_firewall_certificate"
            except ValueError:
                errors["base"] = "invalid_records"
            except DynamicDnsApiError:
                errors["base"] = "cannot_connect"
            else:
                return self.async_update_reload_and_abort(
                    entry,
                    unique_id=_first_record_title(
                        user_input[CONF_ADDITIONAL_RECORDS]
                    ).lower(),
                    data={
                        **user_input,
                        CONF_CONFIG_SCHEMA_VERSION: CONFIG_SCHEMA_FQDN_RECORDS,
                        CONF_TARGET_DOMAIN: "",
                        CONF_PRIMARY_RECORD_TYPE: DEFAULT_PRIMARY_RECORD_TYPE,
                        CONF_PRIMARY_RECORD_NAME: "",
                    },
                    title=_first_record_title(user_input[CONF_ADDITIONAL_RECORDS]),
                )
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=_data_schema(user_input or dict(entry.data)),
            errors=errors,
        )

    @staticmethod
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlowWithReload:
        return DynamicDnsOptionsFlow()


class DynamicDnsOptionsFlow(OptionsFlowWithReload):
    """Edit an existing config entry."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            data, options = _maintenance_data(self.config_entry, user_input)
            validation_data = {**data, **options}
            try:
                await _validate_input(self.hass, validation_data)
            except DynamicDnsAuthError:
                errors["base"] = "invalid_auth"
            except DynamicDnsCertificateError:
                errors["base"] = "invalid_firewall_certificate"
            except ValueError:
                errors["base"] = "invalid_records"
            except DynamicDnsApiError:
                errors["base"] = "cannot_connect"
            else:
                self.hass.config_entries.async_update_entry(
                    self.config_entry,
                    data=data,
                    options=options,
                    title=_first_record_title(validation_data[CONF_ADDITIONAL_RECORDS]),
                )
                return self.async_create_entry(data=options)

        defaults = {**self.config_entry.data, **self.config_entry.options}
        defaults[CONF_ADDITIONAL_RECORDS] = format_config_records_for_display(
            defaults.get(CONF_TARGET_DOMAIN, ""),
            defaults.get(CONF_PRIMARY_RECORD_TYPE, DEFAULT_PRIMARY_RECORD_TYPE),
            defaults.get(CONF_PRIMARY_RECORD_NAME, ""),
            defaults.get(CONF_ADDITIONAL_RECORDS, ""),
        )
        return self.async_show_form(
            step_id="init", data_schema=_options_schema(defaults), errors=errors
        )
