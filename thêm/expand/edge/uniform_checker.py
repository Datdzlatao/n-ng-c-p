# -*- coding: utf-8 -*-
"""
=============================================================
  BUOC 3: MODULE NHAN DIEN TRANG PHUC REALTIME
  uniform_checker.py

  Chức năng:
  - Nhận diện trang phục học sinh qua camera realtime
  - Tự động biết hôm nay là thứ mấy → quy định trang phục gì
  - Thứ 7, Chủ nhật: Không yêu cầu trang phục
  - Trả về: Đúng / Sai / Không rõ (UNCLEAR) / Không yêu cầu

  UNCLEAR: Trang phục không xác định được → camera chụp → upload cloud

  Dùng:
    Import vào main.py  : from uniform_checker import UniformChecker
    Chạy test camera    : python uniform_checker.py --test
    Chạy test ảnh file  : python uniform_checker.py --image path/to/img.jpg
=============================================================
"""
import time
import json
import numpy as np
import cv2
from datetime import datetime
from pathlib import Path
from enum import Enum

# ==================== CẤU HÌNH ====================
BASE_DIR      = Path(__file__).parent
_CANDIDATE_DIRS = [
    BASE_DIR / "data",
    BASE_DIR.parent / "backend" / "data",
    BASE_DIR.parent / "data",
]
MODEL_PATH    = next((d / "uniform_model_v2.tflite" for d in _CANDIDATE_DIRS if (d / "uniform_model_v2.tflite").exists()), BASE_DIR / "data" / "uniform_model_v2.tflite")   # v2: 2 nhãn [dan_toc / other]
LABELS_PATH   = next((d / "uniform_labels_v2.json" for d in _CANDIDATE_DIRS if (d / "uniform_labels_v2.json").exists()), BASE_DIR / "data" / "uniform_labels_v2.json")    # v2: nhãn tương ứng
IMAGE_SIZE    = (224, 224)
CONFIDENCE_THRESHOLD = 0.55  # Độ tự tin tối thiểu, thấp hơn = "Không rõ"


# ==================== QUY ĐỊNH TRANG PHỤC THEO NGÀY ====================
class UniformRule(Enum):
    TRANG_PHUC_DAN_TOC = "trang_phuc_dan_toc"  # Thứ 2
    AO_TRANG           = "ao_trang"             # Thứ 3, Thứ 5
    TU_DO_CO_CO        = "tu_do_co_co"          # Thứ 4 (không phân biệt bằng AI, dùng logic)
    AO_DOAN            = "ao_doan"              # Thứ 6
    NGHI               = "nghi"                 # Thứ 7, Chủ nhật


# weekday(): 0=Thứ 2, 1=Thứ 3, 2=Thứ 4, 3=Thứ 5, 4=Thứ 6, 5=Thứ 7, 6=CN
WEEKDAY_RULES = {
    0: UniformRule.TRANG_PHUC_DAN_TOC,
    1: UniformRule.AO_TRANG,
    2: UniformRule.AO_TRANG,               
    3: UniformRule.AO_TRANG,
    4: UniformRule.AO_DOAN,
    5: UniformRule.AO_TRANG,
    6: UniformRule.NGHI,
}

# Hiển thị tiếng Việt
RULE_DISPLAY = {
    UniformRule.TRANG_PHUC_DAN_TOC : "Trang phuc dan toc",
    UniformRule.AO_TRANG           : "Ao trang + Quan den",
    UniformRule.TU_DO_CO_CO        : "Tu do([áo có cổ])",
    UniformRule.AO_DOAN            : "Ao doan vien",
    UniformRule.NGHI               : "Ngay nghi",
}

# Màu hiển thị trên camera (BGR)
COLOR_OK      = (0, 200, 50)    # Xanh lá
COLOR_FAIL    = (0, 50, 220)    # Đỏ
COLOR_SKIP    = (180, 120, 0)   # Xanh dương (ngày tự do)
COLOR_UNCLEAR = (0, 165, 255)   # Cam (không chắc chắn)


