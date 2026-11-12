# -*- coding: utf-8 -*-
"""
STANDALONE AI RUNNER — CHẠY ĐỘC LẬP TOÀN BỘ AI NHẬN DIỆN
standalone_runner.py

Tính năng:
- Nhận diện khuôn mặt thời gian thực (YuNet + SFace)
- Chống gian lận liveness (MiniFASNet + Heuristic)
- Phân tích và kiểm tra đồng phục học sinh theo ngày
- Xem trực tiếp qua màn hình OpenCV hoặc MJPEG Web Stream (cổng 8080)
- Tương thích 100% không phụ thuộc mã nguồn gốc

Cách dùng:
  1. Chạy Webcam:
     python standalone_runner.py --source 0

  2. Chạy Camera IP (RTSP):
     python standalone_runner.py --source "rtsp://admin:pass@192.168.1.100:554/ch1"

  3. Kiểm tra ảnh tĩnh:
     python standalone_runner.py --image "test.jpg"

  4. Đăng ký khuôn mặt mới vào hệ thống:
     python standalone_runner.py --register "HS01" "Nguyen Van A" --image "avatar.jpg"
"""
import os
import cv2
import time
import json
import argparse
import numpy as np
from datetime import datetime
from typing import Optional

from face_engine import FaceEngine, ThreadedCamera
from anti_spoofing import AntiSpoofingDetector
from uniform_checker import UniformChecker

# Optional MJPEG Web Stream server
try:
    from http.server import BaseHTTPRequestHandler, HTTPServer
    from socketserver import ThreadingMixIn
    class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
        daemon_threads = True
except ImportError:
    ThreadingHTTPServer = None


