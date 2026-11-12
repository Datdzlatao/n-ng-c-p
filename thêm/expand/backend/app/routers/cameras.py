"""
app/routers/cameras.py — Camera station & RTSP / Webcam management (ADMIN / HEADMASTER)
Đã được module hóa sạch sẽ:
- Dịch vụ quản trị DB & Đồng bộ Edge : app.services.camera_service.CameraService
- Dịch vụ Streaming & WebSocket Relay: app.services.camera_stream_service.CameraStreamService
"""
import logging
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any

_PROJ_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(_PROJ_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJ_ROOT))

import base64
import time
from datetime import datetime
import httpx
from fastapi import APIRouter, HTTPException, Depends, Query, Header, WebSocket, Cookie, Request, BackgroundTasks
from fastapi.responses import StreamingResponse, Response
from pydantic import BaseModel

from app.database import get_db
from app.config import UPLOAD_DIR
from app.routers.websocket import broadcast_to_school
from app.core.deps import require_role
from app.core.security import decode_access_token
from app.services.camera_service import CameraService
from app.services.camera_stream_service import CameraStreamService

# Export lại các hàm tiện ích để tương thích ngược hoàn toàn
sync_camera_to_edge_conf = CameraService.sync_camera_to_edge_conf
sync_all_cameras_to_edge_conf = CameraService.sync_all_cameras_to_edge_conf

router = APIRouter(prefix="/api/v1/s/{school_id}/cameras", tags=["Cameras"])
log = logging.getLogger("stem.cameras")


# ─── Pydantic DTO Schemas ────────────────────────────────────────────────────

class CreateCamera(BaseModel):
    name:            Optional[str] = None
    location:        Optional[str] = None
    stream_type:     str = "WEBCAM"   # WEBCAM | RTSP | HTTP_CAM
    stream_url:      str = "0"        # "0", "1", "rtsp://...", "http://..."
    uniform_check:   bool = True      # Bật/tắt nhận diện đồng phục
    occlusion_check: bool = True      # Bật/tắt cảnh báo che camera (Tamper Detection)
    direction:       str = "IN"       # IN | OUT | BIDIRECTIONAL


class UpdateCamera(BaseModel):
    name:            Optional[str] = None
    location:        Optional[str] = None
    stream_type:     Optional[str] = None
    stream_url:      Optional[str] = None
    uniform_check:   Optional[bool] = None
    occlusion_check: Optional[bool] = None
    direction:       Optional[str] = None


class ToggleUniformRequest(BaseModel):
    enabled: Optional[bool] = None


class ToggleOcclusionRequest(BaseModel):
    enabled: Optional[bool] = None


class CameraPing(BaseModel):
    secret_key: Optional[str] = None


class CameraOcclusionAlert(BaseModel):
    secret_key: Optional[str] = None
    occlusion_percent: float = 60.0
    proof_image_base64: Optional[str] = None
    details: Optional[str] = None


class TestConnectionRequest(BaseModel):
    stream_url: Optional[str] = None


def _check_scope(school_id: int, current: dict):
    if current.get("role") in ("ADMIN", "PLATFORM_ADMIN"):
        return
    if current.get("school_id") != school_id:
        raise HTTPException(403, "Không thuộc quyền quản lý của trường này.")


# ─── 1. Quản lý CRUD Trạm Camera ─────────────────────────────────────────────

@router.get("")
async def list_cameras(
    school_id: int,
    current: dict = Depends(require_role("HEADMASTER", "INSPECTOR", "ADMIN"))
):
    """Lấy danh sách tất cả các trạm camera của trường."""
    _check_scope(school_id, current)
    return CameraService.list_cameras(school_id)


@router.post("")
async def create_camera(
    school_id: int,
    req: CreateCamera,
    current: dict = Depends(require_role("HEADMASTER", "ADMIN"))
):
    """Thêm trạm camera mới và tự động sinh cấu hình."""
    _check_scope(school_id, current)
    return CameraService.create_camera(
        school_id=school_id,
        name=req.name,
        location=req.location,
        stream_type=req.stream_type,
        stream_url=req.stream_url,
        uniform_check=req.uniform_check,
        direction=req.direction,
        occlusion_check=req.occlusion_check
    )


