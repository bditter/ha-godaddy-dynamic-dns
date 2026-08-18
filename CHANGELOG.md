# Changelog

## 1.2.0

- Make the existing service Configure dialog a full maintenance form.
- Allow firewall, GoDaddy, target-domain, primary-record, polling, TTL, and
  managed-record settings to be changed without deleting the config entry.
- Preserve existing firewall and GoDaddy secrets when replacement fields are
  left blank.

## 1.1.0

- Support managed update records from multiple GoDaddy domains.
- Allow record lines in `NAME`, `FQDN`, or `DOMAIN,NAME` format.
- Keep backward compatibility with existing `A,NAME` and `A,DOMAIN,NAME` entries.
- Clarify that records can be added, edited, or deleted from the options form.

## 1.0.0

- Initial public release.
- Reads WAN IPv4 addresses from the Sophos XML API.
- Updates configured GoDaddy `A` records after WAN address changes.
- Supports configurable polling, TTL, TLS verification, and private CAs.
- Provides status sensors, connectivity sensors, and manual action buttons.
