import os
import logging
from fastapi import Request, HTTPException
from pydantic import BaseModel
from modules.webhooks.routes.router import webhookRouter
from modules.websocket.events import emit_notification

logger = logging.getLogger(__name__)

WEBHOOK_SECRET = os.getenv("FUSIONBOARD_WEBHOOK_SECRET", "fusionboard-webhook-secret-2026")


class WebhookPayload(BaseModel):
    event: str
    data: dict


# Event type -> (title_template, message_template, icon, color)
EVENT_CONFIG = {
    "player.created": {
        "title": "New Player Added",
        "message": lambda d: f"{d.get('name', 'Unknown')} has joined{' (' + d['position'] + ')' if d.get('position') else ''}",
        "icon": "person_add",
        "color": "#22C55E",
    },
    "team.created": {
        "title": "New Team Created",
        "message": lambda d: f"Team '{d.get('name', 'Unknown')}' has been registered",
        "icon": "groups",
        "color": "#F59E0B",
    },
    "match.created": {
        "title": "New Match Scheduled",
        "message": lambda d: f"{d.get('team1Name', '?')} vs {d.get('team2Name', '?')}" + (f" — {d.get('location', '')}" if d.get('location') else ""),
        "icon": "sports_soccer",
        "color": "#3B82F6",
    },
    "goal.scored": {
        "title": "Goal Scored!",
        "message": lambda d: f"{d.get('playerName', 'Unknown')} scored! {d.get('team1Name', '?')} {d.get('scoreTeam1', '?')} - {d.get('scoreTeam2', '?')} {d.get('team2Name', '?')}",
        "icon": "sports_score",
        "color": "#EF4444",
    },
    "card.issued": {
        "title": lambda d: f"{'Red' if d.get('cardType') == 'RED' else 'Yellow'} Card",
        "message": lambda d: f"{d.get('playerName', 'Unknown')} received a {d.get('cardType', '').lower()} card ({d.get('teamName', '')})",
        "icon": lambda d: "square" if d.get("cardType") == "RED" else "warning",
        "color": lambda d: "#EF4444" if d.get("cardType") == "RED" else "#F59E0B",
    },
}


@webhookRouter.post("/football")
async def receive_football_webhook(payload: WebhookPayload, request: Request):
    """
    Receives webhook notifications from Football Tracking backend.
    Validates the shared secret and broadcasts as WebSocket notification.
    """
    # Validate webhook secret
    secret = request.headers.get("X-Webhook-Secret", "")
    if secret != WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail="Invalid webhook secret")

    event = payload.event
    data = payload.data

    config = EVENT_CONFIG.get(event)
    if not config:
        logger.warning(f"Unknown webhook event: {event}")
        return {"status": "ignored", "event": event}

    # Resolve callable configs
    title = config["title"](data) if callable(config["title"]) else config["title"]
    message = config["message"](data) if callable(config["message"]) else config["message"]
    icon = config["icon"](data) if callable(config["icon"]) else config["icon"]
    color = config["color"](data) if callable(config["color"]) else config["color"]

    await emit_notification(
        category="football",
        title=title,
        message=message,
        icon=icon,
        color=color,
        meta=data,
    )

    logger.info(f"Webhook processed: {event}")
    return {"status": "ok", "event": event}
