# -*- coding: utf-8 -*-
"""
=============================================================
  STEM CAMERA EDGE — SERVER BRIDGE (HEARTBEAT, OFFLINE QUEUE & FACE SYNC)
  edge/server_bridge.py
  
  Chức năng:
  - Tự động gửi Heartbeat Ping định kỳ lên Máy Chủ Trường Học
    để hiển thị trạng thái 🟢 ONLINE trên Web Dashboard.
  - Đồng bộ sự kiện điểm danh & vi phạm theo thời gian thực (ThreadPoolExecutor).
  - Tự động lưu hàng đợi ngoại tuyến (SQLite Offline Queue) khi mất mạng,
    tự động đẩy bù 100% dữ liệu khi kết nối được phục hồi.
  - Tự động đồng bộ FaceID từ Máy Chủ (Face Sync Engine): Tải ảnh học sinh mới
    về thư mục cục bộ edge/data/faces và kích hoạt tính lại embeddings.
=============================================================
"""

import os
import time
import json
import sqlite3
import threading
import urllib.request
import urllib.error
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Dict, Any, List

import base64

try:
    from config import (
        SERVER_API_URL, SCHOOL_ID, CAMERA_ID, CAMERA_SECRET,
        OFFLINE_PROOFS_RETENTION_DAYS
    )
except ImportError:
    SERVER_API_URL = "http://localhost:8000"
    SCHOOL_ID      = 1
    CAMERA_ID      = 1
    CAMERA_SECRET  = ""
    OFFLINE_PROOFS_RETENTION_DAYS = 7

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
OFFLINE_DB_PATH = os.path.join(DATA_DIR, "edge_offline_queue.db")
OFFLINE_PROOFS_DIR = os.path.join(DATA_DIR, "offline_proofs")
DEFAULT_FACES_DIR = os.path.join(DATA_DIR, "faces")


