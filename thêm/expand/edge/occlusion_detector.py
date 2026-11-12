# -*- coding: utf-8 -*-
"""
=============================================================================
  STEM CAMERA EDGE — CAMERA OCCLUSION & TAMPERING DETECTOR
  edge/occlusion_detector.py
  
  Chức năng:
  - Tự động phân tích từng khung hình video theo lưới không gian (Spatial Grid).
  - Đo đạc độ suy giảm chi tiết biên (Sobel Gradient Magnitude), độ phẳng sắc độ
    (Standard Deviation) và độ tối/sáng cực đoan (Blackout / Whiteout).
  - Tính toán chính xác tỉ lệ phần trăm camera bị che khuất (Occlusion Percentage).
  - Tự động kích hoạt cảnh báo khẩn cấp khi mức độ che khuất vượt ngưỡng (mặc định 60%)
    duy trì liên tục (chống báo động giả khi có người lướt qua).
  - Gửi ảnh chụp bằng chứng đối chứng trực tiếp về Server cho Giám thị & BGH.
=============================================================================
"""

import cv2
import time
import base64
import numpy as np
from typing import Tuple, Optional, Callable


class CameraOcclusionDetector:
    def __init__(
        self,
        threshold_percent: float = 60.0,
        min_consecutive_frames: int = 12,
        cooldown_seconds: float = 45.0,
        on_alert_callback: Optional[Callable[[float, str], None]] = None
    ):
        """
        :param threshold_percent: Tỉ lệ che khuất tối thiểu để coi là bị che (mặc định 60%).
        :param min_consecutive_frames: Số frame liên tiếp bị che trước khi kích hoạt cảnh báo
                                       (khoảng 1 - 1.5s ở 10-15 FPS, chống báo động giả).
        :param cooldown_seconds: Thời gian giãn cách giữa 2 lần gửi cảnh báo liên tiếp (tránh spam).
        :param on_alert_callback: Hàm callback gọi khi phát hiện che khuất: fn(occlusion_percent, proof_base64).
        """
        self.threshold_percent = float(threshold_percent)
        self.min_consecutive_frames = int(min_consecutive_frames)
        self.cooldown_seconds = float(cooldown_seconds)
        self.on_alert_callback = on_alert_callback

        self.consecutive_occluded = 0
        self.consecutive_clear = 0
        self.is_occluded = False
        self.last_alert_time = 0.0
        self.current_occlusion_percent = 0.0
        self.last_analysis_time = 0.0

    def analyze_frame(self, frame: np.ndarray, grid_size: Tuple[int, int] = (10, 10)) -> float:
        """
        Phân tích frame và trả về tỉ lệ che khuất theo phần trăm (0.0% - 100.0%).
        Áp dụng toàn diện 3 phương pháp kỹ thuật xử lý hình ảnh chuẩn công nghiệp:
          1. Phân tích độ sáng trung bình (Mean Intensity):
             - Nhận diện bóng tối cực đoan (Blackout: vải đen, tay đè, sơn đen).
             - Nhận diện lóa sáng cực đoan (Whiteout: đèn pin rọi mù, giấy trắng áp sát).
          2. Độ lệch chuẩn & Độ tương phản (Standard Deviation / Contrast):
             - Ống kính bị vật thể gần (vải, da, giấy, mờ đục) che làm triệt tiêu tương phản (sigma cực thấp).
          3. Phân tích tần số không gian (Spatial Frequency & Edge Detection):
             - Sobel Gradient & Laplacian Variance: Sụt giảm đột ngột các đường nét, chi tiết góc cạnh.
        """
        if frame is None or frame.size == 0:
            return 100.0

        try:
            small = cv2.resize(frame, (160, 120))
            gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)

            # ── 1. Toàn cục: Phân tích độ mờ / mất nét toàn diện (Laplacian Variance)
            laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
            global_mean = float(np.mean(gray))
            global_std = float(np.std(gray))

            # Trường hợp 100% khung hình bị tối đen hoàn toàn hoặc trắng lóa
            if global_mean < 18.0 or (global_mean > 240.0 and global_std < 8.0):
                return 100.0

            # ── 2. Cục bộ: Lọc biên đạo hàm Sobel (Spatial Frequency)
            sobel_x = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
            sobel_y = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
            grad_mag = cv2.magnitude(sobel_x, sobel_y)

            h, w = gray.shape
            rows, cols = grid_size
            cell_h, cell_w = h // rows, w // cols

            occluded_cells = 0
            total_cells = rows * cols

            for r in range(rows):
                for c in range(cols):
                    y1, y2 = r * cell_h, (r + 1) * cell_h
                    x1, x2 = c * cell_w, (c + 1) * cell_w

                    cell_gray = gray[y1:y2, x1:x2]
                    cell_grad = grad_mag[y1:y2, x1:x2]

                    # 3 chỉ số kỹ thuật chính theo từng vùng lưới không gian:
                    mean_val = float(np.mean(cell_gray))     # 1. Mean Intensity (Độ sáng trung bình)
                    std_val = float(np.std(cell_gray))        # 2. Standard Deviation (Độ tương phản)
                    mean_grad = float(np.mean(cell_grad))    # 3. Spatial Edge Magnitude (Tần số không gian biên)

                    # [KỸ THUẬT 1] Phân tích độ sáng trung bình (Mean Intensity)
                    is_blackout = (mean_val < 25.0)
                    is_whiteout = (mean_val > 230.0 and std_val < 12.0)

                    # [KỸ THUẬT 2] Độ tương phản / Độ lệch chuẩn (Contrast / StdDev)
                    is_low_contrast = (std_val < 10.0 and mean_grad < 9.0)

                    # [KỸ THUẬT 3] Tần số không gian / Lọc biên (Spatial Frequency / Edge)
                    is_no_edges = (mean_grad < 6.5 and std_val < 15.0)

                    if is_blackout or is_whiteout or is_low_contrast or is_no_edges:
                        occluded_cells += 1

            percent = (occluded_cells / float(total_cells)) * 100.0

            # Bổ sung trọng số Laplacian toàn cục nếu toàn bộ khung hình bị mờ đục mất nét
            if laplacian_var < 10.0 and percent > 45.0:
                percent = min(100.0, percent * 1.25)

            return round(percent, 1)
        except Exception:
            return 0.0

    def trigger_hardware_tamper(self, reason: str = "Hardware Tamper Switch Triggered"):
        """
        [KỸ THUẬT 4] Cảm biến phần cứng tích hợp (Hardware Tamper Switch):
        Cho phép vi xử lý / mạch GPIO / camera switch kích hoạt báo động lập tức 100%.
        """
        self.is_occluded = True
        self.current_occlusion_percent = 100.0
        self.consecutive_occluded = self.min_consecutive_frames
        if self.on_alert_callback:
            try:
                self.on_alert_callback(100.0, None)
            except Exception as e:
                print(f"[OCCLUSION DETECTOR] Lỗi gọi callback Hardware Tamper: {e}")

    def update(self, frame: np.ndarray) -> Tuple[bool, float, bool]:
        """
        Cập nhật trạng thái che khuất với frame mới.
        :return: (is_currently_occluded, occlusion_percent, alert_just_triggered)
        """
        now = time.time()
        self.current_occlusion_percent = self.analyze_frame(frame)
        alert_triggered = False

        if self.current_occlusion_percent >= self.threshold_percent:
            self.consecutive_occluded += 1
            self.consecutive_clear = 0

            # Nếu bị che liên tục đủ số frame quy định -> Xác nhận bị che khuất
            if self.consecutive_occluded >= self.min_consecutive_frames:
                self.is_occluded = True

                # Kiểm tra cooldown để gửi cảnh báo
                if (now - self.last_alert_time) > self.cooldown_seconds:
                    self.last_alert_time = now
                    alert_triggered = True

                    # Tạo ảnh bằng chứng Base64
                    proof_b64 = None
                    try:
                        ret, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
                        if ret:
                            proof_b64 = base64.b64encode(buf.tobytes()).decode('utf-8')
                    except Exception:
                        pass

                    if self.on_alert_callback:
                        try:
                            self.on_alert_callback(self.current_occlusion_percent, proof_b64)
                        except Exception as e:
                            print(f"[OCCLUSION DETECTOR] Lỗi gọi callback cảnh báo: {e}")
        else:
            self.consecutive_clear += 1
            # Khi camera thông suốt liên tục ít nhất 10 frames -> Hết che khuất
            if self.consecutive_clear >= 10:
                self.consecutive_occluded = 0
                if self.is_occluded:
                    print(f"[OCCLUSION DETECTOR] 🟢 Camera đã khôi phục tầm nhìn bình thường (Che khuất: {self.current_occlusion_percent}%).")
                self.is_occluded = False

        return self.is_occluded, self.current_occlusion_percent, alert_triggered

    def draw_hud(self, frame: np.ndarray) -> np.ndarray:
        """
        Vẽ HUD cảnh báo trực quan trên frame nếu camera đang bị che khuất.
        """
        if not self.is_occluded and self.current_occlusion_percent < 40.0:
            return frame

        h, w = frame.shape[:2]
        pct = int(self.current_occlusion_percent)

        if self.is_occluded:
            # Khung viền đỏ cảnh báo nhấp nháy
            cv2.rectangle(frame, (0, 0), (w - 1, h - 1), (0, 0, 255), 6)
            # Banner trên đầu
            cv2.rectangle(frame, (0, 0), (w, 50), (0, 0, 200), -1)
            text = f"CANH BAO: CAMERA BI CHE KHUAT ({pct}%) - MAT TAM NHIN AN NINH"
            cv2.putText(frame, text, (20, 34), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        elif self.current_occlusion_percent >= 40.0:
            # Cảnh báo vàng tiềm ẩn
            cv2.rectangle(frame, (0, 0), (w, 40), (0, 165, 255), -1)
            text = f"CHU Y: CAMERA DANG BI CAN TRO ({pct}%)"
            cv2.putText(frame, text, (20, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 0, 0), 2)

        return frame
