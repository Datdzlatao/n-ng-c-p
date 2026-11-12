# -*- coding: utf-8 -*-
"""
UNIFORM CHECKER — ĐIỀU PHỐI KIỂM TRA ĐỒNG PHỤC THEO QUY ĐỊNH
uniform_checker.py

Nâng cấp:
- Hỗ trợ nhận diện chuẩn Nông Nghiệp Công Nghệ Cao (Chuẩn image.png).
- Tích hợp MaskDetector: BẮT BUỘC ĐEO KHẨU TRANG mới nhận diện là đúng trang phục!
- Phân tích màu áo xanh dương bảo hộ + quần dài tối màu.
"""
import os
import json
import base64
import numpy as np
import cv2
from datetime import datetime
from typing import Dict, Any, Optional, Tuple, List

try:
    from person_detector import PersonDetector
    from uniform_color_analyzer import UniformColorAnalyzer, UniformAnalysisResult
except ImportError:
    from standalone_ai_engine.person_detector import PersonDetector
    from standalone_ai_engine.uniform_color_analyzer import UniformColorAnalyzer, UniformAnalysisResult

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(CURRENT_DIR, "assets", "uniform_model_v2.tflite")
LABELS_PATH = os.path.join(CURRENT_DIR, "assets", "uniform_labels_v2.json")

RULE_DISPLAY = {
    -1: "⭐ Chuẩn image.png (Áo xanh dương + Quần tối + BẮT BUỘC KHẨU TRANG)",
    10: "⭐ Chuẩn image.png (Áo xanh dương + Quần tối + BẮT BUỘC KHẨU TRANG)",
    1: "Áo trắng + Quần tối màu (Thứ 3)",
    2: "Áo trắng + Quần tối màu (Thứ 4)",
    3: "Áo trắng + Quần tối màu (Thứ 5)",
    4: "Áo Đoàn thanh niên (Thứ 6)",
    0: "Trang phục dân tộc (Thứ 2)",
    5: "Ngày nghỉ / Hoạt động ngoại khóa (Thứ 7)",
    6: "Ngày nghỉ (Chủ nhật)",
}


