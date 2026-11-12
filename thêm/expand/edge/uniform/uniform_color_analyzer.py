# -*- coding: utf-8 -*-
"""
=============================================================
  MODULE PHAN TICH MAU SAC TRANG PHUC
  uniform_color_analyzer.py

  Phan tich mau sac ao va quan bang khong gian mau HSV.
  KHONG can training AI - chay tuc thi, on dinh cao.

  Quy dinh:
    Thu 2  : Trang phuc dan toc   (xu ly boi TFLite AI)
    Thu 3  : Ao TRANG + Quan TOI MAU
    Thu 4  : Tu do co co          (khong check tu dong)
    Thu 5  : Ao TRANG + Quan TOI MAU
    Thu 6  : Ao XANH DUONG (doan) + Quan TOI MAU
    Thu 7  : Nghi
    CN     : Nghi

  Calibration:
    Chay step1_hsv_calibrator.py -> luu data/hsv_config.json
    Module nay tu dong load config do neu ton tai,
    fallback ve gia tri mac dinh neu chua calibrate.
=============================================================
"""

import cv2
import numpy as np
import json
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass
from typing import Tuple, Optional


# ==================== TU DONG LOAD CALIBRATION CONFIG ====================
_BASE = Path(__file__).parent
_CANDIDATE_CONFIG_PATHS = [
    _BASE.parent / "data" / "hsv_config.json",          # edge/data/hsv_config.json
    _BASE / "data" / "hsv_config.json",                 # edge/uniform/data/hsv_config.json
    _BASE.parent / "tools" / "data" / "hsv_config.json",# edge/tools/data/hsv_config.json
]
_CONFIG_PATH = next((p for p in _CANDIDATE_CONFIG_PATHS if p.exists()), _BASE.parent / "data" / "hsv_config.json")

# Gia tri mac dinh (dung khi chua calibrate - toi uu do chinh xac cao cho cong truong)
_DEFAULTS = {
    "white"      : {"s_max": 70,  "v_min": 145},
    "blue"       : {"h_min": 85,  "h_max": 138, "s_min": 40, "v_min": 35},
    "dark_pants" : {"v_max": 115, "ratio_min": 0.42},
    "options"    : {"waist_up_auto_ignore_pants": True},
}

def _load_hsv_config() -> dict:
    """Load HSV config tu file JSON neu co, fallback ve default."""
    if _CONFIG_PATH.exists():
        try:
            with open(_CONFIG_PATH, encoding="utf-8") as f:
                cfg = json.load(f)
            print(f"[ColorAnalyzer] Da load HSV config tu: {_CONFIG_PATH}")
            cal_time = cfg.get("calibrated_at", "?")
            print(f"                Calibrated at: {cal_time}")
            # Merge voi default de dam bao day du key
            merged = {k: dict(v) for k, v in _DEFAULTS.items()}
            for section in ("white", "blue", "dark_pants", "options"):
                if section in cfg:
                    merged[section].update(cfg[section])
            return merged
        except Exception as e:
            print(f"[ColorAnalyzer] WARN: Loi doc config ({e}) - Dung gia tri mac dinh")
    return {k: dict(v) for k, v in _DEFAULTS.items()}

_CFG = _load_hsv_config()

# ==================== CAU HINH MAU HSV ====================
# HSV: H(0-179), S(0-255), V(0-255) trong OpenCV
# (Cac bien nay duoc cap nhat tu _CFG, co the ghi de bang calibration)

# Ao trang: Sac bao hoa thap (it mau), Do sang cao
WHITE_S_MAX = _CFG["white"]["s_max"]    # Saturation <= 70: bat tot duoi nang vang som
WHITE_V_MIN = _CFG["white"]["v_min"]    # Value >= 145: bat tot trong bong ram cong truong

# Ao xanh duong (doan vien): Hue trong vung xanh duong
BLUE_H_MIN  = _CFG["blue"]["h_min"]     # Hue bat dau vung xanh duong
BLUE_H_MAX  = _CFG["blue"]["h_max"]     # Hue ket thuc vung xanh duong
BLUE_S_MIN  = _CFG["blue"]["s_min"]     # Du bao hoa (khong phai xam)
BLUE_V_MIN  = _CFG["blue"]["v_min"]     # Khong qua toi

# Quan toi mau: Do sang (Value) thap hoac xanh den
DARK_V_MAX      = _CFG["dark_pants"]["v_max"]       # Value <= 115: bao gom ca quan vai/jean toi mau
DARK_RATIO_MIN  = _CFG["dark_pants"]["ratio_min"]   # >= 42%
WAIST_UP_IGNORE = _CFG.get("options", {}).get("waist_up_auto_ignore_pants", False)

# Nguong do chinh xac toi thieu de chap nhan ket qua
MIN_PIXEL_RATIO = 0.42  # 42% pixels vung nguc phai khop moi duoc tin tuong


