import json
import logging
from fastapi import WebSocket, WebSocketDisconnect, Query
from extensions.auth_jwt.auth_jwt import AuthJWT
from modules.websocket.connection_manager import manager
from .router import websocketRouter

logger = logging.getLogger(__name__)


@websocketRouter.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(None)):
    """
    WebSocket endpoint with JWT authentication.
    Connect with: ws://host/ws?token=<jwt_access_token>

    Client can send JSON messages:
    - {"action": "page_change", "page": "football"} - Update current page
    - {"action": "ping"} - Keep alive
    """
    if not token:
        await websocket.close(code=4001, reason="Token required")
        return

    # Validate JWT
    try:
        authorize = AuthJWT()
        authorize._token = token
        authorize.jwt_required()
        claims = authorize.get_raw_jwt()
        user_id = claims.get("userId")
        user_name = claims.get("userName", "Unknown")
        role = claims.get("role", "PLAYER")
    except Exception as e:
        logger.warning(f"WebSocket auth failed: {e}")
        await websocket.close(code=4003, reason="Invalid token")
        return

    if not user_id:
        await websocket.close(code=4003, reason="Invalid token claims")
        return

    # Connect
    await manager.connect(websocket, user_id, user_name, role)
    logger.info(f"WebSocket connected: {user_name} (ID: {user_id})")

    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                action = message.get("action")

                if action == "page_change":
                    page = message.get("page", "overview")
                    await manager.update_page(user_id, page)

                elif action == "ping":
                    await manager.send_to_user(user_id, "pong", {})

            except json.JSONDecodeError:
                pass

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {user_name} (ID: {user_id})")
        await manager.disconnect(user_id)
    except Exception as e:
        logger.error(f"WebSocket error for {user_name}: {e}")
        await manager.disconnect(user_id)