@router.put("/{camera_id}")
async def update_camera(
    school_id: int,
    camera_id: int,
    req: UpdateCamera,
    current: dict = Depends(require_role("HEADMASTER", "ADMIN"))
):
    """Cập nhật thông tin cấu hình trạm camera."""
    _check_scope(school_id, current)
    return CameraService.update_camera(school_id, camera_id, req.dict())


@router.delete("/{camera_id}")
async def delete_camera(
    school_id: int,
    camera_id: int,
    current: dict = Depends(require_role("HEADMASTER", "ADMIN"))
):
    """
    Xóa trạm camera an toàn:
    Tự động gỡ liên kết trong attendance_logs để chống lỗi Foreign Key Constraint
    và giữ nguyên 100% dữ liệu điểm danh của học sinh.
    """
    _check_scope(school_id, current)
    return CameraService.delete_camera(school_id, camera_id)


@router.post("/{camera_id}/toggle-uniform")
async def toggle_uniform_check(
    school_id: int,
    camera_id: int,
    req: Optional[ToggleUniformRequest] = None,
    current: dict = Depends(require_role("HEADMASTER", "ADMIN"))
):
    """Bật/tắt tính năng kiểm tra đồng phục cho trạm camera."""
    _check_scope(school_id, current)
    enabled = req.enabled if req else None
    return CameraService.toggle_uniform_check(school_id, camera_id, enabled)


@router.post("/{camera_id}/toggle-occlusion")
async def toggle_occlusion_check(
    school_id: int,
    camera_id: int,
    req: Optional[ToggleOcclusionRequest] = None,
    current: dict = Depends(require_role("HEADMASTER", "ADMIN", "INSPECTOR"))
):
    """Bật/tắt tính năng cảnh báo che camera (Tamper Detection >= 60%) cho trạm camera."""
    _check_scope(school_id, current)
    enabled = req.enabled if req else None
    return CameraService.toggle_occlusion_check(school_id, camera_id, enabled)


# ─── 2. Cấu hình & Đồng bộ Edge Client ────────────────────────────────────────

@router.get("/{camera_id}/edge-config")
async def get_edge_config(
    school_id: int,
    camera_id: int,
    current: dict = Depends(require_role("HEADMASTER", "ADMIN"))
):
    """Lấy đoạn mã cấu hình Python và INI cho máy trạm Raspberry Pi / Laptop."""
    _check_scope(school_id, current)
    cam = CameraService.get_camera_by_id(school_id, camera_id)
    if not cam:
        raise HTTPException(404, "Không tìm thấy camera.")

    stream_val = cam["stream_url"]
    cam_index_val = f'"{stream_val}"' if not str(stream_val).isdigit() else int(stream_val)
    pi_conf = f"""[camera]
school_id   = {school_id}
camera_id   = {camera_id}
camera_name = {cam['name']}
secret_key  = {cam['secret_key']}
stream_type = {cam['stream_type']}
stream_url  = {stream_val}
server_url  = http://localhost:8000
"""
    edge_code = f"""SCHOOL_ID       = {school_id}
CAMERA_ID       = {camera_id}
CAMERA_NAME     = "{cam['name']}"
CAMERA_LOCATION = "{cam['location'] or 'Cổng'}"
STREAM_TYPE     = "{cam['stream_type']}"
CAMERA_INDEX    = {cam_index_val}
CAMERA_SECRET   = "{cam['secret_key']}"
SERVER_API_URL  = "http://localhost:8000"
"""
    return {
        "status": "success",
        "camera_id": camera_id,
        "raspberry_pi_conf": pi_conf,
        "edge_config_snippet": edge_code,
        "camera": cam
    }


