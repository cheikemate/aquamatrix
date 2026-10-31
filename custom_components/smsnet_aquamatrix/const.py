from __future__ import annotations

from homeassistant.const import Platform

DOMAIN = "smsnet_aquamatrix"
DEFAULT_BASE_URL = "https://www.aquamatrix.pt"
CONF_TENANT = "SMASVFX"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
PLATFORMS = [Platform.SENSOR]
