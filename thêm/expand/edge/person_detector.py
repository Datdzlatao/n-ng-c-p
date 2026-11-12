# -*- coding: utf-8 -*-
"""
=============================================================
  MODULE PHÁT HIỆN NGƯỜI — HOG PERSON DETECTOR
  person_detector.py

  Tích hợp 2 phương pháp phát hiện người:
  1. HOG + SVM (OpenCV built-in) — Chính xác, không cần GPU
  2. Face-based fallback — Dùng khi HOG không phát hiện được

  Cách dùng:
    from person_detector import PersonDetector
    detector = PersonDetector()
    boxes = detector.detect(frame)   # List[dict]
    # boxes[i] = {
    #   "body_box"  : (x, y, w, h),   # Vùng thân người (đầy đủ)
    #   "shirt_box" : (x, y, w, h),   # Vùng áo (15%–55% chiều cao)
    #   "pants_box" : (x, y, w, h),   # Vùng quần (55%–90% chiều cao)
    #   "source"    : "hog" | "face"  # Nguồn phát hiện
    # }
=============================================================
"""

import cv2
import numpy as np
from typing import Optional

# ──────────────────────────────────────────────────────────────────────
# CẤU HÌNH HOG DETECTOR
# ──────────────────────────────────────────────────────────────────────

# Kích thước cửa sổ phát hiện (yêu cầu bởi HOG SVM OpenCV)
HOG_WIN_STRIDE  = (8, 8)
HOG_PADDING     = (4, 4)
HOG_SCALE       = 1.06      # Tối ưu độ chính xác: 1.06 quét mịn hơn nhiều kích thước người so với 1.15
HOG_FINAL_THRESH= 0.1       # Ngưỡng confidence HOG loại bỏ các phát hiện rác không phải người

# Scale frame trước khi detect (0.65 = 65% độ phân giải giúp bắt rõ toàn thân học sinh)
DETECT_SCALE    = 0.65

# Ngưỡng NMS (Non-Maximum Suppression) — lọc bỏ hộp chồng nhau
NMS_OVERLAP_THRESH = 0.60

# Vùng phân tích áo/quần (tính theo tỷ lệ chiều cao body_box)
SHIRT_ZONE_TOP    = 0.12   # Tránh đầu/cổ
SHIRT_ZONE_BOTTOM = 0.52   # Điểm cắt áo-quần
PANTS_ZONE_TOP    = 0.52
PANTS_ZONE_BOTTOM = 0.90   # Tránh giày dép

from pathlib import Path

# Face Model Paths
_BASE_DIR = Path(__file__).parent
_YUNET_CANDIDATES = [
    _BASE_DIR / "assets" / "models" / "face_detection_yunet_2023mar.onnx",
    _BASE_DIR.parent / "assets" / "models" / "face_detection_yunet_2023mar.onnx",
    _BASE_DIR / "face_detection_yunet_2023mar.onnx",
]
YUNET_MODEL_PATH = next((p for p in _YUNET_CANDIDATES if p.exists()), None)

# Face Cascade (fallback)
FACE_CASCADE_PATH = cv2.data.haarcascades + "haarcascade_frontalface_default.xml" if hasattr(cv2, "data") and hasattr(cv2.data, "haarcascades") else ""

# Ước tính thân người từ mặt:
# Thân người trung bình cao gấp ~6.5 lần chiều cao khuôn mặt
# Vai người rộng khoảng 2.6 lần chiều rộng khuôn mặt (chuẩn nhân trắc học)
FACE_TO_BODY_HEIGHT_RATIO = 6.5
FACE_TO_BODY_WIDTH_RATIO  = 2.6


