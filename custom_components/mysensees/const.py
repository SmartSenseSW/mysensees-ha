from __future__ import annotations

from datetime import timedelta

DOMAIN = "mysensees"

CONF_GATEWAY_ID = "gateway_id"
CONF_BASE_URL = "base_url"

DEFAULT_BASE_URL = "https://iot-stage.smart-sense.hr"
DEFAULT_SCAN_INTERVAL = timedelta(seconds=120)

PLATFORMS = ["sensor"]
