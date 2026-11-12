# -*- coding: utf-8 -*-
"""
=============================================================
  BƯỚC 1C — CALIBRATE NGƯỠNG MÀU HSV REALTIME
  step1_hsv_calibrator.py

  Tool GUI tương tác để chỉnh ngưỡng HSV cho camera thực tế:
  - Hiển thị mask màu trắng (Thứ 3, 5: áo trắng)
  - Hiển thị mask màu xanh dương (Thứ 6: áo đoàn)
  - Hiển thị mask tối màu (quần tối)
  - Lưu ngưỡng đã calibrate vào JSON để uniform_color_analyzer.py đọc

  Tại sao cần calibrate?
  ─────────────────────────────────────────────────────────────────────
  Ngưỡng HSV mặc định trong code là ước tính lý thuyết.
  Thực tế, ánh sáng phòng học (đèn huỳnh quang, neon, ánh mặt trời)
  ảnh hưởng đáng kể đến màu sắc phát hiện được.
  Calibration giúp điều chỉnh ngưỡng phù hợp với điều kiện thực tế.

  Cách dùng:
  1. Mặc áo trắng / áo đoàn / quần tối đứng trước camera
  2. Chỉnh slider đến khi mask highlight đúng vùng áo/quần
  3. Nhấn 'S' để lưu | 'Q' để thoát | 'R' để reset về default

  Phím tắt:
    1 = Chế độ Trắng (Thứ 3, 5)
    2 = Chế độ Xanh Dương (Thứ 6)
    3 = Chế độ Tối (Quần)
    D = Debug: hiện giá trị HSV tại điểm con trỏ
    S = Lưu cấu hình
    R = Reset về default
    Q = Thoát
=============================================================
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import cv2
import numpy as np
import json
from pathlib import Path
from datetime import datetime

# ──────────────────────────────────────────────────────────────────────
# CẤU HÌNH
# ──────────────────────────────────────────────────────────────────────
BASE_DIR        = Path(__file__).parent
CONFIG_OUTPUT   = BASE_DIR.parent / "data" / "hsv_config.json"

# Ngưỡng mặc định (đồng bộ với uniform_color_analyzer.py)
DEFAULTS = {
    "white": {
        "s_max": 70,    # Saturation tối đa — trắng: S thấp
        "v_min": 145,   # Value tối thiểu — trắng: V cao
    },
    "blue": {
        "h_min": 95,    # Hue bắt đầu — xanh dương Đoàn
        "h_max": 135,
        "s_min": 55,    # Saturation tối thiểu — đủ bão hòa
        "v_min": 40,    # Không quá tối
    },
    "dark_pants": {
        "v_max": 115,           # Value tối đa — tối màu
        "ratio_min": 0.38,      # Tỷ lệ pixels tối tối thiểu
    }
}

WINDOW_MAIN    = "HSV Calibrator - Nhan phim de dieu chinh"
WINDOW_MASK    = "Mask Preview (trang/xanh/toi)"
WINDOW_TRACKBAR= "Trackbar Controls"

# Màu overlay
COLOR_WHITE_OVERLAY = (200, 200, 255)   # BGR: trắng tím nhạt
COLOR_BLUE_OVERLAY  = (255, 150, 0)     # BGR: xanh dương
COLOR_DARK_OVERLAY  = (0, 50, 200)      # BGR: đỏ tối


# ──────────────────────────────────────────────────────────────────────
# CALIBRATOR
# ──────────────────────────────────────────────────────────────────────
class HSVCalibrator:
    """
    Tool calibrate ngưỡng HSV qua camera realtime.
    Dùng OpenCV Trackbar để chỉnh ngưỡng trực quan.
    """

    MODES = {
        1: "Trang (Thu 3, 5)",
        2: "Xanh Duong (Thu 6)",
        3: "Toi Mau (Quan)",
    }

    def __init__(self):
        self.cfg     = {k: dict(v) for k, v in DEFAULTS.items()}  # Deep copy
        self.mode    = 1      # Bắt đầu ở chế độ White
        self.debug   = False
        self.mouse_pos = (0, 0)
        self.mouse_hsv = (0, 0, 0)
        self._trackbars_created = False

    def run(self, camera_idx: int = 0):
        """Vòng lặp chính."""
        cap = cv2.VideoCapture(camera_idx)
        if not cap.isOpened():
            print(f"[ERROR] Không mở được camera (index {camera_idx})!")
            print("       Thử chạy với: python step1_hsv_calibrator.py --camera 1")
            return

        # Tối ưu camera cho calibration
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_FPS, 30)

        print("=" * 60)
        print("  HSV CALIBRATOR — ĐÃ MỞ CAMERA")
        print("=" * 60)
        print(f"  Phím: 1=Trắng  2=Xanh  3=Tối | D=Debug | S=Lưu | R=Reset | Q=Thoát")
        print(f"  Config sẽ lưu tại: {CONFIG_OUTPUT}")
        print("=" * 60)

        # Tạo cửa sổ trackbar
        cv2.namedWindow(WINDOW_TRACKBAR, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(WINDOW_TRACKBAR, 450, 300)
        self._create_trackbars_for_mode()

        # Mouse callback để hiện giá trị HSV
        cv2.namedWindow(WINDOW_MAIN)
        cv2.setMouseCallback(WINDOW_MAIN, self._mouse_callback)

        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frame = cv2.flip(frame, 1)

            # Đọc giá trị từ trackbar
            self._read_trackbars()

            # Tính mask theo mode hiện tại
            hsv  = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            mask = self._compute_mask(hsv, self.mode)

            # Tạo ảnh overlay: tô màu vùng được phát hiện
            overlay = frame.copy()
            colors  = {1: COLOR_WHITE_OVERLAY, 2: COLOR_BLUE_OVERLAY, 3: COLOR_DARK_OVERLAY}
            overlay[mask > 0] = colors[self.mode]
            result = cv2.addWeighted(frame, 0.5, overlay, 0.5, 0)

            # Vẽ chia vùng áo/quần
            h_f, w_f = result.shape[:2]
            y_shirt_top = int(h_f * 0.12)
            y_shirt_bot = int(h_f * 0.52)
            y_pants_top = int(h_f * 0.52)
            y_pants_bot = int(h_f * 0.90)

            cv2.rectangle(result, (0, y_shirt_top), (w_f - 1, y_shirt_bot),
                          (0, 200, 100), 1)
            cv2.putText(result, "Vung Ao", (5, y_shirt_top + 18),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 200, 100), 1)
            cv2.rectangle(result, (0, y_pants_top), (w_f - 1, y_pants_bot),
                          (200, 100, 0), 1)
            cv2.putText(result, "Vung Quan", (5, y_pants_top + 18),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 100, 0), 1)

            # Thống kê tỷ lệ mask
            total_px   = mask.shape[0] * mask.shape[1]
            shirt_zone = mask[y_shirt_top:y_shirt_bot, :]
            pants_zone = mask[y_pants_top:y_pants_bot, :]
            shirt_ratio = np.sum(shirt_zone > 0) / max(shirt_zone.size, 1)
            pants_ratio = np.sum(pants_zone > 0) / max(pants_zone.size, 1)
            total_ratio = np.sum(mask > 0) / max(total_px, 1)

            # HUD — thông tin trạng thái
            mode_name = self.MODES[self.mode]
            self._draw_hud(result, mode_name, shirt_ratio, pants_ratio, total_ratio)

            # Debug: HSV tại điểm con trỏ
            if self.debug:
                mx, my = self.mouse_pos
                if 0 <= my < hsv.shape[0] and 0 <= mx < hsv.shape[1]:
                    self.mouse_hsv = tuple(int(x) for x in hsv[my, mx])
                cv2.putText(result,
                            f"HSV tai con tro: H={self.mouse_hsv[0]} S={self.mouse_hsv[1]} V={self.mouse_hsv[2]}",
                            (10, result.shape[0] - 35),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

            # Hiển thị mask nhỏ góc phải
            mask_small = cv2.resize(cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR),
                                    (160, 120))
            result[10:130, result.shape[1] - 170:result.shape[1] - 10] = mask_small
            cv2.putText(result, "Mask Preview",
                        (result.shape[1] - 168, 145),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (180, 180, 180), 1)

            cv2.imshow(WINDOW_MAIN, result)

            # Xử lý phím
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
            elif key in (ord("1"), ord("2"), ord("3")):
                new_mode = int(chr(key))
                if new_mode != self.mode:
                    self.mode = new_mode
                    cv2.destroyWindow(WINDOW_TRACKBAR)
                    cv2.namedWindow(WINDOW_TRACKBAR, cv2.WINDOW_NORMAL)
                    cv2.resizeWindow(WINDOW_TRACKBAR, 450, 300)
                    self._create_trackbars_for_mode()
                    print(f"[MODE] Chuyển sang: {self.MODES[self.mode]}")
            elif key == ord("d"):
                self.debug = not self.debug
                print(f"[DEBUG] {'BẬT' if self.debug else 'TẮT'} — Di chuyển chuột lên camera để xem HSV")
            elif key == ord("s"):
                self._save_config()
            elif key == ord("r"):
                self._reset_defaults()
                print("[RESET] Đã reset về giá trị mặc định.")

        cap.release()
        cv2.destroyAllWindows()
        print("[DONE] Calibrator đã đóng.")

    # ──────────────────────────────────────────────────────────────────
    # TRACKBAR
    # ──────────────────────────────────────────────────────────────────
    def _create_trackbars_for_mode(self):
        """Tạo trackbar phù hợp với chế độ hiện tại."""
        def nothing(x): pass

        if self.mode == 1:  # Trắng
            cv2.createTrackbar("S_max (trang)", WINDOW_TRACKBAR, self.cfg["white"]["s_max"], 255, nothing)
            cv2.createTrackbar("V_min (trang)", WINDOW_TRACKBAR, self.cfg["white"]["v_min"], 255, nothing)

        elif self.mode == 2:  # Xanh dương
            cv2.createTrackbar("H_min (xanh)", WINDOW_TRACKBAR, self.cfg["blue"]["h_min"], 179, nothing)
            cv2.createTrackbar("H_max (xanh)", WINDOW_TRACKBAR, self.cfg["blue"]["h_max"], 179, nothing)
            cv2.createTrackbar("S_min (xanh)", WINDOW_TRACKBAR, self.cfg["blue"]["s_min"], 255, nothing)
            cv2.createTrackbar("V_min (xanh)", WINDOW_TRACKBAR, self.cfg["blue"]["v_min"], 255, nothing)

        elif self.mode == 3:  # Tối
            cv2.createTrackbar("V_max (toi)", WINDOW_TRACKBAR, self.cfg["dark_pants"]["v_max"], 255, nothing)

        self._trackbars_created = True

    def _read_trackbars(self):
        """Đọc giá trị hiện tại từ trackbar vào cfg."""
        try:
            if self.mode == 1:
                self.cfg["white"]["s_max"] = cv2.getTrackbarPos("S_max (trang)", WINDOW_TRACKBAR)
                self.cfg["white"]["v_min"] = cv2.getTrackbarPos("V_min (trang)", WINDOW_TRACKBAR)
            elif self.mode == 2:
                self.cfg["blue"]["h_min"] = cv2.getTrackbarPos("H_min (xanh)", WINDOW_TRACKBAR)
                self.cfg["blue"]["h_max"] = cv2.getTrackbarPos("H_max (xanh)", WINDOW_TRACKBAR)
                self.cfg["blue"]["s_min"] = cv2.getTrackbarPos("S_min (xanh)", WINDOW_TRACKBAR)
                self.cfg["blue"]["v_min"] = cv2.getTrackbarPos("V_min (xanh)", WINDOW_TRACKBAR)
            elif self.mode == 3:
                self.cfg["dark_pants"]["v_max"] = cv2.getTrackbarPos("V_max (toi)", WINDOW_TRACKBAR)
        except cv2.error:
            pass

    # ──────────────────────────────────────────────────────────────────
    # TÍNH MASK
    # ──────────────────────────────────────────────────────────────────
    def _compute_mask(self, hsv: np.ndarray, mode: int) -> np.ndarray:
        """Tính mask nhị phân theo chế độ và ngưỡng hiện tại."""
        if mode == 1:  # Trắng
            return cv2.inRange(
                hsv,
                np.array([0,   0,                        self.cfg["white"]["v_min"]]),
                np.array([179, self.cfg["white"]["s_max"], 255])
            )
        elif mode == 2:  # Xanh dương
            return cv2.inRange(
                hsv,
                np.array([self.cfg["blue"]["h_min"], self.cfg["blue"]["s_min"], self.cfg["blue"]["v_min"]]),
                np.array([self.cfg["blue"]["h_max"], 255,                       255])
            )
        elif mode == 3:  # Tối
            return cv2.inRange(
                hsv,
                np.array([0, 0, 0]),
                np.array([179, 255, self.cfg["dark_pants"]["v_max"]])
            )
        return np.zeros(hsv.shape[:2], dtype=np.uint8)

    # ──────────────────────────────────────────────────────────────────
    # VẼ HUD
    # ──────────────────────────────────────────────────────────────────
    def _draw_hud(self, frame, mode_name, shirt_r, pants_r, total_r):
        h, w = frame.shape[:2]

        # Nền mờ cho HUD
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, h - 70), (w, h), (20, 20, 20), -1)
        cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)

        # Mode
        cv2.putText(frame, f"CHE DO: {mode_name}",
                    (10, h - 50), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

        # Tỷ lệ
        shirt_color = (0, 220, 60) if shirt_r > 0.3 else (0, 80, 220)
        pants_color = (0, 220, 60) if pants_r > 0.45 else (0, 80, 220)

        cv2.putText(frame,
                    f"Ao: {shirt_r * 100:.0f}%  Quan: {pants_r * 100:.0f}%  Tong: {total_r * 100:.0f}%",
                    (10, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                    (180, 180, 180), 1)

        # Ngưỡng hiện tại
        cfg_text = ""
        if self.mode == 1:
            cfg_text = f"S_max={self.cfg['white']['s_max']}  V_min={self.cfg['white']['v_min']}"
        elif self.mode == 2:
            b = self.cfg["blue"]
            cfg_text = f"H=[{b['h_min']},{b['h_max']}]  S_min={b['s_min']}  V_min={b['v_min']}"
        elif self.mode == 3:
            cfg_text = f"V_max={self.cfg['dark_pants']['v_max']}"

        cv2.putText(frame, cfg_text,
                    (10, h - 75), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 0), 1)

        # Hướng dẫn phím
        guide = "1=Trang | 2=Xanh | 3=Toi | S=Luu | R=Reset | Q=Thoat"
        cv2.putText(frame, guide,
                    (10, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (180, 180, 180), 1)

    # ──────────────────────────────────────────────────────────────────
    # LƯU / LOAD CONFIG
    # ──────────────────────────────────────────────────────────────────
    def _save_config(self):
        """Lưu ngưỡng đã calibrate vào JSON."""
        CONFIG_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        output = {
            "calibrated_at": datetime.now().isoformat(),
            "description"  : "Ngưỡng HSV đã calibrate theo camera thực tế",
            "white": {
                "s_max"    : self.cfg["white"]["s_max"],
                "v_min"    : self.cfg["white"]["v_min"],
            },
            "blue": {
                "h_min"    : self.cfg["blue"]["h_min"],
                "h_max"    : self.cfg["blue"]["h_max"],
                "s_min"    : self.cfg["blue"]["s_min"],
                "v_min"    : self.cfg["blue"]["v_min"],
            },
            "dark_pants": {
                "v_max"    : self.cfg["dark_pants"]["v_max"],
                "ratio_min": self.cfg["dark_pants"]["ratio_min"],
            },
        }
        with open(CONFIG_OUTPUT, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        print(f"\n[SAVED] Cấu hình HSV đã lưu:")
        print(f"        {CONFIG_OUTPUT}")
        print(f"  White : S_max={output['white']['s_max']}  V_min={output['white']['v_min']}")
        print(f"  Blue  : H=[{output['blue']['h_min']},{output['blue']['h_max']}]  "
              f"S_min={output['blue']['s_min']}  V_min={output['blue']['v_min']}")
        print(f"  Dark  : V_max={output['dark_pants']['v_max']}")
        print(f"\n  → uniform_color_analyzer.py sẽ tự động load file này!")

    def _reset_defaults(self):
        """Reset về giá trị mặc định."""
        self.cfg = {k: dict(v) for k, v in DEFAULTS.items()}
        cv2.destroyWindow(WINDOW_TRACKBAR)
        cv2.namedWindow(WINDOW_TRACKBAR, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(WINDOW_TRACKBAR, 450, 300)
        self._create_trackbars_for_mode()

    def _mouse_callback(self, event, x, y, flags, param):
        """Ghi lại vị trí chuột để hiện HSV tại điểm đó."""
        self.mouse_pos = (x, y)


# ──────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Calibrate ngưỡng HSV cho camera thực tế")
    parser.add_argument("--camera", type=int, default=0,
                        help="Index camera (default: 0)")
    args = parser.parse_args()

    calibrator = HSVCalibrator()
    calibrator.run(camera_idx=args.camera)
