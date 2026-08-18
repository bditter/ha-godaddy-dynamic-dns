"""Configuration helpers for GoDaddy Dynamic DNS."""

from __future__ import annotations

from .models import RecordSpec


def _normalize_domain(value: str) -> str:
    """Normalize a DNS zone name."""
    domain = value.strip().strip(".").lower()
    if "." not in domain or any(not part for part in domain.split(".")):
        raise ValueError("Domain must contain at least two labels")
    return domain


def _normalize_record_name(value: str) -> str:
    """Normalize a DNS record name."""
    name = value.strip().strip(".").lower()
    if not name or any(not part for part in name.split(".")):
        raise ValueError("Record name is invalid")
    return name


def _split_fqdn(value: str) -> tuple[str, str]:
    """Split a simple FQDN into a GoDaddy zone and record name."""
    labels = value.strip().strip(".").lower().split(".")
    if len(labels) < 2 or any(not label for label in labels):
        raise ValueError("FQDN must include a domain")
    if len(labels) == 2:
        return ".".join(labels), "@"
    return ".".join(labels[-2:]), ".".join(labels[:-2])


def _fqdn(record: RecordSpec) -> str:
    """Return a simple FQDN for a record."""
    if record.name == "@":
        return record.domain
    return f"{record.name}.{record.domain}"


def parse_fqdn_records(value: str) -> list[RecordSpec]:
    """Parse managed FQDN records."""
    records: list[RecordSpec] = []
    for line_number, raw_line in enumerate(value.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        if "," in line:
            raise ValueError(f"Line {line_number} must be a full hostname")
        domain, name = _split_fqdn(line)
        records.append(RecordSpec(domain, "A", name))
    if not records:
        raise ValueError("At least one record is required")
    return list(dict.fromkeys(records))


def parse_additional_records(value: str, target_domain: str) -> list[RecordSpec]:
    """Parse one managed record per line."""
    records: list[RecordSpec] = []
    target_domain = _normalize_domain(target_domain)
    for line_number, raw_line in enumerate(value.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        parts = [part.strip() for part in line.split(",")]
        if len(parts) == 1:
            record_type = "A"
            value = parts[0]
            if "." in value.strip().strip("."):
                domain, name = _split_fqdn(value)
            else:
                domain = target_domain
                name = _normalize_record_name(value)
        elif len(parts) == 2 and parts[0].upper() == "A" and all(parts):
            record_type = "A"
            value = parts[1]
            if "." in value.strip().strip("."):
                domain, name = _split_fqdn(value)
            else:
                domain = target_domain
                name = _normalize_record_name(value)
        elif len(parts) == 2 and all(parts):
            record_type = "A"
            domain = _normalize_domain(parts[0])
            name = _normalize_record_name(parts[1])
        elif len(parts) == 3 and all(parts):
            record_type = parts[0].upper()
            domain = _normalize_domain(parts[1])
            name = _normalize_record_name(parts[2])
        else:
            raise ValueError(
                f"Line {line_number} must use NAME, FQDN, DOMAIN,NAME, or A,DOMAIN,NAME"
            )
        if record_type != "A":
            raise ValueError(f"Line {line_number}: only A records are supported")
        records.append(RecordSpec(domain, record_type, name))
    return records


def all_records(
    target_domain: str,
    primary_type: str,
    primary_name: str,
    additional_records: str,
) -> list[RecordSpec]:
    """Return a de-duplicated list containing primary and additional records."""
    target_domain = _normalize_domain(target_domain)
    records = [
        RecordSpec(
            target_domain,
            primary_type.upper(),
            _normalize_record_name(primary_name),
        ),
        *parse_additional_records(additional_records, target_domain),
    ]
    return list(dict.fromkeys(records))


def records_from_config(
    target_domain: str,
    primary_type: str,
    primary_name: str,
    additional_records: str,
) -> list[RecordSpec]:
    """Return managed records from new FQDN config or legacy config."""
    try:
        return parse_fqdn_records(additional_records)
    except ValueError:
        return all_records(
            target_domain,
            primary_type,
            primary_name,
            additional_records,
        )


def format_config_records_for_display(
    target_domain: str,
    primary_type: str,
    primary_name: str,
    additional_records: str,
) -> str:
    """Format new or legacy managed records as FQDN lines."""
    try:
        records = parse_fqdn_records(additional_records)
    except ValueError:
        try:
            records = all_records(
                target_domain,
                primary_type,
                primary_name,
                additional_records,
            )
        except ValueError:
            return additional_records
    return "\n".join(_fqdn(record) for record in records)
