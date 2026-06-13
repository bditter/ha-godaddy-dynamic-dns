"""Update coordinator for GoDaddy Dynamic DNS."""

from __future__ import annotations

import asyncio
from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .api import DynamicDnsApi, DynamicDnsApiError, DynamicDnsAuthError
from .const import (
    CONF_ADDITIONAL_RECORDS,
    CONF_PRIMARY_RECORD_NAME,
    CONF_PRIMARY_RECORD_TYPE,
    CONF_SCAN_INTERVAL,
    CONF_TARGET_DOMAIN,
    CONF_TTL,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TTL,
    DOMAIN,
    STORE_KEY_PREFIX,
    STORE_VERSION,
)
from .helpers import all_records
from .models import DynamicDnsState, RecordSpec

_LOGGER = logging.getLogger(__name__)


class DynamicDnsCoordinator(DataUpdateCoordinator[DynamicDnsState]):
    """Coordinate public IP checks and conditional DNS updates."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        api: DynamicDnsApi,
    ) -> None:
        self.entry = entry
        self.api = api
        self.state = DynamicDnsState()
        self._lock = asyncio.Lock()
        self._store: Store[dict] = Store(
            hass, STORE_VERSION, f"{STORE_KEY_PREFIX}.{entry.entry_id}"
        )
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(
                seconds=entry.options.get(
                    CONF_SCAN_INTERVAL,
                    entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                )
            ),
        )

    async def async_load_state(self) -> None:
        """Load counters and history without writing to the SD card each poll."""
        self.state = DynamicDnsState.from_store(await self._store.async_load())

    async def _async_update_data(self) -> DynamicDnsState:
        return await self._async_check(force=False)

    async def async_force_update(self) -> None:
        """Update all configured records even when DNS is already in sync."""
        await self._async_check(force=True)
        self.async_set_updated_data(self.state)

    async def _async_check(self, *, force: bool) -> DynamicDnsState:
        async with self._lock:
            now = dt_util.utcnow()
            self.state.last_check_time = now
            domain = self.entry.data[CONF_TARGET_DOMAIN]
            primary_name = self.entry.data[CONF_PRIMARY_RECORD_NAME]

            state_changed = False
            internet_task = asyncio.create_task(self.api.async_check_internet())
            try:
                selected_ip = await self.api.async_get_firewall_ip()
            except DynamicDnsApiError:
                self.state.internet_available = await internet_task
                self.state.firewall_available = False
                self.state.last_update_result = "Sophos WAN IP unavailable"
                return self.state

            self.state.internet_available = await internet_task
            self.state.firewall_available = True
            self.state.public_ip_source = "Sophos firewall"
            if selected_ip != self.state.wan_ip:
                if self.state.wan_ip:
                    self.state.previous_wan_ip = self.state.wan_ip
                self.state.wan_ip = selected_ip
                self.state.last_ip_change_time = now
                self.state.pending_ip = selected_ip
                self.state.dns_in_sync = False
                state_changed = True

            if force:
                state_changed = (
                    await self._async_update_records(selected_ip, now) or state_changed
                )
                if self.state.godaddy_api_available:
                    self.state.pending_ip = None
                    self.state.dns_record_ip = selected_ip
                    self.state.dns_addresses = [selected_ip]
                    self.state.dns_in_sync = True
            elif self.state.pending_ip != selected_ip:
                self.state.last_update_result = "WAN IP unchanged"
            else:
                try:
                    godaddy_addresses = await self.api.async_get_record_addresses(
                        domain,
                        self.entry.data[CONF_PRIMARY_RECORD_TYPE],
                        primary_name,
                    )
                except DynamicDnsApiError:
                    self.state.godaddy_api_available = False
                    self.state.last_update_result = (
                        "Could not read the primary record from GoDaddy; retry pending"
                    )
                else:
                    self.state.godaddy_api_available = True
                    self.state.dns_addresses = godaddy_addresses
                    self.state.dns_record_ip = godaddy_addresses[0]
                    self.state.dns_in_sync = selected_ip in godaddy_addresses
                    if self.state.dns_in_sync:
                        self.state.last_update_result = "No update needed"
                        self.state.pending_ip = None
                        state_changed = True
                    else:
                        state_changed = (
                            await self._async_update_records(selected_ip, now)
                            or state_changed
                        )
                        if self.state.godaddy_api_available:
                            self.state.pending_ip = None
                            self.state.dns_record_ip = selected_ip
                            self.state.dns_addresses = [selected_ip]
                            self.state.dns_in_sync = True
            if state_changed:
                await self._store.async_save(self.state.to_store())
            return self.state

    async def _async_update_records(self, ip_address: str, now) -> bool:
        """Update every configured GoDaddy record."""
        records = self._records()
        updated = 0
        ttl = self.entry.options.get(
            CONF_TTL, self.entry.data.get(CONF_TTL, DEFAULT_TTL)
        )
        try:
            for record in records:
                await self.api.async_replace_record(
                    self.entry.data[CONF_TARGET_DOMAIN],
                    record.record_type,
                    record.name,
                    ip_address,
                    ttl,
                )
                updated += 1
        except DynamicDnsAuthError:
            self.state.godaddy_api_available = False
            self.state.records_updated = updated
            self.state.last_update_result = (
                f"Authentication failed after {updated} record(s)"
            )
            return True
        except DynamicDnsApiError as err:
            self.state.godaddy_api_available = False
            self.state.records_updated = updated
            self.state.last_update_result = (
                f"Update failed after {updated} record(s): {err}"
            )
            return True

        self.state.godaddy_api_available = True
        self.state.records_updated = updated
        self.state.total_updates_performed += 1
        self.state.last_update_time = now
        self.state.last_update_result = f"Updated {updated} record(s)"
        self.state.pending_ip = ip_address
        return True

    def _records(self) -> list[RecordSpec]:
        return all_records(
            self.entry.data[CONF_PRIMARY_RECORD_TYPE],
            self.entry.data[CONF_PRIMARY_RECORD_NAME],
            self.entry.options.get(
                CONF_ADDITIONAL_RECORDS,
                self.entry.data.get(CONF_ADDITIONAL_RECORDS, ""),
            ),
        )
