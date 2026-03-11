import os
import logging
from typing import Any

import requests

logger = logging.getLogger(__name__)

FOOTBALL_API_URL = os.getenv(
    "FOOTBALL_TRACKING_API_URL",
    "https://footballtracking.duckdns.org/dashboard",
)
FOOTBALL_API_KEY = os.getenv(
    "FOOTBALL_TRACKING_API_KEY",
    "TmBeiP9Y1GSyaMBsb6gU2y6tiftgLL_7D_sbtbfVYeHDZIX-V-Od-o6XfSJfYoHR",
)

_session = requests.Session()
_session.headers.update({"X-API-Key": FOOTBALL_API_KEY})


def fetch(endpoint: str, params: dict[str, Any] | None = None) -> Any:
    """Fetch data from the football tracking dashboard API."""
    url = f"{FOOTBALL_API_URL}{endpoint}"
    cleaned = {k: v for k, v in (params or {}).items() if v is not None}
    resp = _session.get(url, params=cleaned, timeout=15)
    resp.raise_for_status()
    return resp.json()
