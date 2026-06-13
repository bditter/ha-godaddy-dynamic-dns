"""Constants for the GoDaddy Dynamic DNS integration."""

from homeassistant.const import Platform

DOMAIN = "godaddy_dynamic_dns"
PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR, Platform.BUTTON]

CONF_FIREWALL_BASE_URL = "firewall_base_url"
CONF_FIREWALL_CA_PATH = "firewall_ca_path"
CONF_FIREWALL_USERNAME = "firewall_username"
CONF_FIREWALL_PASSWORD = "firewall_password"
CONF_FIREWALL_INTERFACE = "firewall_interface"
CONF_VERIFY_SSL = "verify_ssl"
CONF_GODADDY_API_URL = "godaddy_api_url"
CONF_API_KEY = "api_key"
CONF_API_SECRET = "api_secret"
CONF_TARGET_DOMAIN = "target_domain"
CONF_PRIMARY_RECORD_TYPE = "primary_record_type"
CONF_PRIMARY_RECORD_NAME = "primary_record_name"
CONF_ADDITIONAL_RECORDS = "additional_records"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_TTL = "ttl"

DEFAULT_GODADDY_API_URL = "https://api.godaddy.com"
DEFAULT_PRIMARY_RECORD_TYPE = "A"
DEFAULT_SCAN_INTERVAL = 300
DEFAULT_TTL = 600
DEFAULT_VERIFY_SSL = True
STORE_VERSION = 1
STORE_KEY_PREFIX = f"{DOMAIN}.state"
