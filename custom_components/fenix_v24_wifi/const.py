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

# Data Storage Keys
ATTR_SMARTHOMES = "smarthomes"
ATTR_DEVICES = "devices"
ATTR_DEVICE_ID = "device_id"
ATTR_SMARTHOME_ID = "smarthome_id"

# Update Interval
SCAN_INTERVAL = timedelta(seconds=10)  # same as GoodWe

# Temperature Limits (in Celsius)
MIN_TEMP = 5
MAX_TEMP = 35
TEMP_PRECISION = 0.5

# Temperature conversion formula: y = 18x + 320
# where x is temperature in Celsius and y is the API value
TEMP_MIN_VALUE = int(18 * MIN_TEMP + 320)  # 410
TEMP_MAX_VALUE = int(18 * MAX_TEMP + 320)  # 950
