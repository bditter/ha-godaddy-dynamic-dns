"""API clients and network helpers for GoDaddy Dynamic DNS."""

from __future__ import annotations

import asyncio
import ipaddress
import ssl
from typing import Any
from urllib.parse import quote, urljoin
from xml.etree import ElementTree

from aiohttp import (
    ClientConnectorCertificateError,
    ClientError,
    ClientSession,
    FormData,
)


class DynamicDnsApiError(Exception):
    """Base API error."""


class DynamicDnsAuthError(DynamicDnsApiError):
    """Authentication or authorization error."""


class DynamicDnsCertificateError(DynamicDnsApiError):
    """Firewall TLS certificate validation error."""


def _valid_ipv4(value: object) -> str:
    """Validate and normalize an IPv4 address."""
    try:
        address = ipaddress.ip_address(str(value).strip())
    except ValueError as err:
        raise DynamicDnsApiError(f"Invalid IP address returned: {value}") from err
    if address.version != 4 or not address.is_global:
        raise DynamicDnsApiError(f"Non-public IPv4 address returned: {address}")
    return str(address)


class DynamicDnsApi:
    """Network access for WAN discovery, DNS, and GoDaddy."""

    def __init__(
        self,
        session: ClientSession,
        *,
        firewall_base_url: str,
        firewall_ca_path: str,
        firewall_username: str,
        firewall_password: str,
        firewall_interface: str,
        verify_ssl: bool,
        godaddy_api_url: str,
        api_key: str,
        api_secret: str,
    ) -> None:
        self._session = session
        self._firewall_url = urljoin(
            firewall_base_url.rstrip("/") + "/", "webconsole/APIController"
        )
        self._firewall_ssl = self._create_firewall_ssl_context(
            verify_ssl, firewall_ca_path
        )
        self._firewall_username = firewall_username
        self._firewall_password = firewall_password
        self._firewall_interface = firewall_interface
        self._godaddy_api_url = godaddy_api_url.rstrip("/")
        self._headers = {
            "Accept": "application/json",
            "Authorization": f"sso-key {api_key}:{api_secret}",
        }

    @staticmethod
    def _create_firewall_ssl_context(
        verify_ssl: bool, firewall_ca_path: str
    ) -> ssl.SSLContext | bool:
        """Build firewall TLS validation using an optional private CA."""
        if not verify_ssl:
            return False
        if firewall_ca_path.strip():
            try:
                return ssl.create_default_context(cafile=firewall_ca_path.strip())
            except (OSError, ssl.SSLError) as err:
                raise DynamicDnsCertificateError(
                    f"Could not load firewall CA file: {err}"
                ) from err
        return ssl.create_default_context()

    async def async_get_firewall_ip(self) -> str:
        """Get the WAN IP from the local firewall API."""
        request_xml = (
            '<Request APIVersion="2000.1">'
            "<Login>"
            f"<Username>{self._xml_escape(self._firewall_username)}</Username>"
            f"<Password>{self._xml_escape(self._firewall_password)}</Password>"
            "</Login>"
            "<Get><Interface/></Get>"
            "</Request>"
        )
        form = FormData()
        form.add_field("reqxml", request_xml, content_type="application/xml")
        try:
            async with self._session.post(
                self._firewall_url,
                data=form,
                ssl=self._firewall_ssl,
                timeout=20,
            ) as response:
                response.raise_for_status()
                payload = await response.text()
            root = ElementTree.fromstring(payload)
        except ClientConnectorCertificateError as err:
            raise DynamicDnsCertificateError(
                f"Firewall TLS certificate validation failed: {err.certificate_error}"
            ) from err
        except (ClientError, asyncio.TimeoutError, ElementTree.ParseError) as err:
            raise DynamicDnsApiError("Firewall API request failed") from err

        for interface in root.findall(".//Interface"):
            if interface.findtext("Name") == self._firewall_interface:
                return _valid_ipv4(interface.findtext("IPAddress"))
        raise DynamicDnsApiError(
            f"Firewall interface '{self._firewall_interface}' was not returned"
        )

    async def async_check_internet(self) -> bool:
        """Check internet connectivity without using the result for DNS updates."""
        try:
            async with self._session.get(
                "https://api.ipify.org",
                params={"format": "text"},
                ssl=True,
                timeout=10,
            ) as response:
                response.raise_for_status()
                _valid_ipv4(await response.text())
        except (ClientError, asyncio.TimeoutError, DynamicDnsApiError):
            return False
        return True

    @staticmethod
    def _xml_escape(value: str) -> str:
        """Escape a value used in the Sophos API request."""
        return (
            value.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;")
        )

    def _record_url(self, domain: str, record_type: str, name: str) -> str:
        return (
            f"{self._godaddy_api_url}/v1/domains/{quote(domain, safe='')}/records/"
            f"{quote(record_type, safe='')}/{quote(name, safe='')}"
        )

    async def async_get_record(
        self, domain: str, record_type: str, name: str
    ) -> list[dict[str, Any]]:
        """Read one GoDaddy record set. Used only during setup validation."""
        try:
            async with self._session.get(
                self._record_url(domain, record_type, name),
                headers=self._headers,
                timeout=20,
            ) as response:
                if response.status in (401, 403):
                    raise DynamicDnsAuthError("GoDaddy rejected the API credentials")
                response.raise_for_status()
                payload = await response.json()
        except DynamicDnsAuthError:
            raise
        except (ClientError, asyncio.TimeoutError, ValueError) as err:
            raise DynamicDnsApiError(f"GoDaddy API request failed: {err}") from err
        if not isinstance(payload, list):
            raise DynamicDnsApiError("GoDaddy returned an unexpected response")
        return payload

    async def async_get_record_addresses(
        self, domain: str, record_type: str, name: str
    ) -> list[str]:
        """Read and validate IPv4 values directly from a GoDaddy record set."""
        records = await self.async_get_record(domain, record_type, name)
        addresses: list[str] = []
        for record in records:
            if isinstance(record, dict) and "data" in record:
                addresses.append(_valid_ipv4(record["data"]))
        if not addresses:
            raise DynamicDnsApiError("GoDaddy returned no IPv4 values for the record")
        return sorted(set(addresses))

    async def async_replace_record(
        self,
        domain: str,
        record_type: str,
        name: str,
        value: str,
        ttl: int,
    ) -> None:
        """Replace one GoDaddy record set."""
        body = [{"data": value, "ttl": ttl}]
        try:
            async with self._session.put(
                self._record_url(domain, record_type, name),
                headers={**self._headers, "Content-Type": "application/json"},
                json=body,
                timeout=20,
            ) as response:
                if response.status in (401, 403):
                    raise DynamicDnsAuthError("GoDaddy rejected the API credentials")
                response.raise_for_status()
        except DynamicDnsAuthError:
            raise
        except (ClientError, asyncio.TimeoutError) as err:
            raise DynamicDnsApiError(f"GoDaddy update failed: {err}") from err
