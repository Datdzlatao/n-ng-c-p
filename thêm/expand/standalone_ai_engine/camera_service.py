# -*- coding: utf-8 -*-
"""
CAMERA STREAM SERVICE — QUẢN LÝ LUỒNG CAMERA VÀ PHÂN TÍCH THỜI GIAN THỰC
camera_service.py

Tính năng:
- Thu nhận luồng camera thời gian thực (Webcam/RTSP) đa luồng (Multi-threaded).
- Chạy suy luận AI (Nhận diện khuôn mặt, Anti-spoofing, Đồng phục) bất đồng bộ (Zero-lag).
- Phát luồng video MJPEG (chuẩn HTTP Streaming) để nhúng trực tiếp vào Web HTML/img.
- Cung cấp API trạng thái, dữ liệu telemetries (FPS, MSSV, tên, đồng phục) theo thời gian thực.
"""
import cv2
import time
import threading
import numpy as np
from typing import Optional, Union, Dict, Any, Generator
from standalone_runner import StandaloneVisionPipeline


class CameraStreamService:
    def __init__(self, pipeline: StandaloneVisionPipeline):
        self.pipeline = pipeline
        self.source: Union[int, str] = 0
        self.weekday_override: Optional[int] = None

        self.cap: Optional[cv2.VideoCapture] = None
        self.is_running: bool = False
        self.lock = threading.Lock()

        self.latest_raw_frame: Optional[np.ndarray] = None
        self.latest_result: Dict[str, Any] = {
            "status": "idle",
            "faces_detected": 0,
            "faces": [],
            "uniform": None,
            "process_time_ms": 0.0
        }

        self.latest_jpeg: Optional[bytes] = None
        self.latest_raw_jpeg: Optional[bytes] = None

        self.capture_fps: float = 0.0
        self.ai_fps: float = 0.0
        self.last_ai_time_ms: float = 0.0
        self.error_message: Optional[str] = None

        self._capture_thread: Optional[threading.Thread] = None
        self._ai_thread: Optional[threading.Thread] = None

    def start(self, source: Union[int, str] = 0, weekday_override: Optional[int] = None) -> bool:
        """Khởi động luồng camera và tiến trình AI nền."""
        src_val = int(source) if str(source).isdigit() else str(source).strip()

        with self.lock:
            if self.is_running and self.source == src_val:
                self.weekday_override = weekday_override
                return True

        # Nếu đang chạy nguồn khác thì dừng trước
        if self.is_running:
            self.stop()

        self.source = src_val
        self.weekday_override = weekday_override
        self.error_message = None

        print(f"[CAM SERVICE] Đang kết nối tới nguồn camera: {self.source}...")
        cap = cv2.VideoCapture(self.source)
        if not cap.isOpened():
            self.error_message = f"Không thể mở nguồn camera: {self.source}"
            print(f"[CAM SERVICE ERROR] {self.error_message}")
            return False

        # Tối ưu buffer giảm độ trễ
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        self.cap = cap
        self.is_running = True

        self._capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._ai_thread = threading.Thread(target=self._ai_worker_loop, daemon=True)

        self._capture_thread.start()
        self._ai_thread.start()
        print(f"[CAM SERVICE] Đã bật camera thành công: {self.source}")
        return True

    def stop(self):
        """Dừng thu luồng camera và giải phóng tài nguyên."""
        self.is_running = False

        if self._capture_thread and self._capture_thread.is_alive():
            self._capture_thread.join(timeout=1.0)
        if self._ai_thread and self._ai_thread.is_alive():
            self._ai_thread.join(timeout=1.0)

        with self.lock:
            if self.cap is not None:
                try:
                    self.cap.release()
                except Exception:
                    pass
                self.cap = None
            self.latest_raw_frame = None
            self.latest_jpeg = None
            self.latest_raw_jpeg = None
            self.capture_fps = 0.0
            self.ai_fps = 0.0

        print("[CAM SERVICE] Đã dừng camera.")

    def _capture_loop(self):
        """Luồng thu nhận khung hình tốc độ cao (30 FPS) và mã hóa JPEG stream."""
        frame_count = 0
        start_time = time.time()

        while self.is_running and self.cap is not None:
            ret, frame = self.cap.read()
            if not ret or frame is None:
                time.sleep(0.02)
                continue

            with self.lock:
                self.latest_raw_frame = frame
                res = self.latest_result

            # Vẽ HUD nhận diện lên khung hình
            annotated = self.pipeline.draw_hud(frame, res)

            # Mã hóa JPEG chất lượng 80 tối ưu băng thông mạng local
            _, raw_jpg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            _, hud_jpg = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 80])

            with self.lock:
                self.latest_raw_jpeg = raw_jpg.tobytes()
                self.latest_jpeg = hud_jpg.tobytes()

            frame_count += 1
            now = time.time()
            elapsed = now - start_time
            if elapsed >= 1.0:
                self.capture_fps = round(frame_count / elapsed, 1)
                frame_count = 0
                start_time = now

            time.sleep(0.01)

    def _ai_worker_loop(self):
        """Luồng xử lý AI bất đồng bộ (Zero-lag)."""
        ai_count = 0
        start_time = time.time()

        while self.is_running:
            frame_to_process = None
            with self.lock:
                if self.latest_raw_frame is not None:
                    frame_to_process = self.latest_raw_frame.copy()

            if frame_to_process is None:
                time.sleep(0.03)
                continue

            t0 = time.time()
            try:
                res = self.pipeline.process_frame(
                    frame_to_process,
                    weekday_override=self.weekday_override
                )
                dt = (time.time() - t0) * 1000
                with self.lock:
                    self.latest_result = res
                    self.last_ai_time_ms = round(dt, 1)
            except Exception as e:
                print(f"[CAM SERVICE AI ERROR] {e}")

            ai_count += 1
            now = time.time()
            elapsed = now - start_time
            if elapsed >= 1.0:
                self.ai_fps = round(ai_count / elapsed, 1)
                ai_count = 0
                start_time = now

            # Nghỉ ngắn giữa các lần phân tích AI để nhường CPU cho streaming
            time.sleep(0.02)

    def get_status(self) -> Dict[str, Any]:
        """Lấy thông tin trạng thái dịch vụ và số liệu telemetries."""
        with self.lock:
            return {
                "is_running": self.is_running,
                "source": self.source,
                "weekday_override": self.weekday_override,
                "capture_fps": self.capture_fps,
                "ai_fps": self.ai_fps,
                "process_time_ms": self.last_ai_time_ms,
                "error": self.error_message,
                "faces_detected": self.latest_result.get("faces_detected", 0)
            }

    def get_latest_result(self) -> Dict[str, Any]:
        """Lấy kết quả nhận diện và đồng phục mới nhất."""
        with self.lock:
            res = dict(self.latest_result)
            res["capture_fps"] = self.capture_fps
            res["ai_fps"] = self.ai_fps
            res["is_running"] = self.is_running
            return res

    def get_snapshot(self, overlay: bool = True) -> Optional[bytes]:
        """Chụp 1 ảnh tĩnh tức thời từ luồng camera."""
        with self.lock:
            return self.latest_jpeg if overlay else self.latest_raw_jpeg

    def generate_mjpeg(self, overlay: bool = True) -> Generator[bytes, None, None]:
        """Tạo luồng multipart/x-mixed-replace cho thẻ <img> hoặc trình duyệt."""
        while self.is_running:
            with self.lock:
                frame_bytes = self.latest_jpeg if overlay else self.latest_raw_jpeg

            if frame_bytes is not None:
                yield (b"--frame\r\n"
                       b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n")
            time.sleep(0.033)  # Giới hạn ~30 FPS trên client
