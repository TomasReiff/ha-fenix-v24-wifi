"""Constants for the Fenix V24 WiFi integration."""

from datetime import timedelta

DOMAIN = "fenix_v24_wifi"

# API Configuration
API_BASE_URL = "https://v24.fenixgroup.eu/api/v0.1/human/"
AUTH_URL = "https://auth.v24.fenixgroup.eu/realms/fenix/protocol/openid-connect/"
API_TIMEOUT = 10

# Config Flow Keys
CONF_EMAIL = "email"
CONF_PASSWORD = "password"
CONF_SCAN_INTERVAL = "scan_interval"

# Data Storage Keys
ATTR_SMARTHOMES = "smarthomes"
ATTR_DEVICES = "devices"
ATTR_DEVICE_ID = "device_id"
ATTR_SMARTHOME_ID = "smarthome_id"

# Update Interval
DEFAULT_SCAN_INTERVAL_SECONDS = 30
SCAN_INTERVAL = timedelta(seconds=DEFAULT_SCAN_INTERVAL_SECONDS)

# Temperature Limits (in Celsius)
MIN_TEMP = 5
MAX_TEMP = 35
TEMP_PRECISION = 0.5

# Temperature conversion formula: y = 18x + 320
# where x is temperature in Celsius and y is the API value
TEMP_MIN_VALUE = int(18 * MIN_TEMP + 320)  # 410
TEMP_MAX_VALUE = int(18 * MAX_TEMP + 320)  # 950

# Presets & Modes
PRESET_COMFORT = "comfort"
PRESET_ECO = "eco"
PRESET_AWAY = "away"  # Frost Protection
PRESET_BOOST = "boost"
PRESET_MANUAL = "manual"

PRESET_TO_GV_MODE = {
    PRESET_COMFORT: "0",
    PRESET_AWAY: "2",
    PRESET_ECO: "3",
    PRESET_BOOST: "4",
    PRESET_MANUAL: "15",
}

GV_MODE_TO_PRESET = {
    "0": PRESET_COMFORT,
    "2": PRESET_AWAY,
    "3": PRESET_ECO,
    "4": PRESET_BOOST,
    "15": PRESET_MANUAL,
}