class UniformChecker:
    """Module nhận diện trang phục tích hợp vào hệ thống điểm danh."""

    def __init__(self, use_person_detector: bool = True):
        self.interpreter     = None
        self.labels          = []
        self.input_details   = None
        self.output_details  = None
        self._load_model()

        # ── Pose Estimator (YOLOv8-Pose) — khoi tao truoc color_analyzer ──
        self.pose_estimator = None
        try:
            import sys
            if str(BASE_DIR) not in sys.path:
                sys.path.insert(0, str(BASE_DIR))
            from pose_estimator import PoseEstimator
            self.pose_estimator = PoseEstimator()
            if self.pose_estimator.available:
                print("[OK] YOLOv8-Pose Estimator da san sang — dung zone chinh xac.")
            else:
                print("[WARN] PoseEstimator khong kha dung — dung fixed-ratio fallback.")
        except Exception as _pe_exc:
            print(f"[WARN] Khong khoi tao duoc PoseEstimator ({_pe_exc}) — dung fallback.")

        # [fix] Khoi tao UniformColorAnalyzer 1 LAN duy nhat thay vi moi
        # lan goi predict() — truoc day tao moi instance moi 15 frame,
        # lang phi tai nguyen khong can thiet.
        try:
            from uniform_color_analyzer import UniformColorAnalyzer
        except ImportError:
            from uniform.uniform_color_analyzer import UniformColorAnalyzer
        self.color_analyzer = UniformColorAnalyzer(pose_estimator=self.pose_estimator)

        # ── HOG Person Detector ──
        self.person_detector = None
        if use_person_detector:
            try:
                from person_detector import PersonDetector
                self.person_detector = PersonDetector(use_face_fallback=True, verbose=False)
                print("[OK] HOG Person Detector đã sẵn sàng.")
            except ImportError:
                print("[WARN] Không tìm thấy person_detector.py — bỏ qua HOG detection.")
            except Exception as e:
                print(f"[WARN] PersonDetector lỗi: {e}")

    def _load_model(self):
        """Nạp model TFLite vào bộ nhớ."""
        if not MODEL_PATH.exists():
            print(f"[WARN] Chưa có model: {MODEL_PATH}")
            print("       Hãy chạy: python uniform_trainer.py")
            return

        if not LABELS_PATH.exists():
            print(f"[WARN] Chưa có file nhãn: {LABELS_PATH}")
            return

        try:
            import tflite_runtime.interpreter as tflite
            Interpreter = tflite.Interpreter
        except ImportError:
            import tensorflow as tf
            Interpreter = tf.lite.Interpreter

        self.interpreter = Interpreter(model_path=str(MODEL_PATH))
        self.interpreter.allocate_tensors()
        self.input_details  = self.interpreter.get_input_details()
        self.output_details = self.interpreter.get_output_details()

        with open(LABELS_PATH, encoding="utf-8") as f:
            self.labels = json.load(f)

        print(f"[OK] Đã nạp model nhận diện trang phục ({len(self.labels)} nhãn)")
        print(f"     Nhãn: {self.labels}")

    def is_model_ready(self) -> bool:
        return self.interpreter is not None

    # ------------------------------------------------------------------
    # PHÁT HIỆN NGƯỜI — HOG BODY BOX
    # ------------------------------------------------------------------
    def get_body_boxes(self, frame: np.ndarray) -> list[dict]:
        """
        Phát hiện tất cả người trong frame dùng HOG detector.

        Returns:
            List[dict] — mỗi phần tử là:
            {
                "body_box"  : (x, y, w, h),
                "shirt_box" : (x, y, w, h),
                "pants_box" : (x, y, w, h),
                "source"    : "hog" | "face" | "full_frame"
            }
        """
        if self.person_detector is not None:
            return self.person_detector.detect(frame)
        # Fallback: dùng toàn bộ frame
        h, w = frame.shape[:2]
        return [{
            "body_box"  : (0, 0, w, h),
            "shirt_box" : (0, int(h * 0.12), w, int(h * 0.40)),
            "pants_box" : (0, int(h * 0.52), w, int(h * 0.38)),
            "source"    : "full_frame",
        }]

    # ------------------------------------------------------------------
    # LOGIC QUY ĐỊNH THEO NGÀY
    # ------------------------------------------------------------------
    @staticmethod
    def get_today_rule(weekday: int = None) -> UniformRule:
        """Trả về quy định trang phục hôm nay."""
        if weekday is None:
            weekday = datetime.now().weekday()
        return WEEKDAY_RULES.get(weekday, UniformRule.NGHI)

    @staticmethod
    def get_today_rule_display(weekday: int = None) -> str:
        rule = UniformChecker.get_today_rule(weekday)
        return RULE_DISPLAY[rule]

    # ------------------------------------------------------------------
    # NHẬN DIỆN TRANG PHỤC
    # ------------------------------------------------------------------
    def predict(self, frame: np.ndarray, body_box: tuple = None,
                weekday_override: int = None) -> dict:
        """
        Nhan dien trang phuc trong anh.

        Luong xu ly:
        - Thu 2: TFLite AI → [trang_phuc_dan_toc | other]
            + other → UNCLEAR → camera chup + upload cloud
        - Thu 3, 5: Color Analyzer (ao trang + quan toi)
        - Thu 4: SKIP (tu do co co - khong check tu dong)
        - Thu 6: Color Analyzer (ao xanh + quan toi)
        - Thu 7, CN: SKIP (nghi)

        Args:
            frame           : Frame BGR tu camera
            body_box        : (x,y,w,h) override. None = tu dong dung HOG
            weekday_override: Override thu trong tuan (dung khi test)
        """
        today_rule = self.get_today_rule(weekday_override)
        rule_text  = RULE_DISPLAY[today_rule]
        weekday    = weekday_override if weekday_override is not None else datetime.now().weekday()

        # ---- NGAY NGHI -> SKIP ----
        if today_rule == UniformRule.NGHI:
            return self._result("nghi", 1.0, True, rule_text, "SKIP",
                                "Cuoi tuan - Khong yeu cau trang phuc")

        # ---- XAC DINH BODY BOX (HOG hoac override) ----
        if body_box is None:
            # Dung HOG person detector tu dong
            detections = self.get_body_boxes(frame)
            # Lay detection dau tien (lon nhat / chinh xac nhat)
            detected   = detections[0] if detections else None
            body_box   = detected["body_box"] if detected else None

        # ---- THU 3, 5, 6: DUNG COLOR ANALYZER ----
        if today_rule in (UniformRule.AO_TRANG, UniformRule.AO_DOAN):
            color_result = self.color_analyzer.check(frame, body_box, weekday)

            is_correct = color_result.status == "OK"
            status     = color_result.status
            msg        = color_result.message

            return {
                "label"        : color_result.shirt_color,
                "confidence"   : color_result.shirt_ratio,
                "is_correct"   : is_correct,
                "rule"         : rule_text,
                "status"       : status,
                "message"      : msg,
                "color_result" : color_result,   # Du lieu goc de draw_result dung
                "body_box"     : body_box,
            }

        # ---- THU 2: DUNG TFLITE AI (trang phuc dan toc) ----
        if not self.is_model_ready():
            return self._result("unknown", 0.0, False, rule_text, "NO_MODEL",
                                "Model chua duoc training")

        # Cat vung than nguoi cho AI
        if body_box is not None:
            x, y, w, h = body_box
            y_start = max(0, y + int(h * 0.12))
            y_end   = min(frame.shape[0], y + int(h * 0.80))
            region  = frame[y_start:y_end, x:x + w]
        else:
            h, w    = frame.shape[:2]
            y_start = h // 4
            y_end   = h * 3 // 4
            region  = frame[y_start:y_end, :]

        if region.size == 0:
            region = frame

        img = cv2.resize(region, IMAGE_SIZE)
        img = img.astype(np.float32) / 255.0
        img = np.expand_dims(img, axis=0)

        self.interpreter.set_tensor(self.input_details[0]["index"], img)
        self.interpreter.invoke()
        output = self.interpreter.get_tensor(self.output_details[0]["index"])[0]

        predicted_idx   = int(np.argmax(output))
        confidence      = float(np.max(output))
        predicted_label = self.labels[predicted_idx] if predicted_idx < len(self.labels) else "unknown"

        # ── Confidence thap → UNCLEAR ──
        if confidence < CONFIDENCE_THRESHOLD:
            return self._result(
                predicted_label, confidence, False, rule_text, "UNCLEAR",
                f"Khong ro trang phuc ({confidence*100:.0f}%) → Se chup anh kiem tra"
            )

        # ── Nhan "other" → UNCLEAR (trang phuc khong phai dan toc) ──
        # Hoc sinh co the dang mac trang phuc tan tien chua trong dataset
        # → UNCLEAR de nguoi giam sat xem xet, camera se chup lai
        if predicted_label == "other":
            return self._result(
                "other", confidence, False, rule_text, "UNCLEAR",
                f"Trang phuc khong xac dinh ({confidence*100:.0f}%) → Se chup anh kiem tra"
            )

        # ── Nhan "trang_phuc_dan_toc" → OK ──
        is_correct = self._check_rule(predicted_label, today_rule)
        if is_correct:
            msg    = f"OK: Trang phuc dan toc ({confidence*100:.0f}%)"
            status = "OK"
        else:
            msg    = f"SAI: Can mac trang phuc dan toc ({confidence*100:.0f}%)"
            status = "FAIL"

        result = self._result(predicted_label, confidence, is_correct,
                              rule_text, status, msg)
        result["body_box"] = body_box
        return result

    def predict_track(self, frame: np.ndarray, track, weekday_override: int = None) -> dict:
        """
        Nhận diện trang phục cho 1 track (TrackState hoặc dict có body_box).
        Cập nhật trực tiếp `track.uniform_status = result["status"]`.
        """
        body_box = getattr(track, "body_box", None)
        if isinstance(track, dict):
            body_box = track.get("body_box", None)

        result = self.predict(frame, body_box=body_box, weekday_override=weekday_override)

        status = result.get("status", "UNCLEAR")
        msg    = result.get("message", "")
        label  = result.get("label", "")
        conf   = result.get("confidence", 0.0)

        if hasattr(track, "uniform_status"):
            track.uniform_status = status
            track.status_time = time.time()
            if hasattr(track, "uniform_message"):
                track.uniform_message = msg
            if hasattr(track, "uniform_label"):
                track.uniform_label = label
            if hasattr(track, "uniform_conf"):
                track.uniform_conf = conf
        elif isinstance(track, dict):
            track["uniform_status"] = status
            track["uniform_message"] = msg
            track["uniform_label"] = label
            track["uniform_conf"] = conf

        return result

    def predict_tracks(self, frame: np.ndarray, tracks,
                       frame_count: int = 0,
                       check_interval: int = 15,
                       weekday_override: int = None) -> dict:
        """
        Phân tích trang phục ĐA MỤC TIÊU cho danh sách các tracks.

        Giảm tải CPU:
        - Chỉ chạy kiểm tra khi frame_count % check_interval == 0 HOẶC
          khi track chưa được kiểm tra bao giờ (uniform_status is None).

        Args:
            frame           : Frame camera BGR
            tracks          : Dict {track_id: TrackState} hoặc List[TrackState]
            frame_count     : Số thứ tự frame hiện tại
            check_interval  : N frame chạy kiểm tra 1 lần
            weekday_override: Override ngày trong tuần

        Returns:
            Dict {track_id: uni_result}
        """
        import time
        results = {}
        if not tracks:
            return results

        track_list = tracks.values() if isinstance(tracks, dict) else tracks

        for trk in track_list:
            trk_id = getattr(trk, "id", None)
            current_status = getattr(trk, "uniform_status", None)

            # [fix] Nếu học sinh đến gần hơn (body_box tăng >40%), reset để check lại
            # Tránh trường hợp đã check UNCLEAR từ xa, rồi bỏ qua khi đến gần
            body_box = getattr(trk, "body_box", None)
            if body_box is not None and current_status is not None:
                prev_area = getattr(trk, "_last_uniform_body_area", 0)
                curr_area = body_box[2] * body_box[3]
                if prev_area > 0 and curr_area > prev_area * 1.4:
                    current_status = None  # Học sinh lại gần → buộc check lại trang phục

            # Optim: chạy kiểm tra nếu chưa check hoặc đến frame chu kỳ N
            should_check = (current_status is None) or (frame_count % check_interval == 0)

            if should_check:
                # Lưu diện tích body_box hiện tại để so sánh lần sau
                if body_box is not None:
                    trk._last_uniform_body_area = body_box[2] * body_box[3]
                res = self.predict_track(frame, trk, weekday_override=weekday_override)
                if trk_id is not None:
                    results[trk_id] = res
            elif trk_id is not None and current_status is not None:
                results[trk_id] = self._result(
                    label=current_status,
                    conf=1.0,
                    correct=(current_status in ("OK", "SKIP")),
                    rule=self.get_today_rule_display(weekday_override),
                    status=current_status,
                    msg=f"Trang phuc: {current_status}"
                )

        return results


    def _check_rule(self, predicted_label: str, rule: UniformRule) -> bool:
        """Kiểm tra nhãn dự đoán có khớp với quy định hôm nay không."""
        mapping = {
            UniformRule.TRANG_PHUC_DAN_TOC : ["trang_phuc_dan_toc"],
            UniformRule.AO_TRANG           : ["ao_trang"],
            UniformRule.AO_DOAN            : ["ao_doan"],
        }
        allowed = mapping.get(rule, [])
        return predicted_label in allowed

    @staticmethod
    def _result(label, conf, correct, rule, status, msg) -> dict:
        return {
            "label"      : label,
            "confidence" : round(conf, 3),
            "is_correct" : correct,
            "rule"       : rule,
            "status"     : status,
            "message"    : msg,
        }

    # ------------------------------------------------------------------
    # VẼ KẾT QUẢ LÊN FRAME (Dùng trong chế độ realtime)
    # ------------------------------------------------------------------
    def draw_result(self, frame: np.ndarray, result: dict,
                    position: tuple = (10, 30)) -> np.ndarray:
        """Vẽ thông tin trang phục lên frame camera."""
        status  = result.get("status", "")
        message = result.get("message", "")
        rule    = result.get("rule", "")
        
        # Chọn màu theo trạng thái
        color_map = {
            "OK"      : COLOR_OK,
            "FAIL"    : COLOR_FAIL,
            "SKIP"    : COLOR_SKIP,
            "UNCLEAR" : COLOR_UNCLEAR,
            "NO_MODEL": COLOR_UNCLEAR,
        }
        color = color_map.get(status, COLOR_UNCLEAR)

        x, y = position
        # Nền mờ cho chữ
        overlay = frame.copy()
        cv2.rectangle(overlay, (x, y - 20), (x + 420, y + 55), (30, 30, 30), -1)
        cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)

        # Dòng 1: Quy định hôm nay
        weekday_names = ["Thu 2", "Thu 3", "Thu 4", "Thu 5", "Thu 6", "Thu 7", "CN"]
        today_name    = weekday_names[datetime.now().weekday()]
        cv2.putText(frame, f"{today_name}: {rule}",
                    (x, y + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1)

        # Dòng 2: Kết quả nhận diện
        cv2.putText(frame, message,
                    (x, y + 35), cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2)

        return frame


# ==============================================================
# CHẠY TEST TRỰC TIẾP
# ==============================================================
def run_camera_test():
    """Test nhận diện trang phục realtime qua webcam."""
    checker = UniformChecker()
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("[ERROR] Không mở được camera!")
        return

    print("[INFO] Đang mở camera test... Nhấn 'Q' để thoát")
    print(f"[INFO] Hôm nay: {checker.get_today_rule_display()}")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)  # Lật gương

        # Nhận diện trang phục
        result = checker.predict(frame)

        # Vẽ kết quả lên frame
        frame = checker.draw_result(frame, result)

        # Hiển thị FPS và thời gian
        now = datetime.now().strftime("%H:%M:%S")
        cv2.putText(frame, now, (frame.shape[1] - 90, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (180, 180, 180), 1)

        cv2.imshow("Kiem tra trang phuc hoc sinh - Nhan Q de thoat", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()


def run_image_test(image_path: str):
    """Test nhận diện trang phục trên một ảnh tĩnh."""
    checker = UniformChecker()
    
    frame = cv2.imread(image_path)
    if frame is None:
        print(f"[ERROR] Không đọc được ảnh: {image_path}")
        return
    
    result = checker.predict(frame)
    
    print("\n===== KẾT QUẢ NHẬN DIỆN =====")
    for k, v in result.items():
        print(f"  {k:15s}: {v}")
    
    # Vẽ và hiển thị
    frame = checker.draw_result(frame, result)
    
    # Resize nếu ảnh quá to
    h, w = frame.shape[:2]
    if w > 900:
        scale = 900 / w
        frame = cv2.resize(frame, (900, int(h * scale)))
    
    cv2.imshow("Kiem tra trang phuc - Nhan phim bat ky de thoat", frame)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


if __name__ == "__main__":
    import sys
    args = sys.argv[1:]

    if "--image" in args:
        idx = args.index("--image")
        if idx + 1 < len(args):
            run_image_test(args[idx + 1])
        else:
            print("Dùng: python uniform_checker.py --image <duong_dan_anh>")
    else:
        # Mặc định: test camera
        run_camera_test()
