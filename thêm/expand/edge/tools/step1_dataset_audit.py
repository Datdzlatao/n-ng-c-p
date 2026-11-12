# -*- coding: utf-8 -*-
"""
=============================================================
  BƯỚC 1A — KIỂM KÊ DATASET
  step1_dataset_audit.py

  Script này quét toàn bộ thư mục data/uniform_picdemo và:
  1. Đếm số ảnh từng loại, từng dân tộc
  2. Kiểm tra định dạng file hợp lệ
  3. Phát hiện ảnh lỗi / kích thước quá nhỏ
  4. Đưa ra khuyến nghị bổ sung dữ liệu
  5. Xuất báo cáo chi tiết ra file audit_report.txt

  Chạy:
    python step1_dataset_audit.py
    python step1_dataset_audit.py --show-samples   (hiện ảnh mẫu)
=============================================================
"""

import sys
import os
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import argparse
from pathlib import Path
from datetime import datetime
import json

# CẤU HÌNH
# ──────────────────────────────────────────────────────────────────────
BASE_DIR   = Path(__file__).parent
_CANDIDATES = [
    BASE_DIR.parents[1] / "backend" / "data",
    BASE_DIR.parent / "data",
    BASE_DIR / "data",
    BASE_DIR.parents[1] / "data",
]
DATA_DIR   = next((d for d in _CANDIDATES if (d / "uniform_picdemo").exists()), BASE_DIR / "data")
PICDEMO    = DATA_DIR / "uniform_picdemo"
REPORT_OUT = DATA_DIR / "audit_report.txt"

SUPPORTED_EXT   = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}
MIN_IMAGE_SIZE  = 32          # px — ảnh nhỏ hơn coi là lỗi
MIN_RECOMMENDED = 50          # ảnh tối thiểu khuyến nghị mỗi nhãn chính
MIN_ABSOLUTE    = 20          # ảnh tối thiểu tuyệt đối để train được

# Nhãn chính của hệ thống
MAIN_LABELS = {
    "trang_phuc_dan_toc": "Trang phục dân tộc (Thứ 2 — AI)",
    "ao_trang"          : "Áo trắng (Thứ 3, 5 — Color Analyzer)",
    "ao_doan"           : "Áo Đoàn (Thứ 6 — Color Analyzer)",
}

# ──────────────────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────────────────
def collect_images(directory: Path) -> list[Path]:
    """Thu thập tất cả file ảnh hợp lệ từ thư mục (đệ quy)."""
    return [
        p for p in directory.rglob("*")
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXT
    ]


def check_image_valid(path: Path) -> tuple[bool, str, tuple]:
    """
    Kiểm tra ảnh có đọc được không, trả về (ok, error_msg, size).
    Dùng OpenCV nếu có, fallback sang PIL.
    """
    try:
        import cv2
        img = cv2.imread(str(path))
        if img is None:
            return False, "Không đọc được (file lỗi hoặc không phải ảnh)", (0, 0)
        h, w = img.shape[:2]
        if h < MIN_IMAGE_SIZE or w < MIN_IMAGE_SIZE:
            return False, f"Ảnh quá nhỏ ({w}×{h}px)", (w, h)
        return True, "", (w, h)
    except Exception as e:
        return False, str(e), (0, 0)


def format_bar(value: int, max_value: int, width: int = 30) -> str:
    """Tạo thanh tiến trình ASCII."""
    if max_value == 0:
        return "─" * width
    filled = int(value / max_value * width)
    return "█" * filled + "░" * (width - filled)


