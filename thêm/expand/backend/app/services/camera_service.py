"""
app/services/camera_service.py — Dịch vụ quản trị trạm camera AI & đồng bộ Edge
Tách biệt toàn bộ logic nghiệp vụ, xử lý cơ sở dữ liệu và đồng bộ tệp cấu hình.
"""
import os
import json
import secrets
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from fastapi import HTTPException

from app.database import get_db

log = logging.getLogger("stem.camera_service")

# Đường dẫn thư mục dữ liệu trạm Edge
_PROJ_ROOT = Path(__file__).resolve().parent.parent.parent.parent
EDGE_DATA_DIR = _PROJ_ROOT / "edge" / "data"


class CameraService:
    """Xử lý toàn bộ logic nghiệp vụ, database và đồng bộ file của Trạm Camera."""

    @staticmethod
    def list_cameras(school_id: int) -> List[Dict[str, Any]]:
        """Lấy danh sách tất cả các camera của một trường kèm link Tailscale HTTPS."""
        conn = get_db()
        try:
            rows = conn.execute(
                """SELECT id, camera_num, name, location, stream_type, stream_url, uniform_check, direction, status, last_ping_at, created_at, public_stream_url, tailscale_enabled 
                   FROM camera_stations WHERE school_id=? ORDER BY camera_num ASC, id ASC""",
                (school_id,)
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    @staticmethod
    def get_camera_by_id(school_id: int, camera_id: int) -> Optional[Dict[str, Any]]:
        """Lấy thông tin chi tiết một camera."""
        conn = get_db()
        try:
            row = conn.execute(
                "SELECT * FROM camera_stations WHERE id=? AND school_id=?",
                (camera_id, school_id)
            ).fetchone()
            if not row:
                return None
            return dict(row)
        finally:
            conn.close()

    @staticmethod
    def create_camera(school_id: int, name: Optional[str], location: Optional[str],
                      stream_type: str, stream_url: str, uniform_check: bool,
                      direction: str = "IN", occlusion_check: bool = True) -> Dict[str, Any]:
        """Tạo trạm camera mới và tự động sinh cấu hình + tự động xuất bản Tailscale HTTPS."""
        conn = get_db()
        try:
            cur_max = conn.execute(
                "SELECT COALESCE(MAX(camera_num), 0) FROM camera_stations WHERE school_id=?",
                (school_id,)
            ).fetchone()[0]
            camera_num = cur_max + 1

            c_name = name.strip() if name and name.strip() else f"Camera {camera_num}"
            c_loc = location.strip() if location and location.strip() else f"Cổng {camera_num}"
            c_type = stream_type.upper() if stream_type else "WEBCAM"
            c_url = stream_url.strip() if stream_url else "0"
            c_dir = direction.upper() if direction and direction.upper() in ("IN", "OUT", "BIDIRECTIONAL") else "IN"
            u_check = 1 if uniform_check else 0
            occ_check = 1 if occlusion_check else 0
            secret_key = secrets.token_urlsafe(24)

            conn.execute(
                """INSERT INTO camera_stations (school_id, camera_num, name, location, stream_type, stream_url, secret_key, status, uniform_check, occlusion_check, direction, tailscale_enabled)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,1)""",
                (school_id, camera_num, c_name, c_loc, c_type, c_url, secret_key, "OFFLINE", u_check, occ_check, c_dir)
            )
            conn.commit()
            camera_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

            # Đồng bộ cấu hình ra Edge
            CameraService.sync_camera_to_edge_conf(school_id, camera_id, {
                "name": c_name, "location": c_loc, "stream_type": c_type,
                "stream_url": c_url, "secret_key": secret_key, "uniform_check": u_check,
                "occlusion_check": occ_check, "direction": c_dir
            })
            CameraService.sync_all_cameras_to_edge_conf(school_id)

            return {
                "status": "success",
                "message": f"Đã khởi tạo thành công '{c_name}' ({c_type})!",
                "camera_id": camera_id,
                "camera_num": camera_num,
                "name": c_name,
                "location": c_loc,
                "stream_type": c_type,
                "stream_url": c_url,
                "secret_key": secret_key,
                "uniform_check": bool(u_check),
                "occlusion_check": bool(occ_check),
                "direction": c_dir
            }
        finally:
            conn.close()

    @staticmethod
    def update_camera(school_id: int, camera_id: int, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Cập nhật thông tin cấu hình trạm camera và tự động cập nhật link Tailscale HTTPS."""
        conn = get_db()
        try:
            row = conn.execute(
                "SELECT id, camera_num, secret_key, stream_type, stream_url FROM camera_stations WHERE id=? AND school_id=?",
                (camera_id, school_id)
            ).fetchone()
            if not row:
                raise HTTPException(404, "Không tìm thấy trạm camera.")

            fields = []
            values = []
            for k in ("name", "location", "stream_type", "stream_url", "uniform_check", "occlusion_check", "direction"):
                if k in updates and updates[k] is not None:
                    fields.append(f"{k}=?")
                    val = updates[k]
                    if k in ("uniform_check", "occlusion_check"):
                        val = 1 if val else 0
                    elif k == "direction":
                        val = str(val).upper() if str(val).upper() in ("IN", "OUT", "BIDIRECTIONAL") else "IN"
                    values.append(val)

            if fields:
                values.extend([camera_id, school_id])
                conn.execute(f"UPDATE camera_stations SET {', '.join(fields)} WHERE id=? AND school_id=?", tuple(values))
                conn.commit()

            # Đồng bộ lại ra tệp cấu hình Edge
            CameraService.sync_all_cameras_to_edge_conf(school_id)

            return {
                "status": "success",
                "message": "Đã cập nhật cấu hình camera thành công.",
                "camera_id": camera_id,
                "stream_url": final_url,
                "stream_type": final_type
            }
        finally:
            conn.close()

    @staticmethod
    def delete_camera(school_id: int, camera_id: int) -> Dict[str, Any]:
        """
        Xóa trạm camera an toàn:
        1. Gỡ liên kết trong attendance_logs (SET camera_station_id = NULL) để không vi phạm ràng buộc khóa ngoại
           và không làm mất lịch sử điểm danh của học sinh.
        2. Xóa khỏi bảng camera_stations.
        3. Tự động đồng bộ lại cameras.json để Supervisor tắt tiến trình camera ngay lập tức.
        """
        conn = get_db()
        try:
            row = conn.execute(
                "SELECT id, name FROM camera_stations WHERE id=? AND school_id=?",
                (camera_id, school_id)
            ).fetchone()
            if not row:
                raise HTTPException(404, "Không tìm thấy trạm camera cần xóa.")

            cam_name = row["name"]

            # BƯỚC 1: Gỡ khóa ngoại trong attendance_logs và security_alerts
            conn.execute(
                "UPDATE attendance_logs SET camera_station_id = NULL WHERE camera_station_id=?",
                (camera_id,)
            )
            conn.execute(
                "UPDATE security_alerts SET camera_station_id = NULL WHERE camera_station_id=?",
                (camera_id,)
            )

            # BƯỚC 2: Xóa khỏi bảng camera_stations
            conn.execute("DELETE FROM camera_stations WHERE id=?", (camera_id,))
            conn.commit()

            # BƯỚC 3: Đồng bộ lại file cameras.json
            CameraService.sync_all_cameras_to_edge_conf(school_id)
            log.info(f"[CAMERA] Đã xóa trạm camera #{camera_id} ({cam_name}) an toàn.")

            return {
                "status": "success",
                "message": f"Đã xóa trạm camera #{camera_id} ({cam_name}) thành công."
            }
        finally:
            conn.close()

    @staticmethod
    def toggle_uniform_check(school_id: int, camera_id: int, enabled: Optional[bool] = None) -> Dict[str, Any]:
        """Bật/tắt tính năng nhận diện đồng phục của trạm camera."""
        conn = get_db()
        try:
            row = conn.execute(
                "SELECT id, uniform_check, name FROM camera_stations WHERE id=? AND school_id=?",
                (camera_id, school_id)
            ).fetchone()
            if not row:
                raise HTTPException(404, "Không tìm thấy trạm camera.")

            curr = bool(row["uniform_check"]) if row["uniform_check"] is not None else True
            new_val = not curr if enabled is None else bool(enabled)

            conn.execute(
                "UPDATE camera_stations SET uniform_check=? WHERE id=?",
                (1 if new_val else 0, camera_id)
            )
            conn.commit()

            CameraService.sync_all_cameras_to_edge_conf(school_id)
            return {
                "status": "success",
                "camera_id": camera_id,
                "uniform_check": new_val,
                "message": f"Đã {'BẬT' if new_val else 'TẮT'} kiểm tra đồng phục cho {row['name']}."
            }
        finally:
            conn.close()

    @staticmethod
    def toggle_occlusion_check(school_id: int, camera_id: int, enabled: Optional[bool] = None) -> Dict[str, Any]:
        """Bật/tắt tính năng cảnh báo che khuất camera (Tamper Detection) của trạm camera."""
        conn = get_db()
        try:
            row = conn.execute(
                "SELECT id, occlusion_check, name FROM camera_stations WHERE id=? AND school_id=?",
                (camera_id, school_id)
            ).fetchone()
            if not row:
                raise HTTPException(404, "Không tìm thấy trạm camera.")

            curr = bool(row["occlusion_check"]) if row["occlusion_check"] is not None else True
            new_val = not curr if enabled is None else bool(enabled)

            conn.execute(
                "UPDATE camera_stations SET occlusion_check=? WHERE id=?",
                (1 if new_val else 0, camera_id)
            )
            conn.commit()

            CameraService.sync_all_cameras_to_edge_conf(school_id)
            return {
                "status": "success",
                "camera_id": camera_id,
                "occlusion_check": new_val,
                "message": f"Đã {'BẬT' if new_val else 'TẮT'} cảnh báo che khuất camera cho {row['name']}."
            }
        finally:
            conn.close()

    @staticmethod
    def ping_camera(school_id: int, camera_id: int, secret_key: Optional[str] = None) -> Dict[str, Any]:
        """Nhận nhịp tim (Heartbeat / Ping) từ trạm camera Edge."""
        conn = get_db()
        try:
            row = conn.execute(
                "SELECT id, secret_key, stream_url, stream_type, name FROM camera_stations WHERE id=? AND school_id=?",
                (camera_id, school_id)
            ).fetchone()
            if not row:
                raise HTTPException(404, "Không tìm thấy trạm camera.")

            if secret_key and row["secret_key"] != secret_key:
                raise HTTPException(403, "Secret key không khớp.")

            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            conn.execute(
                "UPDATE camera_stations SET status='ONLINE', last_ping_at=? WHERE id=?",
                (now_str, camera_id)
            )
            conn.commit()

            return {
                "status": "ok",
                "message": "Ping received.",
                "stream_url": row["stream_url"],
                "stream_type": row["stream_type"],
                "camera_name": row["name"]
            }
        finally:
            conn.close()

    @staticmethod
    def get_students_for_camera(school_id: int, camera_id: int, secret_key: str) -> List[Dict[str, Any]]:
        """Đồng bộ danh sách học sinh có mẫu khuôn mặt về trạm Edge."""
        if not secret_key:
            raise HTTPException(400, "Thiếu secret_key của trạm camera.")

        conn = get_db()
        try:
            station = conn.execute(
                "SELECT id FROM camera_stations WHERE id=? AND school_id=? AND secret_key=?",
                (camera_id, school_id, secret_key)
            ).fetchone()
            if not station:
                raise HTTPException(403, "Secret key không hợp lệ.")

            rows = conn.execute("""
                SELECT s.id, s.student_code, s.full_name, s.qr_token, s.face_photo_url, s.updated_at, c.name as class_name
                FROM students s
                LEFT JOIN classes c ON s.class_id = c.id
                WHERE s.school_id=? AND s.is_active=1 AND s.is_deleted=0
                ORDER BY s.student_code ASC
            """, (school_id,)).fetchall()
            stus = [dict(r) for r in rows]

            # Đính kèm danh sách ảnh mẫu đa góc (nếu có)
            sample_rows = conn.execute("""
                SELECT student_id, angle_type, image_url
                FROM student_face_samples
                WHERE school_id=?
                ORDER BY student_id, sample_index ASC
            """, (school_id,)).fetchall()
            samples_by_sid = {}
            for sr in sample_rows:
                sid = sr["student_id"]
                samples_by_sid.setdefault(sid, []).append({
                    "angle_type": sr["angle_type"],
                    "image_url": sr["image_url"]
                })
            for stu in stus:
                stu["samples"] = samples_by_sid.get(stu["id"], [])
            return stus
        finally:
            conn.close()

    # -------------------------------------------------------------------------
    # ĐỒNG BỘ CẤU HÌNH TỆP TIN EDGE (CONFIG SYNC)
    # -------------------------------------------------------------------------

    @staticmethod
    def sync_camera_to_edge_conf(school_id: int, camera_id: int, cam_data: dict) -> bool:
        """Đồng bộ cấu hình camera vào edge/data/camera.conf (tương thích 1 camera)."""
        try:
            EDGE_DATA_DIR.mkdir(parents=True, exist_ok=True)
            conf_path = EDGE_DATA_DIR / "camera.conf"

            stream_val = str(cam_data.get("stream_url", "0")).strip().strip('"\'')
            cam_name = str(cam_data.get("name", f"Camera {camera_id}")).strip().strip('"\'')
            location = str(cam_data.get("location", "Cổng")).strip().strip('"\'')
            stream_type = str(cam_data.get("stream_type", "WEBCAM")).strip().strip('"\'')
            secret_key = str(cam_data.get("secret_key", "")).strip().strip('"\'')
            u_check = bool(cam_data.get("uniform_check", 1))
            occ_check = bool(cam_data.get("occlusion_check", 1))

            content = f"""# Cấu hình trạm Camera AI Cổng Trường (EduSAMS Edge)
# Tự động đồng bộ từ Web Dashboard khi Lưu
[camera]
school_id       = {school_id}
camera_id       = {camera_id}
camera_name     = {cam_name}
location        = {location}
stream_type     = {stream_type}
stream_url      = {stream_val}
secret_key      = {secret_key}
server_url      = http://localhost:8000
uniform_check   = {'true' if u_check else 'false'}
occlusion_check = {'true' if occ_check else 'false'}
"""
            with open(conf_path, "w", encoding="utf-8") as f:
                f.write(content)
            return True
        except Exception as ex:
            log.warning(f"[CAMERA] Lỗi ghi camera.conf: {ex}")
            return False

    @staticmethod
    def sync_all_cameras_to_edge_conf(school_id: int) -> bool:
        """Đồng bộ toàn bộ danh sách camera vào edge/data/cameras.json cho Supervisor."""
        try:
            EDGE_DATA_DIR.mkdir(parents=True, exist_ok=True)
            json_path = EDGE_DATA_DIR / "cameras.json"

            conn = get_db()
            try:
                rows = conn.execute(
                    """SELECT id, school_id, camera_num, name, location, stream_type, stream_url, secret_key, uniform_check, occlusion_check, status 
                       FROM camera_stations WHERE school_id=? AND (status != 'DISABLED' OR status IS NULL)
                       ORDER BY camera_num ASC, id ASC""",
                    (school_id,)
                ).fetchall()
            finally:
                conn.close()

            cameras_list = []
            base_port = 8081
            for idx, r in enumerate(rows):
                c_dict = dict(r)
                c_dict["stream_port"] = base_port + idx
                c_dict["uniform_check"] = bool(c_dict.get("uniform_check", 1))
                c_dict["occlusion_check"] = bool(c_dict.get("occlusion_check", 1))
                cameras_list.append(c_dict)

            data = {
                "school_id": school_id,
                "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "cameras": cameras_list
            }

            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            # Đồng bộ camera cuối vào camera.conf nếu có
            if cameras_list:
                CameraService.sync_camera_to_edge_conf(school_id, cameras_list[-1]["id"], cameras_list[-1])

            # Tự động cập nhật go2rtc.yaml và reload go2rtc WebRTC Server
            try:
                gen_tool = _PROJ_ROOT / "edge" / "tools" / "gen_go2rtc_config.py"
                if gen_tool.is_file():
                    import subprocess
                    subprocess.run(["python3", str(gen_tool)], timeout=5.0, capture_output=True)
                    try:
                        import httpx
                        with httpx.Client(timeout=1.5) as hclient:
                            hclient.post("http://127.0.0.1:1984/api/restart")
                    except Exception:
                        pass
            except Exception as rtc_err:
                log.info(f"[CAMERA] Bỏ qua reload go2rtc: {rtc_err}")

            log.info(f"[CAMERA] Đã đồng bộ {len(cameras_list)} camera vào {json_path}")
            return True
        except Exception as ex:
            log.warning(f"[CAMERA] Lỗi đồng bộ cameras.json: {ex}")
            return False
