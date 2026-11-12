# -*- coding: utf-8 -*-
"""
=============================================================
  MODULE POSE ESTIMATION (YOLOv8-Pose)
  pose_estimator.py

  Dung YOLOv8-Pose de xac dinh chinh xac vi tri:
    - Hip (khop hang): keypoint 11 & 12
    - Knee (dau goi):  keypoint 13 & 14
    - Ankle (co chan): keypoint 15 & 16
    - Shoulder:        keypoint 5 & 6

  Tu do tinh chinh xac vung ao (shirt) va vung quan (pants)
  trong body_box theo toa do khop xuong thay vi ty le co dinh.

  Fallback: neu khong phat hien duoc pose, tra ve None
  -> uniform_color_analyzer.py se dung ti le co dinh (0.15-0.55 / 0.55-0.90).

  COCO Keypoint Order (17 diem):
    0: Nose        1: Left Eye     2: Right Eye
    3: Left Ear    4: Right Ear    5: Left Shoulder
    6: Right Shoulder              7: Left Elbow
    8: Right Elbow 9: Left Wrist   10: Right Wrist
   11: Left Hip   12: Right Hip   13: Left Knee
   14: Right Knee 15: Left Ankle  16: Right Ankle
=============================================================
"""

import os
import cv2
import numpy as np
from pathlib import Path
from typing import Optional, Tuple, Dict

# ===================== KHAI BAO DUONG DAN MODEL =====================
_EDGE_DIR = Path(__file__).parent
_MODEL_CANDIDATES = [
    _EDGE_DIR / "assets" / "models" / "yolov8n-pose.pt",
    _EDGE_DIR / "data" / "yolov8n-pose.pt",
    _EDGE_DIR / "yolov8n-pose.pt",
]

# ===================== KEYPOINT INDICES (COCO) =====================
KP_LEFT_SHOULDER  = 5
KP_RIGHT_SHOULDER = 6
KP_LEFT_HIP       = 11
KP_RIGHT_HIP      = 12
KP_LEFT_KNEE      = 13
KP_RIGHT_KNEE     = 14
KP_LEFT_ANKLE     = 15
KP_RIGHT_ANKLE    = 16

# Nguong do tin cay keypoint (0 = off, 1 = full confidence trong YOLO)
KP_CONF_THRESHOLD = 0.25

# Fallback zones (dung khi pose khong kha dung)
FALLBACK_SHIRT_ZONE  = (0.15, 0.55)
FALLBACK_PANTS_ZONE  = (0.55, 0.90)