@router.post("/{camera_id}/apply-local")
async def apply_local_camera(
    school_id: int,
    camera_id: int,
    current: dict = Depends(require_role("HEADMASTER", "ADMIN"))
):
    """Lập tức đồng bộ cấu hình camera này vào file cục bộ edge/data/camera.conf."""
    _check_scope(school_id, current)
    cam = CameraService.get_camera_by_id(school_id, camera_id)
    if not cam:
        raise HTTPException(404, "Không tìm thấy camera.")

    ok = CameraService.sync_camera_to_edge_conf(school_id, camera_id, cam)
    CameraService.sync_all_cameras_to_edge_conf(school_id)
    if not ok:
        raise HTTPException(500, "Không thể ghi cấu hình vào edge/data/camera.conf.")

    return {
        "status": "success",
        "message": f"Đã áp dụng trạm '{cam['name']}' vào hệ thống camera cục bộ!",
        "camera": cam
    }


@router.get("/{camera_id}/runtime-config")
async def get_runtime_config(
    school_id: int,
    camera_id: int,
    secret_key: Optional[str] = Query(None)
):
    """Trạm camera Edge đọc cấu hình runtime động khi khởi động."""
    if not secret_key:
        raise HTTPException(400, "Thiếu secret_key.")
    cam = CameraService.get_camera_by_id(school_id, camera_id)
    if not cam:
        raise HTTPException(404, "Không tìm thấy trạm camera.")
    if cam["secret_key"] != secret_key:
        raise HTTPException(403, "Secret key không hợp lệ.")

    return {
        "status": "success",
        "school_id": school_id,
        "camera_id": camera_id,
        "camera_name": cam["name"],
        "stream_type": cam["stream_type"],
        "stream_url": cam["stream_url"],
        "uniform_check": bool(cam.get("uniform_check", 1))
    }


@router.post("/{camera_id}/ping")
async def camera_ping(
    school_id: int,
    camera_id: int,
    secret_key: Optional[str] = Query(None),
    req: Optional[CameraPing] = None
):
    """Nhận nhịp tim (Heartbeat) định kỳ từ trạm camera Edge."""
    s_key = (req.secret_key if req and req.secret_key else None) or secret_key
    return CameraService.ping_camera(school_id, camera_id, s_key)


@router.get("/{camera_id}/students")
async def camera_get_students(
    school_id: int,
    camera_id: int,
    secret_key: Optional[str] = Query(None)
):
    """Đồng bộ danh bạ học sinh về máy trạm Edge."""
    return CameraService.get_students_for_camera(school_id, camera_id, secret_key or "")


# ─── 2.1. Tự Động Xuất Bản Tailscale HTTPS ──────────────────────────────────

@router.get("/tailscale-status")
async def get_tailscale_status(
    school_id: int,
    current: dict = Depends(require_role("HEADMASTER", "ADMIN", "INSPECTOR"))
):
    """Lấy trạng thái kết nối daemon Tailscale và cấu hình Funnel HTTPS."""
    _check_scope(school_id, current)
    from app.services.tailscale_service import TailscaleService
    return TailscaleService.get_status()


@router.post("/{camera_id}/publish-tailscale")
async def publish_camera_tailscale(
    school_id: int,
    camera_id: int,
    current: dict = Depends(require_role("HEADMASTER", "ADMIN"))
):
    """Kích hoạt và xuất bản luồng camera sang link HTTPS Tailscale Funnel."""
    _check_scope(school_id, current)
    cam = CameraService.get_camera_by_id(school_id, camera_id)
    if not cam:
        raise HTTPException(404, "Không tìm thấy camera.")
    from app.services.tailscale_service import TailscaleService
    return TailscaleService.auto_publish_camera(school_id, camera_id, stream_url=cam.get("stream_url"))


@router.post("/tailscale/enable-funnel")
async def enable_tailscale_funnel(
    school_id: int,
    current: dict = Depends(require_role("HEADMASTER", "ADMIN"))
):
    """Kích hoạt Tailscale Funnel trên cổng 8000 để mở HTTPS toàn cầu."""
    _check_scope(school_id, current)
    from app.services.tailscale_service import TailscaleService
    return TailscaleService.ensure_funnel(port=8000)


