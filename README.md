# GoDaddy Dynamic DNS for Home Assistant

[![Latest release](https://img.shields.io/github/v/release/bditter/ha-godaddy-dynamic-dns?display_name=tag&sort=semver)](https://github.com/bditter/ha-godaddy-dynamic-dns/releases/latest)
[![HACS custom repository](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/docs/faq/custom_repositories/)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-Custom%20Integration-41BDF5.svg)](https://www.home-assistant.io/)
[![Release workflow](https://github.com/bditter/ha-godaddy-dynamic-dns/actions/workflows/release.yml/badge.svg)](https://github.com/bditter/ha-godaddy-dynamic-dns/actions/workflows/release.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A Home Assistant custom integration that synchronizes GoDaddy `A` records
with the public WAN address reported by a Sophos Firewall.

## Features

- Reads the WAN IPv4 address through the Sophos XML API.
- Stores the last observed WAN address.
- Contacts GoDaddy only after the WAN address changes or an update remains
  pending.
- Reads the primary record directly from GoDaddy instead of using local DNS.
- Updates the primary record and any configured additional records.
- Supports managed update records across multiple GoDaddy domains.
- Provides configurable polling interval and DNS TTL.
- Supports public certificates, private certificate authorities, and optional
  TLS verification.
- Provides an independent ipify-based internet connectivity sensor.
- Includes manual check and force-update buttons.

## Installation

### HACS custom repository

1. Open HACS.
2. Add `https://github.com/bditter/ha-godaddy-dynamic-dns` as a custom
   integration repository.
3. Install **GoDaddy Dynamic DNS for Home Assistant**.
4. Restart Home Assistant.

### Manual installation

Copy:

```text
custom_components/godaddy_dynamic_dns
```

to:

```text
/config/custom_components/godaddy_dynamic_dns
```

Restart Home Assistant, then open:

```text
Settings > Devices & services > Add integration
```

Search for **GoDaddy Dynamic DNS for Home Assistant**.

## Configuration

The setup flow requests:

- Sophos Firewall base URL
- Sophos API username and password
- WAN interface name
- TLS verification preference
- Optional private CA certificate path
- GoDaddy API URL, key, and secret
- Target domain
- Primary record type and name
- Optional records to update
- Polling interval
- DNS TTL

No firewall address, interface, credentials, domain, record name, or additional
target is preconfigured.

After setup, open the integration's **Configure** dialog to change any of the
same settings without deleting the service. The stored firewall and GoDaddy
secret values are shown in password fields so they can be reviewed or edited.

Managed records can be added, edited, or deleted in **Configure**. Since only
`A` records are supported, the record type is implied. Use one record per line.

For records in the target domain:

```text
host-one
host-two
```

For ordinary fully qualified records:

```text
host-one.example.net
```

For explicit GoDaddy zone control, use:

```text
example.net,host-one
```

For example, to update `espforge.ditter-lab.net`:

```text
ditter-lab.net,espforge
```

Only IPv4 `A` records are currently supported. Existing entries that include
`A,` still work for backward compatibility.

## Private CA certificates

For a firewall certificate issued by a private CA:

1. Export the issuing CA certificate in PEM format.
2. Upload it to Home Assistant, for example as `/ssl/firewall-ca.pem`.
3. Keep **Verify firewall TLS certificate** enabled.
4. Enter `/ssl/firewall-ca.pem` as the firewall CA certificate path.

This trusts the private CA only for this integration's firewall connection.

## Operation

During each polling interval:

1. Read the Sophos WAN address.
2. Check ipify for the independent **Internet online** sensor.
3. Compare the WAN address with the integration's stored value.
4. Stop without contacting GoDaddy when the WAN address is unchanged.
5. When changed, read the primary record directly from GoDaddy.
6. Update all configured records when the primary record differs.
7. Retain a pending change and retry if GoDaddy is unavailable.

**Check now** runs the normal polling flow immediately.

**Force update** writes the current Sophos WAN address to every configured
record without first reading the primary record from GoDaddy.

## Entities

Sensors:

- WAN IP address
- Previous WAN IP address
- GoDaddy A record IP address
- Last update time
- Last update result
- Last IP change time
- Records updated
- Total updates performed
- Public IP source

Binary sensors:

- GoDaddy record in sync
- Internet online
- Firewall API available
- GoDaddy API available

Buttons:

- Check now
- Force update

## Branding

Local branding files are included under `brand/`. Local custom-integration
branding requires Home Assistant 2026.3 or newer.

## Security

- Use a dedicated, least-privilege Sophos API account.
- Keep TLS verification enabled whenever possible.
- Credentials are redacted from Home Assistant diagnostics.
- The Sophos XML request is sent in the HTTPS request body rather than the URL.

## Version

Current release: `1.2.2`

## License

[MIT](LICENSE)
