from modules.platform_registry.service_registry import registry, PlatformService
from modules.football_tracking.api_client import fetch


async def _football_health() -> dict:
    """Health check that reuses the authenticated API client."""
    try:
        fetch("/stats")
        return {"healthy": True}
    except Exception as e:
        return {"healthy": False, "error": str(e)}


def register_football_service() -> None:
    registry.register(PlatformService(
        id="football_tracking",
        name="Football Tracking",
        description="FC Basecamp football management platform - matches, players, teams, tournaments",
        prefix="/services/football",
        health_check=_football_health,
        icon="sports_soccer",
        color="#22C55E",
    ))
