"""
=============================================================
  BƯỚC 4: HƯỚNG DẪN SỬ DỤNG TOÀN BỘ HỆ THỐNG
  uniform_run.py

  Script tích hợp và kiểm tra nhanh toàn bộ pipeline
  Chạy: python uniform_run.py
=============================================================
"""

import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent

def check_requirements():
    """Kiểm tra các thư viện cần thiết."""
    required = {
        "tensorflow" : "tensorflow",
        "cv2"        : "opencv-python",
        "numpy"      : "numpy",
        "PIL"        : "Pillow",
    }
    missing = []
    for module, package in required.items():
        try:
            __import__(module)
        except ImportError:
            missing.append(package)
    return missing


def print_banner():
    print("""
╔══════════════════════════════════════════════════════════╗
║     HỆ THỐNG NHẬN DIỆN TRANG PHỤC HỌC SINH - STEM      ║
║                  AI TFLite + OpenCV                      ║
╚══════════════════════════════════════════════════════════╝

QUY ĐỊNH TRANG PHỤC:
  ┌─────────┬──────────────────────────────────────────┐
  │ Thứ 2   │ 👘 Trang phục dân tộc                    │
  │ Thứ 3   │ 👔 Áo trắng                              │
  │ Thứ 4   │ 👕 Tự do (phải có cổ - không check AI)   │
  │ Thứ 5   │ 👔 Áo trắng                              │
  │ Thứ 6   │ 🔵 Áo đoàn viên                          │
  │ Thứ 7   │ 🏖️  Nghỉ - Không yêu cầu                 │
  │ CN      │ 🏖️  Nghỉ - Không yêu cầu                 │
  └─────────┴──────────────────────────────────────────┘
""")


def main():
    print_banner()

    # ==================== BƯỚC 0: KIỂM TRA THƯ VIỆN ====================
    print("[ BƯỚC 0 ] Kiểm tra thư viện...")
    missing = check_requirements()
    if missing:
        print(f"\n[CẢNH BÁO] Thiếu thư viện: {missing}")
        print("Chạy lệnh sau để cài đặt:")
        print(f"  pip install {' '.join(missing)}\n")
        install = input("Cài đặt tự động ngay bây giờ? (y/n): ").strip().lower()
        if install == "y":
            for pkg in missing:
                subprocess.run([sys.executable, "-m", "pip", "install", pkg], check=True)
            print("[OK] Cài đặt xong!\n")
        else:
            print("[EXIT] Vui lòng cài đặt thư viện trước khi tiếp tục.")
            return
    else:
        print("[OK] Đầy đủ thư viện.\n")

    # ==================== BƯỚC 1: KIỂM TRA DATASET ====================
    print("[ BƯỚC 1 ] Kiểm tra dataset...")
    _DATA_CANDIDATES = [
        BASE_DIR / "data",
        BASE_DIR.parent / "data",
        BASE_DIR.parents[1] / "backend" / "data",
        BASE_DIR.parents[1] / "data",
    ]
    data_dir = next((d for d in _DATA_CANDIDATES if (d / "uniform_dataset_v2").exists() or (d / "uniform_dataset").exists() or (d / "uniform_picdemo").exists()), BASE_DIR / "data")
    dataset_dir = data_dir / "uniform_dataset_v2" if (data_dir / "uniform_dataset_v2").exists() else data_dir / "uniform_dataset"
    source_dir  = data_dir / "uniform_picdemo"

    if not source_dir.exists() and not dataset_dir.exists():
        print(f"[LỖI] Không tìm thấy thư mục ảnh gốc: {source_dir}")
        print("      Hãy đảm bảo ảnh đã được đặt vào đúng thư mục.")
        return

    if not dataset_dir.exists():
        print("[INFO] Dataset chưa được tổ chức. Đang chạy bước chuẩn bị...")
        subprocess.run([sys.executable, "uniform_dataset_prep.py"], check=True)
    else:
        print(f"[OK] Dataset đã sẵn sàng tại: {dataset_dir}")

    # Báo cáo số lượng ảnh
    train_dir = dataset_dir / "train"
    if train_dir.exists():
        for cls_dir in sorted(train_dir.iterdir()):
            if cls_dir.is_dir():
                count = len(list(cls_dir.glob("*")))
                print(f"       {cls_dir.name:30s}: {count} ảnh (train)")

    # ==================== BƯỚC 2: KIỂM TRA MODEL ====================
    print("\n[ BƯỚC 2 ] Kiểm tra model AI...")
    model_path = next((d / "uniform_model_v2.tflite" for d in _DATA_CANDIDATES if (d / "uniform_model_v2.tflite").exists()), None)
    if model_path is None:
        model_path = next((d / "uniform_model.tflite" for d in _DATA_CANDIDATES if (d / "uniform_model.tflite").exists()), None)

    if model_path is None or not model_path.exists():
        print("[INFO] Model chưa được training.")
        train_now = input("Bắt đầu training ngay bây giờ? (y/n): ").strip().lower()
        if train_now == "y":
            print("\n[TRAINING] Đang bắt đầu... Quá trình có thể mất 10-40 phút.")
            subprocess.run([sys.executable, "uniform_trainer.py"], check=True)
        else:
            print("[INFO] Bạn có thể chạy training sau bằng lệnh: python uniform_trainer.py")
            return
    else:
        size_mb = model_path.stat().st_size / (1024 * 1024)
        print(f"[OK] Model đã sẵn sàng: {model_path.name} ({size_mb:.1f} MB tại {model_path})")

    # ==================== BƯỚC 3: CHỌN CHẾ ĐỘ CHẠY ====================
    print("\n[ BƯỚC 3 ] Chọn chế độ chạy:")
    print("  1. Test camera realtime (webcam)")
    print("  2. Test với ảnh tĩnh (file ảnh)")
    print("  3. Xem thông tin quy định trang phục hôm nay")
    print("  4. Thoát")

    choice = input("\nNhập lựa chọn (1-4): ").strip()

    if choice == "1":
        print("\n[START] Mở camera... Nhấn Q để thoát.\n")
        subprocess.run([sys.executable, "uniform_checker.py"])

    elif choice == "2":
        img_path = input("Nhập đường dẫn file ảnh: ").strip().strip('"')
        if Path(img_path).exists():
            subprocess.run([sys.executable, "uniform_checker.py", "--image", img_path])
        else:
            print(f"[LỖI] Không tìm thấy file: {img_path}")

    elif choice == "3":
        from uniform_checker import UniformChecker
        from datetime import datetime
        checker = UniformChecker()
        weekday = datetime.now().weekday()
        day_names = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ nhật"]
        print(f"\n  Hôm nay là   : {day_names[weekday]}")
        print(f"  Quy định     : {checker.get_today_rule_display()}")
        print(f"  Thời gian    : {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}")

    elif choice == "4":
        print("Thoát. Tạm biệt!")

    else:
        print("[LỖI] Lựa chọn không hợp lệ.")


if __name__ == "__main__":
    main()
