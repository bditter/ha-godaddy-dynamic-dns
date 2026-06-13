"""Configuration helpers for GoDaddy Dynamic DNS."""

from __future__ import annotations

from .models import RecordSpec


def parse_additional_records(value: str) -> list[RecordSpec]:
    """Parse one TYPE,NAME record per line."""
    records: list[RecordSpec] = []
    for line_number, raw_line in enumerate(value.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        parts = [part.strip() for part in line.split(",", maxsplit=1)]
        if len(parts) != 2 or not all(parts):
            raise ValueError(f"Line {line_number} must use TYPE,NAME")
        record_type, name = parts
        record_type = record_type.upper()
        if record_type != "A":
            raise ValueError(f"Line {line_number}: only A records are supported")
        records.append(RecordSpec(record_type, name))
    return records


def all_records(
    primary_type: str, primary_name: str, additional_records: str
) -> list[RecordSpec]:
    """Return a de-duplicated list containing primary and additional records."""
    records = [
        RecordSpec(primary_type.upper(), primary_name.strip()),
        *parse_additional_records(additional_records),
    ]
    return list(dict.fromkeys(records))
