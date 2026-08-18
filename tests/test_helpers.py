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
helpers = _load_module("helpers")
all_records = helpers.all_records
format_config_records_for_display = helpers.format_config_records_for_display
parse_fqdn_records = helpers.parse_fqdn_records
records_from_config = helpers.records_from_config


def test_fqdn_records_are_the_source_of_truth() -> None:
    """FQDN lines are parsed into GoDaddy domain and record name pairs."""
    assert parse_fqdn_records(
        "example.com\nplex.example.com\nespforge.lab.net\nai.lab.net"
    ) == [
        RecordSpec("example.com", "A", "@"),
        RecordSpec("example.com", "A", "plex"),
        RecordSpec("lab.net", "A", "espforge"),
        RecordSpec("lab.net", "A", "ai"),
    ]


def test_legacy_records_still_parse_for_migration() -> None:
    """Legacy records are still accepted when stored config has not migrated."""
    assert records_from_config(
        "example.com",
        "A",
        "home",
        "A,legacy\nlab.net,espforge",
    ) == [
        RecordSpec("example.com", "A", "home"),
        RecordSpec("example.com", "A", "legacy"),
        RecordSpec("lab.net", "A", "espforge"),
    ]


def test_records_reject_non_a_records() -> None:
    """Only A records are supported."""
    with pytest.raises(ValueError):
        parse_fqdn_records("not-a-full-hostname")


def test_legacy_records_are_formatted_as_fqdns() -> None:
    """Existing target-domain configs display as full hostnames."""
    assert (
        format_config_records_for_display(
            "example.com",
            "A",
            "home",
            "A,firewall\nA,lab.net,espforge",
        )
        == "home.example.com\nfirewall.example.com\nespforge.lab.net"
    )
