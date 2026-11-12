# -*- coding: utf-8 -*-
"""
ANTI-SPOOFING ENGINE — PHÁT HIỆN GIAN LẬN KHUÔN MẶT
Hybrid MiniFASNet ONNX + Heuristic Fallback
"""
import os
import cv2
import time
import urllib.request
import numpy as np
from collections import deque
from typing import Tuple, Dict, Any, Optional, List

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_MODEL_DIR = os.path.join(CURRENT_DIR, "assets", "models")
MODEL_FILENAME = "2.7_80x80_MiniFASNetV2.onnx"
DEFAULT_MODEL_PATH = os.path.join(DEFAULT_MODEL_DIR, MODEL_FILENAME)

MODEL_URLS = [
    "https://raw.githubusercontent.com/QingHeYang/Silent-Face-Anti-Spoofing-onnx/main/onnx/2.7_80x80_MiniFASNetV2.onnx",
    "https://media.githubusercontent.com/media/minivision-ai/Silent-Face-Anti-Spoofing/master/resources/anti_spoof_models/2.7_80x80_MiniFASNetV2.onnx"
]


def ensure_model_file(model_path: str, urls: List[str], min_bytes: int = 1_000_000) -> bool:
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
    def __init__(self,
                 model_path: Optional[str] = None,
                 auto_download: bool = True,
                 history_len: int = 16,
                 spoof_vote_ratio: float = 0.75,
                 min_history_frames: int = 8):

        self.history_len = history_len
        self.spoof_vote_ratio = spoof_vote_ratio
        self.min_history_frames = min_history_frames

        if model_path is None:
            self.model_path = DEFAULT_MODEL_PATH
        else:
            self.model_path = model_path

        self.net: Optional[cv2.dnn.Net] = None
        self.backend_mode = "HEURISTIC_FALLBACK"

        if auto_download:
            ensure_model_file(self.model_path, MODEL_URLS)

        if os.path.isfile(self.model_path):
            try:
                self.net = cv2.dnn.readNetFromONNX(self.model_path)
                self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
                self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
                self.backend_mode = "DEEP_LEARNING_ONNX"
                print(f"[ANTI-SPOOF] Đã khởi tạo MiniFASNet ONNX thành công.")
            except Exception as e:
                print(f"[ANTI-SPOOF] Không nạp được ONNX: {e} -> Chuyển sang Heuristic Fallback.")
                self.net = None
                self.backend_mode = "HEURISTIC_FALLBACK"

        self.track_histories: Dict[Any, deque] = {}

    def _crop_face_box(self, frame: np.ndarray, loc: Tuple[int, int, int, int], scale: float = 2.7) -> Optional[np.ndarray]:
        top, right, bottom, left = loc
        h, w = frame.shape[:2]

        box_w = right - left
        box_h = bottom - top
        if box_w <= 0 or box_h <= 0:
            return None

        cx = left + box_w / 2.0
        cy = top + box_h / 2.0

        max_side = max(box_w, box_h) * scale
        half = max_side / 2.0

        x1 = max(0, int(round(cx - half)))
        y1 = max(0, int(round(cy - half)))
        x2 = min(w, int(round(cx + half)))
        y2 = min(h, int(round(cy + half)))

        crop = frame[y1:y2, x1:x2]
        if crop.size == 0 or crop.shape[0] < 10 or crop.shape[1] < 10:
            return None
        return crop

    def _infer_deep_learning(self, crop: np.ndarray) -> Tuple[bool, str, float]:
        blob = cv2.dnn.blobFromImage(
            crop,
            scalefactor=1.0,
            size=(80, 80),
            mean=(0, 0, 0),
            swapRB=True,
            crop=False
        )
        self.net.setInput(blob)
        preds = self.net.forward()
        if preds is None or len(preds) == 0:
            return True, "REAL", 1.0

        logits = preds[0]
        exp_vals = np.exp(logits - np.max(logits))
        probs = exp_vals / np.sum(exp_vals)

        p_paper = float(probs[0])
        p_real  = float(probs[1]) if len(probs) > 1 else 0.0
        p_screen= float(probs[2]) if len(probs) > 2 else 0.0

        if p_real >= 0.60:
            return True, "REAL", p_real
        elif p_screen > p_paper:
            return False, "SCREEN", p_screen
        else:
            return False, "PAPER", p_paper

    def _infer_heuristic(self, crop: np.ndarray) -> Tuple[bool, str, float]:
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        lap_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())

        f = np.fft.fft2(gray)
        fshift = np.fft.fftshift(f)
        magnitude_spectrum = np.log(np.abs(fshift) + 1.0)
        hf_mean = float(np.mean(magnitude_spectrum))

        ycrcb = cv2.cvtColor(crop, cv2.COLOR_BGR2YCrCb)
        cr = ycrcb[:, :, 1]
        cb = ycrcb[:, :, 2]
        skin_mask = (cr >= 133) & (cr <= 173) & (cb >= 77) & (cb <= 127)
        skin_ratio = float(np.count_nonzero(skin_mask)) / float(crop.shape[0] * crop.shape[1])

        hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
        v_channel = hsv[:, :, 2]
        glare_ratio = float(np.count_nonzero(v_channel >= 250)) / float(crop.shape[0] * crop.shape[1])

        is_spoof = False
        spoof_type = "REAL"
        conf = 1.0

        if lap_var < 28.0 or hf_mean < 4.0:
            is_spoof = True
            spoof_type = "PAPER"
            conf = 0.85
        elif glare_ratio > 0.15 or skin_ratio < 0.10:
            is_spoof = True
            spoof_type = "SCREEN"
            conf = 0.80

        return not is_spoof, spoof_type, conf

    def check_liveness(self, frame: np.ndarray, loc: Tuple[int, int, int, int], track_id: Optional[Any] = None) -> Dict[str, Any]:
        crop = self._crop_face_box(frame, loc)
        if crop is None:
            return {"is_real": True, "status": "UNKNOWN", "confidence": 0.0, "message": "Không thể cắt vùng mặt"}

        if self.net is not None:
            try:
                is_real, spoof_type, conf = self._infer_deep_learning(crop)
            except Exception:
                is_real, spoof_type, conf = self._infer_heuristic(crop)
        else:
            is_real, spoof_type, conf = self._infer_heuristic(crop)

        if track_id is not None:
            if track_id not in self.track_histories:
                self.track_histories[track_id] = deque(maxlen=self.history_len)
            hist = self.track_histories[track_id]
            hist.append((is_real, spoof_type, conf))

            if len(hist) >= self.min_history_frames:
                spoof_count = sum(1 for item in hist if not item[0])
                if spoof_count / float(len(hist)) >= self.spoof_vote_ratio:
                    types = [item[1] for item in hist if not item[0]]
                    final_type = max(set(types), key=types.count) if types else "SPOOF"
                    return {
                        "is_real": False,
                        "status": final_type,
                        "confidence": conf,
                        "message": f"Phát hiện gian lận: {final_type}"
                    }
                else:
                    return {"is_real": True, "status": "REAL", "confidence": conf, "message": "Khuôn mặt thật hợp lệ"}

        return {
            "is_real": is_real,
            "status": spoof_type if not is_real else "REAL",
            "confidence": conf,
            "message": "Khuôn mặt thật hợp lệ" if is_real else f"Phát hiện gian lận: {spoof_type}"
        }
