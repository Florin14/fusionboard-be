import logging
from datetime import datetime, timezone
from modules.websocket.connection_manager import manager

logger = logging.getLogger(__name__)


async def emit_notification(category: str, title: str, message: str, icon: str = "notifications", color: str = "#6366F1", meta: dict | None = None):
    """
    Broadcast a notification to all connected users.

    Categories: "football", "system", "platform"
    """
    data = {
        "id": datetime.now(timezone.utc).timestamp(),
        "category": category,
        "title": title,
        "message": message,
        "icon": icon,
        "color": color,
        "meta": meta or {},
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }
    await manager.broadcast("notification", data)
    logger.info(f"Notification broadcast: [{category}] {title}")


async def emit_activity(user_name: str, action: str, target: str, icon: str = "info", color: str = "#6366F1"):
    """Broadcast a user activity event."""
    data = {
        "userName": user_name,
        "action": action,
        "target": target,
        "icon": icon,
        "color": color,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    await manager.broadcast("activity", data)