# ─── 3. Quét Mạng & Tự Động Sửa IP Camera ────────────────────────────────────

@router.post("/discover")
async def discover_lan_cameras(
    school_id: int,
    current: dict = Depends(require_role("HEADMASTER", "ADMIN"))
):
    """Quét toàn bộ mạng LAN tìm camera IP (RTSP/ONVIF)."""
    _check_scope(school_id, current)
    try:
        from edge.net_discovery import discover_cameras, get_local_network_info
        return {
            "status": "success",
            "local_network": get_local_network_info(),
            "cameras": discover_cameras(timeout_per_ip=0.8),
        }
    except Exception as e:
        log.error(f"[CAM DISCOVERY] Lỗi: {e}")
        raise HTTPException(500, f"Lỗi khi quét mạng LAN: {str(e)}")


@router.post("/{camera_id}/test-connection")
async def test_camera_connection(
    school_id: int,
    camera_id: int,
    req: Optional[TestConnectionRequest] = None,
    current: dict = Depends(require_role("HEADMASTER", "ADMIN"))
):
    """Kiểm tra chẩn đoán kết nối tức thì tới camera."""
    _check_scope(school_id, current)
    target_url = None
    if req and req.stream_url and req.stream_url.strip():
        target_url = req.stream_url.strip()
    else:
        cam = CameraService.get_camera_by_id(school_id, camera_id)
        if not cam:
            raise HTTPException(404, "Không tìm thấy camera.")
        if cam["stream_type"] == "WEBCAM":
            return {
                "status": "success",
                "message": "Webcam cắm cổng USB cục bộ, hoạt động trực tiếp qua phần cứng máy tính.",
                "is_webcam": True
            }
        target_url = cam["stream_url"]

    try:
        from edge.net_discovery import check_camera_connection
        return check_camera_connection(target_url)
    except Exception as e:
        raise HTTPException(500, f"Lỗi kiểm tra kết nối: {str(e)}")


