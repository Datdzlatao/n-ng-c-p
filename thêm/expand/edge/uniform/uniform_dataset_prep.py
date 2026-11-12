# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
"""
=============================================================
  BUOC 1: CHUAN BI DATASET
  uniform_dataset_prep.py
  
  Script này sẽ:
  1. Quét toàn bộ thư mục data/uniform_picdemo
  2. Gộp tất cả ảnh dân tộc nam + nữ vào 1 nhãn "trang_phuc_dan_toc"
  3. Chia dataset thành train (80%) / val (20%)
  4. Tạo thư mục dataset/ chuẩn bị cho bước training
  5. Báo cáo số lượng ảnh từng loại
=============================================================
"""

import os
import shutil
import random
from pathlib import Path

# ==================== CẤU HÌNH ====================
BASE_DIR        = Path(__file__).parent
SOURCE_DIR      = BASE_DIR / "data" / "uniform_picdemo"
OUTPUT_DIR      = BASE_DIR / "data" / "uniform_dataset"
TRAIN_RATIO     = 0.8
SUPPORTED_EXT   = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
random.seed(42)  # Đảm bảo kết quả chia dataset giống nhau mỗi lần chạy

# ==================== ÁNH XẠ NHÃN ====================
# Mỗi nhãn tương ứng với một thư mục con trong uniform_picdemo
# Các thư mục con sẽ được gộp lại thành 1 nhãn duy nhất
LABEL_MAP = {
    "ao_doan"           : "ao_doan",           # Áo đoàn viên (Thứ 6)
    "ao_trang"          : "ao_trang",           # Áo trắng (Thứ 3, Thứ 5)
    "trang_phuc_dan_toc": "trang_phuc_dan_toc", # Trang phục dân tộc (Thứ 2)
}


def collect_images_from_dir(directory: Path) -> list:
    """Thu thập tất cả ảnh từ thư mục và tất cả thư mục con (đệ quy)."""
    images = []
    for root, _, files in os.walk(directory):
        for file in files:
            ext = Path(file).suffix.lower()
            if ext in SUPPORTED_EXT:
                images.append(Path(root) / file)
    return images


def prepare_dataset():
    print("=" * 60)
    print("  CHUAN BI DATASET NHAN DIEN TRANG PHUC")
    print("=" * 60)
    
    # Xóa dataset cũ nếu có, tạo lại từ đầu
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
        print(f"[INFO] Đã xóa dataset cũ tại: {OUTPUT_DIR}")

    stats = {}

    for source_folder_name, label in LABEL_MAP.items():
        source_path = SOURCE_DIR / source_folder_name
        
        if not source_path.exists():
            print(f"[WARN] Không tìm thấy thư mục: {source_path}")
            continue

        # Thu thập tất cả ảnh (bao gồm cả subfolder trang phục dân tộc)
        all_images = collect_images_from_dir(source_path)
        
        if not all_images:
            print(f"[WARN] Không có ảnh trong: {source_path}")
            continue

        # Xáo trộn ngẫu nhiên
        random.shuffle(all_images)
        
        # Chia train / val
        split_idx  = int(len(all_images) * TRAIN_RATIO)
        train_imgs = all_images[:split_idx]
        val_imgs   = all_images[split_idx:]

        # Đảm bảo val có ít nhất 1 ảnh
        if len(val_imgs) == 0 and len(train_imgs) > 1:
            val_imgs   = train_imgs[-1:]
            train_imgs = train_imgs[:-1]

        # Tạo thư mục đích
        for split, imgs in [("train", train_imgs), ("val", val_imgs)]:
            dest_dir = OUTPUT_DIR / split / label
            dest_dir.mkdir(parents=True, exist_ok=True)
            
            for idx, img_path in enumerate(imgs):
                ext      = img_path.suffix.lower()
                new_name = f"{label}_{split}_{idx:04d}{ext}"
                dest     = dest_dir / new_name
                shutil.copy2(img_path, dest)

        stats[label] = {
            "total": len(all_images),
            "train": len(train_imgs),
            "val"  : len(val_imgs),
        }
        print(f"[OK] {label:30s} | Tổng: {len(all_images):4d} | Train: {len(train_imgs):4d} | Val: {len(val_imgs):4d}")

    # ==================== BÁO CÁO ====================
    print("\n" + "=" * 60)
    print("  KET QUA CHUAN BI DATASET")
    print("=" * 60)
    total_all   = sum(v["total"] for v in stats.values())
    total_train = sum(v["train"] for v in stats.values())
    total_val   = sum(v["val"]   for v in stats.values())
    print(f"  So nhan (classes)  : {len(stats)}")
    print(f"  Tong anh           : {total_all}")
    print(f"  Anh training       : {total_train} ({total_train/total_all*100:.0f}%)")
    print(f"  Anh validation     : {total_val}   ({total_val/total_all*100:.0f}%)")
    print(f"  Duong dan output   : {OUTPUT_DIR}")
    print("=" * 60)
    
    # Canh bao neu dataset qua it
    for label, s in stats.items():
        if s["total"] < 30:
            print(f"\n[CANH BAO] '{label}' chi co {s['total']} anh.")
            print("           Khuyen dung it nhat 50-100 anh/nhan de model chinh xac hon.")
            print("           He thong van chay duoc nhung do chinh xac co the thap.")
    
    print("\n[DONE] San sang chay buoc training: python uniform_trainer.py")
    return stats


if __name__ == "__main__":
    prepare_dataset()
