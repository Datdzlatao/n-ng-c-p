"""
=================================================
  HE THONG DIEM DANH QR CODE + NHAN DIEN MAT
       + KIEM TRA TRANG PHUC TU DONG
  v5.0 Pro — MULTI-OBJECT TRACKING + ANTI-SPOOFING
             + SMART BEST-SHOT + ASYNC I/O WORKER
=================================================
TU V1-MODIFIED (tinh nang ban them vao):
  [+] FaceEngine 2 lop: Haar nhanh moi frame + face_recognition dinh ky
  [+] Nhan dien NGUOI LA (stranger) - chup + ghi vi pham tu dong
  [+] Sidebar thong tin dep ben canh box khuon mat
  [+] Logic vi pham 3 muc: ok / warn (chua quet) / stranger

TU V2 (bug fix + tinh nang v2):
  [+] BUG FIX: vong lap vo han khi camera mat ket noi -> MAX_CAM_FAILS
  [+] BUG FIX: RAM leak recently_scan, last_results -> don dep dinh ky
  [+] BUG FIX: Unicode crash tren Windows console -> ASCII fallback
  [+] BUG FIX: mat du lieu khi Sheets loi -> SQLite offline buffer
  [+] Phim tat: S=thong ke, R=reload, P=pause mat, A=them mat live
  [+] Tong ket cuoi ngay tu dong len sheet TongKet
  [+] Kiem tra mang realtime hien tren camera
  [+] draw_banner dep voi fade-out
  [+] draw_clock, draw_stats tren camera
  [+] Auto sync offline -> Sheets background

TU V4 & V5 PRO (Multi-Object Tracking, Anti-Spoofing, Visual Flagging,
               Smart Best-Shot Auto Capture, Async I/O Background Queue):
  [+] MultiObjectTracker (IoU + Centroid): theo doi 3-8 nguoi cung luc.
  [+] Spatial Fusion: QR / khuon mat / trang phuc gan vao DUNG track_id.
  [+] UniformChecker: phan tich trang phuc theo quy dinh thu trong tuan.
  [+] AntiSpoofingDetector: phat hien gian lan anh chụp/man hinh.
  [+] Visual Flagging: HUD dong 🟩 Xanh la, 🟨 Vang, 🟥 Do nhap nhay.
  [+] SmartCaptureEngine: chup 2 anh (chan dung + toan canh co watermark).
  [+] BackgroundLogger: luong ghi I/O ngam 0ms delay luong camera.

TU V6 (Multi-Object Tracking + Spatial Fusion — tracker.py):
  [+] MultiObjectTracker (IoU + Centroid, nhe, khong can GPU): moi nguoi
      xuat hien trong camera duoc cap 1 track_id ON DINH, duy tri xuyen
      suot cac frame (ke ca khi tam bi che khuat), thay vi chi dua vao
      "nguoi nhan dien gan nhat" nhu truoc day.
  [+] Spatial Fusion: QR / khuon mat / ket qua trang phuc duoc gan vao
      DUNG track_id theo toa do bounding box, khong con bi nham lan khi
      3-8 hoc sinh dung gan nhau trong khung hinh cung luc.
  [+] Moi track_id mang trang thai DOC LAP: {id, student_id, name,
      qr_scanned, face_matched, uniform_status, is_stranger, status_time}.
  [+] Kiem tra trang phuc gio chay TREN TUNG TRACK dang active (truoc day
      chi cham 1 nguoi dau tien phat hien duoc) -> nhieu hoc sinh diem
      danh + duoc cham trang phuc DOC LAP, dong thoi, khong can xep hang.
  [+] Phim tat moi: T = Bat/tat ve khung debug track_id tren camera.

Cach chay:
    python main.py
"""

import cv2
cv2.setNumThreads(2)
from pyzbar import pyzbar
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, date
import time
import base64
import sys
import os
import csv
import json
import urllib.request
import sqlite3
import threading
import socket
import numpy as np
try:
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer as HTTPServer
except ImportError:
    from http.server import BaseHTTPRequestHandler, HTTPServer
    from socketserver import ThreadingMixIn
    class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
        daemon_threads = True
    HTTPServer = ThreadingHTTPServer
from io import BytesIO
import queue
import argparse
from typing import Optional, List, Dict, Tuple, Any, Union

from config import (
    SPREADSHEET_NAME, SHEET_LOG, SHEET_STUDENTS, SHEET_VIOLATIONS, SHEET_SUMMARY,
    COOLDOWN_SECONDS, CAMERA_INDEX, CREDENTIALS_FILE, SPREADSHEET_ID,
    FACE_GRACE_SECONDS, VIOLATION_COOLDOWN, FACE_SKIP_FRAMES,
    AUTO_SYNC_INTERVAL, BANNER_DURATION, DB_PATH,
    STREAM_ENABLE, STREAM_PORT, STREAM_QUALITY, STREAM_FPS,
    UNIFORM_CHECK_ENABLE, UNIFORM_CHECK_INTERVAL, UNIFORM_VIOLATION_COOLDOWN,
    ASYNC_CAMERA_ENABLE, ASYNC_WORKER_ENABLE,
    MOT_ENABLE, MOT_DETECT_INTERVAL, MOT_MAX_TRACKS, MOT_MAX_DISAPPEARED,
    MOT_IOU_THRESHOLD, MOT_MAX_CENTROID_DIST, MOT_DRAW_TRACKS,
    MOT_ATTENDANCE_COOLDOWN,
    ATTENDANCE_MODE, ANTI_SPOOF_ENABLE, STRANGER_ALERT_ENABLE,
    FACE_CONFIRM_FRAMES,
)
from utils import (
    load_students, find_student,
    beep_success, beep_error,
    draw_overlay, draw_banner, draw_clock, draw_stats,
    print_log, NetworkChecker, FPSCounter
)
from face_engine import FaceEngine, ThreadedCamera, AsyncFaceWorker

FACE_LIB_OK = True  # v5.0 su dung OpenCV DNN YuNet + SFace tich hop san trong OpenCV

try:
    from uniform_checker import UniformChecker, COLOR_FAIL, COLOR_UNCLEAR
    UNIFORM_LIB_OK = True
except ImportError as e:
    print(f"[WARN] Khong the nap module trang phuc: {e}")
    print("       He thong van chay binh thuong, chi bo qua kiem tra trang phuc.")
    UNIFORM_LIB_OK = False
    COLOR_FAIL    = (0, 50, 220)
    COLOR_UNCLEAR = (0, 165, 255)

# [v6] MultiObjectTracker + PersonDetector la tinh nang tuy chon: neu loi
# (VD thieu numpy/opencv-contrib) thi he thong van chay binh thuong nhu
# truoc, chi mat phan theo doi da nguoi + spatial fusion.
try:
    from tracker import MultiObjectTracker
    from person_detector import PersonDetector
    MOT_LIB_OK = True
except ImportError as e:
    print(f"[WARN] Khong the nap module MOT (tracker.py): {e}")
    print("       He thong van chay binh thuong, chi bo qua theo doi da nguoi.")
    MOT_LIB_OK = False

try:
    from anti_spoofing import AntiSpoofingDetector
    SPOOF_LIB_OK = True
except ImportError as e:
    print(f"[WARN] Khong the nap module anti_spoofing: {e}")
    SPOOF_LIB_OK = False

try:
    from smart_capture import SmartCaptureEngine
    SMART_CAP_LIB_OK = True
except ImportError as e:
    print(f"[WARN] Khong the nap module smart_capture: {e}")
    SMART_CAP_LIB_OK = False

try:
    from async_logger import BackgroundLogger
    ASYNC_LOG_LIB_OK = True
except ImportError as e:
    print(f"[WARN] Khong the nap module async_logger: {e}")
    ASYNC_LOG_LIB_OK = False

try:
    from server_bridge import get_server_bridge
    SERVER_BRIDGE_OK = True
except ImportError as e:
    print(f"[WARN] Khong the nap module server_bridge: {e}")
    SERVER_BRIDGE_OK = False

try:
    from occlusion_detector import CameraOcclusionDetector
    OCCLUSION_LIB_OK = True
except ImportError as e:
    print(f"[WARN] Khong the nap module occlusion_detector: {e}")
    OCCLUSION_LIB_OK = False

# =============================================================================
# MJPEG Stream Server — Phat giao dien da xu ly ve thiet bi camera
# =============================================================================
_stream_lock        = threading.Lock()
_stream_condition   = threading.Condition(_stream_lock)
_stream_frame_bytes: bytes = b""
_stream_interval    = 1.0 / max(STREAM_FPS, 1)


def create_standby_frame(title: str, subtitle: str, detail: str = "", status: str = "CONNECTING") -> np.ndarray:
    """Tao frame anh 1280x720 de phat live stream ngay ca khi camera dang khoi dong hoac mat tin hieu."""
    h, w = 720, 1280
    img = np.zeros((h, w, 3), dtype=np.uint8)
    for y in range(h):
        ratio = y / h
        img[y, :] = [int(24 + 10 * ratio), int(16 + 8 * ratio), int(12 + 6 * ratio)]
    
    accent_color = (0, 200, 80) if status == "ONLINE" else ((0, 140, 255) if status == "CONNECTING" else (0, 50, 220))
    cv2.rectangle(img, (20, 20), (w - 20, h - 20), (45, 55, 72), 2)
    cv2.rectangle(img, (20, 20), (w - 20, 70), (35, 45, 60), -1)
    
    cv2.putText(img, "EDUSAMS AI ATTENDANCE SYSTEM - LIVE STREAM", (35, 52),
                cv2.FONT_HERSHEY_DUPLEX, 0.75, (220, 230, 242), 2, cv2.LINE_AA)
    
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cv2.putText(img, now_str, (w - 320, 52),
                cv2.FONT_HERSHEY_SIMPLEX, 0.65, (160, 175, 195), 2, cv2.LINE_AA)
    
    box_w, box_h = 820, 270
    bx1 = (w - box_w) // 2
    by1 = (h - box_h) // 2
    cv2.rectangle(img, (bx1, by1), (bx1 + box_w, by1 + box_h), (30, 40, 55), -1)
    cv2.rectangle(img, (bx1, by1), (bx1 + box_w, by1 + box_h), accent_color, 2)
    
    tag_map = {
        "ONLINE": "[ LIVE AI - HOAT DONG ]",
        "CONNECTING": "[ DANG KET NOI LUONG CAMERA ]",
        "OFFLINE": "[ MAT TIN HIEU / LOI KET NOI RTSP ]"
    }
    icon_text = tag_map.get(status, f"[ {status} ]")
    cv2.putText(img, icon_text, (bx1 + 35, by1 + 55),
                cv2.FONT_HERSHEY_DUPLEX, 0.75, accent_color, 2, cv2.LINE_AA)
    
    cv2.putText(img, str(title)[:60], (bx1 + 35, by1 + 105),
                cv2.FONT_HERSHEY_DUPLEX, 0.85, (255, 255, 255), 2, cv2.LINE_AA)
    
    cv2.putText(img, str(subtitle)[:75], (bx1 + 35, by1 + 155),
                cv2.FONT_HERSHEY_SIMPLEX, 0.65, (200, 210, 225), 1, cv2.LINE_AA)
                
    if detail:
        cv2.putText(img, str(detail)[:80], (bx1 + 35, by1 + 195),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.58, (150, 165, 180), 1, cv2.LINE_AA)
                    
    cv2.putText(img, "He thong tu dong phuc hoi va hien thi ngay khi camera on dinh.", 
                (bx1 + 35, by1 + 235), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (120, 140, 160), 1, cv2.LINE_AA)
                
    return img


_stream_frame_seq   = 0


