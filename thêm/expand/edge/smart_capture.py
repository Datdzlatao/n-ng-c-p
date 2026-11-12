# -*- coding: utf-8 -*-
"""
=============================================================
  MODULE AUTO-CAPTURE THÔNG MINH & WATERMARK VI PHẠM
  smart_capture.py

  Chức năng:
  1. Smart Best-Shot Evaluation: Đánh giá độ nét (Laplacian variance)
     và chọn frame chất lượng tốt nhất của người vi phạm.
  2. Bắt bộ 2 ảnh bằng chứng:
     - 1 ảnh chân dung cận mặt (portrait crop).
     - 1 ảnh toàn cảnh hiện trường có đóng khung đỏ chỉ điểm lỗi (scene capture).
  3. Watermarking: Đóng dấu thông tin chi tiết (Thời gian, Mã HS, Tên,
     Loại vi phạm, Độ tự tin) trực tiếp lên ảnh.
  4. Lưu tự động vào cấu trúc thư mục `data/violations/YYYY-MM-DD/`.
=============================================================
"""

import os
import cv2
import time
import shutil
import base64
import threading
import numpy as np
from datetime import datetime, timedelta
from typing import Tuple, Dict, Any, Optional
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

try:
    from config import VIOLATION_RETENTION_DAYS
except ImportError:
    VIOLATION_RETENTION_DAYS = 30


