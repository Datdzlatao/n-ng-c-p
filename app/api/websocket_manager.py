import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional
from fastapi import WebSocket

logger = logging.getLogger("smart_manager.websocket")


class WebSocketConnectionManager:
    """
    Manages active WebSocket connections from Web and Mobile clients.
    Thread-safe and async-compatible.
    """

    def __init__(self):
        self._active_connections: set[WebSocket] = set()

    @property
    def total_connections(self) -> int:
        return len(self._active_connections)

    async def connect(self, websocket: WebSocket):
        """Accept and register a new WebSocket client."""
        await websocket.accept()
        self._active_connections.add(websocket)
        logger.info(f"WebSocket client connected. Total clients: {len(self._active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """Unregister a disconnected WebSocket client."""
        self._active_connections.discard(websocket)
        logger.info(f"WebSocket client disconnected. Total clients: {len(self._active_connections)}")

    async def send_personal_message(self, message: dict[str, Any], websocket: WebSocket):
        """Send a JSON payload to a specific client."""
        try:
            await websocket.send_text(json.dumps(message, ensure_ascii=False))
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
            self.disconnect(websocket)

    async def broadcast(self, event: str, data: dict[str, Any]):
        """
        Broadcast an event and data payload to all connected clients.
        Example event: 'alert', 'chat_message', 'env_update', 'scheduler_briefing'.
        """
        if not self._active_connections:
            return

        message = {
            "event": event,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        raw_text = json.dumps(message, ensure_ascii=False)

        dead_connections = set()
        for connection in list(self._active_connections):
            try:
                await connection.send_text(raw_text)
            except Exception as e:
                logger.warning(f"Failed to send to client, removing from pool: {e}")
                dead_connections.add(connection)

        for dead in dead_connections:
            self._active_connections.discard(dead)


# Global singleton instance
ws_manager = WebSocketConnectionManager()
