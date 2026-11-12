# -*- coding: utf-8 -*-
"""
UNIFORM CHECKER — ĐIỀU PHỐI KIỂM TRA ĐỒNG PHỤC THEO QUY ĐỊNH
uniform_checker.py
"""
import os
import json
import numpy as np
import cv2
from datetime import datetime
from typing import Dict, Any, Optional, Tuple, List
from person_detector import PersonDetector
from uniform_color_analyzer import UniformColorAnalyzer, UniformAnalysisResult

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(CURRENT_DIR, "assets", "uniform_model_v2.tflite")
LABELS_PATH = os.path.join(CURRENT_DIR, "assets", "uniform_labels_v2.json")

RULE_DISPLAY = {
    0: "Trang phục dân tộc (Thứ 2)",
    1: "Áo trắng + Quần tối màu (Thứ 3)",
    2: "Áo trắng + Quần tối màu (Thứ 4)",
    3: "Áo trắng + Quần tối màu (Thứ 5)",
    4: "Áo Đoàn thanh niên (Thứ 6)",
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

    def get_body_boxes(self, frame: np.ndarray, face_locations: Optional[List[Tuple[int, int, int, int]]] = None) -> List[Dict]:
        if self.person_detector is not None:
            return self.person_detector.detect(frame, face_locations=face_locations)
        h, w = frame.shape[:2]
        return [{
            "body_box": (0, 0, w, h),
            "shirt_box": (0, int(h * 0.12), w, int(h * 0.40)),
            "pants_box": (0, int(h * 0.52), w, int(h * 0.38)),
            "source": "full_frame"
        }]

    def check_uniform(self, frame: np.ndarray,
                      body_box: Optional[Tuple[int, int, int, int]] = None,
                      face_location: Optional[Tuple[int, int, int, int]] = None,
                      weekday_override: Optional[int] = None) -> Dict[str, Any]:
        """
        Kiểm tra đồng phục của người trong khung hình.
        Returns:
            {
                "is_correct": bool,
                "status": "OK" | "FAIL" | "UNCLEAR" | "SKIP",
                "rule": str,
                "message": str,
                "shirt_color": str,
                "pants_color": str,
                "body_box": tuple
            }
        """
        weekday = weekday_override if weekday_override is not None else datetime.now().weekday()
        rule_desc = RULE_DISPLAY.get(weekday, "Không rõ")

        # Weekend: Skip
        if weekday in (5, 6):
            return {
                "is_correct": True,
                "status": "SKIP",
                "rule": rule_desc,
                "message": "Cuối tuần: Không yêu cầu đồng phục",
                "shirt_color": "any",
                "pants_color": "any",
                "body_box": body_box
            }

        # Find body box if not provided
        if body_box is None:
            faces = [face_location] if face_location else None
            detections = self.get_body_boxes(frame, face_locations=faces)
            if detections:
                body_box = detections[0]["body_box"]

        if body_box is None:
            return {
                "is_correct": False,
                "status": "UNCLEAR",
                "rule": rule_desc,
                "message": "Không nhận diện được vóc dáng người",
                "shirt_color": "unknown",
                "pants_color": "unknown",
                "body_box": None
            }

        # Monday (Thứ 2): Trang phục Dân tộc
        if weekday == 0:
            if self.interpreter is not None:
                # Infer with TFLite
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
                    return {
                        "is_correct": True,
                        "status": "OK",
                        "rule": rule_desc,
                        "message": f"Đúng quy định: Trang phục dân tộc ({conf*100:.1f}%)",
                        "shirt_color": label,
                        "pants_color": "N/A",
                        "body_box": body_box
                    }
                else:
                    return {
                        "is_correct": False,
                        "status": "FAIL",
                        "rule": rule_desc,
                        "message": f"Vi phạm: Thứ 2 yêu cầu trang phục dân tộc",
                        "shirt_color": label,
                        "pants_color": "N/A",
                        "body_box": body_box
                    }
            else:
                # If model not available, analyze shirt color
                res = self.color_analyzer.check(frame, body_box, weekday=1)
                return {
                    "is_correct": res.status == "OK",
                    "status": "OK" if res.status == "OK" else "UNCLEAR",
                    "rule": rule_desc,
                    "message": "Chưa có model TFLite Dân tộc, chấp nhận tạm áo trắng" if res.status == "OK" else "Cần kiểm tra thủ công trang phục dân tộc",
                    "shirt_color": res.shirt_color,
                    "pants_color": res.pants_color,
                    "body_box": body_box
                }

        # Tuesday - Friday: HSV Color Analyzer
        res = self.color_analyzer.check(frame, body_box, weekday=weekday)
        return {
            "is_correct": (res.status == "OK"),
            "status": res.status,
            "rule": rule_desc,
            "message": res.message,
            "shirt_color": res.shirt_color,
            "pants_color": res.pants_color,
            "body_box": body_box
        }
