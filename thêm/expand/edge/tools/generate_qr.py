"""
=================================================
  GENERATE_QR.PY — TAO THE QR CHO HOC SINH
=================================================
BUG FIX:
  - _font(): crash tren Linux khi khong co font -> fallback tot hon
  - make_card(): text bi tran khi ten qua dai

MOI:
  - The dep hon: them logo STEM, mau gradient, duong vien tinh te
  - In nhieu the tren 1 trang A4 (option --sheet)
  - Xuat PDF trang the (option --pdf)
  - Preview truoc khi in (hien 1 the mau)

Cach dung:
    python generate_qr.py              # Tao tung file PNG
    python generate_qr.py --preview    # Hien 1 the mau tren man hinh
    python generate_qr.py --sheet      # Xuat anh luoi nhieu the / trang A4
    python generate_qr.py --pdf        # Xuat file PDF (can: pip install reportlab)
"""

import qrcode
import csv
import os
import sys
import argparse
from PIL import Image, ImageDraw, ImageFont

# ── Cau hinh ──────────────────────────────────────────────────────────────────
INPUT_CSV  = "students.csv"
OUTPUT_DIR = "qr_cards"
CARD_W, CARD_H = 420, 560        # Pixel (tuong duong 3.5 x 4.7 cm @ 120 DPI)
QR_SIZE    = 300

# Mau sac
BG_COLOR      = (250, 250, 252)
HEADER_COLOR  = (25, 90, 185)
ACCENT_COLOR  = (0, 180, 120)
TEXT_COLOR    = (25, 25, 35)
SUB_COLOR     = (100, 105, 115)
BORDER_COLOR  = (200, 210, 230)

# Luoi A4 (in nhieu the tren 1 trang)
A4_W_PX, A4_H_PX = 2480, 3508   # A4 @ 300 DPI
CARDS_PER_ROW = 4
CARDS_PER_COL = 5
MARGIN_PX     = 60


# ── Font helper ──────────────────────────────────────────────────────────────
def _font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    """[BUG FIX] Thu cac font theo thu tu uu tien, fallback an toan."""
    candidates = []
    if bold:
        candidates = [
            # Windows
            "C:/Windows/Fonts/arialbd.ttf",
            "C:/Windows/Fonts/calibrib.ttf",
            # Linux
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf",
            # macOS
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
        ]
    else:
        candidates = [
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/calibri.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/usr/share/fonts/truetype/ubuntu/Ubuntu-R.ttf",
            "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
        ]

    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass

    # Fallback tuyet doi (PIL built-in)
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


