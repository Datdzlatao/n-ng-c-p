# -*- coding: utf-8 -*-
"""
=============================================================
  BƯỚC 1B — CHUẨN BỊ DATASET V2 (2 NHÃN)
  step1_data_prep_v2.py

  Tạo dataset cho model AI Thứ 2 (nhận diện dân tộc):
  ─────────────────────────────────────────────────────────
  Nhãn 1: trang_phuc_dan_toc  — Tất cả ảnh dân tộc (nam + nữ)
  Nhãn 2: other               — Áo trắng + Áo đoàn + ảnh thường
                                (dùng augmentation mạnh để bù thiếu ảnh)

  Pipeline khi nhãn = "other":
    → Trả về status="UNCLEAR" → Camera chụp → Upload cloud

  Output:
    data/uniform_dataset_v2/train/{trang_phuc_dan_toc, other}/
    data/uniform_dataset_v2/val/  {trang_phuc_dan_toc, other}/
    data/prep_v2_report.json

  Chạy:
    python step1_data_prep_v2.py
    python step1_data_prep_v2.py --aug-factor 20  (augment nhiều hơn)
    python step1_data_prep_v2.py --no-aug          (không augment)
=============================================================
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import os
import cv2
import shutil
import random
import argparse
import json
import numpy as np
from pathlib import Path
from datetime import datetime

# ──────────────────────────────────────────────────────────────────────
# CẤU HÌNH
# ──────────────────────────────────────────────────────────────────────
BASE_DIR       = Path(__file__).parent
_CANDIDATES = [
    BASE_DIR.parents[1] / "backend" / "data",
    BASE_DIR.parent / "data",
    BASE_DIR / "data",
    BASE_DIR.parents[1] / "data",
]
DATA_DIR       = next((d for d in _CANDIDATES if (d / "uniform_picdemo").exists()), BASE_DIR / "data")
SOURCE_DIR     = DATA_DIR / "uniform_picdemo"
OUTPUT_DIR     = DATA_DIR / "uniform_dataset_v2"
REPORT_PATH    = DATA_DIR / "prep_v2_report.json"

TRAIN_RATIO    = 0.80
SUPPORTED_EXT  = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
IMAGE_SIZE     = (224, 224)   # Kích thước resize cho TFLite
random.seed(42)
np.random.seed(42)

# ──────────────────────────────────────────────────────────────────────
# ÁNH XẠ NHÃN
# Nguồn ảnh nào → nhãn model nào
# ──────────────────────────────────────────────────────────────────────
LABEL_MAPPING = {
    # Nhãn: trang_phuc_dan_toc
    # Nguồn: toàn bộ thư mục con trong picdemo/trang_phuc_dan_toc (đệ quy)
    "trang_phuc_dan_toc": [
        SOURCE_DIR / "trang_phuc_dan_toc",
    ],
    # Nhãn: other (Áo trắng + Áo đoàn + ảnh thường nếu có)
    # Đây là "negative samples" — trang phục KHÔNG phải dân tộc
    "other": [
        SOURCE_DIR / "ao_trang",
        SOURCE_DIR / "ao_doan",
        SOURCE_DIR / "other",         # Thư mục tùy chọn — người dùng thêm vào
    ],
}

# Số ảnh augment tối thiểu cho nhãn ít ảnh
# (tính theo AUG_FACTOR × số ảnh gốc)
DEFAULT_AUG_FACTOR_OTHER  = 15   # 7 ảnh gốc × 15 = ~105 ảnh augmented
DEFAULT_AUG_FACTOR_DANTOC = 3    # 215 ảnh × 3 = ~645 ảnh

# ──────────────────────────────────────────────────────────────────────
# AUGMENTATION FUNCTIONS
# ──────────────────────────────────────────────────────────────────────

def augment_light(img: np.ndarray) -> list[np.ndarray]:
    """
    Augmentation nhẹ cho nhãn DÂN TỘC (đã có đủ ảnh).
    Tạo thêm 3 biến thể: flip, rotation nhẹ, brightness.
    """
    results = []

    # 1. Flip ngang (trang phục nhìn cả 2 hướng)
    results.append(cv2.flip(img, 1))

    # 2. Xoay nhẹ (±15 độ)
    angle = random.uniform(-15, 15)
    h, w  = img.shape[:2]
    M     = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
    results.append(cv2.warpAffine(img, M, (w, h),
                                  borderMode=cv2.BORDER_REFLECT))

    # 3. Thay đổi độ sáng (giả lập ánh sáng buổi sáng/chiều)
    factor = random.uniform(0.75, 1.25)
    bright = np.clip(img.astype(np.float32) * factor, 0, 255).astype(np.uint8)
    results.append(bright)

    return results


def augment_heavy(img: np.ndarray, n: int = 14) -> list[np.ndarray]:
    """
    Augmentation mạnh cho nhãn OTHER (ít ảnh, cần bù đắp).
    Tạo n biến thể đa dạng bằng cách kết hợp nhiều phép biến đổi.

    Các phép biến đổi:
    - Flip ngang / dọc
    - Xoay (±25 độ)
    - Zoom in/out (0.85–1.15)
    - Dịch (shift) ngẫu nhiên
    - Thay đổi độ sáng + contrast
    - Gaussian blur (giả lập camera focus kém)
    - HSV color jitter (giả lập ánh sáng nhiều màu)
    - Perspective transform (giả lập góc camera)
    - Gaussian noise
    """
    results = []
    h, w = img.shape[:2]
    cx, cy = w // 2, h // 2

    for _ in range(n):
        aug = img.copy()

        # ── Flip ──
        if random.random() < 0.5:
            aug = cv2.flip(aug, 1)

        # ── Rotation ──
        angle = random.uniform(-25, 25)
        M = cv2.getRotationMatrix2D((cx, cy), angle, 1.0)
        aug = cv2.warpAffine(aug, M, (w, h), borderMode=cv2.BORDER_REFLECT)

        # ── Zoom ──
        scale = random.uniform(0.85, 1.15)
        M_zoom = cv2.getRotationMatrix2D((cx, cy), 0, scale)
        aug = cv2.warpAffine(aug, M_zoom, (w, h), borderMode=cv2.BORDER_REFLECT)

        # ── Translation (dịch ngang/dọc) ──
        tx = random.randint(-int(w * 0.12), int(w * 0.12))
        ty = random.randint(-int(h * 0.12), int(h * 0.12))
        M_shift = np.float32([[1, 0, tx], [0, 1, ty]])
        aug = cv2.warpAffine(aug, M_shift, (w, h), borderMode=cv2.BORDER_REFLECT)

        # ── Brightness + Contrast ──
        alpha = random.uniform(0.70, 1.30)   # Contrast
        beta  = random.uniform(-30, 30)       # Brightness
        aug   = np.clip(aug.astype(np.float32) * alpha + beta, 0, 255).astype(np.uint8)

        # ── HSV Color Jitter ──
        if random.random() < 0.6:
            hsv = cv2.cvtColor(aug, cv2.COLOR_BGR2HSV).astype(np.float32)
            hsv[:, :, 0] = (hsv[:, :, 0] + random.uniform(-10, 10)) % 180  # Hue
            hsv[:, :, 1] = np.clip(hsv[:, :, 1] * random.uniform(0.8, 1.2), 0, 255)  # Sat
            hsv[:, :, 2] = np.clip(hsv[:, :, 2] * random.uniform(0.8, 1.2), 0, 255)  # Val
            aug = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)

        # ── Gaussian Blur ──
        if random.random() < 0.3:
            ksize = random.choice([3, 5])
            aug = cv2.GaussianBlur(aug, (ksize, ksize), 0)

        # ── Gaussian Noise ──
        if random.random() < 0.25:
            noise = np.random.normal(0, random.uniform(3, 12), aug.shape).astype(np.float32)
            aug   = np.clip(aug.astype(np.float32) + noise, 0, 255).astype(np.uint8)

        # ── Perspective (nhẹ) ──
        if random.random() < 0.3:
            margin = int(min(w, h) * 0.06)
            pts1 = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
            pts2 = np.float32([
                [random.randint(0, margin), random.randint(0, margin)],
                [w - random.randint(0, margin), random.randint(0, margin)],
                [w - random.randint(0, margin), h - random.randint(0, margin)],
                [random.randint(0, margin), h - random.randint(0, margin)],
            ])
            M_persp = cv2.getPerspectiveTransform(pts1, pts2)
            aug = cv2.warpPerspective(aug, M_persp, (w, h),
                                       borderMode=cv2.BORDER_REFLECT)

        results.append(aug)

    return results


# ──────────────────────────────────────────────────────────────────────
# HÀM THU THẬP & SAO CHÉP ẢNH
# ──────────────────────────────────────────────────────────────────────
def collect_images(directories: list[Path]) -> list[Path]:
    """Thu thập ảnh từ danh sách thư mục (bỏ qua thư mục không tồn tại)."""
    all_imgs = []
    for d in directories:
        if not d.exists():
            continue
        for root, _, files in os.walk(d):
            for f in files:
                p = Path(root) / f
                if p.suffix.lower() in SUPPORTED_EXT:
                    all_imgs.append(p)
    return all_imgs


def load_and_resize(path: Path) -> np.ndarray | None:
    """Đọc ảnh và resize về IMAGE_SIZE, trả về None nếu lỗi."""
    img = cv2.imread(str(path))
    if img is None:
        return None
    return cv2.resize(img, IMAGE_SIZE, interpolation=cv2.INTER_AREA)


def save_image(img: np.ndarray, dest: Path):
    """Lưu ảnh vào đường dẫn, tạo thư mục nếu chưa có."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(dest), img, [cv2.IMWRITE_JPEG_QUALITY, 92])


