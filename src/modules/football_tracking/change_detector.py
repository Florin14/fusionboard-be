import asyncio
import logging
from modules.football_tracking.api_client import fetch
from modules.websocket.events import emit_notification

logger = logging.getLogger(__name__)

# Cache of previous counts
_previous_counts: dict[str, int] = {}
_running = False


async def _check_football_changes():
    """Poll football API and detect new players/matches."""
    global _previous_counts

    try:
        stats = await asyncio.to_thread(fetch, "/stats")
        if not stats:
            return

        checks = [
            ("players", "New Player Added", "A new player has joined the platform", "person_add", "#22C55E"),
            ("matches", "New Match Registered", "A new match has been added", "sports_soccer", "#3B82F6"),
            ("teams", "New Team Created", "A new team has been registered", "groups", "#F59E0B"),
            ("tournaments", "New Tournament", "A new tournament has been created", "emoji_events", "#8B5CF6"),
            ("goals", "New Goal Scored", "A new goal has been recorded", "sports_score", "#EF4444"),
        ]

        for key, title, message, icon, color in checks:
            current_count = stats.get(key, 0)
            if isinstance(current_count, dict):
                current_count = current_count.get("total", 0) if "total" in current_count else 0

            prev_count = _previous_counts.get(key)

            if prev_count is not None and current_count > prev_count:
                diff = current_count - prev_count
                msg = f"{message} ({diff} new)" if diff > 1 else message
                await emit_notification(
                    category="football",
                    title=title,
                    message=msg,
                    icon=icon,
                    color=color,
                    meta={"entity": key, "previousCount": prev_count, "currentCount": current_count},
                )

            _previous_counts[key] = current_count

    except Exception as e:
        logger.error(f"Football change detection error: {e}")


async def start_change_detector(interval_seconds: int = 300):
    """Start the background polling task."""
    global _running
    if _running:
        return
    _running = True
    logger.info(f"Football change detector started (interval: {interval_seconds}s)")

    while _running:
        await _check_football_changes()
        await asyncio.sleep(interval_seconds)


def stop_change_detector():
    global _running
    _running = False