@router.post("/{camera_id}/occlusion-alert")
async def report_camera_occlusion(
    school_id: int,
    camera_id: int,
    req: CameraOcclusionAlert,
    background_tasks: BackgroundTasks
):
    """
    Tiếp nhận cảnh báo camera bị che khuất (>=60%) từ máy trạm Edge hoặc kiểm tra.
    Tự động ghi nhận Security Alert và phát thông báo khẩn cấp qua WebSocket cho Giám Thị & BGH.
    """
    conn = get_db()
    try:
        station = conn.execute(
            "SELECT * FROM camera_stations WHERE id=? AND school_id=?",
            (camera_id, school_id)
        ).fetchone()
        if not station:
            raise HTTPException(404, "Không tìm thấy trạm camera.")

        if req.secret_key and station["secret_key"] and req.secret_key != station["secret_key"]:
            raise HTTPException(401, "Mã bí mật trạm camera không khớp.")

        # Kiểm tra nếu tính năng cảnh báo che khuất đang bị tắt trên camera này
        if station["occlusion_check"] == 0:
            return {
                "status": "ignored",
                "message": f"Tính năng cảnh báo che khuất đang TẮT trên trạm '{station['name']}'."
            }

        st_name = station["name"] or f"Camera #{camera_id}"
        st_loc = station["location"] or "Khu vực cổng trường"
        occlusion_pct = round(float(req.occlusion_percent), 1)

        # Lưu ảnh bằng chứng nếu có
        proof_image_url = None
        if req.proof_image_base64:
            try:
                proofs_dir = UPLOAD_DIR / "proofs"
                proofs_dir.mkdir(parents=True, exist_ok=True)
                raw_b64 = req.proof_image_base64
                if "," in raw_b64:
                    raw_b64 = raw_b64.split(",", 1)[1]
                img_bytes = base64.b64decode(raw_b64)
                fn = f"occlusion_{school_id}_{camera_id}_{int(time.time()*1000)}.jpg"
                (proofs_dir / fn).write_bytes(img_bytes)
                proof_image_url = f"/uploads/proofs/{fn}"
            except Exception as e:
                log.warning(f"Không thể lưu ảnh che khuất camera: {e}")

        now_dt = datetime.now()
        iso_timestamp = now_dt.isoformat()
        date_only = now_dt.strftime("%Y-%m-%d")

        alert_title = f"🚨 CẢNH BÁO: CAMERA BỊ CHE KHUẤT ({int(occlusion_pct)}%)"
        alert_desc = f"Camera '{st_name}' ({st_loc}) đang bị che khuất {occlusion_pct}%, mất khả năng nhìn thấy! Giám thị và Ban Giám Hiệu cần kiểm tra xử lý ngay."

        # Chống spam cảnh báo nếu vừa mới gửi trong vòng 20 giây gần nhất cho cùng camera
        recent_alert = conn.execute("""
            SELECT id, timestamp FROM security_alerts
            WHERE school_id=? AND camera_station_id=? AND alert_type='CAMERA_OCCLUSION' AND date_only=?
            ORDER BY id DESC LIMIT 1
        """, (school_id, camera_id, date_only)).fetchone()

        should_insert = True
        if recent_alert:
            try:
                r_dt = datetime.fromisoformat(recent_alert["timestamp"].replace(" ", "T"))
                if abs((now_dt - r_dt).total_seconds()) < 20:
                    should_insert = False
                    if proof_image_url:
                        conn.execute("UPDATE security_alerts SET proof_image_url=? WHERE id=?", (proof_image_url, recent_alert["id"]))
                        conn.commit()
            except Exception:
                pass

        if should_insert:
            conn.execute("""
                INSERT INTO security_alerts (school_id, camera_station_id, alert_type, title, description, direction, proof_image_url, timestamp, date_only)
                VALUES (?, ?, 'CAMERA_OCCLUSION', ?, ?, 'IN', ?, ?, ?)
            """, (school_id, camera_id, alert_title, alert_desc, proof_image_url, iso_timestamp, date_only))
            conn.commit()

            # Phát thông báo khẩn cấp qua WebSocket cho toàn bộ Giám Thị, BGH, Giáo Viên
            ws_payload = {
                "type": "SECURITY_ALERT",
                "alert_type": "CAMERA_OCCLUSION",
                "title": alert_title,
                "message": alert_desc,
                "station_name": st_name,
                "station_id": camera_id,
                "location": st_loc,
                "occlusion_percent": occlusion_pct,
                "timestamp": iso_timestamp,
                "proof_image_url": proof_image_url
            }
            background_tasks.add_task(broadcast_to_school, school_id, ws_payload)
            log.warning(f"[SECURITY] 🚨 Cảnh báo camera bị che khuất: {st_name} ({occlusion_pct}%) tại trường {school_id}")

        return {
            "status": "success",
            "message": f"Đã ghi nhận cảnh báo che khuất camera {st_name} ({occlusion_pct}%)",
            "camera_id": camera_id,
            "camera_name": st_name,
            "occlusion_percent": occlusion_pct,
            "proof_image_url": proof_image_url
        }
    finally:
        conn.close()


@router.post("/{camera_id}/test-occlusion-alert")
async def test_camera_occlusion_alert(
    school_id: int,
    camera_id: int,
    background_tasks: BackgroundTasks,
    current: dict = Depends(require_role("HEADMASTER", "INSPECTOR", "ADMIN"))
):
    """Kiểm thử tính năng gửi cảnh báo camera bị che khuất (>60%) về Giám Thị & BGH."""
    _check_scope(school_id, current)
    test_req = CameraOcclusionAlert(
        occlusion_percent=75.0,
        details="Thử nghiệm cảnh báo camera bị che khuất 75% từ Web Dashboard"
    )
    return await report_camera_occlusion(school_id, camera_id, test_req, background_tasks)