class UniformChecker:
    def __init__(self, use_person_detector: bool = True):
        self.person_detector = PersonDetector(use_face_fallback=True) if use_person_detector else None
        self.color_analyzer = UniformColorAnalyzer()

        self.interpreter = None
        self.labels = []
        self._load_tflite_model()

    def _load_tflite_model(self):
        if os.path.isfile(MODEL_PATH) and os.path.isfile(LABELS_PATH):
            try:
                try:
                    import tflite_runtime.interpreter as tflite
                    Interpreter = tflite.Interpreter
                except ImportError:
                    import tensorflow as tf
                    Interpreter = tf.lite.Interpreter

                self.interpreter = Interpreter(model_path=MODEL_PATH)
                self.interpreter.allocate_tensors()
                self.input_details = self.interpreter.get_input_details()
                self.output_details = self.interpreter.get_output_details()

                with open(LABELS_PATH, encoding="utf-8") as f:
                    self.labels = json.load(f)
                print(f"[UNIFORM] Đã nạp model TFLite cho Trang phục Dân tộc ({len(self.labels)} nhãn)")
            except Exception as e:
                print(f"[UNIFORM] TFLite không nạp được ({e}), tiếp tục dùng HSV Analyzer.")
                self.interpreter = None

    def detect_mask(self, frame: np.ndarray,
                    face_location: Optional[Tuple[int, int, int, int]] = None,
                    body_box: Optional[Tuple[int, int, int, int]] = None) -> Dict[str, Any]:
        """
        Phát hiện đeo khẩu trang bảo hộ (y tế/vải).
        Phân tích vùng nửa dưới khuôn mặt (mũi đến cằm):
        - Nếu không đeo: Sắc tố da tự nhiên chiếm đa số (> 55-85%).
        - Nếu có đeo khẩu trang y tế xanh dương/cyan (giống image.png) hoặc trắng/đen:
          Tỷ lệ sắc tố da giảm mạnh (< 25%), tỷ lệ màu khẩu trang vượt ngưỡng (> 30%).
        """
        ih, iw = frame.shape[:2]
        if face_location is not None:
            top, right, bottom, left = face_location
            x, y, w, h = left, top, right - left, bottom - top
        elif body_box is not None:
            bx, by, bw, bh = body_box
            w = int(bw * 0.45)
            h = int(bh * 0.22)
            x = bx + int(bw * 0.275)
            y = by
        else:
            return {
                "has_mask": False,
                "mask_color": "none",
                "confidence": 0.0,
                "skin_ratio": 0.0,
                "blue_ratio": 0.0,
                "white_ratio": 0.0,
                "mask_box": None,
                "message": "Không tìm thấy vùng mặt để quét khẩu trang"
            }

        x = max(0, min(iw - 1, int(x)))
        y = max(0, min(ih - 1, int(y)))
        w = max(1, min(iw - x, int(w)))
        h = max(1, min(ih - y, int(h)))

        lower_y = y + int(h * 0.42)
        lower_h = y + h - lower_y
        if lower_h <= 0 or w <= 0:
            return {"has_mask": False, "mask_color": "none", "confidence": 0.0, "mask_box": None}

        lower_crop = frame[lower_y:lower_y+lower_h, x:x+w]
        upper_crop = frame[y:lower_y, x:x+w]
        if lower_crop.size == 0:
            return {"has_mask": False, "mask_color": "none", "confidence": 0.0, "mask_box": None}

        hsv_lower = cv2.cvtColor(lower_crop, cv2.COLOR_BGR2HSV)
        total_pixels = lower_crop.shape[0] * lower_crop.shape[1]

        # 1. Sắc tố da (HSV)
        skin_mask = (
            ((hsv_lower[:,:,0] <= 25) | (hsv_lower[:,:,0] >= 160)) &
            (hsv_lower[:,:,1] >= 25) & (hsv_lower[:,:,1] <= 180) &
            (hsv_lower[:,:,2] >= 50)
        )
        skin_ratio = float(np.sum(skin_mask) / total_pixels)

        # 2. Khẩu trang y tế xanh dương / Cyan (đặc trưng chuẩn image.png)
        blue_mask = (
            (hsv_lower[:,:,0] >= 75) & (hsv_lower[:,:,0] <= 135) &
            (hsv_lower[:,:,1] >= 20) & (hsv_lower[:,:,2] >= 40)
        )
        blue_ratio = float(np.sum(blue_mask) / total_pixels)

        # 3. Khẩu trang trắng
        white_mask = (hsv_lower[:,:,1] <= 35) & (hsv_lower[:,:,2] >= 145)
        white_ratio = float(np.sum(white_mask) / total_pixels)

        # 4. Khẩu trang tối màu/đen
        dark_mask = hsv_lower[:,:,2] <= 55
        dark_ratio = float(np.sum(dark_mask) / total_pixels)

        has_mask = False
        mask_color = "none"
        mask_conf = 0.0

        if blue_ratio >= 0.25:
            has_mask = True
            mask_color = "blue"
            mask_conf = min(0.99, blue_ratio * 1.3)
        elif white_ratio >= 0.32 and skin_ratio < 0.35:
            has_mask = True
            mask_color = "white"
            mask_conf = min(0.98, white_ratio * 1.2)
        elif dark_ratio >= 0.30 and skin_ratio < 0.25:
            has_mask = True
            mask_color = "black"
            mask_conf = min(0.95, dark_ratio * 1.25)
        elif skin_ratio < 0.20:
            has_mask = True
            mask_color = "covered"
            mask_conf = 0.85

        return {
            "has_mask": has_mask,
            "mask_color": mask_color,
            "confidence": round(float(mask_conf), 3),
            "skin_ratio": round(float(skin_ratio), 3),
            "blue_ratio": round(float(blue_ratio), 3),
            "white_ratio": round(float(white_ratio), 3),
            "mask_box": [int(x), int(lower_y), int(w), int(lower_h)]
        }

    def get_body_boxes(self, frame: np.ndarray, face_locations: Optional[List[Tuple[int, int, int, int]]] = None) -> List[Dict]:
        if self.person_detector is not None:
            return self.person_detector.detect(frame, face_locations=face_locations)
        h, w = frame.shape[:2]
        return [{
            "body_box": (0, 0, w, h),
            "shirt_box": (0, int(h * 0.12), w, int(h * 0.38)),
            "pants_box": (0, int(h * 0.52), w, int(h * 0.38)),
            "source": "full_frame"
        }]

    def check_uniform(self, frame: np.ndarray,
                      body_box: Optional[Tuple[int, int, int, int]] = None,
                      face_location: Optional[Tuple[int, int, int, int]] = None,
                      weekday_override: Optional[int] = None) -> Dict[str, Any]:
        """
        Kiểm tra đồng phục của người trong khung hình bằng cách quét toàn bộ cơ thể.
        """
        weekday = weekday_override if weekday_override is not None else datetime.now().weekday()
        rule_desc = RULE_DISPLAY.get(weekday, "Chuẩn image.png: Áo xanh dương + Quần tối + BẮT BUỘC KHẨU TRANG")

        # 1. Phát hiện thân người toàn diện (HOG Person Detector + Face estimation)
        shirt_box = None
        pants_box = None
        if body_box is None:
            faces = [face_location] if face_location else None
            detections = self.get_body_boxes(frame, face_locations=faces)
            if detections:
                det = detections[0]
                body_box = det["body_box"]
                shirt_box = det.get("shirt_box")
                pants_box = det.get("pants_box")
        else:
            bx, by, bw, bh = body_box
            shirt_box = (bx, by + int(bh * 0.12), bw, int(bh * 0.38))
            pants_box = (bx, by + int(bh * 0.52), bw, int(bh * 0.38))

        # 2. Phân tích khẩu trang
        mask_info = self.detect_mask(frame, face_location=face_location, body_box=body_box)
        require_mask = (weekday in (-1, 10))

        if body_box is None:
            return {
                "person_detected": False,
                "is_correct": False,
                "status": "UNCLEAR",
                "rule": rule_desc,
                "message": "Không nhận diện được vóc dáng người trong ảnh. Vui lòng đứng trước camera để quét toàn thân.",
                "shirt_color": "unknown",
                "shirt_ratio": 0.0,
                "pants_color": "unknown",
                "pants_ratio": 0.0,
                "body_box": None,
                "shirt_box": None,
                "pants_box": None,
                "mask": mask_info,
                "require_mask": require_mask
            }

        # 3. Phân tích vùng áo và quần qua Color Analyzer (HSV)
        res = self.color_analyzer.check(frame, body_box, weekday=1 if weekday in (-1, 10, None) else weekday)

        # 4. Phán đoán kết quả đồng phục theo quy định
        if weekday in (-1, 10):
            # =================================================================
            # QUY ĐỊNH NÔNG NGHIỆP CÔNG NGHỆ CAO (CHUẨN IMAGE.PNG):
            # 1. BẮT BUỘC PHẢI ĐEO KHẨU TRANG (Y tế xanh hoặc vải che kín mũi miệng)
            # 2. ÁO BẢO HỘ XANH DƯƠNG / XANH DA TRỜI (hoặc trắng theo tiêu chuẩn)
            # 3. QUẦN DÀI TỐI MÀU (Đen / Xanh đen)
            # =================================================================
            if not mask_info.get("has_mask"):
                is_correct = False
                status = "FAIL_NO_MASK"
                message = "❌ VI PHẠM: Chưa đeo khẩu trang bảo hộ (Yêu cầu bắt buộc đeo khẩu trang che kín mũi miệng theo chuẩn image.png)!"
            elif res.shirt_color not in ("blue", "cyan", "white"):
                is_correct = False
                status = "FAIL_SHIRT"
                message = f"❌ VI PHẠM ÁO: Áo màu {res.shirt_color} không đúng (Yêu cầu áo xanh dương bảo hộ giống image.png)!"
            elif res.pants_color != "dark":
                is_correct = False
                status = "FAIL_PANTS"
                message = f"❌ VI PHẠM QUẦN: Quần màu {res.pants_color} không đúng (Yêu cầu quần dài tối màu)!"
            else:
                is_correct = True
                status = "OK"
                mask_color_vn = "Xanh y tế" if mask_info.get("mask_color") == "blue" else "Bảo hộ"
                message = f"✅ ĐÚNG QUY ĐỊNH: Đã đeo khẩu trang ({mask_color_vn}) + Áo xanh dương + Quần tối màu chuẩn image.png!"

        elif weekday == 0 and self.interpreter is not None:
            # Thứ 2: Trang phục Dân tộc qua TFLite
            bx, by, bw, bh = body_box
            crop = frame[max(0, by):min(frame.shape[0], by + bh), max(0, bx):min(frame.shape[1], bx + bw)]
            resized = cv2.resize(crop, (224, 224))
            input_data = np.expand_dims(resized.astype(np.float32) / 255.0, axis=0)
            self.interpreter.set_tensor(self.input_details[0]["index"], input_data)
            self.interpreter.invoke()
            preds = self.interpreter.get_tensor(self.output_details[0]["index"])[0]
            top_idx = int(np.argmax(preds))
            conf = float(preds[top_idx])
            label = self.labels[top_idx] if top_idx < len(self.labels) else "other"
            if "dan_toc" in label and conf >= 0.55:
                is_correct = True
                status = "OK"
                message = f"Đúng quy định: Trang phục dân tộc ({conf*100:.1f}%)"
            else:
                is_correct = False
                status = "FAIL"
                message = "Vi phạm: Thứ 2 yêu cầu trang phục dân tộc"
        else:
            is_correct = (res.status == "OK")
            status = res.status
            message = res.message

        return {
            "person_detected": True,
            "is_correct": is_correct,
            "status": status,
            "rule": rule_desc,
            "message": message,
            "shirt_color": res.shirt_color,
            "shirt_ratio": round(getattr(res, "shirt_ratio", 0.0), 3),
            "pants_color": res.pants_color,
            "pants_ratio": round(getattr(res, "pants_ratio", 0.0), 3),
            "body_box": list(body_box),
            "shirt_box": list(shirt_box) if shirt_box else None,
            "pants_box": list(pants_box) if pants_box else None,
            "mask": mask_info,
            "require_mask": require_mask
        }

    def draw_uniform_hud(self, frame: np.ndarray, uniform_result: Dict[str, Any]) -> np.ndarray:
        """
        Vẽ trực quan bounding boxes toàn thân, khẩu trang, vùng áo, vùng quần lên ảnh.
        """
        canvas = frame.copy()
        if not uniform_result.get("person_detected") or not uniform_result.get("body_box"):
            return canvas

        bx, by, bw, bh = uniform_result["body_box"]
        is_ok = uniform_result.get("is_correct", False)
        status = uniform_result.get("status", "UNCLEAR")
        body_color = (0, 220, 80) if is_ok else (0, 50, 240) # Green / Red

        # 1. Vẽ khung toàn thân
        cv2.rectangle(canvas, (bx, by), (bx + bw, by + bh), body_color, 2)
        tag = f"DONG PHUC: {status} - {uniform_result.get('message', '')[:40]}"
        cv2.rectangle(canvas, (bx, max(0, by - 24)), (bx + bw, by), body_color, -1)
        cv2.putText(canvas, tag, (bx + 4, max(16, by - 6)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)

        # 2. Vẽ khung khẩu trang (Mask Box)
        mask_data = uniform_result.get("mask")
        if mask_data and mask_data.get("mask_box"):
            mx, my, mw, mh = mask_data["mask_box"]
            has_m = mask_data.get("has_mask", False)
            m_color = (0, 220, 80) if has_m else (0, 0, 255)
            cv2.rectangle(canvas, (mx, my), (mx + mw, my + mh), m_color, 2)
            m_lbl = f"KHAU TRANG: {'DA DEO (' + mask_data.get('mask_color', '').upper() + ')' if has_m else 'CHUA DEO!'}"
            cv2.putText(canvas, m_lbl, (mx, max(14, my - 4)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.38, m_color, 1, cv2.LINE_AA)

        # 3. Vẽ vùng áo
        shirt_box = uniform_result.get("shirt_box")
        if shirt_box:
            sx, sy, sw, sh = shirt_box
            cv2.rectangle(canvas, (sx, sy), (sx + sw, sy + sh), (255, 200, 0), 1)
            shirt_lbl = f"AO: {uniform_result.get('shirt_color')} ({int(uniform_result.get('shirt_ratio', 0)*100)}%)"
            cv2.putText(canvas, shirt_lbl, (sx + 4, sy + 14),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.40, (255, 200, 0), 1, cv2.LINE_AA)

        # 4. Vẽ vùng quần
        pants_box = uniform_result.get("pants_box")
        if pants_box:
            px, py, pw, ph = pants_box
            cv2.rectangle(canvas, (px, py), (px + pw, py + ph), (0, 165, 255), 1)
            pants_lbl = f"QUAN: {uniform_result.get('pants_color')} ({int(uniform_result.get('pants_ratio', 0)*100)}%)"
            cv2.putText(canvas, pants_lbl, (px + 4, py + 14),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.40, (0, 165, 255), 1, cv2.LINE_AA)

        return canvas