# ──────────────────────────────────────────────────────────────────────
# CLASS CHÍNH
# ──────────────────────────────────────────────────────────────────────
class PersonDetector:
    """
    Phát hiện người trong frame camera và tính toán vùng áo/quần.

    Ưu tiên HOG (thân đầy đủ), fallback & hợp nhất sang YuNet DNN face-based estimation.
    """

    def __init__(self, use_face_fallback: bool = True, verbose: bool = False):
        self.verbose         = verbose
        self.use_face_fallback = use_face_fallback

        # ── Khởi tạo HOG ──
        self.hog = cv2.HOGDescriptor()
        self.hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
        if verbose:
            print("[PersonDetector] HOG SVM người đã sẵn sàng.")

        # ── Khởi tạo YuNet Face Detector (ưu tiên số 1 cho Face-based body estimation) ──
        self.yunet = None
        if use_face_fallback and YUNET_MODEL_PATH is not None:
            try:
                self.yunet = cv2.FaceDetectorYN.create(
                    str(YUNET_MODEL_PATH), "", (320, 320), score_threshold=0.50
                )
                if verbose:
                    print(f"[PersonDetector] YuNet face detector đã sẵn sàng: {YUNET_MODEL_PATH.name}")
            except Exception as e:
                if verbose:
                    print(f"[PersonDetector] Không thể nạp YuNet: {e}")

        # ── Khởi tạo Face Cascade (fallback legacy) ──
        self.face_cascade = None
        if use_face_fallback and self.yunet is None and FACE_CASCADE_PATH:
            try:
                import os
                if os.path.isfile(FACE_CASCADE_PATH):
                    self.face_cascade = cv2.CascadeClassifier(FACE_CASCADE_PATH)
                    if self.face_cascade.empty():
                        self.face_cascade = None
                    elif verbose:
                        print("[PersonDetector] Face cascade đã sẵn sàng (fallback).")
            except Exception as e:
                if verbose:
                    print(f"[PersonDetector] WARN: {e}")

    # ──────────────────────────────────────────────────────────────────
    # HÀM PHÁT HIỆN CHÍNH
    # ──────────────────────────────────────────────────────────────────
    def detect(self, frame: np.ndarray,
               min_person_height: int = 80) -> list[dict]:
        """
        Phát hiện người trong frame và trả về danh sách bounding box.

        Args:
            frame             : Frame BGR từ camera.
            min_person_height : Chiều cao tối thiểu (px) để coi là người.

        Returns:
            List[dict] với mỗi phần tử là:
            {
                "body_box"  : (x, y, w, h),   # Vùng thân người
                "shirt_box" : (x, y, w, h),   # Vùng áo
                "pants_box" : (x, y, w, h),   # Vùng quần
                "source"    : "hog" | "face" | "full_frame"
            }
        """
        h_frame, w_frame = frame.shape[:2]
        results = []

        # ── 1. Thử HOG trước ──
        hog_boxes = self._detect_hog(frame, min_person_height)
        for box in hog_boxes:
            parsed = self._parse_body_box(box, w_frame, h_frame)
            parsed["source"] = "hog"
            results.append(parsed)

        # ── 2. Bổ sung từ Face Detection (YuNet hoặc Cascade) ──
        # Đảm bảo mọi học sinh có mặt trong khung hình đều có body_box riêng,
        # tránh trường hợp HOG bỏ sót học sinh đứng sát nhau.
        if self.use_face_fallback and (self.yunet is not None or self.face_cascade is not None):
            face_boxes = self._detect_faces(frame)
            for fbox in face_boxes:
                fx, fy, fw, fh = fbox
                fcx, fcy = fx + fw // 2, fy + fh // 2

                # Kiểm tra mặt này đã nằm trong body_box của HOG nào chưa
                covered_by_hog = False
                for r in results:
                    bx, by, bw, bh = r["body_box"]
                    if bx <= fcx <= bx + bw and by <= fcy <= by + bh:
                        covered_by_hog = True
                        break

                if not covered_by_hog:
                    body_box = self._estimate_body_from_face(fbox, w_frame, h_frame)
                    parsed   = self._parse_body_box(body_box, w_frame, h_frame)
                    parsed["source"] = "face"
                    results.append(parsed)

            if self.verbose and results:
                print(f"[PersonDetector] Tổng cộng: {len(results)} người phát hiện (HOG + Face).")

        if results:
            return results

        # ── 3. Không tìm thấy gì → Dùng toàn frame ──
        if self.verbose:
            print("[PersonDetector] Không phát hiện người — dùng toàn frame.")
        full_box = (0, 0, w_frame, h_frame)
        parsed   = self._parse_body_box(full_box, w_frame, h_frame)
        parsed["source"] = "full_frame"
        return [parsed]

    # ──────────────────────────────────────────────────────────────────
    # HOG DETECTION
    # ──────────────────────────────────────────────────────────────────
    def _detect_hog(self, frame: np.ndarray,
                    min_height: int) -> list[tuple]:
        """Chạy HOG detector và trả về danh sách (x,y,w,h) sau NMS."""
        # Scale nhỏ để tăng tốc
        h, w    = frame.shape[:2]
        small   = cv2.resize(frame, (int(w * DETECT_SCALE), int(h * DETECT_SCALE)))

        try:
            rects, weights = self.hog.detectMultiScale(
                small,
                winStride    = HOG_WIN_STRIDE,
                padding      = HOG_PADDING,
                scale        = HOG_SCALE,
                finalThreshold = HOG_FINAL_THRESH
            )
        except cv2.error:
            return []

        if len(rects) == 0:
            return []

        # Scale box trở về kích thước gốc
        inv = 1.0 / DETECT_SCALE
        rects_orig = [
            (int(x * inv), int(y * inv), int(w2 * inv), int(h2 * inv))
            for (x, y, w2, h2) in rects
        ]

        # Lọc theo chiều cao tối thiểu
        rects_orig = [(x, y, w2, h2) for (x, y, w2, h2) in rects_orig if h2 >= min_height]
        if not rects_orig:
            return []

        # NMS — loại bỏ hộp chồng nhau
        return self._nms(rects_orig, NMS_OVERLAP_THRESH)

    # ──────────────────────────────────────────────────────────────────
    # FACE DETECTION (FALLBACK)
    # ──────────────────────────────────────────────────────────────────
    def _detect_faces(self, frame: np.ndarray) -> list[tuple]:
        """Phát hiện khuôn mặt trong frame dùng YuNet DNN hoặc Haar cascade."""
        h, w = frame.shape[:2]
        if self.yunet is not None:
            try:
                self.yunet.setInputSize((w, h))
                _, faces = self.yunet.detect(frame)
                if faces is not None and len(faces) > 0:
                    return [(int(f[0]), int(f[1]), int(f[2]), int(f[3])) for f in faces]
            except Exception:
                pass

        if self.face_cascade is not None:
            try:
                gray  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                gray  = cv2.equalizeHist(gray)
                faces = self.face_cascade.detectMultiScale(
                    gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30)
                )
                return list(faces) if len(faces) > 0 else []
            except Exception:
                return []
        return []

    def _estimate_body_from_face(self, face_box: tuple,
                                  frame_w: int, frame_h: int) -> tuple:
        """
        Ước tính bounding box thân người từ khuôn mặt.

        Nguyên lý nhân trắc học:
        - Thân người trung bình cao gấp ~6.5 lần khuôn mặt.
        - Chiều rộng vai bằng ~2.6 lần chiều rộng mặt.
        - Đỉnh đầu cao hơn mắt/mặt khoảng 0.2 lần chiều cao mặt.
        """
        fx, fy, fw, fh = face_box

        body_w = int(fw * FACE_TO_BODY_WIDTH_RATIO)
        body_h = int(fh * FACE_TO_BODY_HEIGHT_RATIO)

        # Căn giữa theo trục ngang
        body_x = fx + fw // 2 - body_w // 2
        body_y = max(0, fy - int(fh * 0.2))  # Đỉnh đầu

        # Clip vào frame
        body_x = max(0, body_x)
        body_y = max(0, body_y)
        body_w = min(body_w, frame_w - body_x)
        body_h = min(body_h, frame_h - body_y)

        return (body_x, body_y, body_w, body_h)

    # ──────────────────────────────────────────────────────────────────
    # TINH CHỈNH VÙNG ÁO / QUẦN
    # ──────────────────────────────────────────────────────────────────
    @staticmethod
    def _parse_body_box(body_box: tuple,
                         frame_w: int, frame_h: int) -> dict:
        """
        Từ body_box (x,y,w,h), tính vùng áo và quần theo tỷ lệ.
        """
        x, y, w, h = body_box

        # Clip body box vào frame
        x = max(0, x); y = max(0, y)
        w = min(w, frame_w - x)
        h = min(h, frame_h - y)

        # Vùng áo
        sy0 = y + int(h * SHIRT_ZONE_TOP)
        sy1 = y + int(h * SHIRT_ZONE_BOTTOM)
        sy0 = max(0, min(sy0, frame_h - 1))
        sy1 = max(sy0 + 1, min(sy1, frame_h))

        # Vùng quần
        py0 = y + int(h * PANTS_ZONE_TOP)
        py1 = y + int(h * PANTS_ZONE_BOTTOM)
        py0 = max(0, min(py0, frame_h - 1))
        py1 = max(py0 + 1, min(py1, frame_h))

        return {
            "body_box"  : (x, y, w, h),
            "shirt_box" : (x, sy0, w, sy1 - sy0),
            "pants_box" : (x, py0, w, py1 - py0),
            "source"    : "unknown",
        }

    def extract_zones(self, frame: np.ndarray, body_box: tuple) -> dict:
        """
        Trích xuất phân vùng áo/quần và cắt ảnh crop ứng với từng body_box (track_id).
        """
        h_frame, w_frame = frame.shape[:2]
        parsed = self._parse_body_box(body_box, w_frame, h_frame)
        sx, sy, sw, sh = parsed["shirt_box"]
        px, py, pw, ph = parsed["pants_box"]

        shirt_crop = frame[sy:sy + sh, sx:sx + sw] if sw > 0 and sh > 0 else frame
        pants_crop = frame[py:py + ph, px:px + pw] if pw > 0 and ph > 0 else frame

        parsed["shirt_crop"] = shirt_crop
        parsed["pants_crop"] = pants_crop
        return parsed

    @staticmethod
    def draw_target_boxes(frame: np.ndarray,
                          body_box: tuple,
                          face_location: tuple = None,
                          label_info: dict = None,
                          force_red: bool = False) -> np.ndarray:
        """
        Vẽ Bounding Box động (Visual Flagging) theo từng trạng thái của target:
        - 🟩 Xanh lá (0, 220, 80) : Hợp lệ (Quét thẻ + Khớp mặt + Đúng đồng phục)
        - 🟨 Vàng (0, 220, 255)   : Đang xử lý / Chờ quét thẻ
        - 🟥 Đỏ (0, 0, 255) + Nhấp nháy : Vi phạm (Hiển thị nhãn lỗi cụ thể)
        """
        import time
        img = frame.copy()
        if body_box is None:
            return img

        bx, by, bw, bh = body_box

        # Xác định trạng thái mục tiêu
        is_violation = force_red
        is_valid = False
        violation_label = ""

        if label_info:
            if label_info.get("is_violation", False):
                is_violation = True
                violation_label = label_info.get("violation_label", "VI PHAM")

            uniform = label_info.get("uniform_status", "")
            spoof = label_info.get("spoof_status", "REAL")
            is_stranger = label_info.get("is_stranger", False)
            qr_scanned = label_info.get("qr_scanned", False)
            face_matched = label_info.get("face_matched", False)

            if spoof in ("SPOOF_SCREEN", "SPOOF_PHOTO"):
                is_violation = True
                violation_label = f"LOI: GIA MAO KHUON MAT ({spoof})"
            elif uniform == "FAIL":
                is_violation = True
                violation_label = label_info.get("uniform_message") or label_info.get("message", "LOI: Sai trang phuc")
            elif is_stranger:
                is_violation = True
                violation_label = "LOI: NGUOI LA"
            elif (face_matched or qr_scanned) and uniform in ("OK", "SKIP"):
                is_valid = True

        # Màu Bounding Box & nhấp nháy
        if is_violation:
            # Hiệu ứng nhấp nháy đỏ 250ms
            flash = (int(time.time() * 4) % 2 == 0)
            body_color = (0, 0, 255) if flash else (50, 50, 255)
            corner_color = (0, 0, 255)
            thick = 3
        elif is_valid:
            body_color = (0, 220, 80)      # Xanh lá hợp lệ
            corner_color = (0, 255, 100)
            thick = 2
        else:
            body_color = (0, 220, 255)     # Vàng đang xử lý
            corner_color = (0, 255, 255)
            thick = 2

        # 1. Vẽ Khung cơ thể (Body Box)
        cv2.rectangle(img, (bx, by), (bx + bw, by + bh), body_color, thick)

        # Góc Target Accent cho Body Box
        line_len = min(22, max(6, bw // 4), max(6, bh // 4))
        # Top-Left
        cv2.line(img, (bx, by), (bx + line_len, by), corner_color, thick + 1)
        cv2.line(img, (bx, by), (bx, by + line_len), corner_color, thick + 1)
        # Top-Right
        cv2.line(img, (bx + bw, by), (bx + bw - line_len, by), corner_color, thick + 1)
        cv2.line(img, (bx + bw, by), (bx + bw, by + line_len), corner_color, thick + 1)
        # Bottom-Left
        cv2.line(img, (bx, by + bh), (bx + line_len, by + bh), corner_color, thick + 1)
        cv2.line(img, (bx, by + bh), (bx, by + bh - line_len), corner_color, thick + 1)
        # Bottom-Right
        cv2.line(img, (bx + bw, by + bh), (bx + bw - line_len, by + bh), corner_color, thick + 1)
        cv2.line(img, (bx + bw, by + bh), (bx + bw, by + bh - line_len), corner_color, thick + 1)

        # 2. Badge Kiểm Tra Trang Phục (Uniform Inspection Badge) trên Body Box
        if label_info:
            u_status = label_info.get("uniform_status", "")
            u_msg    = label_info.get("uniform_message", "")
            u_lbl    = label_info.get("uniform_label", "")

            if u_status == "OK":
                u_text = f"TRANG PHUC: HOP LE ({u_lbl or 'Chuan'})"
                u_bg   = (0, 140, 40)
            elif u_status == "FAIL":
                u_text = f"SAI TRANG PHUC: {u_msg[:24] if u_msg else 'Khong dung'}"
                u_bg   = (0, 0, 200)
            elif u_status in ("UNCLEAR", "CHUA_CHECK", ""):
                u_text = "DANG QUET TRANG PHUC..."
                u_bg   = (0, 120, 200)
            elif u_status == "SKIP":
                u_text = "TRANG PHUC: TU DO / NGHI"
                u_bg   = (140, 90, 0)
            else:
                u_text = f"TRANG PHUC: {u_status}"
                u_bg   = (60, 60, 60)

            (u_w, u_h), _ = cv2.getTextSize(u_text, cv2.FONT_HERSHEY_SIMPLEX, 0.44, 1)
            u_pad = min(img.shape[1] - bx, u_w + 10)
            cv2.rectangle(img, (bx, by), (bx + u_pad, min(img.shape[0], by + u_h + 10)), u_bg, -1)
            cv2.putText(img, u_text, (bx + 5, by + u_h + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (255, 255, 255), 1)

        # 3. Vẽ Khung khuôn mặt & Đường nối đồng bộ Face <-> Body
        if face_location is not None:
            top, right, bottom, left = face_location
            fcx = (left + right) // 2
            bcx = bx + bw // 2

            # Đường nối quang học (Synchronized Fusion Link) Face -> Body
            beam_col = (0, 220, 80) if is_valid else ((0, 0, 255) if is_violation else (0, 220, 255))
            cv2.line(img, (fcx, bottom), (bcx, by), beam_col, 2, cv2.LINE_AA)
            cv2.circle(img, (fcx, bottom), 3, beam_col, -1)
            cv2.circle(img, (bcx, by), 3, beam_col, -1)

            # Khung khuôn mặt với góc accent
            face_color = body_color
            cv2.rectangle(img, (left, top), (right, bottom), face_color, 2)
            f_len = min(12, max(4, (right - left) // 4))
            cv2.line(img, (left, top), (left + f_len, top), corner_color, 3)
            cv2.line(img, (left, top), (left, top + f_len), corner_color, 3)
            cv2.line(img, (right, top), (right - f_len, top), corner_color, 3)
            cv2.line(img, (right, top), (right, top + f_len), corner_color, 3)

            # Badge khuôn mặt
            if label_info:
                name = label_info.get("name", "Nguoi dung")
                sid = label_info.get("student_id", "")
                if label_info.get("face_matched"):
                    f_tag = f"MAT: {name} ({sid})" if sid else f"MAT: {name}"
                    f_bg = (0, 140, 40)
                elif label_info.get("is_stranger"):
                    f_tag = "MAT: NGUOI LA"
                    f_bg = (0, 0, 200)
                else:
                    f_tag = "MAT: DANG QUET..."
                    f_bg = (20, 20, 20)
            else:
                f_tag = "MAT: DANG QUET..."
                f_bg = (20, 20, 20)

            (ftw, fth), _ = cv2.getTextSize(f_tag, cv2.FONT_HERSHEY_SIMPLEX, 0.42, 1)
            f_y = max(fth + 8, top - 6)
            cv2.rectangle(img, (left, f_y - fth - 4), (left + ftw + 8, f_y + 2), f_bg, -1)
            cv2.putText(img, f_tag, (left + 4, f_y - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 1)

        # 4. Panel Header Target ID
        if label_info:
            trk_id = label_info.get("track_id", "?")
            name = label_info.get("name", "Nguoi dung")
            sid = label_info.get("student_id", "")

            if is_violation:
                text = f"[TARGET #{trk_id}] {name} ({sid}) | {violation_label}"
                bg_color = (0, 0, 180)
            elif is_valid:
                text = f"[TARGET #{trk_id}] {name} ({sid}) | HOP LE [OK]"
                bg_color = (0, 140, 40)
            else:
                text = f"[TARGET #{trk_id}] {name} ({sid if sid else 'N/A'}) | CHUYEN CAN..."
                bg_color = (20, 20, 20)

            pad_w = min(img.shape[1] - bx, len(text) * 9 + 12)
            header_y = max(0, by - 24)
            cv2.rectangle(img, (bx, header_y), (bx + pad_w, max(24, by)), bg_color, -1)
            cv2.putText(img, text, (bx + 6, max(16, by - 6)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.46, (255, 255, 255), 1)

        return img

    # ──────────────────────────────────────────────────────────────────
    # VẼ BOUNDING BOX LÊN FRAME (Debug / UI)
    # ──────────────────────────────────────────────────────────────────
    @staticmethod
    def draw_detections(frame: np.ndarray,
                        detections: list[dict],
                        draw_zones: bool = True) -> np.ndarray:
        """
        Vẽ bounding box và vùng áo/quần lên frame để kiểm tra.

        Args:
            frame      : Frame BGR gốc (sẽ được vẽ lên).
            detections : Kết quả từ detect().
            draw_zones : True = vẽ thêm vùng áo (xanh lá) và quần (xanh dương).

        Returns:
            Frame đã vẽ.
        """
        SOURCE_COLOR = {
            "hog"        : (0, 255, 0),      # Xanh lá — HOG chính xác
            "face"       : (255, 165, 0),    # Cam — Ước tính từ mặt
            "full_frame" : (150, 150, 150),  # Xám — Không phát hiện được
        }
        SHIRT_COLOR = (50, 220, 50)    # Xanh lá nhạt
        PANTS_COLOR = (220, 100, 50)   # Cam nhạt

        for d in detections:
            src   = d.get("source", "unknown")
            color = SOURCE_COLOR.get(src, (200, 200, 200))
            x, y, w, h = d["body_box"]

            # Vẽ body box
            cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
            cv2.putText(frame, f"Person [{src}]",
                        (x, y - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

            if draw_zones:
                # Vùng áo
                sx, sy, sw, sh = d["shirt_box"]
                cv2.rectangle(frame, (sx, sy), (sx + sw, sy + sh), SHIRT_COLOR, 1)
                cv2.putText(frame, "Ao", (sx + 4, sy + 16),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.42, SHIRT_COLOR, 1)

                # Vùng quần
                px, py, pw, ph = d["pants_box"]
                cv2.rectangle(frame, (px, py), (px + pw, py + ph), PANTS_COLOR, 1)
                cv2.putText(frame, "Quan", (px + 4, py + 16),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.42, PANTS_COLOR, 1)

        return frame

    # ──────────────────────────────────────────────────────────────────
    # NMS — NON-MAXIMUM SUPPRESSION
    # ──────────────────────────────────────────────────────────────────
    @staticmethod
    def _nms(boxes: list[tuple], overlap_thresh: float) -> list[tuple]:
        """
        Áp dụng Non-Maximum Suppression để loại bỏ hộp chồng nhau.
        Dựa trên thuật toán Malisiewicz et al. (fast NMS).
        """
        if not boxes:
            return []

        boxes_arr = np.array(boxes, dtype=float)
        x1 = boxes_arr[:, 0]
        y1 = boxes_arr[:, 1]
        x2 = boxes_arr[:, 0] + boxes_arr[:, 2]
        y2 = boxes_arr[:, 1] + boxes_arr[:, 3]
        areas = (x2 - x1 + 1) * (y2 - y1 + 1)

        # Sắp xếp theo y2 (dưới cùng) — chọn hộp thấp nhất (thân người đầy đủ hơn)
        idxs = np.argsort(y2)
        pick = []

        while len(idxs) > 0:
            last = idxs[-1]
            pick.append(last)

            xx1 = np.maximum(x1[last], x1[idxs[:-1]])
            yy1 = np.maximum(y1[last], y1[idxs[:-1]])
            xx2 = np.minimum(x2[last], x2[idxs[:-1]])
            yy2 = np.minimum(y2[last], y2[idxs[:-1]])

            inter_w = np.maximum(0, xx2 - xx1 + 1)
            inter_h = np.maximum(0, yy2 - yy1 + 1)
            overlap  = (inter_w * inter_h) / areas[idxs[:-1]]

            idxs = np.delete(idxs, np.concatenate([[len(idxs) - 1],
                                                    np.where(overlap > overlap_thresh)[0]]))

        return [tuple(int(v) for v in boxes_arr[i]) for i in pick]


# ──────────────────────────────────────────────────────────────────────
# TEST TRỰC TIẾP QUA CAMERA
# ──────────────────────────────────────────────────────────────────────
def _run_camera_test():
    """Test PersonDetector realtime qua webcam. Nhấn Q để thoát, Z để bật/tắt zones."""
    detector = PersonDetector(verbose=True)
    cap      = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("[ERROR] Không mở được camera!")
        return

    print("=== TEST PERSON DETECTOR ===")
    print("  HOG phát hiện người → vẽ body box + vùng áo/quần")
    print("  Q = Thoát | Z = Bật/tắt zone visualization")

    show_zones = True
    frame_count = 0
    fps_start   = cv2.getTickCount()

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frame = cv2.flip(frame, 1)

        # Phát hiện người
        detections = detector.detect(frame)

        # Vẽ kết quả
        frame = PersonDetector.draw_detections(frame, detections, draw_zones=show_zones)

        # FPS
        frame_count += 1
        if frame_count % 30 == 0:
            elapsed = (cv2.getTickCount() - fps_start) / cv2.getTickFrequency()
            fps = frame_count / elapsed
            frame_count = 0
            fps_start   = cv2.getTickCount()
        else:
            fps = 0

        if fps > 0:
            cv2.putText(frame, f"FPS: {fps:.1f}  Nguoi: {len(detections)}",
                        (10, frame.shape[0] - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

        cv2.putText(frame, "Q=Thoat  Z=Zones",
                    (frame.shape[1] - 160, frame.shape[0] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (150, 150, 150), 1)

        cv2.imshow("Person Detector Test — HOG", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
        elif key == ord("z"):
            show_zones = not show_zones
            print(f"[TEST] Zones: {'BẬT' if show_zones else 'TẮT'}")

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    _run_camera_test()