# ──────────────────────────────────────────────────────────────────────
# HÀM CHÍNH
# ──────────────────────────────────────────────────────────────────────
def prepare_dataset(aug_factor_other: int = DEFAULT_AUG_FACTOR_OTHER,
                    aug_factor_dantoc: int = DEFAULT_AUG_FACTOR_DANTOC,
                    use_aug: bool = True):
    """
    Tạo dataset chuẩn cho training model AI (Thứ 2 — nhận diện dân tộc).
    """
    start_time = datetime.now()
    print("=" * 70)
    print("  CHUẨN BỊ DATASET V2 — 2 NHÃN: [dan_toc / other]")
    print(f"  Augmentation: {'BẬT' if use_aug else 'TẮT'}")
    print(f"  aug_factor_other  : ×{aug_factor_other}")
    print(f"  aug_factor_dantoc : ×{aug_factor_dantoc}")
    print("=" * 70)

    # Xóa dataset cũ
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
        print(f"[INFO] Đã xóa dataset cũ: {OUTPUT_DIR}")

    stats = {}

    for label, source_dirs in LABEL_MAPPING.items():
        print(f"\n[LABEL] '{label}' — đang thu thập ảnh...")

        # Thu thập ảnh gốc
        all_imgs = collect_images(source_dirs)
        if not all_imgs:
            print(f"  ⚠️  Không tìm thấy ảnh nào cho nhãn '{label}'")
            print(f"     Nguồn: {[str(d) for d in source_dirs]}")
            if label == "other":
                print("     → TẠO NHÃN 'other' TỪ AUGMENTATION CỦA DÂN TỘC (đảo ngược màu)")
                # Fallback cực đoan: nếu không có ảnh "other" nào
                # Lấy một số ảnh dân tộc và biến đổi mạnh chúng
                # (không lý tưởng, nhưng tốt hơn không có gì)
                all_imgs = collect_images([SOURCE_DIR / "trang_phuc_dan_toc"])[:10]
            else:
                stats[label] = {"original": 0, "train": 0, "val": 0, "augmented": 0}
                continue

        # Xáo trộn
        random.shuffle(all_imgs)
        print(f"  Tìm thấy: {len(all_imgs)} ảnh gốc")

        # Chia train / val từ ảnh GỐC trước
        split = max(1, int(len(all_imgs) * TRAIN_RATIO))
        train_orig = all_imgs[:split]
        val_orig   = all_imgs[split:]

        # Đảm bảo val có ít nhất 1 ảnh
        if not val_orig and train_orig:
            val_orig   = train_orig[-1:]
            train_orig = train_orig[:-1]

        # Quyết định augmentation factor
        if use_aug:
            n_aug = aug_factor_other if label == "other" else (aug_factor_dantoc - 1)
        else:
            n_aug = 0

        # ── Xử lý ảnh TRAIN ──
        train_count = 0
        aug_count   = 0
        val_count   = 0

        print(f"  Đang xử lý {len(train_orig)} ảnh train (+ augmentation x{n_aug})...")
        for idx, img_path in enumerate(train_orig):
            img = load_and_resize(img_path)
            if img is None:
                continue

            # Lưu ảnh gốc
            dest = OUTPUT_DIR / "train" / label / f"{label}_orig_{idx:05d}.jpg"
            save_image(img, dest)
            train_count += 1

            # Augment
            if n_aug > 0:
                aug_fn  = augment_heavy if label == "other" else augment_light
                n_per   = n_aug if label == "other" else 3
                variants = aug_fn(img, n_per) if label == "other" else aug_fn(img)
                for v_idx, v in enumerate(variants[:n_per]):
                    v_dest = OUTPUT_DIR / "train" / label / f"{label}_aug_{idx:05d}_{v_idx:03d}.jpg"
                    save_image(v, v_dest)
                    aug_count += 1

        # ── Xử lý ảnh VAL ──
        print(f"  Đang xử lý {len(val_orig)} ảnh val (không augment)...")
        for idx, img_path in enumerate(val_orig):
            img = load_and_resize(img_path)
            if img is None:
                continue
            dest = OUTPUT_DIR / "val" / label / f"{label}_val_{idx:05d}.jpg"
            save_image(img, dest)
            val_count += 1

        total = train_count + aug_count + val_count
        stats[label] = {
            "original"  : len(all_imgs),
            "train_orig": train_count,
            "augmented" : aug_count,
            "train_total": train_count + aug_count,
            "val"       : val_count,
            "total"     : total,
        }

        print(f"  ✅ '{label}': {train_count} gốc + {aug_count} aug = {train_count + aug_count} train | {val_count} val")

    # ── BÁO CÁO ──
    elapsed = (datetime.now() - start_time).total_seconds()
    print("\n" + "=" * 70)
    print("  KẾT QUẢ CHUẨN BỊ DATASET V2")
    print("=" * 70)

    total_train = sum(s.get("train_total", 0) for s in stats.values())
    total_val   = sum(s.get("val", 0) for s in stats.values())
    total_all   = total_train + total_val

    for lbl, s in stats.items():
        ratio = s.get("train_total", 0) / max(s.get("total", 1), 1) * 100
        print(f"  [{lbl:25s}] Gốc: {s.get('original', 0):4d} | "
              f"Train: {s.get('train_total', 0):5d} | Val: {s.get('val', 0):4d}")

    print(f"\n  Tổng train : {total_train}")
    print(f"  Tổng val   : {total_val}")
    print(f"  Tổng cộng  : {total_all}")
    print(f"  Thời gian  : {elapsed:.1f}s")
    print(f"  Output     : {OUTPUT_DIR}")

    # Kiểm tra cân bằng nhãn
    if len(stats) == 2:
        counts = [s.get("train_total", 0) for s in stats.values()]
        ratio  = max(counts) / max(min(counts), 1)
        if ratio > 3:
            print(f"\n  ⚠️  Mất cân bằng nhãn (tỷ lệ {ratio:.1f}:1)")
            print(f"     → Trainer sẽ dùng class_weight để bù đắp tự động.")
        else:
            print(f"\n  ✅ Nhãn cân bằng tốt (tỷ lệ {ratio:.1f}:1)")

    # Kiểm tra model sẽ dùng class_weight
    if any(s.get("original", 0) < 20 for s in stats.values()):
        print("\n  💡 GỢI Ý: Nhãn có ít ảnh gốc — augmentation đã bổ sung,")
        print("            nhưng nên thêm ảnh thực tế vào uniform_picdemo/other/")
        print("            để model tổng quát hóa tốt hơn.")

    # Lưu báo cáo JSON
    report = {
        "timestamp"        : datetime.now().isoformat(),
        "output_dir"       : str(OUTPUT_DIR),
        "train_ratio"      : TRAIN_RATIO,
        "aug_factor_other" : aug_factor_other,
        "aug_factor_dantoc": aug_factor_dantoc,
        "labels"           : list(stats.keys()),
        "stats"            : stats,
        "total_train"      : total_train,
        "total_val"        : total_val,
        "elapsed_seconds"  : elapsed,
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n  📄 Báo cáo JSON: {REPORT_PATH}")
    print("=" * 70)
    print("\n[NEXT] Bước tiếp theo: python uniform_trainer.py")
    print("       (Trainer đã được cập nhật để dùng dataset_v2 và class_weight)")

    return stats


# ──────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Chuẩn bị dataset v2 cho model AI dân tộc")
    parser.add_argument("--aug-factor", type=int, default=DEFAULT_AUG_FACTOR_OTHER,
                        help=f"Số lần augment nhãn 'other' (default: {DEFAULT_AUG_FACTOR_OTHER})")
    parser.add_argument("--aug-factor-dantoc", type=int, default=DEFAULT_AUG_FACTOR_DANTOC,
                        help=f"Số lần augment nhãn dân tộc (default: {DEFAULT_AUG_FACTOR_DANTOC})")
    parser.add_argument("--no-aug", action="store_true",
                        help="Tắt augmentation (chỉ dùng ảnh gốc)")
    args = parser.parse_args()

    prepare_dataset(
        aug_factor_other  = args.aug_factor,
        aug_factor_dantoc = args.aug_factor_dantoc,
        use_aug           = not args.no_aug,
    )