class StandaloneVisionPipeline:
    def __init__(self, faces_dir: str = "known_faces", enable_anti_spoof: bool = True):
        print("=" * 60)
        print("  STANDALONE AI VISION PIPELINE (Face + Spoof + Uniform)")
        print("=" * 60)
        self.face_engine = FaceEngine(faces_dir=faces_dir)
        self.anti_spoof = AntiSpoofingDetector() if enable_anti_spoof else None
        self.uniform_checker = UniformChecker(use_person_detector=True)
        print("[PIPELINE] Khởi tạo các module AI thành công.")

    def process_frame(self, frame: np.ndarray, weekday_override: Optional[int] = None) -> dict:
        t0 = time.time()
        # 1. Nhận diện khuôn mặt
        face_results = self.face_engine.recognize(frame)

        # 2. Kiểm tra chống giả mạo cho từng khuôn mặt
        for fr in face_results:
            loc = fr["location"]
            if self.anti_spoof is not None and loc is not None:
                stu_id = fr.get("student_id") or "UNKNOWN"
                liveness = self.anti_spoof.check_liveness(frame, loc, track_id=stu_id)
                fr["liveness"] = liveness
            else:
                fr["liveness"] = {"is_real": True, "status": "SKIPPED", "confidence": 1.0}

        # 3. Kiểm tra đồng phục
        # Lấy vị trí khuôn mặt đầu tiên nếu có để hỗ trợ xác định thân người
        first_loc = face_results[0]["location"] if face_results else None
        uniform_result = self.uniform_checker.check_uniform(
            frame,
            face_location=first_loc,
            weekday_override=weekday_override
        )

        dt = time.time() - t0
        return {
            "timestamp": datetime.now().isoformat(),
            "process_time_ms": round(dt * 1000, 1),
            "faces_detected": len(face_results),
            "faces": face_results,
            "uniform": uniform_result
        }

    def draw_hud(self, frame: np.ndarray, result: dict) -> np.ndarray:
        h, w = frame.shape[:2]
        canvas = frame.copy()

        # 1. Vẽ bounding box khuôn mặt
        for fr in result["faces"]:
            top, right, bottom, left = fr["location"]
            is_ok = (fr["status"] == "ok")
            is_real = fr["liveness"]["is_real"]

            if not is_real:
                color = (0, 0, 255)       # Đỏ: Giả mạo (Spoof)
                label = f"GIAN LAN: {fr['liveness']['status']}"
            elif is_ok:
                color = (0, 220, 80)      # Xanh lá: Nhận diện thành công
                label = f"{fr['name']} ({fr['student_id']}) [{fr['confidence']:.2f}]"
            else:
                color = (0, 165, 255)     # Cam: Người lạ
                label = f"NGUOI LA [{fr['confidence']:.2f}]"

            cv2.rectangle(canvas, (left, top), (right, bottom), color, 2)
            cv2.rectangle(canvas, (left, max(0, top - 24)), (right, top), color, -1)
            cv2.putText(canvas, label, (left + 4, max(16, top - 6)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)

        # 2. Vẽ bounding box đồng phục
        uni = result.get("uniform")
        if uni and uni.get("body_box"):
            bx, by, bw, bh = uni["body_box"]
            uni_ok = uni["is_correct"]
            u_color = (0, 220, 80) if uni_ok else (0, 50, 240)
            cv2.rectangle(canvas, (bx, by), (bx + bw, by + bh), u_color, 2)

            # Thẻ trạng thái đồng phục góc trên body_box
            u_tag = f"DONG PHUC: {uni['status']} - {uni['message'][:35]}"
            cv2.putText(canvas, u_tag, (bx, max(20, by - 8)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.42, u_color, 1, cv2.LINE_AA)

        # 3. Thanh thông tin phía dưới màn hình
        bar_h = 45
        overlay = canvas.copy()
        cv2.rectangle(overlay, (0, h - bar_h), (w, h), (20, 20, 20), -1)
        cv2.addWeighted(overlay, 0.75, canvas, 0.25, 0, canvas)

        status_text = f"AI Vision | {result['process_time_ms']}ms | Faces: {result['faces_detected']} | Quy dinh: {uni.get('rule', '')}"
        cv2.putText(canvas, status_text, (15, h - 16),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.48, (220, 230, 240), 1, cv2.LINE_AA)
        return canvas


def main():
    parser = argparse.ArgumentParser(description="Standalone AI Vision Engine Runner")
    parser.add_argument("--source", type=str, default="0", help="Camera index (0, 1) or RTSP URL")
    parser.add_argument("--image", type=str, default="", help="Path to static image for testing")
    parser.add_argument("--register", nargs=2, metavar=("ID", "NAME"), help="Register new face: --register HS01 'Nguyen Van A' --image face.jpg")
    parser.add_argument("--weekday", type=int, default=None, help="Override weekday (0=Mon, 1=Tue, ... 6=Sun)")
    parser.add_argument("--no-gui", action="store_true", help="Run in headless mode without cv2.imshow")
    parser.add_argument("--port", type=int, default=0, help="Start MJPEG streaming server on specified port (e.g. 8080)")
    args = parser.parse_args()

    pipeline = StandaloneVisionPipeline()

    # Mode 1: Register Face
    if args.register:
        stu_id, stu_name = args.register
        if not args.image or not os.path.isfile(args.image):
            print("[ERROR] Cần cung cấp ảnh qua tham số --image khi đăng ký.")
            return
        img = cv2.imread(args.image)
        ok = pipeline.face_engine.register_face(stu_id, stu_name, img, save_disk=True)
        if ok:
            print(f"[OK] Đã đăng ký thành công: {stu_name} ({stu_id})")
        else:
            print(f"[FAIL] Không nhận diện được khuôn mặt trong ảnh {args.image}.")
        return

    # Mode 2: Static Image Test
    if args.image:
        if not os.path.isfile(args.image):
            print(f"[ERROR] Không tìm thấy file: {args.image}")
            return
        frame = cv2.imread(args.image)
        res = pipeline.process_frame(frame, weekday_override=args.weekday)
        print("\n--- KẾT QUẢ PHÂN TÍCH ẢNH ---")
        print(json.dumps(res, indent=2, ensure_ascii=False))

        if not args.no_gui:
            annotated = pipeline.draw_hud(frame, res)
            cv2.imshow("Standalone AI - Result", annotated)
            cv2.waitKey(0)
            cv2.destroyAllWindows()
        return

    # Mode 3: Live Camera Stream
    src = int(args.source) if args.source.isdigit() else args.source
    print(f"[RUNNER] Đang kết nối tới nguồn camera: {src}...")
    cam = ThreadedCamera(src=src)
    time.sleep(1.0)

    print("[RUNNER] Nhấn 'q' hoặc 'ESC' trên cửa sổ hình ảnh để dừng.")
    try:
        while True:
            ret, frame = cam.read()
            if not ret or frame is None:
                time.sleep(0.03)
                continue

            res = pipeline.process_frame(frame, weekday_override=args.weekday)
            annotated = pipeline.draw_hud(frame, res)

            # In sự kiện nếu phát hiện học sinh
            for f in res["faces"]:
                if f["status"] == "ok":
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Nhận diện: {f['name']} ({f['student_id']}) - Liveness: {f['liveness']['status']}")

            if not args.no_gui:
                cv2.imshow("Standalone AI Vision (Face + Uniform)", annotated)
                key = cv2.waitKey(1) & 0xFF
                if key in (ord('q'), 27):
                    break
    finally:
        cam.release()
        cv2.destroyAllWindows()
        print("[RUNNER] Đã dừng tiến trình AI.")


if __name__ == "__main__":
    main()