# ==================== KET QUA ====================
@dataclass
class ColorCheckResult:
    status: str          # "OK" / "FAIL" / "SKIP" / "UNCLEAR"
    is_shirt_ok: bool
    is_pants_ok: bool
    shirt_color: str     # Ten mau phat hien duoc
    pants_color: str     # "toi" / "sang" / "khong ro"
    shirt_ratio: float   # Ti le pixels khop voi mau quy dinh (0.0-1.0)
    pants_dark_ratio: float  # Ti le pixels toi mau o vung quan
    message: str
    debug_colors: dict   # Thong tin debug


# ==================== CLASS CHINH ====================
class UniformColorAnalyzer:
    """
    Phan tich trang phuc bang mau sac HSV.
    Ket hop voi uniform_checker.py de kiem tra day du.

    Neu pose_estimator duoc cung cap, su dung YOLOv8-Pose de xac dinh
    chinh xac vung ao/quan theo khop xuong thay vi ti le co dinh.
    """

    # Chia khung hinh thanh vung ao va quan (fallback khi khong co pose)
    # Vung ao: tu 15% den 55% chieu cao (tranh mat, co)
    # Vung quan: tu 55% den 90% chieu cao (tranh giay)
    SHIRT_ZONE = (0.15, 0.55)
    PANTS_ZONE = (0.55, 0.90)

    def __init__(self, pose_estimator=None):
        """
        Args:
            pose_estimator: Instance cua PoseEstimator (edge/pose_estimator.py).
                           None = chi dung phuong phap HSV voi ti le co dinh.
        """
        self.pose_estimator = pose_estimator
        if pose_estimator is not None and pose_estimator.available:
            print("[ColorAnalyzer] Che do: Pose-guided zones (YOLOv8-Pose)")
        else:
            print("[ColorAnalyzer] Che do: Fixed-ratio zones (fallback)")

    # ----------------------------------------------------------------
    # HAM CHINH: KIEM TRA TRANG PHUC THEO NGAY
    # ----------------------------------------------------------------
    def check(self, frame: np.ndarray,
              body_box: Optional[Tuple] = None,
              weekday: Optional[int] = None) -> ColorCheckResult:
        """
        Kiem tra trang phuc dua tren mau sac.

        Args:
            frame    : Anh BGR tu camera
            body_box : (x, y, w, h) vung than nguoi. None = dung toan bo anh
            weekday  : 0=T2, 1=T3, 2=T4, 3=T5, 4=T6, 5=T7, 6=CN
                       None = tu dong lay ngay hom nay

        Returns:
            ColorCheckResult
        """
        if weekday is None:
            weekday = datetime.now().weekday()

        # Cat vung than nguoi
        body_region = self._crop_body(frame, body_box)

        # [fix] Bu sang tong the (lighting compensation) truoc khi phan tich.
        # Nguong HSV trong config.py/hsv_config.json duoc calibrate theo 1
        # dieu kien anh sang/camera cu the -> neu doi phong hoc/camera khac,
        # do sang tong the lech di se lam sai lech ket qua "trang" hay "toi".
        # Tinh 1 he so bu (v_gain) tu chinh vung than nguoi trong frame HIEN
        # TAI, ap dung DONG NHAT cho ca vung ao va vung quan de giu nguyen
        # do tuong phan tuong doi giua ao/quan (khong dung equalizeHist rieng
        # tung vung vi se "xoa" luon do tuong phan can phan biet).
        # Day la giai phap giam nhay cam anh sang o muc vua phai — van
        # KHUYEN NGHI chay lai step1_hsv_calibrator.py neu doi phong/camera
        # co dieu kien anh sang qua khac biet.
        v_gain = self._compute_lighting_gain(body_region)

        # =====================================================================
        # BUOC 1: Thu dung YOLOv8-Pose de xac dinh vung ao/quan chinh xac
        # =====================================================================
        pose_zones = None
        used_pose  = False
        if self.pose_estimator is not None and self.pose_estimator.available:
            try:
                pose_zones = self.pose_estimator.get_body_zones(frame, body_box)
            except Exception as _pe_err:
                pose_zones = None

        if pose_zones is not None:
            # --- Pose thanh cong: dung zone tu khop xuong ---
            shirt_zone = pose_zones["shirt_zone"]
            pants_zone = pose_zones["pants_zone"]
            is_pants_visible = pose_zones["is_pants_visible"]
            used_pose = True
        else:
            # --- Fallback: ti le co dinh ---
            shirt_zone = self.SHIRT_ZONE
            pants_zone = self.PANTS_ZONE
            is_pants_visible = None   # Chua biet

        # =====================================================================
        # BUOC 2: Cat vung ao va quan theo zones da chon
        # =====================================================================
        shirt_region = self._get_zone(body_region, *shirt_zone)
        pants_region = self._get_zone(body_region, *pants_zone)

        # Phan tich mau
        shirt_analysis = self._analyze_shirt_region(shirt_region, v_gain)
        pants_analysis = self._analyze_pants_darkness(pants_region)

        # =====================================================================
        # BUOC 3: Xac dinh is_waist_up (quan ngoai khung / khong phat hien duoc)
        # =====================================================================
        is_waist_up = False
        fh, fw = frame.shape[:2]
        if body_box is not None:
            bx, by, bw, bh = body_box
            aspect_ratio = float(bh) / max(1, bw)
            touches_bottom = (by + bh >= fh - 35)
        else:
            aspect_ratio = float(fh) / max(1, fw)
            touches_bottom = True

        if used_pose:
            # Pose-guided: chi coi la waist_up khi YOLO bao khong thay chan/goi
            if not is_pants_visible:
                is_waist_up = True
        else:
            # Fallback heuristic (logic cu):
            # 1. Vung quan trong hoac khong hop le
            # 2. Khung cat mep duoi frame va ti le khung < 1.95 (nua nguoi)
            # 3. Vung quan bi mau ao tran xuong
            if pants_region is None or pants_region.size == 0:
                is_waist_up = True
            elif touches_bottom and aspect_ratio < 1.95:
                is_waist_up = True
            elif pants_region is not None and pants_region.size > 0:
                p_hsv = cv2.cvtColor(pants_region, cv2.COLOR_BGR2HSV)
                if v_gain > 1.0:
                    v_ch = p_hsv[:, :, 2].astype(np.float32) * v_gain
                    p_hsv[:, :, 2] = np.clip(v_ch, 0, 255).astype(np.uint8)
                p_total = max(1, p_hsv.shape[0] * p_hsv.shape[1])

                pw_mask1 = cv2.inRange(p_hsv, np.array([0, 0, WHITE_V_MIN]), np.array([179, WHITE_S_MAX, 255]))
                pw_mask2 = cv2.inRange(p_hsv, np.array([0, 0, 115]), np.array([179, 35, WHITE_V_MIN]))
                pw_ratio = float(np.sum(cv2.bitwise_or(pw_mask1, pw_mask2) > 0)) / p_total

                pb_mask = cv2.inRange(p_hsv, np.array([BLUE_H_MIN, BLUE_S_MIN, BLUE_V_MIN]), np.array([BLUE_H_MAX, 255, 255]))
                pb_ratio = float(np.sum(pb_mask > 0)) / p_total

                if shirt_analysis["detected"] == "trang" and pw_ratio >= 0.25 and touches_bottom:
                    is_waist_up = True
                elif shirt_analysis["detected"] == "xanh_duong" and pb_ratio >= 0.25 and touches_bottom:
                    is_waist_up = True

        if is_waist_up:
            pants_analysis["color_desc"] = "khong_xac_dinh"
            pants_analysis["is_dark"] = False

        # Luu pose_zones vao debug (de hien thi trong draw_result)
        pants_analysis["_pose_zones"]  = pose_zones
        pants_analysis["_used_pose"]   = used_pose

        # Ap dung quy dinh theo ngay
        return self._apply_rule(weekday, shirt_analysis, pants_analysis, is_waist_up=is_waist_up)

    @staticmethod
    def _compute_lighting_gain(body_region: np.ndarray,
                                target_median_v: float = 135.0,
                                gain_min: float = 1.0,
                                gain_max: float = 1.5) -> float:
        """Tinh he so bu do sang chi khi anh bi thieu sang (median_v < 135).
        Tuyet doi khong giam do sang (gain >= 1.0) de tranh lam toi ao trang ngoai troi."""
        if body_region is None or body_region.size == 0:
            return 1.0
        hsv = cv2.cvtColor(body_region, cv2.COLOR_BGR2HSV)
        median_v = float(np.median(hsv[:, :, 2]))
        if median_v < 1 or median_v >= target_median_v:
            return 1.0
        gain = target_median_v / median_v
        return float(np.clip(gain, gain_min, gain_max))

    # ----------------------------------------------------------------
    # CAC HAM PHAN TICH MAU
    # ----------------------------------------------------------------
    def _analyze_shirt_region(self, region: np.ndarray, v_gain: float = 1.0) -> dict:
        """Phan tich mau ao: trang, xanh duong, hay khac voi co che phat hien mau xung dot."""
        if region is None or region.size == 0:
            return {"detected": "unknown", "white_ratio": 0.0,
                    "blue_ratio": 0.0, "conflict_ratio": 0.0, "dominant_hsv": (0, 0, 0)}

        hsv = cv2.cvtColor(region, cv2.COLOR_BGR2HSV)
        if v_gain > 1.0:
            v_ch = hsv[:, :, 2].astype(np.float32) * v_gain
            hsv[:, :, 2] = np.clip(v_ch, 0, 255).astype(np.uint8)
        total_pixels = max(1, hsv.shape[0] * hsv.shape[1])

        # --- Kiem tra MAU TRANG ---
        # 1. Trang tieu chuan: Saturation <= WHITE_S_MAX, Value >= WHITE_V_MIN
        white_mask1 = cv2.inRange(
            hsv,
            np.array([0,         0,           WHITE_V_MIN]),
            np.array([179,       WHITE_S_MAX, 255])
        )
        # 2. Trang trong bong ram / sang som: Saturation rat thap (<= 35), Value >= 115
        white_mask2 = cv2.inRange(
            hsv,
            np.array([0,         0,           115]),
            np.array([179,       35,          WHITE_V_MIN])
        )
        white_mask = cv2.bitwise_or(white_mask1, white_mask2)
        white_ratio = float(np.sum(white_mask > 0)) / total_pixels

        # --- Kiem tra MAU XANH DUONG (Ao Doan) ---
        blue_mask = cv2.inRange(
            hsv,
            np.array([BLUE_H_MIN, BLUE_S_MIN, BLUE_V_MIN]),
            np.array([BLUE_H_MAX, 255,        255])
        )
        blue_ratio = float(np.sum(blue_mask > 0)) / total_pixels

        # --- KIEM TRA MAU XUNG DOT (CONFLICT COLORS) ---
        # Mau sac dam: Saturation > 65 va Value > 50 (do, vang, cam, tim, xanh la...)
        # Hoac mau toi han: Value < 75 (den, xam dam, nau)
        conflict_mask1 = cv2.inRange(hsv, np.array([0, 65, 50]), np.array([179, 255, 255]))
        conflict_mask2 = cv2.inRange(hsv, np.array([0, 0, 0]), np.array([179, 255, 75]))
        conflict_mask = cv2.bitwise_or(conflict_mask1, conflict_mask2)
        conflict_ratio = float(np.sum(conflict_mask > 0)) / total_pixels

        # Mau trung binh de debug
        mean_hsv = cv2.mean(hsv)[:3]

        # Quyet dinh mau chinh voi do chinh xac cao:
        if white_ratio >= MIN_PIXEL_RATIO and conflict_ratio <= 0.35:
            detected = "trang"
        elif blue_ratio >= 0.28:
            detected = "xanh_duong"
        elif white_ratio >= 0.20:
            detected = "co_trang_1_phan"  # Co trang nhung khong du chuan dong phuc
        else:
            detected = "khac"

        return {
            "detected"      : detected,
            "white_ratio"   : round(white_ratio, 3),
            "blue_ratio"    : round(blue_ratio, 3),
            "conflict_ratio": round(conflict_ratio, 3),
            "dominant_hsv"  : tuple(int(x) for x in mean_hsv),
        }

    def _analyze_pants_darkness(self, region: np.ndarray) -> dict:
        """Kiem tra quan co toi mau khong (chong nhan nham quan sang mau)."""
        if region is None or region.size == 0:
            return {"is_dark": False, "dark_ratio": 0.0, "mean_value": 255, "color_desc": "khong ro"}

        hsv = cv2.cvtColor(region, cv2.COLOR_BGR2HSV)
        total_pixels = max(1, hsv.shape[0] * hsv.shape[1])

        # Toi mau 1: Den / Xam toi (Value <= DARK_V_MAX)
        dark_mask1 = cv2.inRange(
            hsv,
            np.array([0,   0,   0]),
            np.array([179, 255, DARK_V_MAX])
        )
        # Toi mau 2: Xanh den / tim than hoc sinh (Hue 100-140, Value <= 125)
        dark_mask2 = cv2.inRange(
            hsv,
            np.array([100, 35,  0]),
            np.array([140, 255, 125])
        )
        dark_mask = cv2.bitwise_or(dark_mask1, dark_mask2)
        dark_ratio  = float(np.sum(dark_mask > 0)) / total_pixels
        mean_value  = float(np.mean(hsv[:, :, 2]))  # Trung binh do sang

        # Phat hien quan sang mau (quan bo trang/kem/sang)
        bright_mask = cv2.inRange(hsv, np.array([0, 0, 145]), np.array([179, 80, 255]))
        bright_ratio = float(np.sum(bright_mask > 0)) / total_pixels

        # Quan dat chuan toi mau: dark_ratio >= DARK_RATIO_MIN va khong bi sang mau lan at
        is_dark = (dark_ratio >= DARK_RATIO_MIN) and (bright_ratio < 0.35)

        # Mo ta
        if dark_ratio >= 0.60:
            color_desc = "den/xanh den"
        elif is_dark:
            color_desc = "toi mau"
        elif bright_ratio >= 0.35 or mean_value > 165:
            color_desc = "sang mau"
        else:
            color_desc = "trung binh"

        return {
            "is_dark"     : is_dark,
            "dark_ratio"  : round(dark_ratio, 3),
            "bright_ratio": round(bright_ratio, 3),
            "mean_value"  : round(mean_value, 1),
            "color_desc"  : color_desc,
        }

    # ----------------------------------------------------------------
    # AP DUNG QUY DINH THEO NGAY TRONG TUAN
    # ----------------------------------------------------------------
    def _apply_rule(self, weekday: int,
                    shirt: dict, pants: dict,
                    is_waist_up: bool = False) -> ColorCheckResult:

        shirt_color = shirt["detected"]
        pants_desc  = pants["color_desc"]
        is_pants_dark = pants["is_dark"]

        debug = {
            "white_ratio"     : shirt["white_ratio"],
            "blue_ratio"      : shirt["blue_ratio"],
            "dark_pants_ratio": pants["dark_ratio"],
            "mean_pants_value": pants["mean_value"],
            "shirt_hsv_mean"  : shirt["dominant_hsv"],
            "is_waist_up"     : is_waist_up,
            "_pose_zones"     : pants.get("_pose_zones"),
            "_used_pose"      : pants.get("_used_pose", False),
        }

        # ----- THU 3 (weekday=1), THU 4 (weekday=2) va THU 5 (weekday=3): AO TRANG + QUAN DEN/TOI -----
        if weekday in (1, 2, 3):
            is_shirt_ok = shirt_color in ("trang",)
            is_pants_ok = is_pants_dark

            if is_shirt_ok and is_pants_ok:
                return ColorCheckResult(
                    status="OK", is_shirt_ok=True, is_pants_ok=True,
                    shirt_color="Trang", pants_color=pants_desc,
                    shirt_ratio=shirt["white_ratio"],
                    pants_dark_ratio=pants["dark_ratio"],
                    message=f"OK: Ao trang + quan den ({pants['dark_ratio']*100:.0f}% toi)",
                    debug_colors=debug
                )
            elif is_shirt_ok and is_waist_up:
                # Ao trang hop le nhung chua thay quan (chua xac dinh duoc quan do ngoai khung)
                return ColorCheckResult(
                    status="OK", is_shirt_ok=True, is_pants_ok=True,
                    shirt_color="Trang", pants_color="khong_xac_dinh",
                    shirt_ratio=shirt["white_ratio"],
                    pants_dark_ratio=pants["dark_ratio"],
                    message="OK: Ao trang (Quan: Khong xac dinh - ngoai khung)",
                    debug_colors=debug
                )
            elif not is_shirt_ok and is_waist_up:
                # Ao khong dung va chua xac dinh duoc quan -> Chi bao loi ao
                return ColorCheckResult(
                    status="FAIL", is_shirt_ok=False, is_pants_ok=True,
                    shirt_color=shirt_color, pants_color="khong_xac_dinh",
                    shirt_ratio=shirt["white_ratio"],
                    pants_dark_ratio=pants["dark_ratio"],
                    message=f"SAI AO: Can ao trang (phat hien: {shirt_color}) - Quan: Khong xac dinh",
                    debug_colors=debug
                )
            elif not is_shirt_ok and not is_pants_ok:
                return ColorCheckResult(
                    status="FAIL", is_shirt_ok=False, is_pants_ok=False,
                    shirt_color=shirt_color, pants_color=pants_desc,
                    shirt_ratio=shirt["white_ratio"],
                    pants_dark_ratio=pants["dark_ratio"],
                    message="SAI: Can ao trang + quan den/toi mau",
                    debug_colors=debug
                )
            elif not is_shirt_ok:
                return ColorCheckResult(
                    status="FAIL", is_shirt_ok=False, is_pants_ok=True,
                    shirt_color=shirt_color, pants_color=pants_desc,
                    shirt_ratio=shirt["white_ratio"],
                    pants_dark_ratio=pants["dark_ratio"],
                    message=f"SAI AO: Can ao trang (phat hien: {shirt_color})",
                    debug_colors=debug
                )
            else:  # quan sai
                return ColorCheckResult(
                    status="FAIL", is_shirt_ok=True, is_pants_ok=False,
                    shirt_color="Trang", pants_color=pants_desc,
                    shirt_ratio=shirt["white_ratio"],
                    pants_dark_ratio=pants["dark_ratio"],
                    message=f"SAI QUAN: Quan phai mau den/toi (hien tai: {pants_desc})",
                    debug_colors=debug
                )

        # ----- THU 6 (weekday=4): AO XANH DUONG (DOAN) + QUAN TOI -----
        elif weekday == 4:
            is_shirt_ok = shirt_color in ("xanh_duong",)
            is_pants_ok = is_pants_dark

            if is_shirt_ok and is_pants_ok:
                return ColorCheckResult(
                    status="OK", is_shirt_ok=True, is_pants_ok=True,
                    shirt_color="Xanh duong", pants_color=pants_desc,
                    shirt_ratio=shirt["blue_ratio"],
                    pants_dark_ratio=pants["dark_ratio"],
                    message=f"OK: Ao doan xanh + quan toi ({shirt['blue_ratio']*100:.0f}% xanh)",
                    debug_colors=debug
                )
            elif is_shirt_ok and is_waist_up:
                # Ao doan xanh dung, quan chua xac dinh do ngoai khung -> Pass OK
                return ColorCheckResult(
                    status="OK", is_shirt_ok=True, is_pants_ok=True,
                    shirt_color="Xanh duong", pants_color="khong_xac_dinh",
                    shirt_ratio=shirt["blue_ratio"],
                    pants_dark_ratio=pants["dark_ratio"],
                    message="OK: Ao doan xanh (Quan: Khong xac dinh - ngoai khung)",
                    debug_colors=debug
                )
            elif not is_shirt_ok and is_waist_up:
                # Ao doan chua dat va quan chua xac dinh -> Chi bao loi ao
                conf_pct = shirt["blue_ratio"] * 100
                return ColorCheckResult(
                    status="FAIL", is_shirt_ok=False, is_pants_ok=True,
                    shirt_color=shirt_color, pants_color="khong_xac_dinh",
                    shirt_ratio=shirt["blue_ratio"],
                    pants_dark_ratio=pants["dark_ratio"],
                    message=f"SAI AO: Can ao doan xanh (chi co {conf_pct:.0f}% xanh) - Quan: Khong xac dinh",
                    debug_colors=debug
                )
            elif not is_shirt_ok and not is_pants_ok:
                return ColorCheckResult(
                    status="FAIL", is_shirt_ok=False, is_pants_ok=False,
                    shirt_color=shirt_color, pants_color=pants_desc,
                    shirt_ratio=shirt["blue_ratio"],
                    pants_dark_ratio=pants["dark_ratio"],
                    message="SAI: Can ao doan xanh + quan toi mau",
                    debug_colors=debug
                )
            elif not is_shirt_ok:
                conf_pct = shirt["blue_ratio"] * 100
                return ColorCheckResult(
                    status="FAIL", is_shirt_ok=False, is_pants_ok=is_pants_dark,
                    shirt_color=shirt_color, pants_color=pants_desc,
                    shirt_ratio=shirt["blue_ratio"],
                    pants_dark_ratio=pants["dark_ratio"],
                    message=f"SAI AO: Can ao doan xanh duong (chi co {conf_pct:.0f}% xanh)",
                    debug_colors=debug
                )
            else:
                return ColorCheckResult(
                    status="FAIL", is_shirt_ok=True, is_pants_ok=False,
                    shirt_color="Xanh duong", pants_color=pants_desc,
                    shirt_ratio=shirt["blue_ratio"],
                    pants_dark_ratio=pants["dark_ratio"],
                    message=f"SAI QUAN: Quan phai toi mau (hien tai: {pants_desc})",
                    debug_colors=debug
                )

        # ----- CAC NGAY KHAC: SKIP -----
        else:
            day_names = {0: "Thu 2 (dan toc - AI xu ly)",
                         2: "Thu 4 (tu do co co)",
                         5: "Thu 7 (nghi)", 6: "CN (nghi)"}
            msg = day_names.get(weekday, "Khong yeu cau")
            return ColorCheckResult(
                status="SKIP", is_shirt_ok=True, is_pants_ok=True,
                shirt_color="N/A", pants_color="N/A",
                shirt_ratio=0.0, pants_dark_ratio=0.0,
                message=msg, debug_colors=debug
            )

    # ----------------------------------------------------------------
    # HO TRO CAT VUNG
    # ----------------------------------------------------------------
    @staticmethod
    def _crop_body(frame: np.ndarray,
                   body_box: Optional[Tuple]) -> np.ndarray:
        if body_box is None:
            return frame
        x, y, w, h = body_box
        x = max(0, x); y = max(0, y)
        return frame[y:y+h, x:x+w]

    @staticmethod
    def _get_zone(region: np.ndarray,
                  y_start_ratio: float,
                  y_end_ratio: float,
                  x_crop_margin: float = 0.18) -> np.ndarray:
        if region is None or region.size == 0:
            return region
        h, w = region.shape[:2]
        y0 = int(h * y_start_ratio)
        y1 = int(h * y_end_ratio)
        # Cat bo 18% vien 2 ben trai/phai de lay vung loi than nguoi (Torso Core),
        # loai bo hoan toan tay ao, quai ba lo va phong nen nhieu 2 ben
        x0 = int(w * x_crop_margin)
        x1 = max(x0 + 1, int(w * (1.0 - x_crop_margin)))
        cropped = region[y0:y1, x0:x1]
        return cropped if cropped.size > 0 else region[y0:y1, :]

    # ----------------------------------------------------------------
    # VE KET QUA LEN FRAME CAMERA (De tich hop vao main.py)
    # ----------------------------------------------------------------
    def draw_result(self, frame: np.ndarray,
                    result: ColorCheckResult,
                    body_box: Optional[Tuple] = None,
                    position: Tuple = (10, 90)) -> np.ndarray:
        """
        Ve ket qua phan tich mau len frame.
        Goi sau khi da ve ket qua TFLite (uniform_checker.draw_result).
        """
        COLOR_MAP = {
            "OK"     : (0, 200, 50),
            "FAIL"   : (0, 50, 220),
            "SKIP"   : (180, 120, 0),
            "UNCLEAR": (0, 165, 255),
        }
        color = COLOR_MAP.get(result.status, (200, 200, 200))
        x, y  = position

        # Ve duong phan vung ao/quan de debug (neu co body_box)
        if body_box is not None:
            bx, by, bw, bh = body_box

            # Lay zones thuc su duoc dung (pose hoac fallback)
            pose_zones = result.debug_colors.get("_pose_zones") if hasattr(result, "debug_colors") else None
            used_pose  = result.debug_colors.get("_used_pose", False) if hasattr(result, "debug_colors") else False

            if used_pose and pose_zones is not None:
                s_top, s_bot = pose_zones["shirt_zone"]
                p_top, p_bot = pose_zones["pants_zone"]
                shirt_lbl = "Ao[P]"
                pants_lbl = "Quan[P]" if pose_zones.get("is_pants_visible") else "Quan[est]"
                s_col = (0, 230, 80)    # xanh la tuoi (pose)
                p_col = (0, 140, 255)   # cam (pose)
            else:
                s_top, s_bot = self.SHIRT_ZONE
                p_top, p_bot = self.PANTS_ZONE
                shirt_lbl = "Ao"
                pants_lbl = "Quan"
                s_col = (0, 200, 100)   # xanh la nhat (fallback)
                p_col = (200, 100, 0)   # xanh duong nhat (fallback)

            shirt_y0 = by + int(bh * s_top)
            shirt_y1 = by + int(bh * s_bot)
            cv2.rectangle(frame, (bx, shirt_y0), (bx + bw, shirt_y1), s_col, 1)
            cv2.putText(frame, shirt_lbl, (bx + 5, shirt_y0 + 15),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.40, s_col, 1)

            pants_y0 = by + int(bh * p_top)
            pants_y1 = by + int(bh * p_bot)
            cv2.rectangle(frame, (bx, pants_y0), (bx + bw, pants_y1), p_col, 1)
            cv2.putText(frame, pants_lbl, (bx + 5, pants_y0 + 15),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.40, p_col, 1)

        # Nen mo cho text
        overlay = frame.copy()
        cv2.rectangle(overlay, (x, y - 5), (x + 440, y + 80),
                      (20, 20, 20), -1)
        cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)

        # Dong chu ket qua chinh
        cv2.putText(frame, f"[Mau sac] {result.message}",
                    (x, y + 18), cv2.FONT_HERSHEY_SIMPLEX, 0.58, color, 2)

        # Dong chi tiet ao
        shirt_pct = result.shirt_ratio * 100
        shirt_icon = "V" if result.is_shirt_ok else "X"
        cv2.putText(frame,
                    f"  Ao: {result.shirt_color} ({shirt_pct:.0f}%) [{shirt_icon}]",
                    (x, y + 44), cv2.FONT_HERSHEY_SIMPLEX, 0.48,
                    (0, 220, 60) if result.is_shirt_ok else (0, 80, 220), 1)

        # Dong chi tiet quan
        if result.pants_color in ("khong_xac_dinh", "chua_ro_ngoai_khung"):
            cv2.putText(frame,
                        "  Quan: Khong xac dinh (ngoai khung) [?]",
                        (x, y + 66), cv2.FONT_HERSHEY_SIMPLEX, 0.48,
                        (0, 215, 255), 1)
        else:
            pants_pct = result.pants_dark_ratio * 100
            pants_icon = "V" if result.is_pants_ok else "X"
            cv2.putText(frame,
                        f"  Quan: {result.pants_color} (toi: {pants_pct:.0f}%) [{pants_icon}]",
                        (x, y + 66), cv2.FONT_HERSHEY_SIMPLEX, 0.48,
                        (0, 220, 60) if result.is_pants_ok else (0, 80, 220), 1)

        return frame