class ServerBridge:
    def __init__(self, api_url=None, school_id=None, camera_id=None, secret_key=None, faces_dir=None):
        self.api_url    = (api_url or SERVER_API_URL).rstrip('/')
        self.school_id  = school_id or SCHOOL_ID
        self.camera_id  = camera_id or CAMERA_ID
        self.secret_key = secret_key or CAMERA_SECRET
        self.faces_dir  = faces_dir or DEFAULT_FACES_DIR
        self.is_running = True
        self.is_online  = False
        self.current_stream_url = None
        self.current_stream_type = None
        self.on_config_change = None

        # Bounded ThreadPool (tối đa 4 workers) thay vì sinh thread vô hạn
        self._executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="EdgeBridgePool")
        self._db_lock = threading.Lock()

        # Khởi tạo SQLite Queue cho ngoại tuyến
        self._init_offline_db()

        # Start heartbeat + sync queue thread
        self.heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True, name="EdgeServerHeartbeat")
        self.heartbeat_thread.start()

        # Kích hoạt Face Sync ngầm khi vừa khởi tạo
        self._executor.submit(self.sync_faces_from_server)

    # -------------------------------------------------------------------------
    # 1. SQLITE OFFLINE QUEUE
    # -------------------------------------------------------------------------
    def _init_offline_db(self):
        """Khởi tạo bảng lưu trữ hàng đợi điểm danh ngoại tuyến và thư mục ảnh tạm."""
        os.makedirs(DATA_DIR, exist_ok=True)
        os.makedirs(OFFLINE_PROOFS_DIR, exist_ok=True)
        try:
            with self._db_lock:
                conn = sqlite3.connect(OFFLINE_DB_PATH)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS edge_pending_sync (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        school_id INTEGER NOT NULL,
                        endpoint TEXT NOT NULL,
                        payload TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        retry_count INTEGER DEFAULT 0
                    )
                """)
                conn.commit()
                conn.close()
        except Exception as e:
            print(f"[SERVER BRIDGE] Lỗi khởi tạo SQLite Queue: {e}")

    def _enqueue_offline(self, endpoint: str, payload: dict):
        """Lưu bản ghi điểm danh vào hàng đợi cục bộ khi mạng lỗi (tách ảnh ra file nhị phân tránh phình SQLite)."""
        try:
            payload_copy = dict(payload)
            proof_b64 = payload_copy.pop("proof_image_base64", None)

            # Tách ảnh Base64 ra file đĩa nhị phân riêng — giảm kích thước SQLite > 99%
            if proof_b64:
                try:
                    os.makedirs(OFFLINE_PROOFS_DIR, exist_ok=True)
                    clean_b64 = proof_b64.split(",", 1)[1] if "," in proof_b64 else proof_b64
                    img_bytes = base64.b64decode(clean_b64)
                    stu_code_clean = str(payload.get("student_code", "UNKNOWN")).replace("/", "_").replace(" ", "_")
                    fn = f"offline_{stu_code_clean}_{int(time.time() * 1000)}.jpg"
                    fp = os.path.join(OFFLINE_PROOFS_DIR, fn)
                    with open(fp, "wb") as f_img:
                        f_img.write(img_bytes)
                    payload_copy["proof_image_offline_path"] = fp
                except Exception as _e_save:
                    print(f"  [OFFLINE QUEUE] ⚠️ Không thể lưu file ảnh offline: {_e_save}")

            with self._db_lock:
                conn = sqlite3.connect(OFFLINE_DB_PATH)
                conn.execute("""
                    INSERT INTO edge_pending_sync (school_id, endpoint, payload, created_at, retry_count)
                    VALUES (?, ?, ?, ?, 0)
                """, (self.school_id, endpoint, json.dumps(payload_copy), datetime.now().isoformat()))
                conn.commit()
                conn.close()
            stu_code = payload.get("student_code", "UNKNOWN")
            print(f"  [OFFLINE QUEUE] 💾 Đã lưu tạm sự kiện ({stu_code}) vào SQLite cục bộ (chờ có mạng để gửi bù).")
        except Exception as e:
            print(f"  [OFFLINE QUEUE] ⚠️ Không thể ghi hàng đợi SQLite: {e}")

    def _cleanup_orphaned_offline_proofs(self):
        """Quét và xóa các file ảnh tạm offline mồ côi cũ hơn OFFLINE_PROOFS_RETENTION_DAYS."""
        if not os.path.isdir(OFFLINE_PROOFS_DIR):
            return
        cutoff = time.time() - (OFFLINE_PROOFS_RETENTION_DAYS * 86400)
        try:
            for f in os.listdir(OFFLINE_PROOFS_DIR):
                fp = os.path.join(OFFLINE_PROOFS_DIR, f)
                if os.path.isfile(fp) and os.path.getmtime(fp) < cutoff:
                    try:
                        os.remove(fp)
                    except OSError:
                        pass
        except Exception:
            pass

    def _flush_offline_queue(self):
        """Đẩy bù các bản ghi điểm danh ngoại tuyến khi mạng phục hồi."""
        if not self.is_online:
            return

        records = []
        try:
            with self._db_lock:
                conn = sqlite3.connect(OFFLINE_DB_PATH)
                conn.row_factory = sqlite3.Row
                rows = conn.execute("""
                    SELECT id, endpoint, payload, retry_count
                    FROM edge_pending_sync
                    ORDER BY id ASC LIMIT 30
                """).fetchall()
                records = [dict(r) for r in rows]
                conn.close()
        except Exception as e:
            print(f"[OFFLINE QUEUE] Lỗi đọc queue: {e}")
            return

        if not records:
            return

        print(f"[OFFLINE QUEUE] 🔄 Đang đẩy bù {len(records)} bản ghi điểm danh ngoại tuyến lên Cloud...")
        success_ids = []
        cleaned_files = []

        for item in records:
            url = f"{self.api_url}{item['endpoint']}"
            proof_offline_path = None
            try:
                payload_dict = json.loads(item["payload"])
                proof_offline_path = payload_dict.pop("proof_image_offline_path", None)

                # Nạp Base64 đúng lúc (Just-in-Time) từ file ảnh nhị phân
                if proof_offline_path and os.path.isfile(proof_offline_path):
                    try:
                        with open(proof_offline_path, "rb") as f_img:
                            payload_dict["proof_image_base64"] = base64.b64encode(f_img.read()).decode("utf-8")
                    except Exception as _e_read:
                        print(f"  [OFFLINE QUEUE] ⚠️ Không thể nạp lại ảnh offline: {_e_read}")

                data = json.dumps(payload_dict).encode("utf-8")
                req = urllib.request.Request(url, data=data, method="POST")
                req.add_header("Content-Type", "application/json")
                with urllib.request.urlopen(req, timeout=6) as resp:
                    if resp.status in (200, 201):
                        success_ids.append(item["id"])
                        if proof_offline_path and os.path.isfile(proof_offline_path):
                            cleaned_files.append(proof_offline_path)
            except Exception as e:
                # Gặp lỗi -> dừng đợt flush này, thử lại ở chu kỳ sau
                try:
                    with self._db_lock:
                        conn = sqlite3.connect(OFFLINE_DB_PATH)
                        conn.execute("UPDATE edge_pending_sync SET retry_count = retry_count + 1 WHERE id=?", (item["id"],))
                        conn.commit()
                        conn.close()
                except Exception:
                    pass
                break

        if success_ids:
            try:
                with self._db_lock:
                    conn = sqlite3.connect(OFFLINE_DB_PATH)
                    conn.execute(f"DELETE FROM edge_pending_sync WHERE id IN ({','.join('?' * len(success_ids))})", success_ids)
                    conn.commit()
                    conn.close()
                # Xóa các file ảnh tạm đã đồng bộ thành công
                for cfp in cleaned_files:
                    try:
                        os.remove(cfp)
                    except OSError:
                        pass
                print(f"[OFFLINE QUEUE] ✅ Đã đồng bộ bù thành công {len(success_ids)} bản ghi lên Web Dashboard!")
            except Exception as e:
                print(f"[OFFLINE QUEUE] Lỗi xóa bản ghi đã đồng bộ: {e}")

    # -------------------------------------------------------------------------
    # 2. HEARTBEAT & RUNTIME CONFIG
    # -------------------------------------------------------------------------
    def fetch_runtime_config(self):
        """Zero-Touch Provisioning: Tự động lấy cấu hình camera (RTSP URL / Webcam) mới nhất từ Server."""
        if not self.secret_key or not self.school_id or not self.camera_id:
            return None
        url = f"{self.api_url}/api/v1/s/{self.school_id}/cameras/{self.camera_id}/runtime-config?secret_key={self.secret_key}"
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode('utf-8'))
                    self.current_stream_url = data.get("stream_url")
                    self.current_stream_type = data.get("stream_type")
                    return data
        except Exception as e:
            print(f"[SERVER BRIDGE] ⚠️ Không thể lấy runtime config từ Server: {e}")
        return None

    def _heartbeat_loop(self):
        """Send heartbeat to keep camera ONLINE on dashboard, with exponential backoff on network drop."""
        time.sleep(1)
        current_delay = 8.0
        MAX_DELAY = 90.0
        last_face_sync_time = time.time()

        while self.is_running:
            if not self.secret_key or not self.school_id or not self.camera_id:
                time.sleep(5)
                continue

            url = f"{self.api_url}/api/v1/s/{self.school_id}/cameras/{self.camera_id}/ping"
            try:
                body = json.dumps({"secret_key": self.secret_key}).encode("utf-8")
                req  = urllib.request.Request(url, data=body, method="POST")
                req.add_header("Content-Type", "application/json")
                with urllib.request.urlopen(req, timeout=4) as resp:
                    if resp.status == 200:
                        raw = resp.read().decode("utf-8")
                        data = json.loads(raw) if raw else {}
                        server_stream_url = data.get("stream_url")
                        server_stream_type = data.get("stream_type")

                        if not self.is_online:
                            self.is_online = True
                            print(f"[SERVER BRIDGE] 🟢 Đã kết nối Máy Chủ Trường #{self.school_id} (Camera #{self.camera_id}) -> ONLINE")
                            # Mạng vừa online lại -> Đẩy bù ngay hàng đợi offline
                            self._executor.submit(self._flush_offline_queue)

                        # Tự động phát hiện khi Admin đổi RTSP Link trên Web Dashboard
                        if server_stream_url and self.current_stream_url and server_stream_url != self.current_stream_url:
                            print(f"\n[SERVER BRIDGE] 🔄 PHÁT HIỆN ADMIN VỪA ĐỔI CẤU HÌNH CAMERA TRÊN WEB!")
                            print(f"               Link cũ: {self.current_stream_url}")
                            print(f"               Link mới: {server_stream_url} ({server_stream_type})")
                            self.current_stream_url = server_stream_url
                            self.current_stream_type = server_stream_type
                            if self.on_config_change:
                                try:
                                    self.on_config_change(server_stream_url, server_stream_type)
                                except Exception as _e:
                                    print(f"[SERVER BRIDGE] Lỗi gọi hook đổi cấu hình: {_e}")

                        current_delay = 8.0  # Reset backoff

                        # Kiểm tra đẩy bù định kỳ nếu còn tồn và dọn dẹp file tạm offline mồ côi
                        self._flush_offline_queue()
                        self._cleanup_orphaned_offline_proofs()

                        # Định kỳ 10 phút kiểm tra cập nhật FaceID từ Server
                        if time.time() - last_face_sync_time > 600:
                            last_face_sync_time = time.time()
                            self._executor.submit(self.sync_faces_from_server)

            except Exception as e:
                if self.is_online:
                    self.is_online = False
                    print(f"[SERVER BRIDGE] 🔴 Mất kết nối Máy Chủ Trường ({e}) -> Đang thử lại sau {int(current_delay)}s...")
                current_delay = min(current_delay * 1.5, MAX_DELAY)

            time.sleep(current_delay)

    # -------------------------------------------------------------------------
    # 3. REAL-TIME ATTENDANCE SYNC (WITH OFFLINE FALLBACK)
    # -------------------------------------------------------------------------
    def sync_attendance(self, student_code: str, status="ON_TIME", uniform_status="OK", spoof_status="REAL", check_type="FACE_AI", confidence_score: float = 0.95, proof_image_url=None, proof_image_base64=None, violation_reason=None, direction="IN"):
        """Push real-time attendance log to school server with automatic offline queueing."""
        if not self.secret_key or not self.school_id:
            return

        endpoint = f"/api/v1/s/{self.school_id}/attendance/sync"
        payload = {
            "station_secret_key": self.secret_key,
            "student_code":       student_code,
            "timestamp":          datetime.now().isoformat(),
            "direction":          direction,
            "check_type":         check_type,
            "status":             status,
            "uniform_status":     uniform_status,
            "spoof_status":       spoof_status,
            "confidence_score":   round(float(confidence_score), 4),
            "proof_image_url":    proof_image_url,
            "proof_image_base64": proof_image_base64,
            "violation_reason":   violation_reason
        }

        def _do_post():
            url = f"{self.api_url}{endpoint}"
            try:
                data = json.dumps(payload).encode('utf-8')
                req  = urllib.request.Request(url, data=data, method="POST")
                req.add_header("Content-Type", "application/json")
                with urllib.request.urlopen(req, timeout=4) as resp:
                    if resp.status in (200, 201):
                        print(f"  [SERVER BRIDGE] ⚡ Đã đồng bộ điểm danh {student_code} [{direction}] lên Web Dashboard ({status}).")
                        return
            except Exception as e:
                print(f"  [SERVER BRIDGE] ⚠️ Gửi trực tiếp thất bại ({e}) -> Chuyển vào hàng đợi offline.")

            # Nếu lỗi mạng hoặc server lỗi -> Lưu ngay vào SQLite Offline Queue
            self._enqueue_offline(endpoint, payload)

        self._executor.submit(_do_post)

    def send_camera_occlusion_alert(self, camera_id: int, occlusion_percent: float, proof_image_base64: Optional[str] = None):
        """Gửi cảnh báo camera bị che khuất (>60%) khẩn cấp lên Server cho Giám thị & BGH."""
        if not self.school_id:
            return

        cid = camera_id or self.camera_id
        endpoint = f"/api/v1/s/{self.school_id}/cameras/{cid}/occlusion-alert"
        payload = {
            "secret_key": self.secret_key,
            "occlusion_percent": round(float(occlusion_percent), 1),
            "proof_image_base64": proof_image_base64,
            "details": f"Camera bị che khuất {round(float(occlusion_percent), 1)}%, mất tầm nhìn giám sát."
        }

        def _do_post():
            url = f"{self.api_url}{endpoint}"
            try:
                data = json.dumps(payload).encode('utf-8')
                req = urllib.request.Request(url, data=data, method="POST")
                req.add_header("Content-Type", "application/json")
                with urllib.request.urlopen(req, timeout=4) as resp:
                    if resp.status in (200, 201):
                        print(f"  [SERVER BRIDGE] 🚨 Đã gửi cảnh báo che khuất camera #{cid} ({occlusion_percent}%) cho Giám Thị & BGH!")
                        return
            except Exception as e:
                print(f"  [SERVER BRIDGE] ⚠️ Không thể gửi cảnh báo che khuất trực tiếp ({e}) -> Lưu vào offline queue.")

            self._enqueue_offline(endpoint, payload)

        self._executor.submit(_do_post)

    # -------------------------------------------------------------------------
    # 4. FACE DATABASE SYNC ENGINE (TỰ ĐỘNG TẢI KHUÔN MẶT TỪ MÁY CHỦ)
    # -------------------------------------------------------------------------
    def sync_faces_from_server(self, target_dir: Optional[str] = None) -> int:
        """
        Tự động tải ảnh khuôn mặt sinh trắc học mới/cập nhật từ Máy Chủ Cloud về Edge:
        - Gọi API: GET /api/v1/s/{school_id}/cameras/{camera_id}/students
        - Tải file ảnh chính diện và các góc nghiêng vào edge/data/faces/
        - Tự động xóa faces_embeddings.npz để FaceEngine nạp lại đặc trưng mới.
        """
        if not self.secret_key or not self.school_id or not self.camera_id:
            return 0

        faces_dir = target_dir or self.faces_dir
        os.makedirs(faces_dir, exist_ok=True)

        url = f"{self.api_url}/api/v1/s/{self.school_id}/cameras/{self.camera_id}/students?secret_key={self.secret_key}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "StemEdgeSync/2.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                if resp.status != 200:
                    return 0
                students_data = json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            # Server không phản hồi hoặc đang offline
            return 0

        downloaded_count = 0

        for stu in students_data:
            st_code = str(stu.get("student_code", "")).strip()
            if not st_code:
                continue

            # 1. Ảnh chính diện
            face_rel_url = stu.get("face_photo_url")
            if face_rel_url and face_rel_url.startswith("/uploads/"):
                primary_file = os.path.join(faces_dir, f"{st_code}.jpg")
                if not os.path.isfile(primary_file) or os.path.getsize(primary_file) < 100:
                    full_img_url = f"{self.api_url}{face_rel_url}"
                    if self._download_file(full_img_url, primary_file):
                        downloaded_count += 1

            # 2. Các mẫu ảnh đa góc (samples: left, right, tilt)
            samples = stu.get("samples", [])
            for s in samples:
                angle_type = str(s.get("angle_type", "")).lower()
                s_url = s.get("image_url")
                if not s_url or not s_url.startswith("/uploads/"):
                    continue

                suffix = ""
                if "left" in angle_type:
                    suffix = "_left"
                elif "right" in angle_type:
                    suffix = "_right"
                elif "tilt" in angle_type:
                    suffix = "_tilt"

                if suffix:
                    sample_file = os.path.join(faces_dir, f"{st_code}{suffix}.jpg")
                    if not os.path.isfile(sample_file) or os.path.getsize(sample_file) < 100:
                        full_s_url = f"{self.api_url}{s_url}"
                        if self._download_file(full_s_url, sample_file):
                            downloaded_count += 1

        if downloaded_count > 0:
            print(f"[FACE SYNC] 📥 Đã tải thành công {downloaded_count} ảnh khuôn mặt mới từ Cloud Server!")
            # Xóa cache vector đặc trưng cũ để trạm camera tự động nạp lại embeddings
            cache_npz = os.path.join(os.path.dirname(faces_dir), "faces_embeddings.npz")
            if os.path.isfile(cache_npz):
                try:
                    os.remove(cache_npz)
                    print("[FACE SYNC] ♻️ Đã làm mới cache vector đặc trưng faces_embeddings.npz.")
                except Exception:
                    pass

        return downloaded_count

    def _download_file(self, source_url: str, dest_path: str) -> bool:
        """Tải một file từ URL và lưu an toàn vào dest_path."""
        try:
            req = urllib.request.Request(source_url, headers={"User-Agent": "StemEdgeDownloader/2.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status == 200:
                    content = resp.read()
                    if len(content) > 200:  # Valid image payload
                        with open(dest_path, "wb") as f:
                            f.write(content)
                        return True
        except Exception:
            pass
        return False


# Global Singleton instance
_bridge_instance = None

def get_server_bridge(api_url=None, school_id=None, camera_id=None, secret_key=None, faces_dir=None, force_reload=False):
    global _bridge_instance
    if _bridge_instance is None or force_reload:
        _bridge_instance = ServerBridge(api_url, school_id, camera_id, secret_key, faces_dir)
    return _bridge_instance
