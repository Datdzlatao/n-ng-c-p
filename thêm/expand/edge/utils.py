"""
=================================================
  UTILS.PY — HAM HO TRO HE THONG DIEM DANH
  v3.0 — MERGE v1-modified + v2
=================================================
Giu nguyen toan bo v2 (da fix bug Unicode, beep thread, cac ham HUD moi).
Khong co thay doi gi tu v1-modified o file nay (v1-mod chi sua face_engine va main).
"""

import cv2
import numpy as np
import time
import sys
import platform
import threading
import socket

from config import (
    COLOR_SUCCESS, COLOR_ERROR, COLOR_INFO,
    SHOW_CLOCK, SHOW_STATS, BANNER_DURATION
)


# ── Tai danh sach hoc sinh ────────────────────────────────────────────────────
def load_students(sheet_students) -> dict:
    records  = sheet_students.get_all_values()
    students = {}
    for row in records[1:]:
        if len(row) >= 2 and row[0].strip():
            students[row[0].strip()] = row[1].strip()
    return students


def find_student(students: dict, code: str):
    return students.get(code.strip())


# ── Am thanh (thread-safe, khong block UI) ────────────────────────────────────
def _beep_thread(times=1, delay=0.1):
    try:
        for _ in range(times):
            if platform.system() == "Windows":
                import winsound
                winsound.Beep(1000, 150)
            else:
                sys.stdout.write("\a")
                sys.stdout.flush()
            time.sleep(delay)
    except Exception:
        pass


def beep_success():
    threading.Thread(target=_beep_thread, args=(1,), daemon=True).start()


def beep_error():
    threading.Thread(target=_beep_thread, args=(3, 0.07), daemon=True).start()


# ── Ve overlay QR ─────────────────────────────────────────────────────────────
def draw_overlay(frame, decoded_objects, last_result: dict):
    h, w = frame.shape[:2]

    for obj in decoded_objects:
        pts   = np.array([p for p in obj.polygon], dtype=np.int32)
        color = COLOR_SUCCESS if last_result.get("ok") else COLOR_ERROR
        cv2.polylines(frame, [pts], isClosed=True, color=color, thickness=3)
        if pts.size > 0:
            top_pt  = tuple(pts[pts[:, 1].argmin()])
            qr_text = last_result.get("text", "")[:20]
            cv2.putText(frame, qr_text,
                        (top_pt[0], max(top_pt[1] - 10, 15)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1)

    bar_h = 75
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, h - bar_h), (w, h), (15, 15, 15), -1)
    cv2.addWeighted(overlay, 0.80, frame, 0.20, 0, frame)
    cv2.line(frame, (0, h - bar_h), (w, h - bar_h),
             COLOR_SUCCESS if last_result.get("ok") else COLOR_ERROR, 2)

    if last_result.get("name"):
        ok     = last_result["ok"]
        color  = COLOR_SUCCESS if ok else COLOR_ERROR
        line1  = f"[{last_result.get('status','')}]  {last_result.get('name','')}  ({last_result.get('text','')})"
        cv2.putText(frame, line1, (15, h - bar_h + 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.75, color, 2)
        cv2.putText(frame, time.strftime("%d/%m/%Y %H:%M:%S"),
                    (15, h - bar_h + 55),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180, 180, 180), 1)

    hint = "Q/ESC=Thoat  S=Thong ke  R=Reload  P=Pause mat  A=Them mat"
    cv2.putText(frame, hint, (15, h - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.36, (110, 110, 110), 1)
    return frame


# ── Banner thong bao lon (fade-out) ───────────────────────────────────────────
def draw_banner(frame, message: str, color: tuple, alpha: float = 1.0):
    if alpha <= 0:
        return frame
    h, w  = frame.shape[:2]
    bw    = min(w - 60, 720)
    bh    = 100
    bx    = (w - bw) // 2
    by    = (h - bh) // 2

    ov = frame.copy()
    cv2.rectangle(ov, (bx - 5, by - 5), (bx + bw + 5, by + bh + 5), (10, 10, 10), -1)
    cv2.addWeighted(ov, alpha * 0.85, frame, 1 - alpha * 0.85, 0, frame)
    cv2.rectangle(frame, (bx, by), (bx + bw, by + bh), color, 3)

    font_scale = 1.0
    thickness  = 2
    (tw, th), _ = cv2.getTextSize(message, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)
    if tw > bw - 30:
        font_scale = font_scale * (bw - 30) / tw
        (tw, th), _ = cv2.getTextSize(message, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)

    tx = bx + (bw - tw) // 2
    ty = by + (bh + th) // 2
    cv2.putText(frame, message, (tx, ty),
                cv2.FONT_HERSHEY_SIMPLEX, font_scale,
                tuple(int(c * alpha) for c in color), thickness)
    return frame


# ── Đếm FPS thực tế ────────────────────────────────────────────────────────────
class FPSCounter:
    """Đếm FPS thực tế bằng thuật toán Moving Average (window 30 frame)."""
    def __init__(self, window_size: int = 30):
        self.window_size = window_size
        self.timestamps = []

    def update(self) -> float:
        now = time.time()
        self.timestamps.append(now)
        if len(self.timestamps) > self.window_size:
            self.timestamps.pop(0)
        if len(self.timestamps) > 1:
            elapsed = self.timestamps[-1] - self.timestamps[0]
            return (len(self.timestamps) - 1) / elapsed if elapsed > 0 else 0.0
        return 0.0


# ── Dong ho goc tren phai ─────────────────────────────────────────────────────
def draw_clock(frame, fps: float = 0.0):
    if not SHOW_CLOCK:
        return frame
    h, w = frame.shape[:2]
    ov   = frame.copy()
    cv2.rectangle(ov, (w - 210, 0), (w, 60), (10, 10, 10), -1)
    cv2.addWeighted(ov, 0.65, frame, 0.35, 0, frame)
    cv2.putText(frame, time.strftime("%H:%M:%S"), (w - 200, 25),
                cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 220, 200), 2)

    fps_str = f"FPS: {fps:.1f}" if fps > 0 else "FPS: --"
    cv2.putText(frame, f"{time.strftime('%d/%m/%Y')} | {fps_str}", (w - 200, 48),
                cv2.FONT_HERSHEY_SIMPLEX, 0.42, (180, 180, 180), 1)
    return frame


