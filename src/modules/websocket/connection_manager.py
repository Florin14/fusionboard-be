import asyncio
import json
import logging
from datetime import datetime, timezone
from dataclasses import dataclass, field
from fastapi import WebSocket

logger = logging.getLogger(__name__)


@dataclass
class ConnectedUser:
    user_id: int
    user_name: str
    role: str
    websocket: WebSocket
    connected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    current_page: str = "overview"


class ConnectionManager:
    def __init__(self):
        self._connections: dict[int, ConnectedUser] = {}  # user_id -> ConnectedUser
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, user_id: int, user_name: str, role: str):
        await websocket.accept()
        async with self._lock:
            # Disconnect existing connection for same user (only one session per user)
            if user_id in self._connections:
                try:
                    await self._connections[user_id].websocket.close(code=4001, reason="New connection opened")
                except Exception:
                    pass
            self._connections[user_id] = ConnectedUser(
                user_id=user_id, user_name=user_name, role=role, websocket=websocket
            )
        await self.broadcast_presence()

    async def disconnect(self, user_id: int):
        async with self._lock:
            self._connections.pop(user_id, None)
        await self.broadcast_presence()

    async def update_page(self, user_id: int, page: str):
        async with self._lock:
            if user_id in self._connections:
                self._connections[user_id].current_page = page
        await self.broadcast_presence()

    async def broadcast(self, event_type: str, data: dict):
        """Broadcast to all connected users."""
        message = json.dumps({"type": event_type, "data": data, "timestamp": datetime.now(timezone.utc).isoformat()})
        disconnected = []
        async with self._lock:
            connections = list(self._connections.items())
        for user_id, conn in connections:
            try:
                await conn.websocket.send_text(message)
            except Exception:
                disconnected.append(user_id)
        for uid in disconnected:
            async with self._lock:
                self._connections.pop(uid, None)

    async def broadcast_presence(self):
        """Broadcast current online users and their pages."""
        async with self._lock:
            users = [
                {
                    "userId": conn.user_id,
                    "userName": conn.user_name,
                    "currentPage": conn.current_page,
                    "connectedAt": conn.connected_at.isoformat(),
                }
                for conn in self._connections.values()
            ]
        await self.broadcast("presence", {"onlineUsers": users, "count": len(users)})

    async def send_to_user(self, user_id: int, event_type: str, data: dict):
        """Send event to specific user."""
        async with self._lock:
            conn = self._connections.get(user_id)
        if conn:
            try:
                message = json.dumps({"type": event_type, "data": data, "timestamp": datetime.now(timezone.utc).isoformat()})
                await conn.websocket.send_text(message)
            except Exception:
                pass

    @property
    def online_count(self) -> int:
        return len(self._connections)

    def get_online_users(self) -> list[dict]:
        return [
            {
                "userId": conn.user_id,
                "userName": conn.user_name,
                "currentPage": conn.current_page,
                "connectedAt": conn.connected_at.isoformat(),
            }
            for conn in self._connections.values()
        ]


# Singleton
manager = ConnectionManager()