# ── Tao 1 the QR ──────────────────────────────────────────────────────────────
def make_card(student_id: str, student_name: str, class_name: str = "") -> Image.Image:
    """[MOI] The dep hon voi header gradient va layout can doi."""

    # 1. Tao QR
    qr = qrcode.QRCode(
        version=3,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=8,
        border=2,
    )
    qr.add_data(student_id)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="#141418", back_color="white").convert("RGBA")
    qr_img = qr_img.resize((QR_SIZE, QR_SIZE), Image.LANCZOS)

    # 2. Canvas thẻ
    card = Image.new("RGB", (CARD_W, CARD_H), BG_COLOR)
    draw = ImageDraw.Draw(card)

    # Header gradient bang cach ve nhieu hinh chu nhat
    header_h = 90
    for y in range(header_h):
        t  = y / header_h
        r  = int(HEADER_COLOR[0] * (1 - t) + 15 * t)
        g  = int(HEADER_COLOR[1] * (1 - t) + 60 * t)
        b  = int(HEADER_COLOR[2] * (1 - t) + 140 * t)
        draw.rectangle([(0, y), (CARD_W, y + 1)], fill=(r, g, b))

    # Text header
    title_font = _font(22, bold=True)
    sub_font   = _font(12)
    draw.text((CARD_W // 2, 32), "THE DIEM DANH",
              fill="white", anchor="mm", font=title_font)
    draw.text((CARD_W // 2, 62), "CHUONG TRINH STEM",
              fill=(180, 210, 255), anchor="mm", font=sub_font)

    # Duong ke ngang accent
    draw.rectangle([(0, header_h), (CARD_W, header_h + 4)], fill=ACCENT_COLOR)

    # Dan QR vao giua
    qr_x = (CARD_W - QR_SIZE) // 2
    qr_y = header_h + 20
    # Bong do nhe cho QR
    shadow = Image.new("RGBA", (QR_SIZE + 6, QR_SIZE + 6), (0, 0, 0, 30))
    card.paste(shadow, (qr_x + 3, qr_y + 3))
    card.paste(qr_img, (qr_x, qr_y), mask=qr_img.split()[3] if qr_img.mode == "RGBA" else None)

    # [BUG FIX] Kiem tra do dai ten va thu nho neu can
    name_font  = _font(18, bold=True)
    max_name_w = CARD_W - 30
    name_display = student_name
    while True:
        bbox = draw.textbbox((0, 0), name_display, font=name_font)
        if bbox[2] - bbox[0] <= max_name_w or len(name_display) < 5:
            break
        name_font = _font(max(10, name_font.size - 1), bold=True)

    # Ten hoc sinh
    y_text = qr_y + QR_SIZE + 20
    draw.text((CARD_W // 2, y_text), name_display,
              fill=TEXT_COLOR, anchor="mm", font=name_font)

    # Duong ke ngang duoi ten
    draw.rectangle([(60, y_text + 14), (CARD_W - 60, y_text + 16)],
                   fill=BORDER_COLOR)

    # Ma hoc sinh trong hop accent
    id_y = y_text + 30
    id_box_w, id_box_h = 180, 32
    id_bx = (CARD_W - id_box_w) // 2
    draw.rounded_rectangle(
        [(id_bx, id_y), (id_bx + id_box_w, id_y + id_box_h)],
        radius=8, fill=HEADER_COLOR
    )
    draw.text((CARD_W // 2, id_y + id_box_h // 2),
              f"Ma HS: {student_id}",
              fill="white", anchor="mm", font=_font(14, bold=True))

    # Lop (neu co)
    if class_name:
        draw.text((CARD_W // 2, id_y + id_box_h + 18),
                  f"Lop: {class_name}",
                  fill=SUB_COLOR, anchor="mm", font=_font(13))

    # Footer nho
    footer_y = CARD_H - 22
    draw.text((CARD_W // 2, footer_y),
              "Khong chia se the nay cho nguoi khac",
              fill=(180, 180, 190), anchor="mm", font=_font(10))

    # Vien ngoai tinh te
    draw.rounded_rectangle([(2, 2), (CARD_W - 3, CARD_H - 3)],
                            radius=12, outline=BORDER_COLOR, width=2)

    return card


# ── In nhieu the tren 1 trang A4 ─────────────────────────────────────────────
def make_sheet(cards: list) -> Image.Image:
    """[MOI] Xep nhieu the len 1 anh A4."""
    sheet  = Image.new("RGB", (A4_W_PX, A4_H_PX), (230, 230, 235))
    draw   = ImageDraw.Draw(sheet)

    # Tieu de trang
    title_font = _font(36, bold=True)
    draw.text((A4_W_PX // 2, 35), "THE DIEM DANH — STEM",
              fill=(40, 40, 60), anchor="mm", font=title_font)

    # Tinh ti le
    avail_w   = A4_W_PX - 2 * MARGIN_PX
    avail_h   = A4_H_PX - 2 * MARGIN_PX - 80
    cell_w    = avail_w // CARDS_PER_ROW
    cell_h    = avail_h // CARDS_PER_COL

    scaled_w  = int(cell_w * 0.90)
    scaled_h  = int(cell_h * 0.90)

    for idx, card in enumerate(cards):
        row = idx // CARDS_PER_ROW
        col = idx % CARDS_PER_ROW

        if row >= CARDS_PER_COL:
            break

        x = MARGIN_PX + col * cell_w + (cell_w - scaled_w) // 2
        y = MARGIN_PX + 80 + row * cell_h + (cell_h - scaled_h) // 2

        resized = card.resize((scaled_w, scaled_h), Image.LANCZOS)
        sheet.paste(resized, (x, y))

    return sheet


# ── Xuat PDF (tuy chon) ───────────────────────────────────────────────────────
def export_pdf(cards: list, out_path: str = "qr_cards_all.pdf"):
    """[MOI] Xuat PDF luoi the can in."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas as rl_canvas
        import io

        c = rl_canvas.Canvas(out_path, pagesize=A4)
        a4_w, a4_h = A4
        cards_per_page = CARDS_PER_ROW * CARDS_PER_COL
        cell_w_pt = (a4_w - 40) / CARDS_PER_ROW
        cell_h_pt = (a4_h - 80) / CARDS_PER_COL

        for page_start in range(0, len(cards), cards_per_page):
            page_cards = cards[page_start:page_start + cards_per_page]
            for idx, card in enumerate(page_cards):
                col = idx % CARDS_PER_ROW
                row = idx // CARDS_PER_ROW
                x_pt = 20 + col * cell_w_pt
                y_pt = a4_h - 60 - (row + 1) * cell_h_pt
                # Chuyen PIL sang bytes
                buf = io.BytesIO()
                card.save(buf, format="PNG")
                buf.seek(0)
                img = Image.open(buf)
                tmp_path = f"_tmp_card_{idx}.png"
                img.save(tmp_path)
                c.drawImage(tmp_path, x_pt, y_pt,
                            width=cell_w_pt * 0.92, height=cell_h_pt * 0.92,
                            preserveAspectRatio=True)
            c.showPage()
        c.save()

        # Don dep file tam
        for i in range(cards_per_page):
            p = f"_tmp_card_{i}.png"
            if os.path.exists(p):
                os.remove(p)

        print(f"[OK] Da xuat PDF: {out_path}")
    except ImportError:
        print("[!!] Can cai reportlab de xuat PDF:  pip install reportlab")


# ── Doc danh sach tu CSV ─────────────────────────────────────────────────────
def read_students():
    if not os.path.exists(INPUT_CSV):
        print(f"[!] Khong tim thay '{INPUT_CSV}'. Dang tao file mau...")
        _create_sample_csv()
        print(f"    Da tao '{INPUT_CSV}'. Hay dien thong tin roi chay lai.")
        sys.exit(0)

    with open(INPUT_CSV, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows   = list(reader)

    students = []
    for row in rows:
        sid  = row.get("MaHS", "").strip()
        name = row.get("HoTen", "").strip()
        cls  = row.get("Lop", "").strip()
        if sid and name:
            students.append((sid, name, cls))
    return students


def _create_sample_csv():
    sample = [
        ["MaHS", "HoTen", "Lop"],
        ["HS001", "Nguyen Van An", "10A1"],
        ["HS002", "Tran Thi Bich", "10A1"],
        ["HS003", "Le Quoc Cuong", "10A2"],
    ]
    with open(INPUT_CSV, "w", encoding="utf-8-sig", newline="") as f:
        import csv as _csv
        _csv.writer(f).writerows(sample)


# ── Chuong trinh chinh ────────────────────────────────────────────────────────
def generate_all(preview=False, make_sheet_flag=False, make_pdf=False):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    students = read_students()
    print(f"[OK] Doc duoc {len(students)} hoc sinh tu '{INPUT_CSV}'")

    cards_pil = []

    for sid, name, cls in students:
        card = make_card(sid, name, cls)
        cards_pil.append(card)

        if not preview:
            out_path = os.path.join(OUTPUT_DIR, f"{sid}.png")
            card.save(out_path, dpi=(300, 300))
            print(f"  [OK] {sid}  |  {name}  ->  {out_path}")

    if preview and cards_pil:
        # Hien 1 the mau
        sample = cards_pil[0].resize((420, 560))
        sample.show()
        print("[PREVIEW] Hien thi the mau. Dong cua so preview de tiep tuc.")
        return

    if make_sheet_flag and cards_pil:
        sheet_img = make_sheet(cards_pil)
        sheet_path = os.path.join(OUTPUT_DIR, "_trang_in_A4.png")
        sheet_img.save(sheet_path, dpi=(300, 300))
        print(f"[OK] Da xuat trang in A4: {sheet_path}")

    if make_pdf and cards_pil:
        export_pdf(cards_pil, os.path.join(OUTPUT_DIR, "_the_QR_tat_ca.pdf"))

    print(f"\n[OK] Hoan thanh! {len(students)} the trong thu muc '{OUTPUT_DIR}/'")
    print("     In ra va cat tung the de phat cho hoc sinh.")


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Tao the QR diem danh STEM")
    parser.add_argument("--preview", action="store_true",
                        help="Hien thi 1 the mau truoc khi xuat")
    parser.add_argument("--sheet",   action="store_true",
                        help="Xuat luoi nhieu the tren 1 anh A4")
    parser.add_argument("--pdf",     action="store_true",
                        help="Xuat file PDF (can: pip install reportlab)")
    args = parser.parse_args()

    generate_all(
        preview=args.preview,
        make_sheet_flag=args.sheet,
        make_pdf=args.pdf,
    )
