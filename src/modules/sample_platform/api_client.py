"""
Sample API Client - Template
==============================
Replace with your external API integration.
Follow the same pattern as football_tracking/api_client.py.
"""

import os
import logging
from typing import Any

import requests

logger = logging.getLogger(__name__)

# Configure via environment variables
SAMPLE_API_URL = os.getenv("SAMPLE_PLATFORM_API_URL", "https://api.example.com")
SAMPLE_API_KEY = os.getenv("SAMPLE_PLATFORM_API_KEY", "")

_session = requests.Session()
if SAMPLE_API_KEY:
    _session.headers.update({"Authorization": f"Bearer {SAMPLE_API_KEY}"})


def fetch(endpoint: str, params: dict[str, Any] | None = None) -> Any:
    """Fetch data from the sample platform API."""
    url = f"{SAMPLE_API_URL}{endpoint}"
    cleaned = {k: v for k, v in (params or {}).items() if v is not None}
    resp = _session.get(url, params=cleaned, timeout=15)
    resp.raise_for_status()
    return resp.json()