def _push_stream_frame(frame_bgr):
    """Goi sau khi ve xong overlay — encode JPEG va luu vao buffer chia se."""
    global _stream_frame_bytes, _stream_frame_seq
    if not STREAM_ENABLE or frame_bgr is None:
        return
    # Thu nho ve toi da 480px chieu ngang (480x270 16:9 hoac 480x360 4:3), giam 65% bang thong ma van rat ro net tren web
    h, w = frame_bgr.shape[:2]
    target_w = 480
    if w > target_w:
        preview_w = target_w
        preview_h = int(target_w * h / w)
        preview_frame = cv2.resize(frame_bgr, (preview_w, preview_h), interpolation=cv2.INTER_LINEAR)
    else:
        preview_frame = frame_bgr

    quality = max(30, min(int(STREAM_QUALITY), 50))
    ok, buf = cv2.imencode(".jpg", preview_frame,
                           [cv2.IMWRITE_JPEG_QUALITY, quality])

    if not ok:
        return
    data = buf.tobytes()
    with _stream_lock:
        _stream_frame_bytes = data
        _stream_frame_seq += 1
        _stream_condition.notify_all()



class _MJPEGHandler(BaseHTTPRequestHandler):
    """HTTP handler phuc vu trang HTML wrapper va luong MJPEG."""

    def log_message(self, fmt, *args):   # tat Apache-style log trong console
        pass

    def do_HEAD(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

    def do_GET(self):
        clean_path = self.path.split("?")[0]
        if clean_path in ("/", "/index.html"):
            self._serve_html()
        elif clean_path == "/stream":
            self._serve_mjpeg()
        elif clean_path in ("/snapshot", "/frame.jpg", "/current.jpg"):
            self._serve_snapshot()
        else:
            self.send_response(404)
            self.end_headers()

    def _serve_snapshot(self):
        """Phuc vu 1 frame JPEG moi nhat (chup anh tuc thi)."""
        with _stream_lock:
            data = _stream_frame_bytes
        if not data:
            self.send_response(503)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", "image/jpeg")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(data)

    def _serve_html(self):
        html = (
            "<!DOCTYPE html><html><head>"
            "<meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width,initial-scale=1'>"
            "<title>Diem Danh STEM - Live Preview v5.0</title>"
            "<style>"
            "body{margin:0;background:#0d1117;display:flex;flex-direction:column;"
            "align-items:center;justify-content:center;min-height:100vh;"
            "color:#c9d1d9;font-family:sans-serif;}"
            "img{width:100%;max-width:1280px;border:2px solid #238636;"
            "border-radius:8px;box-shadow:0 0 24px #0f0a;}"
            "p{margin:10px;font-size:12px;opacity:.6;}"
            "</style></head><body>"
            "<img src='/stream' />"
            "<p>He Thong Diem Danh STEM v5.0 Pro &mdash; Preview truc tiep (lam moi tu dong)</p>"
            "</body></html>"
        )
        body = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _serve_mjpeg(self):
        """Phat lien tuc frame JPEG theo chuan multipart/x-mixed-replace 30 FPS thoi gian thuc khong do tre."""
        global _stream_frame_bytes, _stream_frame_seq
        try:
            self.connection.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        except Exception:
            pass

        self.send_response(200)
        self.send_header("Content-Type",
                         "multipart/x-mixed-replace; boundary=frame")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        last_sent_seq = -1
        stream_interval = 1.0 / max(STREAM_FPS, 1)
        try:
            while True:
                with _stream_condition:
                    if _stream_frame_seq == last_sent_seq:
                        _stream_condition.wait(timeout=stream_interval)
                    data = _stream_frame_bytes
                    seq = _stream_frame_seq

                if not data or seq == last_sent_seq:
                    continue

                header = (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n"
                    b"Content-Length: " + str(len(data)).encode() + b"\r\n\r\n"
                )
                self.wfile.write(header + data + b"\r\n")
                self.wfile.flush()
                last_sent_seq = seq
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass


def _start_stream_server(port=None):
    """Khoi dong MJPEG HTTP server trong daemon thread."""
    if not STREAM_ENABLE:
        return
    actual_port = int(port) if port is not None else STREAM_PORT
    try:
        server = HTTPServer(("", actual_port), _MJPEGHandler)
        server.daemon_threads = True
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
        try:
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
        except Exception:
            local_ip = "<IP_may_tinh>"
        print(f"[STREAM] Preview server bat dau:")
        print(f"  May tinh nay : http://localhost:{actual_port}")
        print(f"  Thiet bi cam : http://{local_ip}:{actual_port}  (mo trinh duyet)")
        print()
    except Exception as e:
        print(f"[STREAM] ⚠️ Khong the mo port {actual_port} cho stream preview: {e}")


# =============================================================================
# Ket noi Google Sheets
# =============================================================================
def connect_sheets():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    try:
        creds  = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
        client = gspread.authorize(creds)
        ss     = client.open_by_key(SPREADSHEET_ID) if SPREADSHEET_ID \
                 else client.open(SPREADSHEET_NAME)

        sheet_log = ss.worksheet(SHEET_LOG)
        sheet_stu = ss.worksheet(SHEET_STUDENTS)
        sheet_vio = ss.worksheet(SHEET_VIOLATIONS)

        try:
            sheet_sum = ss.worksheet(SHEET_SUMMARY)
        except gspread.WorksheetNotFound:
            sheet_sum = ss.add_worksheet(title=SHEET_SUMMARY, rows=500, cols=8)
            sheet_sum.append_row(
                ["Ngay", "Tong HS", "Co Mat", "Vang Mat",
                 "Vi Pham", "Nguoi La", "Gio Bat Dau", "Gio Ket Thuc"],
                value_input_option="RAW"
            )
            print(f"[OK] Da tao sheet '{SHEET_SUMMARY}'.")

        print(f"[OK] Da ket noi Google Sheets: '{ss.title}'")
        return sheet_log, sheet_stu, sheet_vio, sheet_sum

    except Exception as e:
        print(f"[INFO] Google Sheets khong kha dung ({e}).")
        print("       He thong chuyen sang van hanh qua Cloud Server API & Offline Buffer.")
        return None, None, None, None


# =============================================================================
# SQLite offline buffer
# =============================================================================
def get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS offline_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            thoi_gian TEXT, ma_hs TEXT, ho_ten TEXT, trang_thai TEXT,
            synced INTEGER DEFAULT 0
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS offline_violation (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            thoi_gian TEXT, ma_hs TEXT, ho_ten TEXT, mo_ta TEXT,
            ten_file TEXT, duong_dan TEXT, synced INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    return conn


def save_to_db(conn, rows, synced=0):
    conn.executemany(
        "INSERT INTO offline_log (thoi_gian,ma_hs,ho_ten,trang_thai,synced) VALUES(?,?,?,?,?)",
        [(r[0], r[1], r[2], r[3], synced) for r in rows]
    )
    conn.commit()


def save_violation_to_db(conn, row, synced=0):
    conn.execute(
        "INSERT INTO offline_violation (thoi_gian,ma_hs,ho_ten,mo_ta,ten_file,duong_dan,synced)"
        " VALUES(?,?,?,?,?,?,?)", row + [synced]
    )
    conn.commit()


def sync_offline_to_sheets(conn, sheet_log, sheet_vio):
    rows = conn.execute(
        "SELECT id,thoi_gian,ma_hs,ho_ten,trang_thai FROM offline_log"
        " WHERE synced=0 ORDER BY id LIMIT 50"
    ).fetchall()
    if rows:
        try:
            sheet_log.append_rows([[r[1],r[2],r[3],r[4]] for r in rows],
                                   value_input_option="RAW")
            ids = [r[0] for r in rows]
            conn.execute(
                f"UPDATE offline_log SET synced=1 WHERE id IN ({','.join('?'*len(ids))})", ids
            )
            conn.commit()
            print(f"[SYNC] Dong bo {len(rows)} ban ghi log.")
        except Exception as e:
            print(f"[SYNC] Loi log: {e}")

    vrows = conn.execute(
        "SELECT id,thoi_gian,ma_hs,ho_ten,mo_ta,ten_file,duong_dan"
        " FROM offline_violation WHERE synced=0 LIMIT 20"
    ).fetchall()
    if vrows:
        try:
            sheet_vio.append_rows([[r[1],r[2],r[3],r[4],r[5],r[6]] for r in vrows],
                                   value_input_option="RAW")
            vids = [r[0] for r in vrows]
            conn.execute(
                f"UPDATE offline_violation SET synced=1 WHERE id IN ({','.join('?'*len(vids))})", vids
            )
            conn.commit()
            print(f"[SYNC] Dong bo {len(vrows)} vi pham.")
        except Exception as e:
            print(f"[SYNC] Loi vi pham: {e}")


# =============================================================================
# Cache log hom nay
# =============================================================================
def load_today_log(sheet_log) -> dict:
    if sheet_log is None:
        return {}
    today = date.today().strftime("%d/%m/%Y")
    try:
        records = sheet_log.get_all_values()
    except Exception as e:
        print(f"[!!] Khong tai duoc log hom nay: {e}")
        return {}
    count_map = {}
    for row in records[1:]:
        if len(row) >= 2 and row[0].startswith(today):
            sid = row[1]
            count_map[sid] = count_map.get(sid, 0) + 1
    return count_map


def get_status_cache(count_map: dict, student_id: str) -> str:
    if not student_id:
        return "Vao"
    return "Ra" if count_map.get(str(student_id).strip(), 0) % 2 == 1 else "Vao"

get_status = get_status_cache


# =============================================================================
# Ghi Sheets (fallback SQLite & Background Queue)
# =============================================================================
bg_logger = None

def capture_attendance_frame(frame, student_id: str, student_name: str, direction_str: str = "VAO",
                             face_loc=None, is_violation: bool = False, violation_label: str = None,
                             all_faces: Optional[List[Dict[str, Any]]] = None,
                             multi_students: Optional[List[Dict[str, Any]]] = None) -> Optional[str]:
    """
    Chụp ảnh trực tiếp từ camera khi điểm danh thành công hoặc phát hiện vi phạm.
    [NÂNG CẤP ĐA KHUÔN MẶT]:
    - Hỗ trợ đóng khung toàn bộ học sinh cùng xuất hiện trong ảnh (all_faces / multi_students).
    - Phân biệt nổi bật học sinh được điểm danh và các bạn cùng nhóm.
    - Bố cục watermark và tag tên tinh gọn, không che mặt học sinh.
    """
    if frame is None or getattr(frame, 'size', 0) == 0:
        return None
    try:
        snap = frame.copy()
        h, w = snap.shape[:2]
        scale = 1.0

        # Giới hạn kích thước tối đa 880px chiều rộng để tối ưu dung lượng và độ sắc nét
        if w > 880:
            scale = 880.0 / w
            snap = cv2.resize(snap, (880, int(h * scale)), interpolation=cv2.INTER_AREA)
            h, w = snap.shape[:2]
            if face_loc:
                top, right, bottom, left = face_loc
                face_loc = (int(top * scale), int(right * scale), int(bottom * scale), int(left * scale))

        def _scale_box(box):
            if not box:
                return None
            t, r, b, l = box
            return (int(t * scale), int(r * scale), int(b * scale), int(l * scale))

        drawn_boxes = []

        # 1. Vẽ tất cả các khuôn mặt được phát hiện trong khung hình nếu có all_faces
        if all_faces:
            for f in all_faces:
                f_loc = _scale_box(f.get("location"))
                if not f_loc:
                    continue
                t, r, b, l = f_loc
                sid_f = f.get("student_id")
                name_f = f.get("name", "Nguoi dung")
                conf_f = f.get("confidence", 0.0)

                # Kiểm tra xem đây có phải học sinh chính hay trong nhóm điểm danh
                is_this_target = (sid_f and sid_f == student_id) or (
                    multi_students and any(ms.get("student_id") == sid_f for ms in multi_students)
                )

                if is_this_target:
                    box_col = (0, 220, 80) if direction_str == "VAO" else (0, 160, 255)
                    thick = 2
                    tag_bg = (0, 140, 40) if direction_str == "VAO" else (0, 100, 200)
                    tag_text = f"✓ {name_f}" if name_f else f"✓ {sid_f}"
                elif sid_f:
                    box_col = (255, 210, 0)
                    thick = 1
                    tag_bg = (30, 40, 60)
                    tag_text = f"{name_f}"
                else:
                    box_col = (150, 150, 150)
                    thick = 1
                    tag_bg = (20, 20, 20)
                    tag_text = "Nguoi la"

                # Vẽ khung khuôn mặt
                cv2.rectangle(snap, (l, t), (r, b), box_col, thick)

                # Vẽ 4 góc HUD hiện đại
                corner_len = max(5, min(r - l, b - t) // 5)
                cv2.line(snap, (l, t), (l + corner_len, t), box_col, 2)
                cv2.line(snap, (l, t), (l, t + corner_len), box_col, 2)
                cv2.line(snap, (r, t), (r - corner_len, t), box_col, 2)
                cv2.line(snap, (r, t), (r, t + corner_len), box_col, 2)
                cv2.line(snap, (l, b), (l + corner_len, b), box_col, 2)
                cv2.line(snap, (l, b), (l, b - corner_len), box_col, 2)
                cv2.line(snap, (r, b), (r - corner_len, b), box_col, 2)
                cv2.line(snap, (r, b), (r, b - corner_len), box_col, 2)

                # Badge tên nhỏ gọn trên đầu box
                if tag_text:
                    (tw, th_txt), _ = cv2.getTextSize(tag_text, cv2.FONT_HERSHEY_SIMPLEX, 0.38, 1)
                    badge_y = max(th_txt + 4, t - 4)
                    cv2.rectangle(snap, (l, badge_y - th_txt - 3), (min(w - 1, l + tw + 6), badge_y + 2), tag_bg, -1)
                    cv2.putText(snap, tag_text, (l + 3, badge_y - 1), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (255, 255, 255), 1, cv2.LINE_AA)

                drawn_boxes.append(f_loc)

        # 2. Vẽ fallback cho face_loc nếu chưa được vẽ
        if face_loc and not any(abs(face_loc[0] - db[0]) < 20 and abs(face_loc[3] - db[3]) < 20 for db in drawn_boxes):
            top, right, bottom, left = face_loc
            if is_violation or violation_label:
                box_color = (0, 0, 230)
            else:
                box_color = (0, 220, 80) if direction_str == "VAO" else (0, 160, 255)
            cv2.rectangle(snap, (left, top), (right, bottom), box_color, 2)
            lbl = f"✓ {student_name}" if student_name else f"✓ {student_id}"
            (tw, th_txt), _ = cv2.getTextSize(lbl, cv2.FONT_HERSHEY_SIMPLEX, 0.38, 1)
            b_y = max(th_txt + 4, top - 4)
            cv2.rectangle(snap, (left, b_y - th_txt - 3), (min(w - 1, left + tw + 6), b_y + 2), (0, 140, 40), -1)
            cv2.putText(snap, lbl, (left + 3, b_y - 1), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (255, 255, 255), 1, cv2.LINE_AA)

        # 3. Dải banner thông tin ở đáy ảnh
        banner_h = 46
        ov = snap.copy()
        banner_bg = (30, 20, 10) if (is_violation or violation_label) else (15, 23, 42)
        cv2.rectangle(ov, (0, h - banner_h), (w, h), banner_bg, -1)
        cv2.addWeighted(ov, 0.78, snap, 0.22, 0, snap)

        ts_disp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        if violation_label:
            dir_label = f"⚠️ {violation_label}"
        elif direction_str == "VAO":
            dir_label = "🟢 CỔNG VÀO"
        else:
            dir_label = "🔵 CỔNG RA"

        # Hiển thị số lượng học sinh trong ảnh nếu có nhiều người
        num_faces = len(all_faces) if all_faces else (len(multi_students) if multi_students else 1)
        if multi_students and len(multi_students) > 1:
            multi_tag = f" | [ĐA KHUÔN MẶT: {len(multi_students)} HS]"
            names_str = ", ".join(f"{s.get('name', s.get('student_id'))}" for s in multi_students[:3])
            if len(multi_students) > 3:
                names_str += f" (+{len(multi_students)-3})"
            line2_text = f"ĐIỂM DANH ĐỒNG THỜI: {names_str}"
        elif num_faces > 1:
            multi_tag = f" | [ĐA KHUÔN MẶT: {num_faces} NGƯỜI]"
            line2_text = f"HS ĐIỂM DANH: {student_name} ({student_id})"
        else:
            multi_tag = ""
            line2_text = f"HS: {student_name} ({student_id})"

        text_line1 = f"DIEM DANH CAMERA AI | {dir_label}{multi_tag} | {ts_disp}"
        cv2.putText(snap, text_line1, (10, h - banner_h + 16), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (255, 255, 255), 1, cv2.LINE_AA)
        sub_color = (0, 200, 255) if (is_violation or violation_label) else (56, 189, 248)
        cv2.putText(snap, line2_text, (10, h - banner_h + 35), cv2.FONT_HERSHEY_SIMPLEX, 0.44, sub_color, 1, cv2.LINE_AA)

        ret, buf = cv2.imencode(".jpg", snap, [cv2.IMWRITE_JPEG_QUALITY, 82])
        if ret:
            return base64.b64encode(buf).decode("utf-8")
    except Exception as e:
        print(f"[CAM SNAPSHOT] Lỗi chụp ảnh camera điểm danh: {e}")
    return None

def flush_qr_batch(sheet_log, conn, batch: list, proof_image_base64: str = None) -> bool:
    if not batch:
        return True
    if SERVER_BRIDGE_OK:
        try:
            bridge = get_server_bridge()
            for r in batch:
                if len(r) >= 2:
                    student_code = str(r[1]).strip()
                    direction_str = "OUT" if (len(r) >= 4 and str(r[3]).strip().lower() in ("ra", "out")) else "IN"
                    uni_status = "OK"
                    vio_reason = None
                    if len(r) >= 6 and r[5]:
                        u_raw = str(r[5]).strip().upper()
                        if u_raw in ("VIOLATION", "FAIL"):
                            uni_status = "VIOLATION"
                        elif u_raw in ("OK", "PASS"):
                            uni_status = "OK"
                        else:
                            uni_status = u_raw
                    if len(r) >= 7 and r[6]:
                        vio_reason = str(r[6]).strip()
                    bridge.sync_attendance(
                        student_code=student_code,
                        status="ON_TIME" if uni_status == "OK" else "LATE",
                        uniform_status=uni_status,
                        direction=direction_str,
                        proof_image_base64=proof_image_base64,
                        violation_reason=vio_reason
                    )
        except Exception as e:
            print(f"[EDGE BRIDGE] Lỗi đồng bộ điểm danh: {e}")
    if bg_logger is not None:
        bg_logger.log_attendance_async(batch)
        return True
    if sheet_log is None:
        save_to_db(conn, batch, synced=0)
        return True
    try:
        sheet_log.append_rows(batch, value_input_option="RAW")
        save_to_db(conn, batch, synced=1)
        return True
    except Exception as e:
        print(f"[!!] Loi ghi QR Sheets (luu offline): {e}")
        save_to_db(conn, batch, synced=0)
        return False


def log_violation(sheet_vio, conn, student_id, student_name, photo_path, reason="Khong deo the", proof_image_base64=None, direction="IN"):
    ts       = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    filename = os.path.basename(photo_path) if photo_path else f"vio_{int(time.time()*1000)}.jpg"
    row = [ts, student_id, student_name, reason, filename, photo_path or ""]
    if SERVER_BRIDGE_OK:
        try:
            bridge = get_server_bridge()
            v_stat = "VIOLATION" if ("phuc" in reason.lower() or "ao" in reason.lower() or "quan" in reason.lower()) else "UNKNOWN"
            b64_img = proof_image_base64
            # Fallback đọc từ file đĩa nếu chưa có Base64 bộ nhớ RAM
            if not b64_img and photo_path and os.path.exists(photo_path):
                try:
                    with open(photo_path, "rb") as f:
                        b64_img = base64.b64encode(f.read()).decode('utf-8')
                except Exception:
                    pass
            bridge.sync_attendance(
                student_code=str(student_id).strip(),
                status="LATE",
                uniform_status=v_stat,
                proof_image_base64=b64_img,
                violation_reason=reason,
                direction=direction
            )
        except Exception as _sync_err:
            print(f"  [LOG VIOLATION] Lỗi đồng bộ vi phạm: {_sync_err}")
    if bg_logger is not None:
        bg_logger.log_violation_async(student_id, student_name, photo_path or "", reason)
        return
    if sheet_vio is None:
        save_violation_to_db(conn, row, synced=0)
        return
    try:
        sheet_vio.append_row(row, value_input_option="RAW")
        print(f"  [VI PHAM] {ts} | {student_id} | {student_name} | {reason}")
        save_violation_to_db(conn, row, synced=1)
    except Exception as e:
        print(f"  [!!] Loi ghi vi pham (luu offline): {e}")
        save_violation_to_db(conn, row, synced=0)


def write_daily_summary(sheet_sum, count_map, total_students,
                         violation_count, stranger_count, start_time):
    if sheet_sum is None:
        return
    present = sum(1 for c in count_map.values() if c % 2 == 1)
    if bg_logger is not None:
        bg_logger.write_summary_async(total_students, present, violation_count, stranger_count, start_time)
        return

    today    = date.today().strftime("%d/%m/%Y")
    absent   = total_students - present
    end_ts   = datetime.now().strftime("%H:%M:%S")
    start_ts = start_time.strftime("%H:%M:%S")
    row = [today, total_students, present, absent,
           violation_count, stranger_count, start_ts, end_ts]
    try:
        sheet_sum.append_row(row, value_input_option="RAW")
        print(f"[OK] Da ghi tong ket ngay {today} len sheet '{SHEET_SUMMARY}'.")
    except Exception as e:
        print(f"[!!] Khong ghi duoc tong ket: {e}")


def fetch_students_from_server(api_url=None, school_id=None, camera_id=None, secret_key=None) -> dict:
    """Tải danh sách học sinh trực tiếp từ Backend Server API bằng camera secret key."""
    try:
        from config import SERVER_API_URL, SCHOOL_ID, CAMERA_ID, CAMERA_SECRET
    except ImportError:
        SERVER_API_URL = "http://localhost:8000"
        SCHOOL_ID = 1
        CAMERA_ID = 1
        CAMERA_SECRET = ""

    server = (api_url or SERVER_API_URL).rstrip("/")
    sch_id = school_id or SCHOOL_ID
    cam_id = camera_id or CAMERA_ID
    sec_key = secret_key or CAMERA_SECRET

    students = {}
    if server and sch_id and cam_id and sec_key:
        url = f"{server}/api/v1/s/{sch_id}/cameras/{cam_id}/students?secret_key={sec_key}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "StemEdge/1.0"})
            with urllib.request.urlopen(req, timeout=6) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    students = {str(s["student_code"]).strip(): s.get("full_name", s["student_code"]) for s in data if "student_code" in s}
                    print(f"[OK] Da dong bo {len(students)} hoc sinh tu May Chu Cloud ({server}).")
                    if SERVER_BRIDGE_OK:
                        try:
                            from server_bridge import get_server_bridge
                            bridge = get_server_bridge(api_url=server, school_id=sch_id, camera_id=cam_id, secret_key=sec_key)
                            bridge.sync_faces_from_server()
                        except Exception as _e_sync:
                            print(f"[WARN] Khong the dong bo anh khuon mat: {_e_sync}")
        except Exception as e:
            print(f"[WARN] Khong the tai danh sach hoc sinh tu Cloud Server: {e}")

    # Fallback 1: Đọc trực tiếp từ cơ sở dữ liệu SQLite cục bộ nếu server chưa bật hoặc offline
    if not students:
        local_db = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend", "data", "stem_platform.db")
        if os.path.isfile(local_db):
            try:
                conn_loc = sqlite3.connect(local_db)
                rows = conn_loc.execute(
                    "SELECT student_code, full_name FROM students WHERE school_id=? AND is_active=1 AND is_deleted=0",
                    (sch_id,)
                ).fetchall()
                conn_loc.close()
                if rows:
                    students = {str(r[0]).strip(): r[1] for r in rows if r[0]}
                    print(f"[OK] Da dong bo {len(students)} hoc sinh truc tiep tu SQLite cuc bo ({local_db}).")
            except Exception as _e_loc:
                print(f"[WARN] Khong the doc tu DB cuc bo: {_e_loc}")

    # Lưu bộ đệm offline vào data/students.csv để lần sau offline vẫn chính xác
    if students:
        try:
            csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "students.csv")
            os.makedirs(os.path.dirname(csv_path), exist_ok=True)
            with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["MaHS", "HoTen", "Lop"])
                for code, name in students.items():
                    writer.writerow([code, name, ""])
        except Exception:
            pass

    return students


# =============================================================================
# Vong lap chinh
# =============================================================================
def run(args=None):
    if args is None:
        parser = argparse.ArgumentParser(description="STEM FaceID & Attendance Edge Engine")
        parser.add_argument("--camera", "-c", type=str, default=None, help="Camera index (0, 1) or RTSP stream URL (e.g. rtsp://user:pass@ip:554/live)")
        parser.add_argument("--school", "-s", "--school_id", "--school-id", dest="school", type=int, default=None, help="School ID")
        parser.add_argument("--cam-id", "--camera_id", "--camera-id", dest="cam_id", type=int, default=None, help="Camera Station ID")
        parser.add_argument("--secret", "--secret_key", "--secret-key", dest="secret", type=str, default=None, help="Camera Station Secret Key")
        parser.add_argument("--server", "--api_url", "--api-url", dest="server", type=str, default=None, help="Backend Server URL (e.g. http://localhost:8000)")
        parser.add_argument("--port", "--stream-port", dest="port", type=int, default=None, help="HTTP MJPEG Preview stream port")
        parser.add_argument("--auto-reconnect", action="store_true", default=True, help="Auto reconnect when camera connection drops")
        parser.add_argument("--headless", action="store_true", help="Run in headless mode without GUI window")
        parser.add_argument("--uniform", dest="uniform", action="store_true", default=None, help="Force enable uniform checking")
        parser.add_argument("--no-uniform", dest="uniform", action="store_false", help="Force disable uniform checking")
        parser.add_argument("--occlusion-check", dest="occlusion_check", action="store_true", default=None, help="Force enable camera occlusion/tamper checking")
        parser.add_argument("--no-occlusion-check", dest="occlusion_check", action="store_false", help="Force disable camera occlusion/tamper checking")
        args, _ = parser.parse_known_args()

    cam_source = args.camera if args.camera is not None else CAMERA_INDEX
    if isinstance(cam_source, str):
        cam_source = cam_source.strip().strip('"\'')
        if cam_source.isdigit():
            cam_source = int(cam_source)

    if SERVER_BRIDGE_OK:
        bridge = get_server_bridge(
            api_url=args.server,
            school_id=args.school,
            camera_id=args.cam_id,
            secret_key=args.secret,
            force_reload=(args.secret is not None or args.school is not None or args.cam_id is not None)
        )
        # Tự động đồng bộ luồng RTSP / Webcam mới nhất từ Web Server (Zero-Touch Provisioning)
        if args.camera is None:
            try:
                runtime_cfg = bridge.fetch_runtime_config()
                if runtime_cfg and runtime_cfg.get("stream_url"):
                    server_url = str(runtime_cfg.get("stream_url")).strip().strip('"\'')
                    cam_source = int(server_url) if server_url.isdigit() else server_url
                    print(f"[CLOUD SYNC] 🌐 Tự động nạp cấu hình luồng từ Web Dashboard:")
                    print(f"             Trạm: #{runtime_cfg.get('camera_id')} - {runtime_cfg.get('name')}")
                    print(f"             Loại: {runtime_cfg.get('stream_type')} | Luồng: {server_url}")
            except Exception as _sync_err:
                print(f"[CLOUD SYNC] ⚠️ Không thể đồng bộ từ Server ({_sync_err}), fallback cấu hình cục bộ.")


    print("=" * 60)
    print("  HE THONG DIEM DANH STEM v5.0 Pro")
    print(f"  Camera Source: {cam_source}")
    print("  YuNet Face Detection + SFace Recognition + MOT + Anti-Spoof")
    print("  Smart Best-Shot Capture + Async I/O Worker Queue")
    print("=" * 60)

    start_time = datetime.now()

    sheet_log, sheet_stu, sheet_vio, sheet_sum = connect_sheets()
    students = {}
    if getattr(args, "server", None):
        students = fetch_students_from_server(
            api_url=args.server,
            school_id=args.school,
            camera_id=args.cam_id,
            secret_key=args.secret
        )
    if not students and sheet_stu is not None:
        students = load_students(sheet_stu)
        print(f"[OK] Da tai {len(students)} hoc sinh tu Google Sheets.\n")
    elif sheet_stu is not None:
        try:
            extra_students = load_students(sheet_stu)
            for k, v in extra_students.items():
                if k not in students:
                    students[k] = v
        except Exception:
            pass

    if not students:
        try:
            from test_offline import load_students_local
            students = load_students_local()
            print(f"[OK] Da nap {len(students)} hoc sinh tu bo dem offline cuc bo.\n")
        except Exception:
            students = {}

    conn      = get_db()
    count_map = load_today_log(sheet_log)
    print(f"[OK] Cache log: {sum(count_map.values())} ban ghi hom nay.\n")

    net_checker = NetworkChecker(check_interval=10)

    print("[FACE] Dang khoi tao OpenCV DNN YuNet + SFace Engine (v5.0 Pro)...")
    face_eng = FaceEngine(students)
    print()

    # [v5.0] Khoi tao Async AI Worker Pipeline
    face_worker = AsyncFaceWorker(face_eng) if ASYNC_WORKER_ENABLE else None
    if face_worker:
        print("[AI PIPELINE] Da kich hoat AsyncFaceWorker (Xu ly nhan dien nen 30+ FPS)")

    # [v4] Khoi tao module kiem tra trang phuc (khong lam sap he thong
    # neu thieu model/thu vien — chi tat tinh nang nay)
    uniform_checker = None
    if getattr(args, "uniform", None) is not None:
        uniform_enabled = bool(args.uniform) and UNIFORM_LIB_OK
    else:
        uniform_enabled = UNIFORM_CHECK_ENABLE and UNIFORM_LIB_OK
    if uniform_enabled:
        print("[UNIFORM] Dang khoi tao kiem tra trang phuc (HOG + AI/HSV)...")
        try:
            uniform_checker = UniformChecker(use_person_detector=True)
            print(f"[UNIFORM] Quy dinh hom nay: {UniformChecker.get_today_rule_display()}")
        except Exception as e:
            print(f"[UNIFORM] Loi khoi tao, tat tinh nang trang phuc: {e}")
            uniform_enabled = False
        print()

    # [v6] Khoi tao Multi-Object Tracker + Spatial Fusion (theo doi 3-8
    # nguoi cung luc, gan QR/mat/trang phuc dung track_id theo toa do).
    # Tai su dung PersonDetector cua UniformChecker neu co san de khong
    # phai nap HOG SVM 2 lan; neu khong thi tao rieng 1 PersonDetector.
    mot_tracker      = None
    mot_person_det   = None
    mot_enabled      = MOT_ENABLE and MOT_LIB_OK
    if mot_enabled:
        print("[MOT] Dang khoi tao Multi-Object Tracker (IoU + Centroid)...")
        try:
            mot_tracker = MultiObjectTracker(
                max_disappeared=MOT_MAX_DISAPPEARED,
                iou_threshold=MOT_IOU_THRESHOLD,
                max_centroid_dist=MOT_MAX_CENTROID_DIST,
                max_tracks=MOT_MAX_TRACKS,
            )
            if uniform_enabled and uniform_checker.person_detector is not None:
                mot_person_det = uniform_checker.person_detector
            else:
                mot_person_det = PersonDetector(use_face_fallback=True, verbose=False)
            print(f"[MOT] San sang theo doi toi da {MOT_MAX_TRACKS} nguoi cung luc.")
        except Exception as e:
            print(f"[MOT] Loi khoi tao, tat tinh nang theo doi da nguoi: {e}")
            mot_enabled = False
        print()

    anti_spoof_detector = None
    if SPOOF_LIB_OK and ANTI_SPOOF_ENABLE:
        try:
            anti_spoof_detector = AntiSpoofingDetector()
            print("[ANTI-SPOOF] AntiSpoofingDetector (Multi-factor Liveness Check) da san sang.")
        except Exception as e:
            print(f"[ANTI-SPOOF] Loi khoi tao AntiSpoofingDetector: {e}")
        print()

    smart_capture = None
    if SMART_CAP_LIB_OK:
        try:
            smart_capture = SmartCaptureEngine()
            print("[SMART CAPTURE] SmartCaptureEngine (Best-Shot + Watermark) da san sang.")
        except Exception as e:
            print(f"[SMART CAPTURE] Loi khoi tao SmartCaptureEngine: {e}")
        print()

    global bg_logger
    if ASYNC_LOG_LIB_OK:
        try:
            bg_logger = BackgroundLogger(sheet_log, sheet_vio, sheet_sum, conn, net_checker)
        except Exception as e:
            print(f"[ASYNC LOG] Loi khoi tao BackgroundLogger: {e}")

    fps_counter = FPSCounter()
    active_stream_port = getattr(args, "port", None) or STREAM_PORT
    _start_stream_server(active_stream_port)

    # Day ngay frame cho ban dau de trinh duyet va backend nhan ngay luong
    init_cam_label = f"Tram #{args.cam_id}" if getattr(args, "cam_id", None) else "Tram Camera AI"
    init_frame = create_standby_frame(
        title=f"{init_cam_label}: {cam_source}",
        subtitle="Dang khoi tao ket noi camera va engine AI YuNet + SFace...",
        detail=f"Port stream: {active_stream_port} | Server: {getattr(args, 'server', 'http://localhost:8000')}",
        status="CONNECTING"
    )
    _push_stream_frame(init_frame)

    # Mo camera (Webcam hoac luong RTSP IP)
    if isinstance(cam_source, str) and not str(cam_source).isdigit():
        os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = (
            "rtsp_transport;tcp|fflags;nobuffer|flags;low_delay|max_delay;0|"
            "probesize;32768|analyzeduration;100000|stimeout;4000000"
        )

    if ASYNC_CAMERA_ENABLE:
        print(f"[CAMERA] Khoi chay ThreadedCamera doc lap -> {cam_source}")
        cap = ThreadedCamera(cam_source, width=1280, height=720)
    else:
        cap = cv2.VideoCapture(cam_source)
        if not cap.isOpened():
            print(f"[!!] Khong mo duoc camera (source={cam_source}).")
            sys.exit(1)
        if isinstance(cam_source, int):
            cap.set(cv2.CAP_PROP_FRAME_WIDTH,  1280)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            cap.set(cv2.CAP_PROP_BUFFERSIZE,   1)

    # Cau hinh cua so hien thi chiem 3/4 man hinh va can giua (neu khong chay headless)
    cam_label = f"#{args.cam_id}" if getattr(args, "cam_id", None) else ""
    WINDOW_TITLE = f"He Thong Diem Danh v5.0 Pro {cam_label}".strip()
    if not args.headless:
        cv2.namedWindow(WINDOW_TITLE, cv2.WINDOW_NORMAL)
        try:
            import ctypes
            user32 = ctypes.windll.user32
            user32.SetProcessDPIAware()
            screen_w = user32.GetSystemMetrics(0)
            screen_h = user32.GetSystemMetrics(1)
        except Exception:
            screen_w, screen_h = 1920, 1080

        win_w = int(screen_w * 0.75)
        win_h = int(screen_h * 0.75)
        win_x = max(0, int((screen_w - win_w) / 2))
        win_y = max(0, int((screen_h - win_h) / 2))

        cv2.resizeWindow(WINDOW_TITLE, win_w, win_h)
        cv2.moveWindow(WINDOW_TITLE, win_x, win_y)

    print("=" * 60)
    print("  CAMERA SAN SANG (v5.0 Pro)")
    print("  QR      : Quet the -> diem danh tu dong")
    print("  FACE    : OpenCV DNN YuNet (5ms Detection)")
    print("            OpenCV DNN SFace (15ms Recognition)")
    print("            Phat hien nguoi la / sai the tu dong")
    if uniform_enabled:
        print("  TRANG PHUC : Kiem tra tu dong theo quy dinh tung ngay")
        print("               (SAI/KHONG RO se tu chup anh + ghi PhamLoi)")
    else:
        print("  TRANG PHUC : [TAT] (thieu model hoac bi tat trong config.py)")
    if mot_enabled:
        print(f"  MOT (v6)   : Theo doi toi da {MOT_MAX_TRACKS} nguoi cung luc (IoU+Centroid)")
        print("               Spatial Fusion: QR/Mat/Trang phuc gan dung track_id")
    else:
        print("  MOT (v6)   : [TAT] (thieu tracker.py hoac bi tat trong config.py)")
    print("  Phim    : Q/ESC=Thoat  S=Thong ke  R=Reload")
    print("            P=Pause mat  A=Them mat live  U=Bat/tat trang phuc")
    print("            T=Bat/tat khung debug track_id (MOT)")
    print("=" * 60)

    cooldown_map    = {}
    vio_cooldown    = {}
    recently_scan   = {}
    last_results    = {}
    last_face_attendance = {}
    face_consec_counts   = {}
    stranger_persist_frames = 0
    fast_locations  = []
    face_results    = []
    cached_display_results = []
    cached_display_locs    = []
    last_ai_result_time    = 0.0

    # [FIX #2] Theo doi frame_id cuoi cung da xu ly — chi tang face_consec_counts
    # khi worker tra ve ket qua THUC SU moi (result_frame_id tang), khong tang
    # khi get_results() tra ve cung 1 cached result nhieu lan (stale).
    last_consumed_frame_id = 0

    VERIFY_WINDOW   = 15
    pending_verify  = {}

    banner_msg   = ""
    banner_color = (0, 220, 80)
    banner_end   = 0.0
    face_paused  = False

    violation_count = 0
    stranger_count  = 0
    last_sync_time  = time.time()
    last_roster_sync = time.time()

    uniform_paused       = False
    uniform_cooldown     = {}
    uniform_fail_count   = 0
    uniform_unclear_count = 0
    last_uniform_result  = None

    # [v6] Multi-Object Tracking
    mot_draw_debug        = MOT_DRAW_TRACKS
    mot_attendance_cool   = {}    # {track_id: last_commit_ts} — chong commit lap

    # [fix] Truoc day dung 1 bien current_identity = "mat nhan dien gan nhat"
    # de gan cho MOI ket qua trang phuc -> sai neu 2 hoc sinh dung gan nhau
    # (gan nham nguoi). Nay giu 1 danh sach ngan cac mat da nhan duoc kem
    # toa do, va CHI gan danh tinh cho ket qua trang phuc neu tam khuon mat
    # do thuc su nam trong (hoac gan) body_box dang duoc cham diem.
    recent_faces     = []   # [{"sid","name","location":(top,right,bottom,left),"ts"}]
    IDENTITY_TIMEOUT = 5.0  # Giay — mat nhan dien qua cu se khong con duoc doi chieu

    def _face_center_in_box(location, box, margin_ratio: float = 0.35) -> bool:
        if box is None:
            return False
        top, right, bottom, left = location
        cx, cy = (left + right) / 2.0, (top + bottom) / 2.0
        x, y, w, h = box
        mx, my = w * margin_ratio, h * margin_ratio
        return (x - mx) <= cx <= (x + w + mx) and (y - my) <= cy <= (y + h + my)

    frame_count    = 0
    cam_fail_count = 0
    MAX_CAM_FAILS  = 30

    # Module phát hiện che khuất camera (Occlusion / Tampering >= 60%)
    is_occlusion_enabled = getattr(args, "occlusion_check", None)
    if is_occlusion_enabled is None and SERVER_BRIDGE_OK and bridge:
        try:
            r_cfg = bridge.fetch_runtime_config()
            if r_cfg:
                is_occlusion_enabled = bool(r_cfg.get("occlusion_check", True))
        except Exception:
            is_occlusion_enabled = True
    if is_occlusion_enabled is None:
        is_occlusion_enabled = True

    occlusion_detector = None
    if OCCLUSION_LIB_OK and is_occlusion_enabled:
        def _on_camera_occlusion(pct, proof_b64):
            cam_label = getattr(args, "cam_id", None) or 1
            print(f"\n[CAMERA OCCLUSION] 🚨 PHÁT HIỆN CAMERA #{cam_label} BỊ CHE KHUẤT {pct}% (>= 60%)!")
            print(f"                   Đang gửi thông báo khẩn cấp cho Giám Thị & Ban Giám Hiệu...")
            if bridge:
                bridge.send_camera_occlusion_alert(
                    camera_id=cam_label,
                    occlusion_percent=pct,
                    proof_image_base64=proof_b64
                )
        occlusion_detector = CameraOcclusionDetector(
            threshold_percent=60.0,
            min_consecutive_frames=10,
            cooldown_seconds=45.0,
            on_alert_callback=_on_camera_occlusion
        )
        print(f"[EDGE CAMERA] 🛡️ Đã KÍCH HOẠT tính năng Tamper Detection (Phát hiện che khuất ống kính >= 60%).")
    else:
        print(f"[EDGE CAMERA] ⚠️ Tính năng phát hiện che khuất camera ĐANG TẮT cho trạm này.")

    while True:
        ret, frame = cap.read()
        if not ret:
            cam_fail_count += 1
            # Day frame cho co dong ho thoi gian thuc deu dan (~10 FPS)
            if cam_fail_count % 3 == 0:
                err_cam_label = f"Tram #{args.cam_id}" if getattr(args, "cam_id", None) else "Tram Camera AI"
                reconnect_attempt = (cam_fail_count // 25) + 1
                err_frame = create_standby_frame(
                    title=f"{err_cam_label}: {cam_source}",
                    subtitle="Dang cho ket noi luong RTSP hoac chua mo cong RTSP 554 tren camera",
                    detail=f"Tu dong ket noi lai sau moi 3 giay... (Lan thu #{reconnect_attempt})",
                    status="OFFLINE"
                )
                _push_stream_frame(err_frame)

            if not ASYNC_CAMERA_ENABLE and cam_fail_count >= MAX_CAM_FAILS:
                if getattr(args, "auto_reconnect", True):
                    try:
                        cap.release()
                    except Exception:
                        pass
                    time.sleep(2.0)
                    cap = cv2.VideoCapture(cam_source)
                    cam_fail_count = 0
                    continue
                else:
                    break

            time.sleep(0.04)
            continue
        cam_fail_count = 0

        now        = time.time()
        frame_count += 1

        # Kiểm tra camera bị che khuất (>= 60%) định kỳ mỗi 3 frame
        if occlusion_detector is not None and frame_count % 3 == 0:
            is_cam_occluded, occ_pct, occ_alert = occlusion_detector.update(frame)
            if is_cam_occluded:
                frame = occlusion_detector.draw_hud(frame)

        # [FIX #3] Fallback mac dinh: dung frame hien tai neu worker chua tra ket qua
        recognition_frame = frame

        if frame_count % 300 == 0:
            cutoff       = now - 600
            recently_scan = {k: v for k, v in recently_scan.items() if v > cutoff}
            if len(last_results) > 10:
                for k in list(last_results.keys())[:-10]:
                    del last_results[k]

        if net_checker.is_online and (now - last_sync_time) > AUTO_SYNC_INTERVAL:
            last_sync_time = now
            if bg_logger is not None:
                bg_logger.trigger_sync_async()

        # Tự động đồng bộ lại danh sách học sinh từ Server mỗi 30s (để cập nhật khi Admin thêm/sửa HS trên Web)
        if (now - last_roster_sync) > 30:
            last_roster_sync = now
            try:
                new_stus = fetch_students_from_server(args.server, args.school, args.cam_id, args.secret)
                if new_stus and (set(new_stus.keys()) != set(students.keys())):
                    print(f"\n[ROSTER AUTO-SYNC] 🔄 Đồng bộ danh sách học sinh từ Web:")
                    print(f"                   Trước: {len(students)} HS -> Hiện tại: {len(new_stus)} HS.")
                    students = new_stus
                    face_eng.students = students
            except Exception:
                pass
            try:
                face_eng.check_for_updates()
            except Exception:
                pass

        # =====================================================================
        # BUOC 0: MOT — CAP NHAT MULTI-OBJECT TRACKER (v6)
        # =====================================================================
        # Chay HOG PersonDetector moi mot_step frame de tim body_box
        # cua tat ca nguoi trong khung hinh, roi cap nhat tracker de duy tri
        # track_id on dinh cho tung nguoi (phuc vu Spatial Fusion o Buoc 1/2/2C).
        mot_step = MOT_DETECT_INTERVAL if not (isinstance(cam_source, str) and not str(cam_source).isdigit()) else max(MOT_DETECT_INTERVAL, 12)
        if mot_enabled and frame_count % mot_step == 0:
            try:
                mot_detections = mot_person_det.detect(frame)
                mot_tracker.update([d["body_box"] for d in mot_detections])
            except Exception as e:
                print(f"[MOT] Loi cap nhat tracker: {e}")

        # =====================================================================
        # BUOC 1: QUET QR CODE
        # =====================================================================
        # Toi uu hoa: Quet tren anh xam thu nho moi 3 frame de tiet kiem CPU (nhanh gap 10x ma van rat nhay)
        if frame_count % 3 == 0:
            qr_small_gray = cv2.cvtColor(cv2.resize(frame, (640, 360)), cv2.COLOR_BGR2GRAY)
            if pyzbar.decode(qr_small_gray):
                decoded = pyzbar.decode(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY))
            else:
                decoded = []
        else:
            decoded = []

        for obj in decoded:
            raw = obj.data.decode("utf-8", errors="replace").strip()

            if now - cooldown_map.get(raw, 0) < COOLDOWN_SECONDS:
                continue
            cooldown_map[raw] = now

            name = find_student(students, raw)
            if name is None:
                beep_error()
                last_results[raw] = {"text": raw, "status": "Khong tim thay",
                                     "name": "???", "ok": False}
                banner_msg   = f"The khong hop le: {raw[:20]}"
                banner_color = (0, 0, 200)
                banner_end   = now + BANNER_DURATION
                continue

            # [v6 Spatial Fusion] Gan the QR vua quet vao dung track_id
            # (nguoi) theo toa do — de UniformChecker + HUD biet chinh xac
            # LA AI trong so 3-8 nguoi dang dung truoc camera da quet the.
            if mot_enabled and mot_tracker is not None:
                qr_track = mot_tracker.find_track_for_qr(obj.rect)
                if qr_track is not None:
                    mot_tracker.link_qr(qr_track, raw, name)

            # Tinh trang (Vao/Ra) dua tren count_map HIEN TAI (chua cap nhat)
            status = get_status_cache(count_map, raw)
            ts     = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

            pending_verify[raw] = {
                "scan_time": now,
                "name":      name,
                "ts":        ts,
                "status":    status,
                "batch_row": [ts, raw, name, status],
            }
            print(f"  [XAC MINH] Da quet the: {raw} ({name}) - Dang cho nhan dien mat...")
            beep_success()

            last_results[raw] = {"text": raw, "status": status,
                                  "name": name, "ok": True}

            status_vn    = "VAO" if status == "Vao" else "RA"
            banner_msg   = f"{status_vn}: {name} | Huong mat vao camera..."
            banner_color = (0, 200, 80) if status == "Vao" else (0, 160, 255)
            banner_end   = now + VERIFY_WINDOW

        # =====================================================================
        # BUOC 2: PHAT HIEN & NHAN DIEN KHUON MAT (YuNet + SFace v5.0)
        # =====================================================================
        if face_paused:
            fast_locations = []
            face_results   = []
            cached_display_results = []
            cached_display_locs    = []
        elif face_worker is not None:
            face_worker.submit_frame(frame)
            raw_fast_locs, raw_face_results, ai_latency = face_worker.get_results()

            current_result_frame_id = face_worker.result_frame_id
            is_new_ai_result = (current_result_frame_id != last_consumed_frame_id)
            if is_new_ai_result:
                last_consumed_frame_id = current_result_frame_id
                last_ai_result_time    = now
                rec_f = face_worker.get_recognition_frame()
                recognition_frame = rec_f if rec_f is not None else frame
                face_results = raw_face_results
                fast_locations = raw_fast_locs
                cached_display_results = list(raw_face_results)
                cached_display_locs    = list(raw_fast_locs)
            else:
                # [FIX BOUNDER BOX CŨ] Nếu đã quá 0.28s không có cập nhật AI mới (người đã rời camera)
                # -> XÓA SẠCH toàn bộ bounding box cũ, không để khung cũ bị lưu lại trên màn hình!
                if (now - last_ai_result_time) > 0.28:
                    fast_locations = []
                    cached_display_results = []
                    cached_display_locs    = []
                else:
                    fast_locations = list(cached_display_locs)
                # Không commit điểm danh ở frame trung gian
                face_results = []
        else:
            fast_locations = face_eng.detect_locations(frame)
            if frame_count % FACE_SKIP_FRAMES == 0:
                face_results = face_eng.recognize(frame)
                cached_display_results = list(face_results)
                cached_display_locs    = list(fast_locations)
                last_ai_result_time    = now
            else:
                if (now - last_ai_result_time) > 0.28:
                    fast_locations = []
                    cached_display_results = []
                    cached_display_locs    = []
                face_results = []
            recognition_frame = frame  # Sync mode: frame hien tai la frame nhan dien

        # [v6+ DUAL SCAN: Dong bo tracker tuc thi tu tat ca cac khuon mat phat hien]
        if mot_enabled and mot_tracker is not None:
            if fast_locations:
                mot_tracker.update_from_faces(fast_locations, frame.shape[1], frame.shape[0])

            if not face_paused and face_results:
                for fr in face_results:
                    face_track = mot_tracker.find_track_for_face(fr["location"])
                    if face_track is not None:
                        mot_tracker.link_face(
                            face_track, fr.get("student_id"),
                            fr.get("name"), fr["location"]
                        )

        if not face_paused and face_results:

            for fr in face_results:
                if fr.get("student_id") and fr.get("status") != "stranger":
                    recent_faces.append({
                        "sid": fr["student_id"], "name": fr["name"],
                        "location": fr["location"], "ts": now,
                    })
            if recent_faces:
                recent_faces = [f for f in recent_faces if now - f["ts"] <= IDENTITY_TIMEOUT]

            grace_ids = {
                sid for sid, t in recently_scan.items()
                if (now - t) < FACE_GRACE_SECONDS
            }

            expired = {
                k: v for k, v in pending_verify.items()
                if (now - v["scan_time"]) >= VERIFY_WINDOW
            }
            for card_id, entry in expired.items():
                print(f"  [HUY] The '{card_id}' ({entry['name']}) het {VERIFY_WINDOW}s, khong nhan dien duoc mat -> HUY GHI NHAN")
                banner_msg   = f"[HUY] {entry['name']}: Khong xac minh duoc mat!"
                banner_color = (0, 100, 200)
                banner_end   = now + BANNER_DURATION
            pending_verify = {
                k: v for k, v in pending_verify.items()
                if (now - v["scan_time"]) < VERIFY_WINDOW
            }

            # Xác định người lạ độc lập trong frame (loại trừ nhiễu nền gần học sinh)
            def _is_isolated_stranger(f_stranger, all_faces):
                s_loc = f_stranger.get("location")
                if not s_loc:
                    return False
                fw = s_loc[1] - s_loc[3]
                fh = s_loc[2] - s_loc[0]
                if fw < 45 or fh < 45:
                    return False
                s_cx, s_cy = (s_loc[1] + s_loc[3]) / 2.0, (s_loc[0] + s_loc[2]) / 2.0
                for f_other in all_faces:
                    if f_other.get("student_id") is not None and f_other.get("location"):
                        o_loc = f_other["location"]
                        o_cx, o_cy = (o_loc[1] + o_loc[3]) / 2.0, (o_loc[0] + o_loc[2]) / 2.0
                        if ((s_cx - o_cx) ** 2 + (s_cy - o_cy) ** 2) ** 0.5 < 100:
                            return False
                return True

            has_valid_stranger = any(
                f.get("status") == "stranger" and f.get("student_id") is None and _is_isolated_stranger(f, face_results)
                for f in face_results
            )
            if not has_valid_stranger:
                stranger_persist_frames = 0

            # ----------------------------------------------------------------
            # [FIX #1] Reset face_consec_counts cho cac sid VANG MAT frame nay.
            # Neu khong reset, counter tich luy tu ky truoc khien FACE_CONFIRM_FRAMES
            # vo nghia — hoc sinh can phai xuat hien lien tiep THAT SU moi duoc
            # diem danh, khong phai tong cong cac lan xuat hien roi tu do toi nay.
            # ----------------------------------------------------------------
            detected_sids_this_frame = {
                fr["student_id"] for fr in face_results
                if fr.get("student_id")
            }
            for sid_key in list(face_consec_counts.keys()):
                if sid_key not in detected_sids_this_frame:
                    face_consec_counts[sid_key] = 0

            ready_to_attend = []

            for fr in face_results:
                sid    = fr["student_id"]
                name   = fr["name"]
                status = fr["status"]
                loc    = fr["location"]
                conf   = fr.get("confidence", 0.0)

                # -------------------------------------------------------------
                # 0. KIỂM TRA LIVENESS (ANTI-SPOOFING)
                # -------------------------------------------------------------
                if SPOOF_LIB_OK and anti_spoof_detector is not None and loc is not None and ANTI_SPOOF_ENABLE:
                    trk_current = mot_tracker.find_track_for_face(loc) if (mot_enabled and mot_tracker) else None
                    # [TỐI ƯU] Gán track_id theo MOT hoặc theo student_id đã nhận diện, giúp hàng đợi voting ổn định
                    track_id = trk_current.id if trk_current else (f"stu_{sid}" if sid else None)
                    liveness = anti_spoof_detector.check_liveness(recognition_frame, loc, track_id=track_id)
                    if not liveness["is_real"]:
                        trk_spoof = trk_current
                        if trk_spoof:
                            mot_tracker.link_spoof(trk_spoof, True, liveness["status"])

                        key_spoof = f"SPOOF_{sid if sid else 'UNKNOWN'}"
                        if now - vio_cooldown.get(key_spoof, 0) >= VIOLATION_COOLDOWN:
                            vio_cooldown[key_spoof] = now
                            violation_count += 1
                            target_info = {
                                "track_id": trk_spoof.id if trk_spoof else "?",
                                "name": name if name else "Gia mao",
                                "student_id": sid if sid else "SPOOF",
                                "uniform_status": trk_spoof.uniform_status if trk_spoof else "N/A",
                                "spoof_status": liveness["status"],
                                "is_violation": True,
                                "violation_label": f"LOI: GIA MAO ({liveness['status']})"
                            }
                            snap_b64 = None
                            if smart_capture is not None:
                                portrait_p, scene_p, snap_b64 = smart_capture.capture_best_shot(
                                    recognition_frame, loc, trk_spoof.body_box if trk_spoof else None,
                                    target_info, violation_type=f"LOI_GIA_MAO_{liveness['status']}"
                                )
                                path = scene_p
                            else:
                                target_frame = PersonDetector.draw_target_boxes(
                                    recognition_frame, trk_spoof.body_box if trk_spoof else None,
                                    loc, target_info, force_red=True
                                ) if PersonDetector is not None else recognition_frame.copy()
                                path = face_eng.capture_violation(
                                    target_frame, sid if sid else "SPOOF", name if name else "Khong ro",
                                    reason=liveness['message'], face_loc=loc
                                )

                            if path:
                                log_violation(sheet_vio, conn, sid if sid else "SPOOF", name if name else "Nguoi dung gia mao", path, reason=liveness["message"], proof_image_base64=snap_b64)
                            beep_error()
                            banner_msg   = f"[CANH BAO GIAN LAN] {name}: {liveness['message']}"
                            banner_color = (0, 0, 255)  # Đỏ cảnh báo giả mạo
                            banner_end   = now + BANNER_DURATION * 2
                        continue
                    else:
                        trk_ok = trk_current
                        if trk_ok and trk_ok.is_spoof:
                            mot_tracker.link_spoof(trk_ok, False, None)

                # -------------------------------------------------------------
                # 1. HỌC SINH ĐƯỢC NHẬN DIỆN KHUÔN MẶT HỢP LỆ (sid hợp lệ)
                # -------------------------------------------------------------
                if sid:
                    # A. Khớp thẻ QR trong hàng đợi (2-Factor QR + Face)
                    if pending_verify:
                        matched_card = None
                        for card_id, entry in list(pending_verify.items()):
                            if card_id.strip().upper() == sid.strip().upper():
                                matched_card = card_id
                                break

                        if matched_card:
                            entry = pending_verify.pop(matched_card)
                            count_map[matched_card] = count_map.get(matched_card, 0) + 1
                            # [FIX #4] Dung recognition_frame voi day du all_faces
                            snap_b64 = capture_attendance_frame(
                                recognition_frame, matched_card, entry["name"], "VAO",
                                face_loc=fr.get("location") if fr else None,
                                all_faces=face_results
                            )
                            flush_qr_batch(sheet_log, conn, [entry["batch_row"]], proof_image_base64=snap_b64)
                            recently_scan[matched_card] = now
                            print_log(entry["ts"], matched_card, entry["name"], entry["status"])
                            print(f"  [KHOP 2-FACTOR] The '{matched_card}' - Mat '{sid}' ({name}) -> XAC NHAN DIEM DANH")
                            banner_msg   = f"[OK] KHOP: {name} ({matched_card})"
                            banner_color = (0, 220, 80)
                            banner_end   = now + BANNER_DURATION * 1.5

                            if mot_enabled and mot_tracker is not None:
                                commit_track = mot_tracker.find_track_for_face(fr["location"])
                                if commit_track is not None:
                                    last_commit = mot_attendance_cool.get(commit_track.id, 0)
                                    if now - last_commit >= MOT_ATTENDANCE_COOLDOWN:
                                        mot_attendance_cool[commit_track.id] = now
                                        commit_track.attendance_done = True
                                        commit_track.status_time = now
                                        # [fix] Giữ face_location để uniform check vẫn hoạt động sau khi điểm danh

                        else:
                            for card_id, entry in list(pending_verify.items()):
                                card_name = entry["name"]
                                key_mismatch = f"MISMATCH_{card_id}"
                                if now - vio_cooldown.get(key_mismatch, 0) < VIOLATION_COOLDOWN:
                                    continue
                                vio_cooldown[key_mismatch] = now
                                violation_count += 1
                                pending_verify.pop(card_id, None)
                                print(f"  [GIAN LAN] The '{card_id}' ({card_name}) - Mat '{sid}' ({name}) -> KHONG KHOP! HUY GHI NHAN CA 2")
                                path = face_eng.capture_violation(
                                    recognition_frame.copy(), card_id, card_name,
                                    reason=f"GIAN LAN: The={card_id} Mat={sid}",
                                    face_loc=fr.get("location")
                                )
                                if path:
                                    log_violation(
                                        sheet_vio, conn, card_id, card_name, path,
                                        reason=f"Gian lan: the {card_id} nhung mat {sid} ({name})"
                                    )
                                beep_error()
                                banner_msg   = f"[!!] KHONG KHOP: The={card_id} / Mat={sid} -> HUY"
                                banner_color = (0, 0, 220)
                                banner_end   = now + BANNER_DURATION * 2
                                break

                    # B. Điểm danh sinh trắc học trực tiếp (FaceID Auto Mode) - Gom danh sách đa khuôn mặt
                    elif ATTENDANCE_MODE in ("AUTO", "FACE_ONLY"):
                        face_consec_counts[sid] = face_consec_counts.get(sid, 0) + 1
                        if face_consec_counts[sid] >= FACE_CONFIRM_FRAMES:
                            if (now - last_face_attendance.get(sid, 0)) >= COOLDOWN_SECONDS:
                                ready_to_attend.append(fr)
                            else:
                                # Duy tri hien thi mau xanh da diem danh gan day
                                recently_scan[sid] = now

                    # C. Chế độ bắt buộc quét thẻ trước (2FACTOR_QR_FACE)
                    elif ATTENDANCE_MODE == "2FACTOR_QR_FACE" and status == "warn" and sid not in grace_ids:
                        if now - vio_cooldown.get(sid, 0) >= VIOLATION_COOLDOWN:
                            vio_cooldown[sid] = now
                            violation_count  += 1
                            path = face_eng.capture_violation(
                                frame.copy(), sid, name, reason="CHUA QUET THE",
                                face_loc=fr.get("location")
                            )
                            if path:
                                log_violation(sheet_vio, conn, sid, name, path,
                                              reason="Chua quet the")
                            beep_error()
                            banner_msg   = f"CANH BAO: {name} chua quet the!"
                            banner_color = (0, 60, 230)
                            banner_end   = now + BANNER_DURATION * 1.5

                # -------------------------------------------------------------
                # 2. KHUÔN MẶT KHÔNG XÁC ĐỊNH (NGƯỜI LẠ)
                # -------------------------------------------------------------
                elif status == "stranger" and STRANGER_ALERT_ENABLE:
                    # Kiểm tra khuôn mặt người lạ độc lập (không phải bóng/nhiễu sát học sinh)
                    if not _is_isolated_stranger(fr, face_results):
                        continue

                    stranger_persist_frames += 1
                    # [TỐI ƯU SIÊU TỐC] Giảm từ 8 frame xuống >= 3 frame (~0.25 - 0.35s) để bắt ngay người lạ khi đi qua cổng
                    if stranger_persist_frames >= 8:
                        key_stranger = f"STRANGER_{int(now/VIOLATION_COOLDOWN)}"
                        if now - vio_cooldown.get(key_stranger, 0) >= VIOLATION_COOLDOWN:
                            vio_cooldown[key_stranger] = now
                            stranger_count += 1
                            stranger_trk = mot_tracker.find_track_for_face(loc) if (mot_enabled and mot_tracker) else None
                            b_box = stranger_trk.body_box if stranger_trk else None
                            label_info = {
                                "track_id": stranger_trk.id if stranger_trk else "?",
                                "name": "Nguoi la (Chua xac dinh)",
                                "student_id": "STRANGER",
                                "uniform_status": "N/A",
                                "confidence": conf,
                                "is_violation": True,
                                "violation_label": "CANH BAO AN NINH: NGUOI LA"
                            }

                            # Bắt bộ ảnh nét nhất từ recognition_frame chuẩn thời điểm nhận diện
                            snap_b64 = None
                            if smart_capture is not None:
                                portrait_p, scene_p, snap_b64 = smart_capture.capture_best_shot(
                                    recognition_frame, loc, b_box,
                                    label_info, violation_type="CANH_BAO_NGUOI_LA"
                                )
                                path = scene_p
                            else:
                                path = face_eng.capture_violation(
                                    recognition_frame.copy(), "STRANGER", "Nguoi la", reason="NGUOI LA",
                                    face_loc=loc, body_box=b_box
                                )

                            if path:
                                log_violation(sheet_vio, conn, "STRANGER", "Nguoi la", path,
                                              reason="Nguoi la - khong trong danh sach",
                                              proof_image_base64=snap_b64,
                                              direction="IN")
                            beep_error()
                            banner_msg   = "🚨 CANH BAO AN NINH: Phat hien nguoi la!"
                            banner_color = (0, 0, 200)
                            banner_end   = now + BANNER_DURATION * 2.0

            # -----------------------------------------------------------------
            # [NÂNG CẤP ĐA KHUÔN MẶT]: Xử lý điểm danh đồng thời (Single & Multi)
            # -----------------------------------------------------------------
            if ready_to_attend:
                if len(ready_to_attend) == 1:
                    fr = ready_to_attend[0]
                    sid = fr["student_id"]
                    name = fr["name"]
                    conf = fr.get("confidence", 0.0)
                    last_face_attendance[sid] = now
                    recently_scan[sid] = now
                    face_consec_counts[sid] = 0

                    commit_track = None
                    if mot_enabled and mot_tracker is not None:
                        commit_track = mot_tracker.find_track_for_face(fr["location"])
                        if commit_track is not None:
                            commit_track.attendance_done = True
                            commit_track.status_time = now
                            # [fix] Giữ face_location để uniform check vẫn hoạt động sau khi điểm danh

                    u_stat = "OK"
                    u_reason = None
                    if uniform_enabled and uniform_checker is not None:
                        b_box = commit_track.body_box if commit_track else None
                        trk_u_stat = getattr(commit_track, "uniform_status", None)
                        if trk_u_stat is None:
                            try:
                                uni_eval = uniform_checker.predict(recognition_frame, body_box=b_box)
                                trk_u_stat = uni_eval.get("status")
                                if commit_track is not None:
                                    mot_tracker.link_uniform(
                                        commit_track, trk_u_stat,
                                        uni_eval.get("message", ""),
                                        uni_eval.get("label", ""),
                                        uni_eval.get("confidence", 0.0)
                                    )
                            except Exception:
                                pass
                        if trk_u_stat in ("FAIL", "VIOLATION"):
                            u_stat = "VIOLATION"
                            u_reason = getattr(commit_track, "uniform_message", "Vi pham trang phuc")
                        elif trk_u_stat == "OK":
                            u_stat = "OK"

                    status_att = get_status_cache(count_map, sid)
                    status_vn  = "VAO" if status_att == "Vao" else "RA"
                    count_map[sid] = count_map.get(sid, 0) + 1

                    ts = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                    batch_row = [ts, sid, name, status_att, f"FACE_AI ({int(conf * 100)}%)", u_stat, u_reason]
                    # Chụp ảnh có toàn bộ khuôn mặt trong khung hình (all_faces)
                    snap_b64 = capture_attendance_frame(
                        recognition_frame, sid, name, status_vn,
                        face_loc=fr.get("location"),
                        all_faces=face_results
                    )
                    flush_qr_batch(sheet_log, conn, [batch_row], proof_image_base64=snap_b64)
                    print_log(ts, sid, name, status_att)
                    print(f"  [FACE_ID] {status_vn}: '{sid}' ({name}) - Conf: {conf:.2f} | Phuc: {u_stat} -> DIEM DANH KHUON MAT THANH CONG")

                    beep_success()
                    banner_msg   = f"[OK] {status_vn}: {name} ({sid}) | DIEM DANH THANH CONG"
                    banner_color = (0, 220, 80) if status_att == "Vao" else (0, 160, 255)
                    banner_end   = now + BANNER_DURATION * 1.5
                else:
                    # Điểm danh đồng thời nhiều học sinh (Batch Multi-Face Attendance)
                    batch_rows = []
                    names_attended = []
                    ts = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                    first_status_vn = "VAO"

                    for fr in ready_to_attend:
                        sid = fr["student_id"]
                        name = fr["name"]
                        conf = fr.get("confidence", 0.0)
                        last_face_attendance[sid] = now
                        recently_scan[sid] = now
                        face_consec_counts[sid] = 0

                        commit_track = None
                        if mot_enabled and mot_tracker is not None:
                            commit_track = mot_tracker.find_track_for_face(fr["location"])
                            if commit_track is not None:
                                commit_track.attendance_done = True
                                commit_track.status_time = now
                                # [fix] Giữ face_location để uniform check vẫn hoạt động sau khi điểm danh

                        u_stat = "OK"
                        u_reason = None
                        if uniform_enabled and uniform_checker is not None:
                            b_box = commit_track.body_box if commit_track else None
                            trk_u_stat = getattr(commit_track, "uniform_status", None)
                            if trk_u_stat is None:
                                try:
                                    uni_eval = uniform_checker.predict(recognition_frame, body_box=b_box)
                                    trk_u_stat = uni_eval.get("status")
                                    if commit_track is not None:
                                        mot_tracker.link_uniform(
                                            commit_track, trk_u_stat,
                                            uni_eval.get("message", ""),
                                            uni_eval.get("label", ""),
                                            uni_eval.get("confidence", 0.0)
                                        )
                                except Exception:
                                    pass
                            if trk_u_stat in ("FAIL", "VIOLATION"):
                                u_stat = "VIOLATION"
                                u_reason = getattr(commit_track, "uniform_message", "Vi pham trang phuc")
                            elif trk_u_stat == "OK":
                                u_stat = "OK"

                        status_att = get_status_cache(count_map, sid)
                        status_vn  = "VAO" if status_att == "Vao" else "RA"
                        first_status_vn = status_vn
                        count_map[sid] = count_map.get(sid, 0) + 1

                        batch_rows.append([ts, sid, name, status_att, f"FACE_AI_MULTI ({int(conf * 100)}%)", u_stat, u_reason])
                        names_attended.append(f"{name} ({sid})")
                        print_log(ts, sid, name, status_att)
                        print(f"  [FACE_ID MULTI] {status_vn}: '{sid}' ({name}) - Conf: {conf:.2f} | Phuc: {u_stat} -> DIEM DANH DONG THOI")

                    # Chụp 1 ảnh chung chất lượng cao chứa tất cả các học sinh được đánh dấu
                    snap_b64 = capture_attendance_frame(
                        recognition_frame,
                        student_id="MULTI",
                        student_name=f"{len(ready_to_attend)} HS",
                        direction_str=first_status_vn,
                        all_faces=face_results,
                        multi_students=ready_to_attend
                    )
                    flush_qr_batch(sheet_log, conn, batch_rows, proof_image_base64=snap_b64)

                    beep_success()
                    banner_msg   = f"🎉 [ĐA KHUÔN MẶT - {len(ready_to_attend)} HS] DIEM DANH THANH CONG: {', '.join(names_attended[:2])}"
                    banner_color = (0, 230, 100)
                    banner_end   = now + BANNER_DURATION * 2.0

        # =====================================================================
        # BUOC 2C: KIEM TRA TRANG PHUC [v4] — HOG + AI TFLite / HSV Color
        # [v6] Khi MOT bat: cham DOC LAP tren TUNG track dang active (3-8
        # nguoi cung luc) thay vi chi cham 1 nguoi dau tien phat hien duoc.
        # =====================================================================
        def _handle_uniform_result(uni_result, sid_u, name_u, cooldown_key, track_obj=None, recog_frame=None):
            """Xu ly 1 ket qua kiem tra trang phuc — Smart Best-Shot Dual Capture voi Target Bounding Box & Watermark."""
            nonlocal uniform_fail_count, uniform_unclear_count
            nonlocal banner_msg, banner_color, banner_end

            # [fix] Dùng frame được truyền vào thay vì lấy từ outer scope
            # recognition_frame trong outer scope có thể đã bị cập nhật bởi async worker
            _cap_frame = recog_frame if recog_frame is not None else recognition_frame

            u_status = uni_result["status"]
            if u_status in ("FAIL", "UNCLEAR"):
                vio_tag = f"UNIFORM_{u_status}"
                trk_id_val = getattr(track_obj, "id", None)
                trk_cooldown_key = f"TRK_{trk_id_val}_{vio_tag}" if trk_id_val is not None else None

                # Kiểm tra cooldown theo track (35s) — tránh khóa vĩnh viễn cả track
                if trk_cooldown_key and (now - uniform_cooldown.get(trk_cooldown_key, 0) < UNIFORM_VIOLATION_COOLDOWN):
                    return

                key = f"UNIFORM_{u_status}_{cooldown_key}"
                if now - uniform_cooldown.get(key, 0) >= UNIFORM_VIOLATION_COOLDOWN:
                    uniform_cooldown[key] = now
                    if trk_cooldown_key:
                        uniform_cooldown[trk_cooldown_key] = now

                    if u_status == "FAIL":
                        uniform_fail_count += 1
                    else:
                        uniform_unclear_count += 1

                    label_info = {
                        "track_id": getattr(track_obj, "id", "?"),
                        "name": name_u,
                        "student_id": sid_u,
                        "uniform_status": u_status,
                        "spoof_status": getattr(track_obj, "spoof_status", "REAL"),
                        "confidence": uni_result.get("confidence", None),
                        "is_violation": True,
                        "violation_label": f"LOI: {uni_result['message']}"
                    }

                    snap_b64 = None
                    if smart_capture is not None:
                        portrait_p, scene_p, snap_b64 = smart_capture.capture_best_shot(
                            _cap_frame,
                            getattr(track_obj, "face_location", None),
                            getattr(track_obj, "body_box", None),
                            label_info,
                            violation_type=f"LOI: {uni_result['message']}"
                        )
                        path = scene_p
                    else:
                        target_frame = PersonDetector.draw_target_boxes(
                            _cap_frame,
                            getattr(track_obj, "body_box", None),
                            getattr(track_obj, "face_location", None),
                            label_info,
                            force_red=True
                        ) if PersonDetector is not None else _cap_frame.copy()
                        path = face_eng.capture_violation(target_frame, sid_u, name_u, reason=uni_result['message'])

                    if track_obj is not None and hasattr(track_obj, "captured_violations"):
                        track_obj.captured_violations.add(vio_tag)

                    if path:
                        log_violation(
                            sheet_vio, conn, sid_u, name_u, path,
                            reason=f"Trang phuc ({uni_result['rule']}): {uni_result['message']}",
                            proof_image_base64=snap_b64
                        )
                    beep_error()
                    banner_msg   = f"[TRANG PHUC] {name_u}: {uni_result['message']}"
                    banner_color = COLOR_FAIL if u_status == "FAIL" else COLOR_UNCLEAR
                    banner_end   = now + BANNER_DURATION * 1.5

        # Tối ưu: Kiểm tra ngay lập tức khi có đối tượng mới xuất hiện chưa rõ trang phục
        has_untested_track = False
        if mot_enabled and mot_tracker is not None:
            has_untested_track = any(getattr(t, "uniform_status", None) is None for t in mot_tracker.tracks.values())

        if (uniform_enabled and not uniform_paused
                and (has_untested_track or frame_count % min(6, UNIFORM_CHECK_INTERVAL) == 0)):
            try:
                if mot_enabled and mot_tracker is not None and mot_tracker.count() > 0:
                    # ── [v6] MOT: cham TUNG track dang active, doc lap ──
                    track_results = uniform_checker.predict_tracks(frame, mot_tracker.tracks, frame_count, UNIFORM_CHECK_INTERVAL)
                    for trk_id, uni_result in track_results.items():
                        last_uniform_result = uni_result
                        trk = mot_tracker.get_track(trk_id)
                        if trk:
                            mot_tracker.link_uniform(
                                trk, uni_result["status"],
                                uni_result.get("message", ""),
                                uni_result.get("label", ""),
                                uni_result.get("confidence", 0.0)
                            )
                        sid_u  = trk.student_id if (trk and trk.student_id) else f"TRACK{trk_id}"
                        name_u = trk.name if (trk and trk.name) else f"Nguoi #{trk_id} (chua xac dinh danh tinh)"
                        cooldown_key = sid_u

                        _handle_uniform_result(uni_result, sid_u, name_u, cooldown_key, track_obj=trk, recog_frame=recognition_frame)
                else:
                    # ── Fallback: khong co MOT -> cham 1 nguoi dau tien ──
                    detections = uniform_checker.get_body_boxes(frame)
                    body_box   = detections[0]["body_box"] if detections else None
                    uni_result = uniform_checker.predict(frame, body_box=body_box)
                    last_uniform_result = uni_result

                    recent_faces = [f for f in recent_faces if now - f["ts"] <= IDENTITY_TIMEOUT]
                    matched = next(
                        (f for f in recent_faces if _face_center_in_box(f["location"], body_box)),
                        None
                    )
                    sid_u  = matched["sid"]  if matched else "UNKNOWN"
                    name_u = matched["name"] if matched else "Chua xac dinh danh tinh"

                    _handle_uniform_result(uni_result, sid_u, name_u, sid_u, track_obj=None, recog_frame=recognition_frame)
            except Exception as e:
                print(f"[UNIFORM] Loi khi kiem tra: {e}")

        result_display = {"text": "", "status": "", "name": "", "ok": True}
        if last_results:
            result_display = list(last_results.values())[-1]

        frame = draw_overlay(frame, decoded, result_display)

        grace_ids_draw = {
            sid for sid, t in recently_scan.items()
            if (now - t) < 1.2
        }
        frame = face_eng.draw_overlay(frame, fast_locations, cached_display_results, grace_ids_draw)

        # [v6] Ve khung debug Multi-Object Tracking (chi ve body box de khong de trung khung mat ma)
        if mot_enabled and mot_tracker is not None:
            if mot_draw_debug:
                for trk in mot_tracker.get_active_tracks():
                    trk_info = {
                        "track_id": trk.id,
                        "name": trk.name if trk.name else "Nguoi dung",
                        "student_id": trk.student_id if trk.student_id else "",
                        "uniform_status": trk.uniform_status if trk.uniform_status else "CHUA_CHECK",
                        "uniform_message": getattr(trk, "uniform_message", ""),
                        "uniform_label": getattr(trk, "uniform_label", ""),
                        "uniform_conf": getattr(trk, "uniform_conf", 0.0),
                        "spoof_status": trk.spoof_status if trk.spoof_status else "REAL",
                        "is_stranger": trk.is_stranger,
                        "qr_scanned": trk.qr_scanned,
                        "face_matched": trk.face_matched,
                    }
                    frame = PersonDetector.draw_target_boxes(frame, trk.body_box, None, trk_info) if PersonDetector is not None else frame

        real_fps = fps_counter.update()
        frame = draw_clock(frame, fps=real_fps)
        mot_cnt = mot_tracker.count() if (mot_enabled and mot_tracker is not None) else 0
        frame = draw_stats(frame, count_map, len(students), violation_count=violation_count, mot_count=mot_cnt)

        if now < banner_end and banner_msg:
            alpha = min(1.0, (banner_end - now) / 0.5)
            frame = draw_banner(frame, banner_msg, banner_color, alpha)

        h_f, w_f = frame.shape[:2]
        if face_paused:
            cv2.putText(frame, "[P] Nhan dien mat: TAM DUNG",
                        (10, h_f - 95),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.48, (0, 200, 255), 1)

        net_label = "[ONLINE]" if net_checker.is_online else "[OFFLINE - Luu cuc bo]"
        net_color = (0, 200, 80) if net_checker.is_online else (0, 100, 255)
        cv2.putText(frame, net_label,
                    (w_f - 260, h_f - 85),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, net_color, 1)

        n_haar = len(fast_locations)
        n_recg = len(face_results)
        n_qr   = len(decoded)
        cv2.putText(frame,
                    f"FPS:{real_fps:.1f}  Haar:{n_haar}  Nhan:{n_recg}  QR:{n_qr}  Nguoi la:{stranger_count}"
                    f"  AoSai:{uniform_fail_count}  KhongRo:{uniform_unclear_count}"
                    f"  MOT:{mot_cnt}",
                    (10, h_f - 58),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 255, 255), 1)

        if not uniform_enabled:
            cv2.putText(frame, "[TRANG PHUC: KHONG KHA DUNG]", (10, 90),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (140, 140, 140), 1)
        elif last_uniform_result is not None:
            frame = uniform_checker.draw_result(frame, last_uniform_result, position=(10, 90))
            if uniform_paused:
                cv2.putText(frame, "[U] TAM DUNG", (10, 130),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 200, 255), 1)

        # Day frame da ve hoan tat overlay vao live stream
        _push_stream_frame(frame)

        if not args.headless:
            cv2.imshow("He Thong Diem Danh  v5.0 Pro", frame)
            key = cv2.waitKey(1) & 0xFF
        else:
            time.sleep(0.001)
            key = 0xFF

        if key in (ord("q"), ord("Q"), 27):
            print("\n[CAMERA] Nguoi dung bam Thoat (Q/ESC).")
            break

        elif key in (ord("s"), ord("S")):
            present = sum(1 for c in count_map.values() if c % 2 == 1)
            print("\n" + "=" * 44)
            print(f"  THONG KE  {date.today().strftime('%d/%m/%Y')}")
            print(f"  Tong hoc sinh   : {len(students)}")
            print(f"  Co mat          : {present}")
            print(f"  Vang mat        : {len(students) - present}")
            print(f"  Vi pham (the)   : {violation_count}")
            print(f"  Nguoi la        : {stranger_count}")
            if uniform_enabled:
                print(f"  Sai trang phuc  : {uniform_fail_count}")
                print(f"  Trang phuc KR   : {uniform_unclear_count}")
                print(f"  Quy dinh hom nay: {UniformChecker.get_today_rule_display()}")
            if mot_enabled and mot_tracker is not None:
                print(f"  MOT dang track  : {mot_tracker.count()} nguoi")
                for trk in mot_tracker.get_active_tracks():
                    print(f"    - Track#{trk.id}: {trk.name or '???'} "
                          f"QR={trk.qr_scanned} Mat={trk.face_matched} "
                          f"AoQuan={trk.uniform_status} NguoiLa={trk.is_stranger}")
            print("=" * 44 + "\n")

        elif key in (ord("u"), ord("U")):
            if not uniform_enabled:
                print("[UNIFORM] Khong the bat: thieu model/thu vien hoac da tat trong config.py.")
            else:
                uniform_paused = not uniform_paused
                banner_msg   = "[U] TAM DUNG TRANG PHUC" if uniform_paused else "[U] TIEP TUC TRANG PHUC"
                banner_color = (0, 200, 255) if uniform_paused else (0, 220, 80)
                banner_end   = now + BANNER_DURATION
                print(f"[UNIFORM] {'TAM DUNG' if uniform_paused else 'TIEP TUC'} kiem tra trang phuc.")

        elif key in (ord("t"), ord("T")):
            if not mot_enabled:
                print("[MOT] Khong the bat: thieu tracker.py/person_detector.py hoac da tat trong config.py.")
            else:
                mot_draw_debug = not mot_draw_debug
                banner_msg   = "[T] BAT KHUNG DEBUG MOT" if mot_draw_debug else "[T] TAT KHUNG DEBUG MOT"
                banner_color = (200, 180, 0)
                banner_end   = now + BANNER_DURATION
                print(f"[MOT] {'BAT' if mot_draw_debug else 'TAT'} hien thi khung debug track_id.")

        elif key in (ord("r"), ord("R")):
            print("\n[RELOAD] Dang tai lai danh sach hoc sinh...")
            try:
                if sheet_stu is not None:
                    students  = load_students(sheet_stu)
                else:
                    students  = fetch_students_from_server(args.server, args.school, args.cam_id, args.secret)
                count_map = load_today_log(sheet_log)
                face_eng.students = students
                face_eng.reload()
                print(f"[RELOAD] Da tai {len(students)} hoc sinh.\n")
                banner_msg   = f"Da tai {len(students)} hoc sinh!"
                banner_color = (0, 200, 80)
                banner_end   = now + BANNER_DURATION
            except Exception as e:
                print(f"[RELOAD] Loi: {e}\n")

        elif key in (ord("p"), ord("P")):
            face_paused = not face_paused
            banner_msg   = "[P] TAM DUNG NHAN DIEN MAT" if face_paused else "[P] TIEP TUC NHAN DIEN MAT"
            banner_color = (0, 200, 255) if face_paused else (0, 220, 80)
            banner_end   = now + BANNER_DURATION
            print(f"[FACE] {'TAM DUNG' if face_paused else 'TIEP TUC'} nhan dien mat.")

        elif key in (ord("a"), ord("A")):
            sid_input = input("[ADD FACE] Nhap MaHS: ").strip().upper()
            if sid_input:
                if face_eng.add_face_live(frame.copy(), sid_input):
                    banner_msg   = f"Da them khuon mat: {sid_input}"
                    banner_color = (200, 180, 0)
                    banner_end   = now + BANNER_DURATION
                else:
                    banner_msg   = "Khong tim thay mat trong frame!"
                    banner_color = (0, 0, 200)
                    banner_end   = now + BANNER_DURATION

    write_daily_summary(sheet_sum, count_map, len(students),
                         violation_count, stranger_count, start_time)

    if bg_logger is not None:
        print("[SYNC] Dam bao tat ca log ngam da ghi xong...")
        bg_logger.shutdown()

    conn.close()
    cap.release()
    if not args.headless:
        cv2.destroyAllWindows()

    print("\n" + "=" * 44)
    print("  TONG KET BUOI HOM NAY")
    print(f"  Vi pham the/nguoi la : {violation_count} the, {stranger_count} nguoi la")
    if uniform_enabled:
        print(f"  Sai trang phuc       : {uniform_fail_count}")
        print(f"  Trang phuc khong ro  : {uniform_unclear_count}")
    print("=" * 44)
    print("[OK] He thong da dong. Tam biet!")


if __name__ == "__main__":
    run()
