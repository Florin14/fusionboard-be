import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Awaitable

import requests

logger = logging.getLogger(__name__)


@dataclass
class PlatformService:
    id: str
    name: str
    description: str
    prefix: str
    health_url: str | None = None
    health_check: Callable[[], Awaitable[dict[str, Any]]] | None = None
    icon: str = "extension"
    color: str = "#6366F1"
    meta: dict[str, Any] = field(default_factory=dict)


class ServiceRegistry:
    def __init__(self) -> None:
        self.services: dict[str, PlatformService] = {}

    def register(self, service: PlatformService) -> None:
        self.services[service.id] = service
        logger.info("Registered platform service: %s (%s)", service.name, service.id)

    def unregister(self, service_id: str) -> None:
        self.services.pop(service_id, None)

    async def check_health(self, service_id: str) -> dict[str, Any]:
        svc = self.services.get(service_id)
        if not svc:
            return {"healthy": False, "error": "not_found"}

        start = time.monotonic()
        try:
            if svc.health_check:
                result = await svc.health_check()
                elapsed = round((time.monotonic() - start) * 1000)
                return {**result, "latency_ms": elapsed}

            if svc.health_url:
                loop = asyncio.get_event_loop()
                resp = await loop.run_in_executor(
                    None, lambda: requests.get(svc.health_url, timeout=5)
                )
                elapsed = round((time.monotonic() - start) * 1000)
                return {
                    "healthy": resp.status_code < 400,
                    "status_code": resp.status_code,
                    "latency_ms": elapsed,
                }

            return {"healthy": True, "latency_ms": 0, "note": "no_health_check_configured"}
        except Exception as e:
            elapsed = round((time.monotonic() - start) * 1000)
            logger.warning("Health check failed for %s: %s", service_id, e)
            return {"healthy": False, "error": str(e), "latency_ms": elapsed}

    async def check_all(self) -> dict[str, dict[str, Any]]:
        results = {}
        for sid in self.services:
            results[sid] = await self.check_health(sid)
        return results


# Singleton
registry = ServiceRegistry()
