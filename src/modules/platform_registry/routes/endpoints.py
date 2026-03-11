import logging
from typing import Any

from .router import router
from modules.platform_registry.service_registry import registry

logger = logging.getLogger(__name__)


@router.get("")
async def list_platforms() -> list[dict[str, Any]]:
    """List all registered platform services with their health status."""
    results = []
    for svc in registry.services.values():
        health = await registry.check_health(svc.id)
        results.append({
            "id": svc.id,
            "name": svc.name,
            "description": svc.description,
            "icon": svc.icon,
            "color": svc.color,
            "prefix": svc.prefix,
            "healthy": health["healthy"],
            "latency_ms": health.get("latency_ms"),
        })
    return results


@router.get("/{platform_id}/health")
async def platform_health(platform_id: str) -> dict[str, Any]:
    """Check health of a specific platform service."""
    health = await registry.check_health(platform_id)
    if health.get("error") == "not_found":
        from fastapi import HTTPException
        raise HTTPException(404, detail=f"Platform '{platform_id}' not found")
    return health
