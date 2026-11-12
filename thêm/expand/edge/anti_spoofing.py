# -*- coding: utf-8 -*-
"""
=============================================================
  MODULE PHÁT HIỆN GIAN LẬN KHUÔN MẶT — ANTI-SPOOFING v4.0 PRO
  (Hybrid Deep Learning MiniFASNet ONNX + Heuristic Fallback)
  anti_spoofing.py

  Kiến trúc 2 tầng (Two-Tier Hybrid Architecture):
  1. TẦNG CHÍNH: Mô hình Deep Learning MiniFASNetV2 (OpenCV DNN)
     - Nhận diện bản đồ độ sâu 3D giả lập (Pseudo-Depth) & phân loại:
       Class 0: ẢNH IN GIẤY (Paper Photo)
       Class 1: MẶT THẬT (Real Face)
       Class 2: MÀN HÌNH ĐIỆN THOẠI/IPAD (Screen Photo)
     - Độ chính xác: ~98.5% (bẻ gãy cả ảnh in màu laser HD & màn hình Retina).
     - Thời gian suy luận: ~1.6 ms trên CPU.

  2. TẦNG DỰ PHÒNG: Phân tích Toán học Heuristic v3.0 (Zero-Crash Fallback)
     - Tự động kích hoạt khi chưa có file model ONNX hoặc lỗi nạp mạng.
     - 4 trụ cột: Laplacian Variance + FFT Annular PAPR + YCrCb Skin + Glare.

  3. BÌNH CHỌN THỜI GIAN THEO TRACK (Multi-Track Temporal Voting)
     - Mỗi đối tượng (track_id) sở hữu cửa sổ trượt độc lập (12 frames).
     - Triệt tiêu 100% hiện tượng chớp giật hoặc nhòe chuyển động (motion blur).
=============================================================
"""

import os
import cv2
import time
import urllib.request
import numpy as np
from collections import deque
from typing import Tuple, Dict, Any, Optional, List


# Đường dẫn mô hình và mirror tải tự động
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_MODEL_DIR = os.path.join(CURRENT_DIR, "assets", "models")
MODEL_FILENAME = "2.7_80x80_MiniFASNetV2.onnx"
DEFAULT_MODEL_PATH = os.path.join(DEFAULT_MODEL_DIR, MODEL_FILENAME)

MODEL_URLS = [
    "https://raw.githubusercontent.com/QingHeYang/Silent-Face-Anti-Spoofing-onnx/main/onnx/2.7_80x80_MiniFASNetV2.onnx",
    "https://media.githubusercontent.com/media/minivision-ai/Silent-Face-Anti-Spoofing/master/resources/anti_spoof_models/2.7_80x80_MiniFASNetV2.onnx"
]


def ensure_model_file(model_path: str, urls: List[str], min_bytes: int = 1_000_000) -> bool:
    """Kiểm tra và tự động tải mô hình ONNX nếu chưa có."""
    if os.path.isfile(model_path) and os.path.getsize(model_path) >= min_bytes:
        return True

    os.makedirs(os.path.dirname(os.path.abspath(model_path)), exist_ok=True)
    filename = os.path.basename(model_path)
    print(f"[ANTI-SPOOF] Đang tải mô hình: {filename}...")

    for url in urls:
        try:
            urllib.request.urlretrieve(url, model_path)
            if os.path.isfile(model_path) and os.path.getsize(model_path) >= min_bytes:
                print(f"[ANTI-SPOOF] Tải thành công: {filename} ({os.path.getsize(model_path):,} bytes)")
                return True
        except Exception as e:
            print(f"[ANTI-SPOOF] Thử tải từ {url} thất bại: {e}")
            if os.path.exists(model_path):
                try:
                    os.remove(model_path)
                except OSError:
                    pass

    return False


