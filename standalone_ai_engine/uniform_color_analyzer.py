# -*- coding: utf-8 -*-
"""
UNIFORM COLOR ANALYZER (HSV)
Phân tích màu sắc áo và quần trong không gian màu HSV.
"""
import cv2
import numpy as np
from dataclasses import dataclass
from typing import Tuple, Optional, Dict, Any

@dataclass
class UniformAnalysisResult:
    status: str            # "OK" | "FAIL" | "UNCLEAR" | "SKIP"
    shirt_color: str       # "white" | "blue" | "other"
    shirt_ratio: float     # 0.0 - 1.0
    pants_color: str       # "dark" | "light" | "unknown"
    pants_ratio: float     # 0.0 - 1.0
    message: str


class UniformColorAnalyzer:
    def __init__(self,
                 white_s_max: int = 70,
                 white_v_min: int = 145,
                 white_ratio_min: float = 0.42,
                 blue_h_range: Tuple[int, int] = (85, 138),
                 blue_s_min: int = 40,
                 blue_v_min: int = 35,
                 blue_ratio_min: float = 0.38,
                 dark_pants_v_max: int = 115,
                 dark_pants_ratio_min: float = 0.40):

        self.white_s_max = white_s_max
        self.white_v_min = white_v_min
        self.white_ratio_min = white_ratio_min

        self.blue_h_min, self.blue_h_max = blue_h_range
        self.blue_s_min = blue_s_min
        self.blue_v_min = blue_v_min
        self.blue_ratio_min = blue_ratio_min

        self.dark_pants_v_max = dark_pants_v_max
        self.dark_pants_ratio_min = dark_pants_ratio_min

    def analyze_crop_hsv(self, crop_bgr: np.ndarray) -> Dict[str, float]:
        if crop_bgr is None or crop_bgr.size == 0:
            return {"white": 0.0, "blue": 0.0, "dark": 0.0}

        # Denoise / blur slightly
        blurred = cv2.GaussianBlur(crop_bgr, (5, 5), 0)
        hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)
        h, s, v = hsv[:, :, 0], hsv[:, :, 1], hsv[:, :, 2]
        total_pixels = float(crop_bgr.shape[0] * crop_bgr.shape[1])

        # White mask
        white_mask = (s <= self.white_s_max) & (v >= self.white_v_min)
        white_ratio = float(np.count_nonzero(white_mask)) / total_pixels

        # Blue mask
        blue_mask = (h >= self.blue_h_min) & (h <= self.blue_h_max) & (s >= self.blue_s_min) & (v >= self.blue_v_min)
        blue_ratio = float(np.count_nonzero(blue_mask)) / total_pixels

        # Dark pants mask
        dark_mask = (v <= self.dark_pants_v_max)
        dark_ratio = float(np.count_nonzero(dark_mask)) / total_pixels

        return {
            "white": white_ratio,
            "blue": blue_ratio,
            "dark": dark_ratio
        }

    def check(self, frame: np.ndarray, body_box: Tuple[int, int, int, int], weekday: int) -> UniformAnalysisResult:
        """
        weekday: 0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri, 5=Sat, 6=Sun
        """
        if body_box is None:
            return UniformAnalysisResult("UNCLEAR", "unknown", 0.0, "unknown", 0.0, "Không xác định được vị trí người")

        bx, by, bw, bh = body_box
        h, w = frame.shape[:2]

        # Crop shirt zone: 12% - 50%
        sy1 = max(0, by + int(bh * 0.12))
        sy2 = min(h, by + int(bh * 0.50))
        sx1 = max(0, bx)
        sx2 = min(w, bx + bw)
        shirt_crop = frame[sy1:sy2, sx1:sx2]

        # Crop pants zone: 52% - 90%
        py1 = max(0, by + int(bh * 0.52))
        py2 = min(h, by + int(bh * 0.90))
        px1 = max(0, bx)
        px2 = min(w, bx + bw)
        pants_crop = frame[py1:py2, px1:px2]

        shirt_stats = self.analyze_crop_hsv(shirt_crop)
        pants_stats = self.analyze_crop_hsv(pants_crop)

        w_ratio = shirt_stats["white"]
        b_ratio = shirt_stats["blue"]
        p_dark_ratio = pants_stats["dark"]

        # Determine shirt color
        if w_ratio >= self.white_ratio_min:
            shirt_color = "white"
            shirt_conf = w_ratio
        elif b_ratio >= self.blue_ratio_min:
            shirt_color = "blue"
            shirt_conf = b_ratio
        else:
            shirt_color = "other"
            shirt_conf = max(w_ratio, b_ratio)

        pants_color = "dark" if p_dark_ratio >= self.dark_pants_ratio_min else "light"

        # Check rules:
        # Tuesday (1) & Thursday (3) & Wednesday (2): Áo trắng + Quần tối màu
        if weekday in (1, 2, 3):
            if shirt_color == "white":
                # If pants visible
                if pants_crop.shape[0] > 20 and pants_color != "dark":
                    return UniformAnalysisResult("FAIL", shirt_color, shirt_conf, pants_color, p_dark_ratio, "Vi phạm: Áo trắng nhưng quần không tối màu")
                return UniformAnalysisResult("OK", shirt_color, shirt_conf, pants_color, p_dark_ratio, "Đúng quy định: Áo trắng + Quần tối màu")
            else:
                return UniformAnalysisResult("FAIL", shirt_color, shirt_conf, pants_color, p_dark_ratio, f"Sai đồng phục: Cần áo trắng (hiện tại: {shirt_color})")

        # Friday (4): Áo Đoàn (xanh) + Quần tối màu
        elif weekday == 4:
            if shirt_color == "blue":
                return UniformAnalysisResult("OK", shirt_color, shirt_conf, pants_color, p_dark_ratio, "Đúng quy định: Áo đoàn viên")
            elif shirt_color == "white":
                return UniformAnalysisResult("FAIL", shirt_color, shirt_conf, pants_color, p_dark_ratio, "Vi phạm: Thứ 6 yêu cầu áo Đoàn thanh niên")
            else:
                return UniformAnalysisResult("FAIL", shirt_color, shirt_conf, pants_color, p_dark_ratio, "Sai đồng phục: Cần áo đoàn viên màu xanh")

        return UniformAnalysisResult("SKIP", shirt_color, shirt_conf, pants_color, p_dark_ratio, "Không yêu cầu đồng phục bắt buộc hôm nay")