@router.post("/{camera_id}/auto-fix-ip")
async def auto_fix_camera_ip(
    school_id: int,
    camera_id: int,
    current: dict = Depends(require_role("HEADMASTER", "ADMIN"))
):
    """Tự động sửa IP camera khi đổi modem Wi-Fi."""
    _check_scope(school_id, current)
    cam = CameraService.get_camera_by_id(school_id, camera_id)
    if not cam:
        raise HTTPException(404, "Không tìm thấy camera.")
    old_url = cam["stream_url"]
    if cam["stream_type"] != "RTSP" or not str(old_url).startswith("rtsp://"):
        raise HTTPException(400, "Chỉ áp dụng cho Camera luồng RTSP.")

    from edge.net_discovery import discover_cameras, parse_rtsp_url, check_camera_connection
    parsed = parse_rtsp_url(old_url)
    old_ip = parsed["host"]

    curr_test = check_camera_connection(old_url)
    if curr_test.get("status") == "success":
        return {
            "status": "success",
            "message": f"Camera (IP {old_ip}) đang kết nối rất tốt, không cần sửa đổi.",
            "camera": cam,
            "test": curr_test
        }

    discovered = discover_cameras(timeout_per_ip=0.8)
    if not discovered:
        raise HTTPException(404, "Không tìm thấy Camera RTSP nào trong mạng LAN hiện tại.")

    new_ip = discovered[0]["ip"]
    user_part = f"{parsed['user']}:{parsed['password']}@" if parsed["user"] else ""
    port_part = f":{parsed['port']}" if parsed["port"] != 554 else ":554"
    path_part = parsed["path"] if parsed["path"] else "/Streaming/Channels/101"
    new_url = f"rtsp://{user_part}{new_ip}{port_part}{path_part}"

    CameraService.update_camera(school_id, camera_id, {"stream_url": new_url})
    new_test = check_camera_connection(new_url)

    return {
        "status": "success",
        "message": f"Đã tự động đổi IP camera từ {old_ip} sang {new_ip} thành công!",
        "old_ip": old_ip,
        "new_ip": new_ip,
        "new_url": new_url,
        "test": new_test
    }


# ─── 4. Video Streaming, Snapshot & WebSocket Live ───────────────────────────

def _authorize_viewer(
    token: Optional[str],
    authorization: str,
    school_id: int,
    camera_id: Optional[int] = None,
    key: Optional[str] = None,
    cookie_token: Optional[str] = None
):
    """
    Xác thực người xem luồng video:
    1. Hỗ trợ khóa bảo mật trạm camera ?key=... hoặc ?secret=... (xem trực tiếp vĩnh viễn trên VLC / OBS / Browser).
    2. Hỗ trợ Cookie đăng nhập của trình duyệt (access_token).
    3. Hỗ trợ Token JWT qua query param (?token=...) hoặc Header Bearer.
    """
    # 1. Khóa trạm camera vĩnh viễn (?key=... hoặc ?secret=...)
    if key and camera_id:
        from app.database import get_db
        conn = get_db()
        try:
            cam = conn.execute(
                "SELECT secret_key FROM camera_stations WHERE id=? AND school_id=?",
                (camera_id, school_id)
            ).fetchone()
            if cam and cam["secret_key"] and cam["secret_key"].strip() == key.strip():
                return {"role": "CAMERA_KEY", "school_id": school_id}
        finally:
            conn.close()

    # 2. Token JWT qua Query param, Cookie hoặc Header Authorization
    jwt_token = token or cookie_token
    if not jwt_token and authorization.startswith("Bearer "):
        jwt_token = authorization.removeprefix("Bearer ").strip()

    claims = decode_access_token(jwt_token) if jwt_token else None
    if not claims:
        raise HTTPException(
            401,
            "Vui lòng đăng nhập trên trang Web để xem camera, hoặc dùng link có gắn ?token=... hoặc ?key=SECRET_KEY của camera."
        )

    role = claims.get("role", "")
    allowed = ("ADMIN", "PLATFORM_ADMIN", "HEADMASTER", "INSPECTOR", "TEACHER")
    if role not in allowed:
        raise HTTPException(403, "Không có quyền xem trực tiếp camera.")
    if role not in ("ADMIN", "PLATFORM_ADMIN") and claims.get("school_id") != school_id:
        raise HTTPException(403, "Không thuộc trường này.")
    return claims


