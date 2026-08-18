"""Tests for DNS record parsing helpers."""

import importlib.util
from pathlib import Path
import sys
import types

import pytest

PACKAGE = "custom_components.godaddy_dynamic_dns"
ROOT = Path(__file__).parents[1] / "custom_components" / "godaddy_dynamic_dns"

sys.modules.setdefault("custom_components", types.ModuleType("custom_components"))
package = types.ModuleType(PACKAGE)
package.__path__ = [str(ROOT)]
sys.modules[PACKAGE] = package


def _load_module(name: str):
    spec = importlib.util.spec_from_file_location(f"{PACKAGE}.{name}", ROOT / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[f"{PACKAGE}.{name}"] = module
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


RecordSpec = _load_module("models").RecordSpec
all_records = _load_module("helpers").all_records
format_record_lines_for_display = _load_module("helpers").format_record_lines_for_display
secret_or_existing = _load_module("helpers").secret_or_existing
SECRET_UNCHANGED = _load_module("helpers").SECRET_UNCHANGED


def test_records_accept_plain_names_and_explicit_domains() -> None:
    """Plain names use the target domain; DOMAIN,NAME uses that zone."""
    assert all_records(
        "example.com",
        "A",
        "home",
        "firewall\nlab.net,espforge",
    ) == [
        RecordSpec("example.com", "A", "home"),
        RecordSpec("example.com", "A", "firewall"),
        RecordSpec("lab.net", "A", "espforge"),
    ]


def test_records_accept_fqdn_and_legacy_type_prefix() -> None:
    """Fully qualified and old A-prefixed records are backward compatible."""
    assert all_records(
        "example.com",
        "A",
        "home",
        "host.lab.net\nA,legacy\nA,lab.net,typed",
    ) == [
        RecordSpec("example.com", "A", "home"),
        RecordSpec("lab.net", "A", "host"),
        RecordSpec("example.com", "A", "legacy"),
        RecordSpec("lab.net", "A", "typed"),
    ]


def test_records_reject_non_a_records() -> None:
    """Only A records are supported."""
    with pytest.raises(ValueError):
        all_records("example.com", "A", "home", "CNAME,example.net,alias")


def test_legacy_records_are_formatted_without_a_prefix() -> None:
    """Existing A-prefixed records are shown without the implied type."""
    assert (
        format_record_lines_for_display(
            "A,firewall\nA,lab.net,espforge",
            "example.com",
        )
        == "firewall\nlab.net,espforge"
    )


def test_secret_marker_keeps_existing_values() -> None:
    """Configure dialog secret markers preserve stored secrets."""
    assert secret_or_existing(SECRET_UNCHANGED, "old-secret") == "old-secret"
    assert secret_or_existing("", "old-secret") == "old-secret"
    assert secret_or_existing("new-secret", "old-secret") == "new-secret"
