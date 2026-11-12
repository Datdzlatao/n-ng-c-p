"""
app/services/camera_stream_service.py — Dịch vụ Stream Video & WebSocket Relay
Tách riêng toàn bộ logic kết nối MJPEG, Snapshot, phát hiện cổng stream và WebSocket relay.
"""
import json
import logging
import asyncio
from pathlib import Path
from typing import Optional, AsyncGenerator
import httpx
from fastapi import HTTPException, WebSocket, WebSocketDisconnect

from app.database import get_db

log = logging.getLogger("stem.camera_stream")

_PROJ_ROOT = Path(__file__).resolve().parent.parent.parent.parent
CONF_JSON = _PROJ_ROOT / "edge" / "data" / "cameras.json"


class CameraStreamService:
    """Xử lý proxy luồng video camera (MJPEG/HTTP), Snapshot và WebSocket live."""

    @staticmethod
    def get_camera_target_port(school_id: int, camera_id: int) -> int:
        """Xác định cổng stream nội bộ (8081, 8082, ...) dành riêng cho camera_id."""
        conn = get_db()
        try:
            cam = conn.execute(
                "SELECT id, camera_num, stream_type, stream_url FROM camera_stations WHERE id=? AND school_id=?",
                (camera_id, school_id)
            ).fetchone()
            if not cam:
                cam = conn.execute(
                    "SELECT id, camera_num, stream_type, stream_url FROM camera_stations WHERE school_id=? LIMIT 1",
                    (school_id,)
                ).fetchone()
        finally:
            conn.close()

        cam_dict = dict(cam) if cam else {}
        cam_num = cam_dict.get("camera_num")
        target_port = (8080 + int(cam_num)) if cam_num else 8081

        if CONF_JSON.is_file():
            try:
                with open(CONF_JSON, "r", encoding="utf-8") as f:
                    cfg_data = json.load(f)
                    for c_item in cfg_data.get("cameras", []):
                        if c_item.get("id") == camera_id:
                            target_port = c_item.get("stream_port", target_port)
                            break
            except Exception:
                pass
        return target_port

    @staticmethod
    async def probe_camera_port(target_port: int, max_retries: int = 3) -> bool:
        """Kiểm tra cổng stream của camera có đang phản hồi không."""
        for _ in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=1.0) as probe_client:
                    res = await probe_client.get(f"http://127.0.0.1:{target_port}/")
                    if res.status_code in (200, 301, 302):
                        return True
            except Exception:
                await asyncio.sleep(0.3)
        return False

    @staticmethod
    async def mjpeg_stream_generator(target_port: int) -> AsyncGenerator[bytes, None]:
        """Tạo generator truyền luồng MJPEG từ trạm camera cục bộ sang client."""
        stream_url = f"http://127.0.0.1:{target_port}/stream"
        client = httpx.AsyncClient(timeout=None)
        try:
            async with client.stream("GET", stream_url) as resp:
                if resp.status_code == 200:
                    async for chunk in resp.aiter_raw():
                        yield chunk
        except Exception as e:
            log.info(f"Client disconnected live stream (port {target_port}): {e}")
        finally:
            await client.aclose()

    @staticmethod
    async def fetch_camera_snapshot(target_port: int) -> bytes:
        """Lấy 1 frame ảnh JPEG snapshot tức thời từ camera."""
        snapshot_url = f"http://127.0.0.1:{target_port}/snapshot"
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                res = await client.get(snapshot_url)
                if res.status_code == 200:
                    return res.content
        except Exception:
            pass

        # Fallback đọc từ luồng stream nếu /snapshot chưa hỗ trợ
        stream_url = f"http://127.0.0.1:{target_port}/stream"
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                async with client.stream("GET", stream_url) as resp:
                    buf = b""
                    async for chunk in resp.aiter_raw():
                        buf += chunk
                        s = buf.find(b"\xff\xd8")
                        e = buf.find(b"\xff\xd9", s + 2)
                        if s != -1 and e != -1:
                            return buf[s:e + 2]
        except Exception as e:
            raise HTTPException(503, f"Không thể chụp ảnh từ trạm camera (Cổng {target_port}): {e}")

        raise HTTPException(503, f"Trạm camera (Cổng {target_port}) chưa sẵn sàng xuất ảnh.")

    @staticmethod
    async def proxy_camera_websocket(websocket: WebSocket, school_id: int, camera_id: int):
        """Chuyển tiếp frame video qua giao thức WebSocket cho client di động/yếu mạng."""
        await websocket.accept()
        target_port = CameraStreamService.get_camera_target_port(school_id, camera_id)
        stream_url = f"http://127.0.0.1:{target_port}/stream"

        client = httpx.AsyncClient(timeout=None)
        try:
            async with client.stream("GET", stream_url) as resp:
                buf = b""
                async for chunk in resp.aiter_raw():
                    buf += chunk
                    while True:
                        s = buf.find(b"\xff\xd8")
                        if s == -1:
                            buf = b""
                            break
                        e = buf.find(b"\xff\xd9", s + 2)
                        if e == -1:
                            buf = buf[s:]
                            break
                        jpg = buf[s:e + 2]
                        buf = buf[e + 2:]
                        await websocket.send_bytes(jpg)
                        await asyncio.sleep(0.01)
        except WebSocketDisconnect:
            log.info(f"WebSocket client disconnected from camera #{camera_id}")
        except Exception as e:
            log.warning(f"Error in camera #{camera_id} live WebSocket: {e}")
        finally:
            await client.aclose()
            try:
                await websocket.close()
            except Exception:
                pass