# ──────────────────────────────────────────────────────────────────────
# HÀM KIỂM KÊ CHÍNH
# ──────────────────────────────────────────────────────────────────────
def audit_dataset(show_samples: bool = False) -> dict:
    """Kiểm kê toàn bộ dataset và trả về kết quả."""

    lines = []          # Dòng báo cáo để ghi file
    stats = {}          # Dict kết quả

    def log(msg: str = ""):
        print(msg)
        lines.append(msg)

    # ── HEADER ──
    log("=" * 70)
    log("  KIỂM KÊ DATASET — HỆ THỐNG NHẬN DIỆN TRANG PHỤC HỌC SINH")
    log(f"  Thời điểm: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"  Nguồn    : {PICDEMO}")
    log("=" * 70)

    if not PICDEMO.exists():
        log(f"\n[LỖI] Không tìm thấy thư mục: {PICDEMO}")
        log("      Hãy đảm bảo thư mục data/uniform_picdemo tồn tại.")
        return {}

    # ── THỐNG KÊ TỪNG NHÃN CHÍNH ──
    log("\n📁 THỐNG KÊ TỪNG NHÃN CHÍNH")
    log("─" * 70)

    total_all    = 0
    broken_files = []

    for folder_name, desc in MAIN_LABELS.items():
        folder_path = PICDEMO / folder_name
        if not folder_path.exists():
            log(f"\n  ⚠️  [{folder_name}] — Không tìm thấy thư mục!")
            stats[folder_name] = {"total": 0, "valid": 0, "broken": [], "subfolders": {}}
            continue

        all_images = collect_images(folder_path)
        valid      = []
        broken     = []

        for img_path in all_images:
            ok, err, size = check_image_valid(img_path)
            if ok:
                valid.append((img_path, size))
            else:
                broken.append((img_path, err))
                broken_files.append((img_path, err))

        # Thống kê subfolder (chỉ cho trang phục dân tộc)
        subfolders = {}
        if folder_name == "trang_phuc_dan_toc":
            for gender_dir in sorted(folder_path.iterdir()):
                if gender_dir.is_dir():
                    for ethnic_dir in sorted(gender_dir.iterdir()):
                        if ethnic_dir.is_dir():
                            imgs = collect_images(ethnic_dir)
                            label = f"{gender_dir.name}/{ethnic_dir.name}"
                            subfolders[label] = len(imgs)

        stats[folder_name] = {
            "total"     : len(all_images),
            "valid"     : len(valid),
            "broken"    : broken,
            "subfolders": subfolders,
            "sizes"     : [s for _, s in valid],
        }
        total_all += len(valid)

        # Biểu đồ ASCII
        bar   = format_bar(len(valid), max(len(valid), 1))
        emoji = "✅" if len(valid) >= MIN_RECOMMENDED else ("⚠️ " if len(valid) >= MIN_ABSOLUTE else "🚨")

        log(f"\n  {emoji} [{folder_name}]")
        log(f"     Mô tả  : {desc}")
        log(f"     Tổng   : {len(all_images)} file | Hợp lệ: {len(valid)} | Lỗi: {len(broken)}")
        log(f"     {bar} {len(valid)} ảnh")

        if len(broken) > 0:
            log(f"     ❌ File lỗi:")
            for p, e in broken[:5]:
                log(f"        - {p.name}: {e}")
            if len(broken) > 5:
                log(f"        ... và {len(broken) - 5} file khác")

        # Chi tiết dân tộc
        if subfolders:
            log(f"\n     📊 Phân bổ theo dân tộc ({len(subfolders)} nhóm):")
            sorted_sub = sorted(subfolders.items(), key=lambda x: x[1], reverse=True)
            max_sub    = sorted_sub[0][1] if sorted_sub else 1
            for sub_name, count in sorted_sub[:10]:  # Top 10
                bar_s = format_bar(count, max_sub, 20)
                log(f"        {bar_s} {count:3d}  {sub_name}")
            if len(sorted_sub) > 10:
                remaining = sum(c for _, c in sorted_sub[10:])
                log(f"        ... và {len(sorted_sub) - 10} nhóm khác ({remaining} ảnh)")

    # ── TỔNG KẾT ──
    log("\n" + "=" * 70)
    log("  TỔNG KẾT")
    log("=" * 70)
    log(f"  Tổng ảnh hợp lệ : {total_all}")
    log(f"  File lỗi        : {len(broken_files)}")
    log(f"  Nhãn kiểm kê    : {len(MAIN_LABELS)}")

    # ── PHÂN TÍCH CHO MODEL AI (CHỈ TRAIN DÂN TỘC vs OTHER) ──
    log("\n" + "─" * 70)
    log("  PHÂN TÍCH CHO MODEL AI (Thứ 2 — TFLite)")
    log("─" * 70)

    dan_toc_count = stats.get("trang_phuc_dan_toc", {}).get("valid", 0)
    ao_trang_count = stats.get("ao_trang", {}).get("valid", 0)
    ao_doan_count  = stats.get("ao_doan", {}).get("valid", 0)
    other_raw      = ao_trang_count + ao_doan_count

    log(f"\n  Nhãn 'trang_phuc_dan_toc' : {dan_toc_count} ảnh gốc")
    log(f"  Nhãn 'other' (áo trắng + áo đoàn) : {other_raw} ảnh gốc")

    if other_raw < 20:
        aug_factor = max(10, MIN_RECOMMENDED // max(other_raw, 1))
        log(f"\n  ⚠️  Nhãn 'other' QUÁ ÍT ({other_raw} ảnh)!")
        log(f"     → Script data_prep sẽ áp dụng augmentation x{aug_factor}")
        log(f"     → Ảnh 'other' sau augmentation: ~{other_raw * aug_factor}")
        log(f"\n  💡 KHUYẾN NGHỊ: Thêm ít nhất {max(0, 30 - other_raw)} ảnh vào:")
        log(f"     - data/uniform_picdemo/ao_trang/  (thêm ảnh áo trắng)")
        log(f"     - data/uniform_picdemo/ao_doan/   (thêm ảnh áo đoàn)")
        log(f"     Hoặc thêm ảnh thường vào: data/uniform_picdemo/other/")
    else:
        log(f"\n  ✅ Nhãn 'other' đủ dữ liệu ({other_raw} ảnh)")

    # Đề xuất augmentation
    log("\n  📦 Dự kiến dataset sau data_prep:")
    aug_other  = max(other_raw, 7) * 15  # Augmentation mạnh
    final_dan  = dan_toc_count
    log(f"     trang_phuc_dan_toc : {final_dan} ảnh (gốc + light aug)")
    log(f"     other              : ~{aug_other} ảnh (gốc + heavy aug)")

    # ── KHUYẾN NGHỊ ──
    log("\n" + "─" * 70)
    log("  KHUYẾN NGHỊ & BƯỚC TIẾP THEO")
    log("─" * 70)

    recommendations = []
    if dan_toc_count < MIN_RECOMMENDED:
        recommendations.append(f"Bổ sung thêm ảnh dân tộc (hiện có {dan_toc_count}, khuyến nghị ≥{MIN_RECOMMENDED})")
    if other_raw < 10:
        recommendations.append(f"Bổ sung ảnh 'other' (hiện có {other_raw}, cần ≥20 ảnh thực)")
    if len(broken_files) > 0:
        recommendations.append(f"Xóa/sửa {len(broken_files)} file ảnh lỗi")

    if recommendations:
        log("\n  ⚡ Cần thực hiện trước khi training:")
        for i, rec in enumerate(recommendations, 1):
            log(f"     {i}. {rec}")
    else:
        log("\n  ✅ Dataset sẵn sàng để chuẩn bị!")

    log("\n  📋 BƯỚC TIẾP THEO:")
    log("     1. python step1_data_prep_v2.py    — Chuẩn bị dataset train/val")
    log("     2. python step1_hsv_calibrator.py  — Calibrate ngưỡng màu HSV")
    log("     3. python uniform_trainer.py       — Huấn luyện model AI")
    log("=" * 70)

    # ── LƯU REPORT ──
    REPORT_OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT_OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    log(f"\n  📄 Báo cáo đã lưu tại: {REPORT_OUT}")

    # ── LƯU STATS JSON ──
    stats_path = DATA_DIR / "audit_stats.json"
    safe_stats = {}
    for label, info in stats.items():
        safe_stats[label] = {
            "total"     : info.get("total", 0),
            "valid"     : info.get("valid", 0),
            "broken"    : len(info.get("broken", [])),
            "subfolders": info.get("subfolders", {}),
        }
    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump(safe_stats, f, ensure_ascii=False, indent=2)

    # ── HIỆN ẢNH MẪU NẾU YÊU CẦU ──
    if show_samples:
        _show_sample_grid(stats)

    return stats


def _show_sample_grid(stats: dict):
    """Hiển thị lưới ảnh mẫu từ mỗi nhãn (cần matplotlib + cv2)."""
    try:
        import cv2
        import numpy as np
        import matplotlib
        matplotlib.use("TkAgg")
        import matplotlib.pyplot as plt
        from matplotlib.gridspec import GridSpec
    except ImportError:
        print("\n[SKIP] Cần cài matplotlib để xem ảnh mẫu: pip install matplotlib")
        return

    fig = plt.figure(figsize=(16, 8))
    fig.suptitle("Mẫu Ảnh Dataset — Hệ Thống Nhận Diện Trang Phục", fontsize=14, fontweight="bold")

    all_samples = []
    for label in MAIN_LABELS:
        info = stats.get(label, {})
        folder_path = PICDEMO / label
        if not folder_path.exists():
            continue
        imgs = list(collect_images(folder_path))
        import random
        samples = random.sample(imgs, min(4, len(imgs)))
        for p in samples:
            all_samples.append((label, p))

    cols = min(8, len(all_samples))
    rows = max(1, (len(all_samples) + cols - 1) // cols)

    for idx, (label, path) in enumerate(all_samples):
        ax = fig.add_subplot(rows, cols, idx + 1)
        img = cv2.imread(str(path))
        if img is not None:
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            img = cv2.resize(img, (128, 128))
            ax.imshow(img)
        ax.set_title(label.replace("trang_phuc_dan_toc", "DT")
                        .replace("ao_trang", "Trắng")
                        .replace("ao_doan", "Đoàn"), fontsize=8)
        ax.axis("off")

    plt.tight_layout()
    plt.show()


# ──────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Kiểm kê dataset trang phục học sinh")
    parser.add_argument("--show-samples", action="store_true",
                        help="Hiển thị lưới ảnh mẫu (cần matplotlib)")
    args = parser.parse_args()
    audit_dataset(show_samples=args.show_samples)