# ── Thong ke co/vang mat goc tren trai ───────────────────────────────────────
def draw_stats(frame, count_map: dict, total_students: int, violation_count: int = 0, mot_count: int = 0):
    if not SHOW_STATS:
        return frame
    present = sum(1 for c in count_map.values() if c % 2 == 1)
    absent  = total_students - present
    lines   = [
        f"Co mat  : {present}/{total_students}",
        f"Vang    : {absent}",
        f"Vi pham : {violation_count}",
        f"MOT Track: {mot_count}"
    ]
    x, y0   = 10, 10
    ov = frame.copy()
    cv2.rectangle(ov, (x - 5, y0 - 5),
                  (x + 205, y0 + len(lines) * 22 + 8), (10, 10, 10), -1)
    cv2.addWeighted(ov, 0.65, frame, 0.35, 0, frame)
    colors = [COLOR_SUCCESS, COLOR_ERROR, (0, 0, 255), (0, 220, 255)]
    for i, line in enumerate(lines):
        color = colors[i % len(colors)]
        cv2.putText(frame, line, (x, y0 + 18 + i * 22),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.48, color, 1)
    return frame


# ── Kiem tra ket noi mang (background) ───────────────────────────────────────
class NetworkChecker:
    def __init__(self, check_interval: int = 10):
        self._online   = True
        self._interval = check_interval
        self._lock     = threading.Lock()
        threading.Thread(target=self._loop, daemon=True).start()

    def _loop(self):
        while True:
            try:
                socket.setdefaulttimeout(3)
                socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("8.8.8.8", 53))
                online = True
            except Exception:
                online = False
            with self._lock:
                self._online = online
            time.sleep(self._interval)

    @property
    def is_online(self) -> bool:
        with self._lock:
            return self._online


# ── In log ra console (BUG FIX: ASCII fallback cho Windows) ──────────────────
def print_log(timestamp, student_id, name, status):
    try:
        icon = "✅" if status == "Vào" else "🔴"
        print(f"  {icon}  [{timestamp}]  {student_id}  |  {name}  →  {status}")
    except (UnicodeEncodeError, UnicodeDecodeError):
        icon = "[VAO]" if status == "Vào" else "[RA] "
        print(f"  {icon}  [{timestamp}]  {student_id}  |  {name}  ->  {status}")