class PoseEstimator:
    """
    Wrapper YOLOv8-Pose de trich xuat vung ao/quan chinh xac.

    Usage:
        pe = PoseEstimator()
        zones = pe.get_body_zones(frame, body_box=(x, y, w, h))
        if zones:
            shirt_top, shirt_bot = zones["shirt_zone"]
            pants_top, pants_bot = zones["pants_zone"]
            is_pants_visible = zones["is_pants_visible"]
    """

    def __init__(self, model_path: Optional[str] = None):
        self._model = None
        self._available = False
        self._load_model(model_path)

    def _load_model(self, model_path: Optional[str] = None):
        """Tai YOLOv8-Pose model. Tu dong download neu chua co."""
        try:
            from ultralytics import YOLO
        except ImportError:
            print("[PoseEstimator] WARN: 'ultralytics' chua duoc cai. "
                  "Chay: pip install ultralytics")
            return

        # Tim model file
        if model_path and Path(model_path).exists():
            pt_path = Path(model_path)
        else:
            pt_path = next((p for p in _MODEL_CANDIDATES if p.exists()), None)

        if pt_path is None:
            # Tu dong download yolov8n-pose.pt vao edge/data/
            default_save = _EDGE_DIR / "data" / "yolov8n-pose.pt"
            default_save.parent.mkdir(parents=True, exist_ok=True)
            print("[PoseEstimator] Dang download yolov8n-pose.pt (lan dau)...")
            try:
                m = YOLO("yolov8n-pose.pt")          # download tu Ultralytics hub
                import shutil
                # YOLO luu model tai thu muc hien tai hoac ~/.cache
                downloaded = Path("yolov8n-pose.pt")
                if downloaded.exists():
                    shutil.move(str(downloaded), str(default_save))
                    pt_path = default_save
                else:
                    # Da duoc luu vao cache, su dung truc tiep
                    self._model = m
                    self._available = True
                    print("[PoseEstimator] OK: yolov8n-pose tai tu cache thanh cong.")
                    return
            except Exception as e:
                print(f"[PoseEstimator] WARN: Khong tai duoc model ({e}). "
                      "Se dung fallback zone co dinh.")
                return

        try:
            self._model = YOLO(str(pt_path))
            self._available = True
            print(f"[PoseEstimator] OK: Da tai model tu {pt_path}")
        except Exception as e:
            print(f"[PoseEstimator] WARN: Loi tai model ({e})")

    @property
    def available(self) -> bool:
        return self._available

    def get_body_zones(
        self,
        frame: np.ndarray,
        body_box: Optional[Tuple[int, int, int, int]] = None,
    ) -> Optional[Dict]:
        """
        Phan tich pose trong vung body_box va tra ve vung ao/quan.

        Args:
            frame    : Anh BGR day du tu camera
            body_box : (x, y, w, h) vung than nguoi trong frame.
                       None = dung toan bo frame.

        Returns:
            None neu khong detect duoc (dung fallback).
            dict:
                "shirt_zone"       : (y_top_ratio, y_bot_ratio) trong body_box
                "pants_zone"       : (y_top_ratio, y_bot_ratio) trong body_box
                "is_pants_visible" : bool - co nhin thay khop goi khong
                "hip_y_ratio"      : float - vi tri khop hang / chieu cao body_box
                "knee_y_ratio"     : float - vi tri dau goi / chieu cao body_box
                "ankle_y_ratio"    : float - vi tri co chan / chieu cao body_box
                "keypoints_raw"    : array (17, 3) - (x, y, conf) tuong doi frame
        """
        if not self._available or self._model is None:
            return None

        # Cat vung body_box tu frame (de tang toc, YOLO chi xu ly vung nho hon)
        if body_box is not None:
            bx, by, bw, bh = body_box
            bx = max(0, bx); by = max(0, by)
            fh, fw = frame.shape[:2]
            bx2 = min(fw, bx + bw)
            by2 = min(fh, by + bh)
            crop = frame[by:by2, bx:bx2]
            if crop.size == 0:
                return None
        else:
            crop = frame
            bx, by, bw, bh = 0, 0, frame.shape[1], frame.shape[0]

        try:
            results = self._model(
                crop,
                verbose=False,
                conf=0.25,        # person detection confidence
                iou=0.45,
                quantize=False,   # FP32 de on dinh hon tren CPU
                max_det=5,        # Toi da 5 nguoi trong 1 crop
            )
        except Exception as e:
            print(f"[PoseEstimator] WARN: Loi inference ({e})")
            return None

        if not results or len(results) == 0:
            return None

        result = results[0]
        if result.keypoints is None or result.keypoints.data is None:
            return None

        kps_data = result.keypoints.data  # Tensor shape (N, 17, 3): x, y, conf

        # Chon nguoi co dien tich bbox lon nhat (nguoi chinh trong khung)
        if result.boxes is not None and len(result.boxes) > 1:
            boxes   = result.boxes.xyxy.cpu().numpy()     # (N, 4)
            areas   = (boxes[:, 2] - boxes[:, 0]) * (boxes[:, 3] - boxes[:, 1])
            best_i  = int(np.argmax(areas))
            kps     = kps_data[best_i].cpu().numpy()      # (17, 3)
        else:
            if len(kps_data) == 0:
                return None
            kps = kps_data[0].cpu().numpy()               # (17, 3)

        # kps: (17, 3) -> col0=x_in_crop, col1=y_in_crop, col2=conf
        ch, cw = crop.shape[:2]

        def _get_y_ratio(kp_indices):
            """Lay y trung binh cua cac keypoint co confidence du cao."""
            valid_ys = []
            for ki in kp_indices:
                conf = float(kps[ki, 2])
                if conf >= KP_CONF_THRESHOLD:
                    y_pixel = float(kps[ki, 1])
                    valid_ys.append(y_pixel / max(1, ch))  # thanh ratio trong crop=body_box
            return float(np.mean(valid_ys)) if valid_ys else None

        hip_y    = _get_y_ratio([KP_LEFT_HIP, KP_RIGHT_HIP])
        knee_y   = _get_y_ratio([KP_LEFT_KNEE, KP_RIGHT_KNEE])
        ankle_y  = _get_y_ratio([KP_LEFT_ANKLE, KP_RIGHT_ANKLE])
        shoulder_y = _get_y_ratio([KP_LEFT_SHOULDER, KP_RIGHT_SHOULDER])

        # Kiem tra du lieu
        if hip_y is None:
            # Khong co hip -> khong xac dinh duoc ranh gioi ao/quan
            return None

        # ---- Tinh vung ao (shirt zone) ----
        # Top: tu 5% ben duoi shoulder (hoac 12% neu ko co shoulder)
        if shoulder_y is not None and shoulder_y > 0.05:
            shirt_top = min(shoulder_y + 0.05, hip_y - 0.05)
        else:
            shirt_top = 0.12  # fallback

        shirt_bot = hip_y  # Ranh gioi: khop hang

        # Gioi han hop le
        shirt_top = float(np.clip(shirt_top, 0.05, 0.60))
        shirt_bot = float(np.clip(shirt_bot, shirt_top + 0.05, 0.75))

        # ---- Tinh vung quan (pants zone) ----
        pants_top = hip_y

        if ankle_y is not None:
            pants_bot = min(ankle_y + 0.03, 1.0)
            is_pants_visible = True
        elif knee_y is not None:
            # Chi nhin thay den dau goi
            pants_bot = min(knee_y + 0.05, 1.0)
            is_pants_visible = True
        else:
            # Khong thay chan/goi -> pants zone khong kha dung
            pants_bot = min(hip_y + 0.35, 0.92)
            is_pants_visible = False

        pants_top = float(np.clip(pants_top, shirt_bot, 0.80))
        pants_bot = float(np.clip(pants_bot, pants_top + 0.05, 1.0))

        return {
            "shirt_zone"       : (shirt_top, shirt_bot),
            "pants_zone"       : (pants_top, pants_bot),
            "is_pants_visible" : is_pants_visible,
            "hip_y_ratio"      : hip_y,
            "knee_y_ratio"     : knee_y,
            "ankle_y_ratio"    : ankle_y,
            "shoulder_y_ratio" : shoulder_y,
            "keypoints_raw"    : kps,
        }

    def draw_pose_zones(
        self,
        frame: np.ndarray,
        body_box: Tuple[int, int, int, int],
        zones: Dict,
    ) -> np.ndarray:
        """Ve vung ao/quan (tu pose) len frame de debug."""
        bx, by, bw, bh = body_box
        shirt_top, shirt_bot = zones["shirt_zone"]
        pants_top, pants_bot = zones["pants_zone"]

        sy0 = by + int(bh * shirt_top)
        sy1 = by + int(bh * shirt_bot)
        py0 = by + int(bh * pants_top)
        py1 = by + int(bh * pants_bot)

        # Vung ao: xanh la
        cv2.rectangle(frame, (bx, sy0), (bx + bw, sy1), (0, 230, 80), 2)
        cv2.putText(frame, "Ao [Pose]", (bx + 4, sy0 + 16),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 230, 80), 1)

        # Vung quan: cam
        cv2.rectangle(frame, (bx, py0), (bx + bw, py1), (0, 140, 255), 2)
        lbl = "Quan [Pose]" if zones.get("is_pants_visible") else "Quan [est]"
        cv2.putText(frame, lbl, (bx + 4, py0 + 16),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 140, 255), 1)

        # Ve keypoints neu co
        kps = zones.get("keypoints_raw")
        if kps is not None:
            crop_h, crop_w = bh, bw
            kp_color = (255, 100, 0)
            for ki in [KP_LEFT_HIP, KP_RIGHT_HIP,
                       KP_LEFT_KNEE, KP_RIGHT_KNEE,
                       KP_LEFT_ANKLE, KP_RIGHT_ANKLE,
                       KP_LEFT_SHOULDER, KP_RIGHT_SHOULDER]:
                conf = float(kps[ki, 2])
                if conf >= KP_CONF_THRESHOLD:
                    kx = bx + int(float(kps[ki, 0]))
                    ky = by + int(float(kps[ki, 1]))
                    cv2.circle(frame, (kx, ky), 4, kp_color, -1)

        return frame


# ===================== SIMPLE TEST =====================
if __name__ == "__main__":
    import sys
    img_path = sys.argv[1] if len(sys.argv) > 1 else None
    pe = PoseEstimator()
    print(f"Pose estimator available: {pe.available}")

    if img_path and pe.available:
        img = cv2.imread(img_path)
        if img is not None:
            zones = pe.get_body_zones(img)
            print("Zones (full frame):", zones)
            if zones:
                pe.draw_pose_zones(img, (0, 0, img.shape[1], img.shape[0]), zones)
                out = img_path.replace(".", "_pose.")
                cv2.imwrite(out, img)
                print(f"Da luu: {out}")
