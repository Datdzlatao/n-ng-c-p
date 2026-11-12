"""
=================================================
  TEST_OFFLINE.PY — CHAY THU KHONG CAN SHEETS
  v2.0
=================================================
BUG FIX:
  - decode UTF-8 co the crash neu QR chua ky tu la
    -> dung errors='replace'
  - Vong lap vo han khi camera loi (ret=False) 
    -> them max_fail_count

MOI:
  - Hien FPS thuc te goc tren trai
  - Ghi lich su quet vao file test_log.txt (tuy chon)
  - Hien ten hoc sinh neu MaHS trung voi students.csv
  - Phim S: hien tong ket; phim C: xoa lich su

Cach dung:
    python test_offline.py
    python test_offline.py --log       # Ghi ra test_log.txt
    python test_offline.py --camera 1  # Dung camera index 1
"""

import cv2
from pyzbar import pyzbar
import time
import numpy as np
import csv
import os
import argparse

BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
CSV_PATHS = [
    os.path.join(BASE_DIR, "data", "students.csv"),
    os.path.join(BASE_DIR, "students.csv")
]
COOLDOWN  = 3   # giay


def load_students_local():
    """Doc students.csv neu co, tra ve dict {MaHS: HoTen}."""
    students = {}
    csv_file = next((p for p in CSV_PATHS if os.path.isfile(p)), None)
    if not csv_file:
        return students
    try:
        with open(csv_file, encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                ma  = row.get("MaHS", "").strip()
                ten = row.get("HoTen", "").strip()
                if ma:
                    students[ma] = ten
    except Exception:
        pass
    return students


def run(camera_index=0, log_to_file=False):
    students     = load_students_local()
    log_path     = os.path.join(BASE_DIR, "test_log.txt") if log_to_file else None
    log_fh       = open(log_path, "a", encoding="utf-8") if log_path else None

    # [BUG FIX] them max_fail_count
    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        print(f"[!!] Khong mo duoc camera (index={camera_index})!")
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    cap.set(cv2.CAP_PROP_BUFFERSIZE,   1)

    print("=" * 54)
    print("  TEST OFFLINE — Camera + QR Reader  v2.0")
    print(f"  Camera index: {camera_index}")
    print(f"  Hoc sinh trong CSV: {len(students)}")
    if log_path:
        print(f"  Ghi log ra: {log_path}")
    print("  Phim: Q=Thoat  S=Tong ket  C=Xoa lich su")
    print("=" * 54)

    cooldown_map  = {}
    scan_history  = []   # [(ts, raw, name)]
    fail_count    = 0
    MAX_FAILS     = 30

    # FPS tracking
    fps_counter   = 0
    fps_start     = time.time()
    fps_display   = 0.0

    while True:
        ret, frame = cap.read()

        # [BUG FIX] Thoat neu camera loi lien tuc
        if not ret:
            fail_count += 1
            if fail_count >= MAX_FAILS:
                print(f"[!!] Camera mat ket noi sau {MAX_FAILS} lan thu. Thoat.")
                break
            time.sleep(0.03)
            continue
        fail_count = 0

        now = time.time()
        fps_counter += 1
        elapsed = now - fps_start
        if elapsed >= 1.0:
            fps_display = fps_counter / elapsed
            fps_counter = 0
            fps_start   = now

        # Quet QR
        decoded = pyzbar.decode(frame)
        for obj in decoded:
            # [BUG FIX] errors='replace' thay vi mac dinh strict
            raw  = obj.data.decode("utf-8", errors="replace").strip()
            last = cooldown_map.get(raw, 0)
            if now - last < COOLDOWN:
                continue

            cooldown_map[raw] = now
            ts   = time.strftime("%H:%M:%S")
            name = students.get(raw, "Khong trong danh sach")
            scan_history.append((ts, raw, name))

            print(f"  [{ts}]  {raw}  |  {name}")

            if log_fh:
                log_fh.write(f"{time.strftime('%d/%m/%Y %H:%M:%S')}  {raw}  {name}\n")
                log_fh.flush()

            # Ve khung xanh / do
            pts   = np.array([p for p in obj.polygon], dtype=np.int32)
            color = (0, 220, 80) if raw in students else (0, 60, 220)
            cv2.polylines(frame, [pts], True, color, 3)

            # Nhan ten
            label    = f"{name} [{raw}]" if raw in students else raw[:30]
            label_pt = (pts[pts[:, 1].argmin()][0], max(pts[:, 1].min() - 10, 15))
            cv2.putText(frame, label, label_pt,
                        cv2.FONT_HERSHEY_SIMPLEX, 0.58, color, 2)

        # ── HUD ──────────────────────────────────────────────────────────
        h, w = frame.shape[:2]

        # FPS
        cv2.putText(frame, f"FPS: {fps_display:.1f}",
                    (15, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 200, 255), 2)

        # So QR trong khung
        cv2.putText(frame, f"QR trong khung: {len(decoded)}",
                    (15, 56), cv2.FONT_HERSHEY_SIMPLEX, 0.60, (255, 200, 0), 1)

        # Tong so da quet
        cv2.putText(frame, f"Tong da quet: {len(scan_history)}",
                    (15, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1)

        # Lich su 3 ban quet cuoi (goc phai)
        for i, (ts, raw, name) in enumerate(scan_history[-3:][::-1]):
            alpha_text = (180 - i * 40, 180 - i * 40, 180 - i * 40)
            cv2.putText(frame, f"{ts}  {name[:16]}",
                        (w - 310, h - 110 + i * 28),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, alpha_text, 1)

        # Footer
        cv2.putText(frame, "Q=Thoat  S=Tong ket  C=Xoa lich su",
                    (15, h - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (120, 120, 120), 1)

        cv2.imshow("Test Offline v2.0", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q") or key == 27:
            break
        elif key == ord("s"):
            # Tong ket
            known   = sum(1 for _, r, _ in scan_history if r in students)
            unknown = len(scan_history) - known
            print("\n" + "=" * 40)
            print(f"  TONG KET TEST")
            print(f"  Tong luot quet : {len(scan_history)}")
            print(f"  Co trong DS    : {known}")
            print(f"  Khong trong DS : {unknown}")
            print("=" * 40 + "\n")
        elif key == ord("c"):
            scan_history.clear()
            cooldown_map.clear()
            print("[OK] Da xoa lich su.")

    cap.release()
    cv2.destroyAllWindows()
    if log_fh:
        log_fh.close()
    print(f"\n[OK] Ket thuc. Tong so QR da quet: {len(scan_history)}")


# =============================================================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test camera + QR offline")
    parser.add_argument("--camera", type=int, default=0,
                        help="Camera index (mac dinh: 0)")
    parser.add_argument("--log",    action="store_true",
                        help="Ghi ket qua ra test_log.txt")
    args = parser.parse_args()
    run(camera_index=args.camera, log_to_file=args.log)
