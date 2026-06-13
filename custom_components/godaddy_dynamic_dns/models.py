"""Data models for GoDaddy Dynamic DNS."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class RecordSpec:
    """A DNS record managed by the integration."""

    record_type: str
    name: str


@dataclass(slots=True)
class DynamicDnsState:
    """Current and persisted integration state."""

    wan_ip: str | None = None
    previous_wan_ip: str | None = None
    dns_record_ip: str | None = None
    dns_addresses: list[str] = field(default_factory=list)
    dns_in_sync: bool = False
    internet_available: bool = False
    firewall_available: bool = False
    godaddy_api_available: bool | None = None
    last_check_time: datetime | None = None
    last_update_time: datetime | None = None
    last_update_result: str = "Never updated"
    last_ip_change_time: datetime | None = None
    records_updated: int = 0
    total_updates_performed: int = 0
    public_ip_source: str = "Sophos firewall"
    pending_ip: str | None = None

    def to_store(self) -> dict[str, Any]:
        """Convert state to JSON-safe storage."""
        data = asdict(self)
        for key in ("last_check_time", "last_update_time", "last_ip_change_time"):
            value = data[key]
            data[key] = value.isoformat() if value else None
        return data

    @classmethod
    def from_store(cls, data: dict[str, Any] | None) -> DynamicDnsState:
        """Restore state from storage."""
        if not data:
            return cls()
        clean = {key: value for key, value in data.items() if key in cls.__dataclass_fields__}
        for key in ("last_check_time", "last_update_time", "last_ip_change_time"):
            if clean.get(key):
                clean[key] = datetime.fromisoformat(clean[key])
        return cls(**clean)