# ==============================================================
# TEST TRUC TIEP - CHAY: python uniform_color_analyzer.py
# ==============================================================
def run_live_debug():
    """Test phan tich mau sac realtime voi thanh debug HSV."""
    import sys

    analyzer = UniformColorAnalyzer()
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("[ERROR] Khong mo duoc camera!")
        return

    # Cho phep chon ngay de test
    print("\nChon ngay de test (mac dinh = hom nay):")
    print("  0=Thu2  1=Thu3  2=Thu4  3=Thu5  4=Thu6  5=Thu7  6=CN")
    inp = input("Nhap so (Enter de dung ngay hom nay): ").strip()
    if inp.isdigit():
        forced_weekday = int(inp)
    else:
        forced_weekday = None

    day_names = ["Thu 2", "Thu 3", "Thu 4", "Thu 5", "Thu 6", "Thu 7", "CN"]
    wday = forced_weekday if forced_weekday is not None else datetime.now().weekday()
    print(f"[INFO] Dang test ngay: {day_names[wday]} | Nhan Q de thoat\n")

    show_debug = False  # Nhan D de bat/tat debug mask

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frame = cv2.flip(frame, 1)

        result = analyzer.check(frame, weekday=forced_weekday)
        frame  = analyzer.draw_result(frame, result)

        # Debug mask (bat/tat bang phim D)
        if show_debug:
            h_frame, w_frame = frame.shape[:2]
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

            white_mask = cv2.inRange(hsv,
                np.array([0,   0,         WHITE_V_MIN]),
                np.array([179, WHITE_S_MAX, 255]))
            blue_mask = cv2.inRange(hsv,
                np.array([BLUE_H_MIN, BLUE_S_MIN, BLUE_V_MIN]),
                np.array([BLUE_H_MAX, 255, 255]))
            dark_mask = cv2.inRange(hsv,
                np.array([0, 0, 0]),
                np.array([179, 255, DARK_V_MAX]))

            # Hien thi mask nho goc phai
            thumb_w = 150
            for i, (mask, label, color) in enumerate([
                (white_mask, "Trang", (220, 220, 220)),
                (blue_mask,  "Xanh",  (220, 100, 0)),
                (dark_mask,  "Toi",   (60,  60,  60)),
            ]):
                mask_rgb = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
                resized  = cv2.resize(mask_rgb, (thumb_w, thumb_w))
                x_off    = w_frame - thumb_w - 10
                y_off    = 10 + i * (thumb_w + 5)
                frame[y_off:y_off+thumb_w, x_off:x_off+thumb_w] = resized
                cv2.putText(frame, label, (x_off, y_off - 3),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1)

        # Huong dan phim
        cv2.putText(frame, "D=debug  Q=thoat",
                    (10, frame.shape[0] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (150, 150, 150), 1)

        # Thong tin debug raw
        d = result.debug_colors
        cv2.putText(frame,
                    f"HSV ao: {d['shirt_hsv_mean']} | "
                    f"W:{d['white_ratio']:.2f} B:{d['blue_ratio']:.2f} "
                    f"Dk:{d['dark_pants_ratio']:.2f}",
                    (10, frame.shape[0] - 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (120, 120, 120), 1)

        cv2.imshow("Kiem tra mau sac trang phuc - Debug", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
        elif key == ord("d"):
            show_debug = not show_debug
            print(f"[DEBUG] Hien thi mask: {'BAT' if show_debug else 'TAT'}")

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    import sys
    if "--image" in sys.argv:
        idx = sys.argv.index("--image")
        img_path = sys.argv[idx + 1]
        frame = cv2.imread(img_path)
        if frame is None:
            print(f"[ERROR] Khong doc duoc anh: {img_path}")
            sys.exit(1)

        inp = input("Nhap so thu (0=T2, 1=T3, 2=T4, 3=T5, 4=T6): ").strip()
        wday = int(inp) if inp.isdigit() else None

        analyzer = UniformColorAnalyzer()
        result = analyzer.check(frame, weekday=wday)

        print("\n===== KET QUA PHAN TICH MAU SAC =====")
        print(f"  Trang thai     : {result.status}")
        print(f"  Ao             : {result.shirt_color} ({result.shirt_ratio*100:.1f}%)")
        print(f"  Quan           : {result.pants_color} (toi: {result.pants_dark_ratio*100:.1f}%)")
        print(f"  Ao dung quy dinh: {'Co' if result.is_shirt_ok else 'Khong'}")
        print(f"  Quan toi mau   : {'Co' if result.is_pants_ok else 'Khong'}")
        print(f"  Thong bao      : {result.message}")
        print(f"  Debug          : {result.debug_colors}")

        frame = analyzer.draw_result(frame, result)
        cv2.imshow("Ket qua phan tich mau", frame)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    else:
        run_live_debug()
