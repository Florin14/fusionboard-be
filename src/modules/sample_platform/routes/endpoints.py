"""
Sample Platform Service - Plug & Play Template
================================================
Duplicate this module to add a new platform service to FusionBoard.

Steps:
1. Copy this entire directory as src/modules/your_platform/
2. Update router prefix in routes/router.py
3. Implement your api_client.py for external API integration
4. Register the service in run_api.py (import + include_router + registry.register)
5. Add frontend components in microfrontends/your_platform/
"""

from typing import Any
from .router import router


@router.get("/stats")
async def get_sample_stats() -> dict[str, Any]:
    """Return sample stats - replace with real API calls."""
    return {
        "totalItems": 42,
        "activeItems": 38,
        "alerts": 2,
        "lastSync": "2026-03-10T12:00:00Z",
    }


@router.get("/items")
async def get_sample_items(
    limit: int = 20,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """Return sample items - replace with real data source."""
    items = [
        {"id": i, "name": f"Item {i}", "status": "active" if i % 3 != 0 else "inactive"}
        for i in range(1, 11)
    ]
    return items[offset:offset + limit]
