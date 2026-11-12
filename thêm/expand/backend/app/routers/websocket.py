"""
app/routers/websocket.py — Real-time WebSocket per school
WS /ws/{school_id}/live?token=... — broadcast attendance & violation alerts
"""
import json, logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from typing import Dict, List, Optional
from app.core.security import decode_access_token
from app.config import APP_DEBUG

router = APIRouter(tags=["WebSocket"])
log    = logging.getLogger("stem.ws")

# In-memory connection registry: {school_id: [WebSocket, ...]}
_connections: Dict[int, List[WebSocket]] = {}


@router.websocket("/ws/{school_id}/live")
async def websocket_live(
    websocket: WebSocket,
    school_id: int,
    token: Optional[str] = Query(None)
):
    # Verify authentication token (H-8)
    user = decode_access_token(token) if token else None
    if not user:
        if not APP_DEBUG:
            log.warning(f"[WS] Connection rejected for school {school_id}: Missing or invalid token.")
            await websocket.close(code=1008, reason="Unauthorized: Token không hợp lệ hoặc đã hết hạn")
            return
        else:
            log.info(f"[WS] Dev mode allowed connection without token for school {school_id}")

    if user and user.get("role") not in ("ADMIN", "PLATFORM_ADMIN"):
        if user.get("school_id") != school_id:
            log.warning(f"[WS] Forbidden access to school {school_id} for user from school {user.get('school_id')}")
            await websocket.close(code=1008, reason="Forbidden: Bạn không thuộc trường này")
            return

    await websocket.accept()
    _connections.setdefault(school_id, []).append(websocket)
    log.info(f"[WS] New client connected to school {school_id}. Total: {len(_connections[school_id])}")
    try:
        # Send welcome
        await websocket.send_json({
            "type": "CONNECTED",
            "school_id": school_id,
            "message": f"Đã kết nối Live Dashboard — Trường #{school_id}"
        })
        while True:
            # Keep alive — client can send ping
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("type") == "PING":
                    await websocket.send_json({"type": "PONG"})
            except Exception:
                pass
    except WebSocketDisconnect:
        try:
            _connections[school_id].remove(websocket)
        except (ValueError, KeyError):
            pass
        log.info(f"[WS] Client disconnected from school {school_id}.")


async def broadcast_to_school(school_id: int, payload: dict):
    """Call this from other routers to push real-time alerts."""
    dead = []
    for ws in _connections.get(school_id, []):
        try:
            await ws.send_json(payload)
        except Exception:
            dead.append(ws)
    for ws in dead:
        try:
            _connections[school_id].remove(ws)
        except (ValueError, KeyError):
            pass