@router.get("/{camera_id}/live-stream")
async def camera_live_stream(
    school_id: int,
    camera_id: int,
    token: Optional[str] = Query(None),
    key: Optional[str] = Query(None),
    secret: Optional[str] = Query(None),
    access_token: Optional[str] = Cookie(None),
    authorization: str = Header(default=""),
):
    """Proxy an toàn luồng MJPEG sang giao thức HTTPS của Web / Tailscale."""
    eff_key = key or secret
    _authorize_viewer(token, authorization, school_id, camera_id=camera_id, key=eff_key, cookie_token=access_token)
    target_port = CameraStreamService.get_camera_target_port(school_id, camera_id)

    is_ready = await CameraStreamService.probe_camera_port(target_port)
    if not is_ready:
        raise HTTPException(
            503,
            f"Trạm camera AI #{camera_id} (Cổng {target_port}) đang khởi động hoặc chưa sẵn sàng."
        )

    return StreamingResponse(
        CameraStreamService.mjpeg_stream_generator(target_port),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*",
        }
    )


@router.get("/{camera_id}/snapshot")
async def camera_snapshot(
    school_id: int,
    camera_id: int,
    token: Optional[str] = Query(None),
    key: Optional[str] = Query(None),
    secret: Optional[str] = Query(None),
    access_token: Optional[str] = Cookie(None),
    authorization: str = Header(default=""),
):
    """Xuất 1 frame ảnh JPEG snapshot tức thời từ camera."""
    eff_key = key or secret
    _authorize_viewer(token, authorization, school_id, camera_id=camera_id, key=eff_key, cookie_token=access_token)
    target_port = CameraStreamService.get_camera_target_port(school_id, camera_id)
    img_bytes = await CameraStreamService.fetch_camera_snapshot(target_port)
    return Response(
        content=img_bytes,
        media_type="image/jpeg",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate, max-age=0",
            "Access-Control-Allow-Origin": "*",
        }
    )


@router.websocket("/{camera_id}/live-ws")
async def camera_live_ws(
    websocket: WebSocket,
    school_id: int,
    camera_id: int
):
    """Truyền phát video qua WebSocket cho thiết bị mạng yếu."""
    await CameraStreamService.proxy_camera_websocket(websocket, school_id, camera_id)


@router.post("/{camera_id}/webrtc")
async def camera_webrtc_whep(
    school_id: int,
    camera_id: int,
    request: Request,
    stream_type: str = Query("ai", pattern="^(ai|raw)$"),
    token: Optional[str] = Query(None),
    key: Optional[str] = Query(None),
    secret: Optional[str] = Query(None),
    access_token: Optional[str] = Cookie(None),
    authorization: str = Header(default=""),
):
    """WebRTC WHEP signaling: nhận SDP offer từ trình duyệt, đàm phán với go2rtc trả về SDP answer."""
    eff_key = key or secret
    _authorize_viewer(token, authorization, school_id, camera_id=camera_id, key=eff_key, cookie_token=access_token)
    stream_name = f"cam_{camera_id}_{stream_type}"
    sdp_offer = await request.body()

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            res = await client.post(
                f"http://127.0.0.1:1984/api/webrtc?src={stream_name}",
                content=sdp_offer,
                headers={"Content-Type": "application/sdp"}
            )
            return Response(
                content=res.content,
                status_code=res.status_code,
                media_type="application/sdp",
                headers={"Access-Control-Allow-Origin": "*"}
            )
        except Exception as e:
            raise HTTPException(502, f"Máy chủ WebRTC (go2rtc) chưa khởi động hoặc gặp lỗi: {e}")