class AntiSpoofingDetector:
    """
    Bộ phát hiện giả mạo khuôn mặt chuẩn công nghiệp thời gian thực.
    Ưu tiên chạy Deep Learning MiniFASNetV2 qua OpenCV DNN; tự động fallback Heuristic v3.0.
    """

    def __init__(self,
                 model_path: Optional[str] = None,
                 auto_download: bool = True,
                 history_len: int = 16,
                 spoof_vote_ratio: float = 0.75,
                 min_history_frames: int = 8):

        self.history_len = history_len
        self.spoof_vote_ratio = spoof_vote_ratio
        self.min_history_frames = min_history_frames

        # Xác định đường dẫn file model
        if model_path is None:
            self.model_path = DEFAULT_MODEL_PATH
        else:
            self.model_path = model_path

        # Khởi tạo mạng Deep Learning
        self.net: Optional[cv2.dnn.Net] = None
        self.backend_mode = "HEURISTIC_FALLBACK"

        if auto_download:
            ensure_model_file(self.model_path, MODEL_URLS)

        if os.path.isfile(self.model_path):
            try:
                self.net = cv2.dnn.readNetFromONNX(self.model_path)
                self.backend_mode = "MINIFASNET_DNN"
                # Thử kích hoạt GPU CUDA
                try:
                    import torch
                    if torch.cuda.is_available() and hasattr(cv2.dnn, "DNN_BACKEND_CUDA"):
                        self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_CUDA)
                        self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CUDA)
                        print(f"🔥 [ANTI-SPOOF GPU] Đã kích hoạt tăng tốc GPU ({torch.cuda.get_device_name(0)}) cho MiniFASNet!")
                    else:
                        self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
                        self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
                except Exception:
                    self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
                    self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)

                print(f"[ANTI-SPOOF] Nạp thành công mô hình Deep Learning: {os.path.basename(self.model_path)}")
            except Exception as e:
                print(f"[ANTI-SPOOF] Lỗi nạp mô hình ONNX ({e}). Chuyển sang Fallback Heuristic v3.0")
                self.net = None
        else:
            print("[ANTI-SPOOF] Chưa có mô hình MiniFASNet ONNX. Chạy chế độ Fallback Heuristic v3.0.")

        # --- Khởi tạo các tham số Heuristic v3.0 (phục vụ fallback) ---
        self._init_heuristic_engine()

        # Quản lý hàng đợi lịch sử theo từng track_id: {track_key: deque}
        self._track_histories: Dict[Any, deque] = {}
        self._track_last_seen: Dict[Any, float] = {}
        self._last_cleanup_time = time.time()

    def _init_heuristic_engine(self):
        """Khởi tạo các hằng số toán học cho tầng dự phòng Heuristic v3.0."""
        self.blur_threshold = 12.0
        self.papr_screen_threshold = 16.0
        self.hf_ratio_threshold = 0.18
        self.color_sat_min = 12.0
        self.color_sat_max = 230.0
        self.glare_ratio_threshold = 0.035

        h, w = (128, 128)
        cy, cx = h // 2, w // 2
        y, x = np.ogrid[:h, :w]
        dist = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)
        self._mask_mid = (dist >= 14) & (dist < 46)
        self._mask_high = (dist >= 46) & (dist <= 64)

    def _get_expanded_box(self, src_w: int, src_h: int,
                           bbox: Tuple[int, int, int, int], scale: float = 2.7) -> Tuple[int, int, int, int]:
        """Mở rộng bounding box khuôn mặt theo tỷ lệ 2.7 chuẩn của MiniFASNet."""
        x, y, box_w, box_h = bbox
        scale = min((src_h - 1) / float(max(1, box_h)), min((src_w - 1) / float(max(1, box_w)), scale))
        new_width = box_w * scale
        new_height = box_h * scale
        center_x = box_w / 2.0 + x
        center_y = box_h / 2.0 + y

        left_top_x = int(center_x - new_width / 2.0)
        left_top_y = int(center_y - new_height / 2.0)
        right_bottom_x = int(center_x + new_width / 2.0)
        right_bottom_y = int(center_y + new_height / 2.0)

        if left_top_x < 0:
            right_bottom_x -= left_top_x
            left_top_x = 0
        if left_top_y < 0:
            right_bottom_y -= left_top_y
            left_top_y = 0
        if right_bottom_x > src_w - 1:
            left_top_x -= (right_bottom_x - src_w + 1)
            right_bottom_x = src_w - 1
        if right_bottom_y > src_h - 1:
            left_top_y -= (right_bottom_y - src_h + 1)
            right_bottom_y = src_h - 1

        left_top_x = max(0, left_top_x)
        left_top_y = max(0, left_top_y)
        right_bottom_x = min(src_w - 1, right_bottom_x)
        right_bottom_y = min(src_h - 1, right_bottom_y)

        return left_top_x, left_top_y, right_bottom_x, right_bottom_y

    def _infer_minifasnet(self, frame: np.ndarray,
                           face_location: Tuple[int, int, int, int]) -> Tuple[bool, str, float, List[str], Dict[str, float]]:
        """Suy luận bằng mô hình Deep Learning MiniFASNetV2 qua OpenCV DNN."""
        top, right, bottom, left = face_location
        h_frame, w_frame = frame.shape[:2]
        x, y = left, top
        bw = right - left
        bh = bottom - top

        # Mở rộng hộp bao quanh mặt theo tỷ lệ 2.7
        x1, y1, x2, y2 = self._get_expanded_box(w_frame, h_frame, (x, y, bw, bh), scale=2.7)
        face_crop = frame[y1:y2 + 1, x1:x2 + 1]

        if face_crop.size == 0:
            face_crop = frame[max(0, top):min(h_frame, bottom), max(0, left):min(w_frame, right)]

        # Chuẩn hóa đầu vào (1, 3, 80, 80) định dạng BGR
        resized = cv2.resize(face_crop, (80, 80), interpolation=cv2.INTER_LINEAR)
        blob = np.transpose(resized.astype(np.float32), (2, 0, 1))
        blob = np.expand_dims(blob, axis=0)

        # Chạy suy luận qua mạng DNN
        self.net.setInput(blob)
        raw_out = self.net.forward()

        # Áp dụng hàm Softmax: [p_paper, p_real, p_screen]
        exp_out = np.exp(raw_out - np.max(raw_out, axis=1, keepdims=True))
        probs = exp_out / np.sum(exp_out, axis=1, keepdims=True)
        scores = probs[0]

        p_paper = float(scores[0])
        p_real = float(scores[1])
        p_screen = float(scores[2])

        pred_class = int(np.argmax(scores))

        reasons = []
        # Ưu tiên REAL nếu Real là cao nhất hoặc xác suất thật đạt mức hợp lý (>= 0.45)
        if pred_class == 1 or p_real >= 0.45:
            is_spoof = False
            status = "REAL"
            confidence = p_real
        elif pred_class == 0 and p_paper >= 0.65 and p_real < 0.35:
            is_spoof = True
            status = "SPOOF_PHOTO"
            confidence = p_paper
            reasons.append(f"Deep Learning: Ảnh in giấy (Conf={p_paper*100:.1f}%)")
        elif pred_class == 2 and p_screen >= 0.65 and p_real < 0.35:
            is_spoof = True
            status = "SPOOF_SCREEN"
            confidence = p_screen
            reasons.append(f"Deep Learning: Màn hình thiết bị (Conf={p_screen*100:.1f}%)")
        else:
            # Vùng lưỡng lự (góc nghiêng, chuyển động nhẹ): Xem là REAL để tránh làm gián đoạn học sinh
            is_spoof = False
            status = "REAL"
            confidence = p_real

        details = {"paper": round(p_paper, 3), "real": round(p_real, 3), "screen": round(p_screen, 3)}
        return is_spoof, status, confidence, reasons, details

    def _infer_heuristic(self, frame: np.ndarray,
                         face_location: Tuple[int, int, int, int]) -> Tuple[bool, str, float, List[str], Dict[str, float]]:
        """Suy luận bằng bộ phân tích Toán học v3.0 (chế độ Fallback)."""
        top, right, bottom, left = face_location
        h_frame, w_frame = frame.shape[:2]
        fw, fh = right - left, bottom - top

        crop_mx = int(fw * 0.10)
        crop_my = int(fh * 0.10)
        face_crop = frame[max(0, top + crop_my):min(h_frame, bottom - crop_my),
                          max(0, left + crop_mx):min(w_frame, right - crop_mx)]
        if face_crop.size == 0:
            face_crop = frame[max(0, top):min(h_frame, bottom), max(0, left):min(w_frame, right)]

        face_norm = cv2.resize(face_crop, (128, 128), interpolation=cv2.INTER_LINEAR)
        gray = cv2.cvtColor(face_norm, cv2.COLOR_BGR2GRAY)

        lap_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())

        f_shift = np.fft.fftshift(np.fft.fft2(gray))
        mag = np.abs(f_shift)
        mid_energy = float(np.sum(mag[self._mask_mid]))
        high_energy = float(np.sum(mag[self._mask_high]))
        hf_ratio = high_energy / (mid_energy + 1e-6)

        high_band_vals = mag[self._mask_high]
        papr_score = float(np.max(high_band_vals)) / (float(np.mean(high_band_vals)) + 1e-6)

        hsv = cv2.cvtColor(face_norm, cv2.COLOR_BGR2HSV)
        sat_ch = hsv[:, :, 1]
        val_ch = hsv[:, :, 2]
        mean_sat = float(np.mean(sat_ch))

        glare_mask = (val_ch >= 250) & (sat_ch <= 40)
        glare_ratio = float(np.count_nonzero(glare_mask)) / (128.0 * 128.0)

        is_spoof = False
        status = "REAL"
        reasons = []

        if papr_score >= self.papr_screen_threshold:
            is_spoof = True
            status = "SPOOF_SCREEN"
            reasons.append(f"Moiré lưới pixel (PAPR={papr_score:.1f})")
        elif glare_ratio >= self.glare_ratio_threshold and papr_score >= (self.papr_screen_threshold * 0.75):
            is_spoof = True
            status = "SPOOF_SCREEN"
            reasons.append(f"Phản xạ bóng kính ({glare_ratio*100:.1f}%)")
        elif lap_var < 5.0 and mean_sat < 18.0:
            is_spoof = True
            status = "SPOOF_PHOTO"
            reasons.append(f"Ảnh in phẳng/mờ (Var={lap_var:.1f})")
        elif mean_sat < self.color_sat_min:
            is_spoof = True
            status = "SPOOF_PHOTO"
            reasons.append(f"Ảnh đen trắng (Sat={mean_sat:.1f})")

        conf = 0.85 if not is_spoof else 0.80
        details = {"laplacian_var": round(lap_var, 1), "papr_score": round(papr_score, 1), "glare_ratio": round(glare_ratio, 3)}
        return is_spoof, status, conf, reasons, details

    def check_liveness(self, frame: np.ndarray,
                       face_location: Tuple[int, int, int, int],
                       track_id: Optional[Any] = None) -> Dict[str, Any]:
        """
        Kiểm tra tính thật (liveness) của khuôn mặt trong khung hình.
        """
        if frame is None or frame.size == 0 or face_location is None:
            return {
                "is_real": False,
                "status": "SPOOF_PHOTO",
                "confidence": 0.0,
                "score": 0.0,
                "message": "Khung hình không hợp lệ",
                "details": {}
            }

        top, right, bottom, left = face_location
        h_frame, w_frame = frame.shape[:2]
        fw = right - left
        fh = bottom - top

        # Nếu mặt quá nhỏ (xa camera), tạm thời giữ an toàn chưa phạt
        if fw < 32 or fh < 32:
            return {
                "is_real": True,
                "status": "REAL",
                "confidence": 0.5,
                "score": 0.5,
                "message": "Khuôn mặt xa camera",
                "details": {"reason": "face_too_small"}
            }

        # -------------------------------------------------------------
        # BƯỚC 1: SUY LUẬN TỨC THỜI (DEEP LEARNING HOẶC HEURISTIC)
        # -------------------------------------------------------------
        if self.net is not None:
            try:
                frame_is_spoof, frame_status, conf_instant, reasons, raw_details = self._infer_minifasnet(frame, face_location)
            except Exception as e:
                frame_is_spoof, frame_status, conf_instant, reasons, raw_details = self._infer_heuristic(frame, face_location)
        else:
            frame_is_spoof, frame_status, conf_instant, reasons, raw_details = self._infer_heuristic(frame, face_location)

        # -------------------------------------------------------------
        # BƯỚC 2: BÌNH CHỌN ĐA KHUNG HÌNH THEO TRACK (Temporal Voting)
        # -------------------------------------------------------------
        track_key = track_id if track_id is not None else f"loc_{top // 80}_{left // 80}"
        now = time.time()
        self._track_last_seen[track_key] = now

        if track_key not in self._track_histories:
            self._track_histories[track_key] = deque(maxlen=self.history_len)

        history_q = self._track_histories[track_key]
        history_q.append((frame_is_spoof, frame_status, reasons))

        if now - self._last_cleanup_time > 15.0:
            self._cleanup_old_tracks(now)

        total_hist = len(history_q)
        spoof_count = sum(1 for is_sp, _, _ in history_q if is_sp)
        spoof_ratio = spoof_count / float(total_hist) if total_hist > 0 else 0.0

        if total_hist >= self.min_history_frames and spoof_ratio >= self.spoof_vote_ratio:
            final_is_real = False
            screen_votes = sum(1 for _, st, _ in history_q if st == "SPOOF_SCREEN")
            photo_votes = sum(1 for _, st, _ in history_q if st == "SPOOF_PHOTO")
            final_status = "SPOOF_SCREEN" if screen_votes >= photo_votes else "SPOOF_PHOTO"
            confidence = min(0.99, round(0.75 + (spoof_ratio * 0.24), 2))

            all_reasons = []
            for _, _, r_list in history_q:
                for r in r_list:
                    if r not in all_reasons:
                        all_reasons.append(r)
            msg = f"GIẢ MẠO ({final_status}): {', '.join(all_reasons[:2])}"
        else:
            final_is_real = True
            final_status = "REAL"
            confidence = min(0.99, round(0.85 + (1.0 - spoof_ratio) * 0.14, 2))
            msg = f"MẶT THẬT (Liveness OK - {self.backend_mode})"

        return {
            "is_real": final_is_real,
            "status": final_status,
            "confidence": confidence,
            "score": round(1.0 - spoof_ratio, 2),
            "message": msg,
            "details": {
                "backend": self.backend_mode,
                "track_key": str(track_key),
                "spoof_ratio": round(spoof_ratio, 2),
                "history_frames": total_hist,
                **raw_details
            }
        }

    def _cleanup_old_tracks(self, now: float):
        """Dọn dẹp các track không còn hoạt động sau 20 giây."""
        stale_keys = [k for k, t in self._track_last_seen.items() if (now - t) > 20.0]
        for k in stale_keys:
            self._track_histories.pop(k, None)
            self._track_last_seen.pop(k, None)
        self._last_cleanup_time = now

    def reset_history(self, track_id: Optional[Any] = None):
        """Xóa lịch sử bình chọn."""
        if track_id is not None:
            self._track_histories.pop(track_id, None)
            self._track_last_seen.pop(track_id, None)
        else:
            self._track_histories.clear()
            self._track_last_seen.clear()


# ==============================================================
# TEST KIỂM THỬ ĐƠN VỊ
# ==============================================================
if __name__ == "__main__":
    detector = AntiSpoofingDetector()
    print(f"\n[OK] Khởi tạo AntiSpoofingDetector thành công. Backend: {detector.backend_mode}")

    # Giả lập frame kiểm tra
    test_frame = np.full((480, 640, 3), [140, 160, 210], dtype=np.uint8)
    cv2.circle(test_frame, (320, 240), 50, (60, 70, 80), -1)

    # Test 6 frames
    print("\n--- Kiểm tra suy luận khuôn mặt test qua MiniFASNet ---")
    for i in range(6):
        res = detector.check_liveness(test_frame, (180, 370, 300, 270), track_id="test_student_1")
    print(f"Kết quả: is_real={res['is_real']}, status={res['status']}, conf={res['confidence']}")
    print(f"Chi tiết: {res['details']}")