class SmartCaptureEngine:
    """
    Engine chụp ảnh vi phạm thông minh (Best-Shot + Dual-Photo + Watermark + Async I/O & Retention).
    """

    def __init__(self, base_dir: Optional[Path] = None, retention_days: int = VIOLATION_RETENTION_DAYS):
        if base_dir is None:
            base_dir = Path(__file__).parent
        self.base_dir = Path(base_dir)
        self.violations_dir = self.base_dir / "data" / "violations"
        self.retention_days = retention_days
        os.makedirs(self.violations_dir, exist_ok=True)

        # ThreadPool ngầm cho I/O ghi ảnh đĩa (Zero-Drop FPS Camera)
        self._writer_pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="SmartCaptureAsyncWriter")

        # Khởi động luồng dọn dẹp ảnh cũ ngầm định kỳ
        self._cleanup_thread = threading.Thread(target=self._retention_loop, daemon=True, name="SmartCaptureRetention")
        self._cleanup_thread.start()

    @staticmethod
    def evaluate_frame_quality(frame: np.ndarray,
                               face_location: Optional[Tuple[int, int, int, int]] = None,
                               body_box: Optional[Tuple[int, int, int, int]] = None) -> float:
        """
        Đánh giá chất lượng của frame (độ nét + kích thước vùng phân tích).
        """
        if frame is None or frame.size == 0:
            return 0.0

        h, w = frame.shape[:2]
        crop = frame

        if face_location is not None:
            top, right, bottom, left = face_location
            top = max(0, top); left = max(0, left)
            right = min(w, right); bottom = min(h, bottom)
            if right > left and bottom > top:
                crop = frame[top:bottom, left:right]
        elif body_box is not None:
            bx, by, bw, bh = body_box
            bx = max(0, bx); by = max(0, by)
            bw = min(w - bx, bw); bh = min(h - by, bh)
            if bw > 0 and bh > 0:
                crop = frame[by:by + bh, bx:bx + bw]

        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        lap_var = cv2.Laplacian(gray, cv2.CV_64F).var()

        size_factor = min(2.0, (crop.shape[0] * crop.shape[1]) / (100 * 100))
        quality_score = lap_var * size_factor

        return round(float(quality_score), 2)

    @staticmethod
    def add_watermark(image: np.ndarray,
                      title: str,
                      metadata: Dict[str, Any]) -> np.ndarray:
        """
        Đóng dấu Watermark chuyên nghiệp lên ảnh bằng chứng.
        """
        img = image.copy()
        h, w = img.shape[:2]

        banner_h = max(60, int(h * 0.12))
        overlay = img.copy()
        cv2.rectangle(overlay, (0, h - banner_h), (w, h), (15, 15, 15), -1)
        cv2.addWeighted(overlay, 0.75, img, 0.25, 0, img)

        cv2.rectangle(img, (0, h - banner_h), (w, h - banner_h + 3), (0, 0, 220), -1)

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sid = metadata.get("student_id", "N/A")
        name = metadata.get("name", "Nguoi dung")
        conf = metadata.get("confidence", None)

        conf_str = f" | Conf: {conf*100:.0f}%" if conf is not None else ""
        text_line1 = f"BANG CHUNG VI PHAM - {now_str}"
        text_line2 = f"HS: {name} ({sid}) | LOI: {title}{conf_str}"

        scale1 = max(0.42, w / 1800.0)
        scale2 = max(0.48, w / 1500.0)

        cv2.putText(img, text_line1, (12, h - banner_h + int(banner_h * 0.35)),
                    cv2.FONT_HERSHEY_SIMPLEX, scale1, (180, 180, 180), 1)
        cv2.putText(img, text_line2, (12, h - banner_h + int(banner_h * 0.78)),
                    cv2.FONT_HERSHEY_SIMPLEX, scale2, (0, 220, 255), 2)

        return img

    def capture_best_shot(self,
                          frame: np.ndarray,
                          face_location: Optional[Tuple[int, int, int, int]] = None,
                          body_box: Optional[Tuple[int, int, int, int]] = None,
                          label_info: Optional[Dict[str, Any]] = None,
                          violation_type: str = "VI_PHAM") -> Tuple[str, str]:
        """
        Tự động bắt bộ 2 ảnh nét nhất (chân dung cận mặt + toàn cảnh hiện trường đóng khung đỏ).

        Returns:
            Tuple[portrait_path, scene_path]
        """
        if label_info is None:
            label_info = {}

        now = datetime.now()
        date_folder = now.strftime("%Y-%m-%d")
        timestamp_str = now.strftime("%H%M%S_%f")[:10]

        target_dir = self.violations_dir / date_folder
        os.makedirs(target_dir, exist_ok=True)

        sid = label_info.get("student_id", "UNKNOWN").replace(" ", "_")
        safe_violation = violation_type.replace(" ", "_").replace(":", "")

        portrait_filename = f"portrait_{sid}_{timestamp_str}_{safe_violation}.jpg"
        scene_filename    = f"scene_{sid}_{timestamp_str}_{safe_violation}.jpg"

        portrait_path = str(target_dir / portrait_filename)
        scene_path    = str(target_dir / scene_filename)

        h_frame, w_frame = frame.shape[:2]

        if face_location is not None:
            top, right, bottom, left = face_location
            fh = bottom - top
            fw = right - left
            pad_y = int(fh * 0.35)
            pad_x = int(fw * 0.35)

            py0 = max(0, top - pad_y)
            py1 = min(h_frame, bottom + pad_y)
            px0 = max(0, left - pad_x)
            px1 = min(w_frame, right + pad_x)

            portrait_crop = frame[py0:py1, px0:px1]
        elif body_box is not None:
            bx, by, bw, bh = body_box
            py0 = max(0, by)
            py1 = min(h_frame, by + int(bh * 0.55))
            px0 = max(0, bx)
            px1 = min(w_frame, bx + bw)
            portrait_crop = frame[py0:py1, px0:px1]
        else:
            portrait_crop = frame

        if portrait_crop.size == 0:
            portrait_crop = frame

        portrait_img = self.add_watermark(portrait_crop, violation_type, label_info)

        scene_frame = frame.copy()
        if body_box is not None or face_location is not None:
            try:
                from person_detector import PersonDetector
                info_copy = dict(label_info)
                info_copy["is_violation"] = True
                info_copy["violation_label"] = violation_type
                scene_frame = PersonDetector.draw_target_boxes(
                    frame, body_box, face_location, label_info=info_copy, force_red=True
                )
            except Exception:
                if body_box is not None:
                    bx, by, bw, bh = body_box
                    cv2.rectangle(scene_frame, (bx, by), (bx + bw, by + bh), (0, 0, 255), 3)

        scene_img = self.add_watermark(scene_frame, violation_type, label_info)

        # [TỐI ƯU 0ms DISK DELAY] Mã hóa Base64 trực tiếp từ RAM cho Web Server
        # Không bao giờ phải đợi ghi file đĩa hay lo lắng file chưa kịp ghi xong
        snap_b64 = None
        try:
            enc_img = scene_img
            h_s, w_s = enc_img.shape[:2]
            if w_s > 960:
                scale_s = 960.0 / w_s
                enc_img = cv2.resize(enc_img, (960, int(h_s * scale_s)), interpolation=cv2.INTER_AREA)
            ret_enc, buf_enc = cv2.imencode(".jpg", enc_img, [cv2.IMWRITE_JPEG_QUALITY, 85])
            if ret_enc:
                snap_b64 = base64.b64encode(buf_enc).decode("utf-8")
        except Exception as _b64_err:
            print(f"  [SMART CAPTURE] Lỗi mã hóa Base64 RAM: {_b64_err}")

        # Ghi ảnh bất đồng bộ qua ThreadPool — giải phóng camera thread tức thì (Zero-Drop Frame)
        def _write_pair(p_path, p_img, s_path, s_img):
            try:
                cv2.imwrite(p_path, p_img, [cv2.IMWRITE_JPEG_QUALITY, 90])
                cv2.imwrite(s_path, s_img, [cv2.IMWRITE_JPEG_QUALITY, 90])
            except Exception as _e:
                print(f"  [SMART CAPTURE] Lỗi ghi ảnh nền: {_e}")

        self._writer_pool.submit(_write_pair, portrait_path, portrait_img, scene_path, scene_img)

        print(f"  [SMART CAPTURE] ⚡ Đã lưu bộ 2 ảnh vi phạm (Async I/O + Instant RAM Base64):")
        print(f"    - Chan dung : {portrait_filename}")
        print(f"    - Toan canh : {scene_filename}")

        return portrait_path, scene_path, snap_b64

    # =========================================================================
    # STORAGE RETENTION & CLEANUP ENGINE
    # =========================================================================
    def cleanup_old_violations(self, days: Optional[int] = None) -> int:
        """
        Quét và xóa các thư mục ảnh vi phạm cũ hơn `retention_days` (mặc định 30 ngày).
        Trả về số thư mục đã dọn dẹp.
        """
        retention = days if days is not None else self.retention_days
        if not self.violations_dir.exists():
            return 0

        cutoff_date = datetime.now() - timedelta(days=retention)
        deleted_count = 0

        try:
            for item in self.violations_dir.iterdir():
                if item.is_dir():
                    try:
                        folder_dt = datetime.strptime(item.name, "%Y-%m-%d")
                        if folder_dt < cutoff_date:
                            shutil.rmtree(item, ignore_errors=True)
                            deleted_count += 1
                            print(f"  [RETENTION] 🧹 Đã dọn dẹp thư mục ảnh vi phạm cũ: {item.name}")
                    except ValueError:
                        pass
        except Exception as e:
            print(f"  [RETENTION] Lỗi dọn dẹp ảnh vi phạm cũ: {e}")

        return deleted_count

    def _retention_loop(self):
        """Vòng lặp chạy ngầm định kỳ 12 giờ/lần để dọn dẹp ảnh cũ."""
        time.sleep(10)  # Đợi 10s sau khởi động
        while True:
            try:
                self.cleanup_old_violations()
            except Exception:
                pass
            time.sleep(12 * 3600)


if __name__ == "__main__":
    engine = SmartCaptureEngine()
    print("[OK] SmartCaptureEngine đã sẵn sàng.")
