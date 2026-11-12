import sqlite3
import os
import io
import base64
from PIL import Image, ImageDraw, ImageFont
import qrcode

DB_PATH = "backend/data/stem_platform.db"
CARDS_DIR = "exports/cards_png"
QR_INFO_DIR = "exports/qr_info"
QR_TOKEN_DIR = "exports/qr_tokens"
OUT_HTML = "exports/danh_sach_tai_khoan_va_ma_qr.html"

for d in [CARDS_DIR, QR_INFO_DIR, QR_TOKEN_DIR]:
    os.makedirs(d, exist_ok=True)

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

# School info
school = conn.execute("SELECT * FROM schools WHERE id=10").fetchone()
school = dict(school) if school else {}
school_name = school.get("name", "Trường PTDTNT THPT Tỉnh")
academic_year = school.get("academic_year", "2026-2027")

# Users
users = conn.execute("""
    SELECT u.id, u.username, u.full_name, u.role, u.phone, u.status, u.verified_status, u.last_login_at
    FROM users u
    WHERE u.school_id = 10
    ORDER BY CASE u.role
        WHEN 'HEADMASTER' THEN 1
        WHEN 'TEACHER' THEN 2
        WHEN 'ADMIN' THEN 3
        WHEN 'STUDENT' THEN 4
        ELSE 5 END, u.id ASC
""").fetchall()

# Students
students = conn.execute("""
    SELECT s.id, s.student_code, s.full_name, c.name as class_name, s.qr_token,
           s.parent_phone, s.current_points, s.face_approved, s.face_photo_url
    FROM students s
    LEFT JOIN classes c ON s.class_id = c.id
    WHERE s.school_id = 10
    ORDER BY s.id ASC
""").fetchall()

# Fonts
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REG  = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

def get_font(size, bold=False):
    p = FONT_BOLD if bold else FONT_REG
    try:
        return ImageFont.truetype(p, size)
    except Exception:
        return ImageFont.load_default()

def make_qr_img(data_str, box_size=8, border=2):
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=box_size,
        border=border
    )
    qr.add_data(data_str)
    qr.make(fit=True)
    return qr.make_image(fill_color="#0f172a", back_color="#ffffff").convert("RGB")

def img_to_b64(img):
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()

# 1. Generate Cards and QR files
card_pil_list = []
students_data = []

CARD_W, CARD_H = 460, 680

for s in students:
    scode = s["student_code"]
    name = s["full_name"]
    cls = s["class_name"] or "12C1 (Chưa gán)"
    phone = s["parent_phone"] or "Chưa có SĐT"
    token = s["qr_token"] or f"QR-{scode}"
    points = s["current_points"] if s["current_points"] is not None else 100

    # Readable text for general QR scanning (Camera/Zalo)
    info_qr_text = (
        f"THẺ HỌC SINH — {school_name}\n"
        f"Họ và tên: {name}\n"
        f"Mã học sinh: {scode}\n"
        f"Lớp: {cls}\n"
        f"Niên khóa: {academic_year}\n"
        f"SĐT Phụ huynh: {phone}\n"
        f"Mã điểm danh: {token}"
    )

    # QR with full info
    img_info_qr = make_qr_img(info_qr_text, box_size=7)
    img_info_qr.save(os.path.join(QR_INFO_DIR, f"{scode}_info_qr.png"))

    # QR with token
    img_token_qr = make_qr_img(token, box_size=8)
    img_token_qr.save(os.path.join(QR_TOKEN_DIR, f"{scode}_token_qr.png"))

    # Create Student ID Card
    card = Image.new("RGB", (CARD_W, CARD_H), (255, 255, 255))
    draw = ImageDraw.Draw(card)

    # Header background (Navy gradient)
    header_h = 100
    for y in range(header_h):
        t = y / header_h
        r = int(15 * (1 - t) + 30 * t)
        g = int(35 * (1 - t) + 65 * t)
        b = int(85 * (1 - t) + 140 * t)
        draw.rectangle([(0, y), (CARD_W, y + 1)], fill=(r, g, b))

    # Accent stripe
    draw.rectangle([(0, header_h), (CARD_W, header_h + 4)], fill=(16, 185, 129))

    # School title
    draw.text((CARD_W // 2, 28), school_name.upper(), fill="#ffffff", anchor="mm", font=get_font(13, bold=True))
    draw.text((CARD_W // 2, 54), "THẺ ĐIỂM DANH HỌC SINH", fill="#38bdf8", anchor="mm", font=get_font(16, bold=True))
    draw.text((CARD_W // 2, 78), f"Niên khóa: {academic_year}", fill="#cbd5e1", anchor="mm", font=get_font(11))

    # Student avatar or monogram
    avatar_size = 72
    avatar_x = 30
    avatar_y = header_h + 20
    avatar_drawn = False

    if s["face_photo_url"]:
        photo_rel = s["face_photo_url"].lstrip("/")
        # check backend/photo_rel
        for p_cand in [photo_rel, os.path.join("backend", photo_rel)]:
            if os.path.exists(p_cand):
                try:
                    p_img = Image.open(p_cand).convert("RGB").resize((avatar_size, avatar_size), Image.LANCZOS)
                    card.paste(p_img, (avatar_x, avatar_y))
                    draw.rectangle([(avatar_x, avatar_y), (avatar_x + avatar_size, avatar_y + avatar_size)], outline="#38bdf8", width=2)
                    avatar_drawn = True
                    break
                except Exception:
                    pass

    if not avatar_drawn:
        # Draw placeholder avatar
        draw.rounded_rectangle([(avatar_x, avatar_y), (avatar_x + avatar_size, avatar_y + avatar_size)], radius=12, fill="#e0f2fe", outline="#0284c7", width=2)
        initials = "".join([w[0] for w in name.split() if w])[-2:].upper()
        draw.text((avatar_x + avatar_size // 2, avatar_y + avatar_size // 2), initials, fill="#0369a1", anchor="mm", font=get_font(24, bold=True))

    # Student Details next to avatar
    info_x = avatar_x + avatar_size + 18
    draw.text((info_x, avatar_y + 10), name.upper(), fill="#0f172a", font=get_font(16, bold=True))
    draw.text((info_x, avatar_y + 34), f"Mã HS: {scode}", fill="#0284c7", font=get_font(13, bold=True))
    draw.text((info_x, avatar_y + 54), f"Lớp: {cls}", fill="#334155", font=get_font(12, bold=True))

    # Parent phone & Points row
    row_y = avatar_y + avatar_size + 14
    draw.line([(24, row_y), (CARD_W - 24, row_y)], fill="#e2e8f0", width=1)

    draw.text((30, row_y + 12), f"Phụ huynh: {phone}", fill="#475569", font=get_font(12))
    draw.text((CARD_W - 30, row_y + 12), f"Điểm: {points}đ", fill="#10b981", anchor="ra", font=get_font(12, bold=True))

    # QR Code in Center (Resized to 230x230)
    qr_w = 230
    qr_resized = img_info_qr.resize((qr_w, qr_w), Image.LANCZOS)
    qr_x = (CARD_W - qr_w) // 2
    qr_y = row_y + 36

    # Shadow box
    draw.rounded_rectangle([(qr_x - 8, qr_y - 8), (qr_x + qr_w + 8, qr_y + qr_w + 8)], radius=12, fill="#f8fafc", outline="#cbd5e1", width=1)
    card.paste(qr_resized, (qr_x, qr_y))

    # Token box below QR
    tok_y = qr_y + qr_w + 16
    draw.rounded_rectangle([(30, tok_y), (CARD_W - 30, tok_y + 32)], radius=8, fill="#0f172a")
    draw.text((CARD_W // 2, tok_y + 16), f"Mã Token: {token}", fill="#38bdf8", anchor="mm", font=get_font(11, bold=True))

    # Card footer
    draw.text((CARD_W // 2, CARD_H - 18), "Quét mã để điểm danh & tra cứu thông tin học sinh", fill="#94a3b8", anchor="mm", font=get_font(10))

    # Outer border
    draw.rounded_rectangle([(1, 1), (CARD_W - 2, CARD_H - 2)], radius=16, outline="#cbd5e1", width=2)

    card_path = os.path.join(CARDS_DIR, f"{scode}_card.png")
    card.save(card_path, dpi=(300, 300))
    card_pil_list.append(card)

    students_data.append({
        "scode": scode,
        "name": name,
        "cls": cls,
        "phone": phone,
        "points": points,
        "token": token,
        "info_qr_text": info_qr_text,
        "card_b64": img_to_b64(card),
        "info_qr_b64": img_to_b64(img_info_qr),
        "token_qr_b64": img_to_b64(img_token_qr),
    })

# 2. Make A4 Sheet if cards exist
if card_pil_list:
    A4_W, A4_H = 2480, 3508
    sheet = Image.new("RGB", (A4_W, A4_H), (245, 247, 250))
    s_draw = ImageDraw.Draw(sheet)
    s_draw.text((A4_W // 2, 80), f"DANH SÁCH THẺ ĐIỂM DANH — {school_name.upper()}", fill="#0f172a", anchor="mm", font=get_font(42, bold=True))

    cols, rows = 4, 4
    margin_x, margin_y = 80, 160
    avail_w = A4_W - 2 * margin_x
    avail_h = A4_H - margin_y - 100
    slot_w = avail_w // cols
    slot_h = avail_h // rows

    target_w = int(slot_w * 0.92)
    target_h = int(slot_h * 0.92)

    for idx, c_img in enumerate(card_pil_list[:cols * rows]):
        r = idx // cols
        c = idx % cols
        x = margin_x + c * slot_w + (slot_w - target_w) // 2
        y = margin_y + r * slot_h + (slot_h - target_h) // 2
        resized = c_img.resize((target_w, target_h), Image.LANCZOS)
        sheet.paste(resized, (x, y))

    sheet.save("exports/tat_ca_the_hoc_sinh_in_A4.png", dpi=(300, 300))
    print("Exported A4 print sheet: exports/tat_ca_the_hoc_sinh_in_A4.png")

# 3. Generate HTML with rich interactive cards
html = f"""<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Thẻ Học Sinh & Dữ Liệu Mã QR — EduSAMS</title>
  <style>
    :root {{
      --bg: #0b0f19;
      --card-bg: #151c2e;
      --card-border: #222f4c;
      --text: #f1f5f9;
      --text-muted: #94a3b8;
      --blue: #3b82f6;
      --green: #10b981;
      --amber: #f59e0b;
      --purple: #8b5cf6;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }}
    body {{ background: var(--bg); color: var(--text); padding: 32px 16px; line-height: 1.5; }}
    .container {{ max-width: 1280px; margin: 0 auto; }}
    
    .header {{ margin-bottom: 28px; border-bottom: 1px solid var(--card-border); padding-bottom: 20px; }}
    .title {{ font-size: 26px; font-weight: 800; color: #fff; display: flex; align-items: center; gap: 12px; }}
    .subtitle {{ color: var(--text-muted); font-size: 14px; margin-top: 6px; }}
    
    .tabs {{ display: flex; gap: 8px; margin-bottom: 24px; border-bottom: 1px solid var(--card-border); padding-bottom: 10px; }}
    .tab-btn {{ background: transparent; border: none; color: var(--text-muted); padding: 8px 18px; font-size: 14px; font-weight: 700; border-radius: 8px; cursor: pointer; transition: all 0.15s; }}
    .tab-btn.active {{ background: var(--blue); color: #fff; }}
    .tab-btn:hover:not(.active) {{ background: rgba(255,255,255,0.05); color: #fff; }}

    .btn {{ background: var(--blue); color: #fff; border: none; padding: 8px 16px; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; text-decoration: none; display: inline-flex; align-items: center; gap: 6px; }}
    .btn:hover {{ background: #2563eb; }}
    .btn-green {{ background: #059669; }}
    .btn-green:hover {{ background: #10b981; }}
    
    /* Card Grid */
    .card-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 24px; }}
    .id-card-wrapper {{ background: var(--card-bg); border: 1px solid var(--card-border); border-radius: 18px; padding: 18px; display: flex; flex-direction: column; align-items: center; box-shadow: 0 10px 25px rgba(0,0,0,0.3); transition: transform 0.2s, border-color 0.2s; }}
    .id-card-wrapper:hover {{ transform: translateY(-4px); border-color: var(--blue); }}
    .id-card-img {{ width: 100%; max-width: 320px; height: auto; border-radius: 12px; box-shadow: 0 4px 16px rgba(0,0,0,0.4); }}
    
    .card-actions {{ margin-top: 14px; display: flex; gap: 8px; width: 100%; justify-content: center; }}
    .card-actions a, .card-actions button {{ font-size: 12px; padding: 6px 12px; border-radius: 6px; }}

    /* Tables */
    table {{ width: 100%; border-collapse: collapse; background: var(--card-bg); border-radius: 12px; overflow: hidden; border: 1px solid var(--card-border); margin-bottom: 24px; }}
    th, td {{ padding: 12px 16px; text-align: left; font-size: 13px; border-bottom: 1px solid var(--card-border); }}
    th {{ background: #1a233a; color: #cbd5e1; font-weight: 700; text-transform: uppercase; font-size: 11px; letter-spacing: 0.5px; }}
    tr:last-child td {{ border-bottom: none; }}
    tr:hover td {{ background: rgba(255,255,255,0.02); }}

    .badge {{ display: inline-block; padding: 3px 8px; border-radius: 999px; font-size: 11px; font-weight: 700; }}
    .badge-blue {{ background: rgba(59, 130, 246, 0.15); color: #60a5fa; border: 1px solid rgba(59, 130, 246, 0.3); }}
    .badge-green {{ background: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.3); }}
    .badge-purple {{ background: rgba(139, 92, 246, 0.15); color: #c084fc; border: 1px solid rgba(139, 92, 246, 0.3); }}
    .badge-red {{ background: rgba(239, 68, 68, 0.15); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.3); }}

    code {{ font-family: ui-monospace, SFMono-Regular, Menlo, monospace; background: rgba(0,0,0,0.4); padding: 2px 6px; border-radius: 4px; color: #38bdf8; font-size: 12px; }}

    .tab-content {{ display: none; }}
    .tab-content.active {{ display: block; }}

    @media print {{
      body {{ background: #fff; color: #000; padding: 0; }}
      .header, .tabs, .card-actions, .actions {{ display: none !important; }}
      .id-card-wrapper {{ background: #fff; border: none; box-shadow: none; padding: 0; break-inside: avoid; margin-bottom: 20px; }}
      .card-grid {{ display: block; }}
      .id-card-img {{ max-width: 320px; margin: 0 auto 20px auto; display: block; page-break-inside: avoid; }}
    }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:16px;">
        <div>
          <h1 class="title">🏫 {school_name}</h1>
          <p class="subtitle">Hệ Thống Xuất Dữ Liệu Thẻ Học Sinh & Mã QR Điểm Danh Có Đầy Đủ Thông Tin</p>
        </div>
        <div class="actions" style="display:flex; gap:10px;">
          <button class="btn btn-green" onclick="window.print()">🖨️ In Danh Sách / Thẻ Học Sinh</button>
        </div>
      </div>
    </div>

    <!-- TABS -->
    <div class="tabs">
      <button class="tab-btn active" onclick="switchTab('tab-cards', this)">🪪 Thẻ Học Sinh Hoàn Chỉnh ({len(students_data)})</button>
      <button class="tab-btn" onclick="switchTab('tab-qr-text', this)">📱 Mã QR Thông Tin Tiếng Việt (Quét Điện Thoại/Zalo)</button>
      <button class="tab-btn" onclick="switchTab('tab-accounts', this)">👥 Toàn Bộ Tài Khoản ({len(users)})</button>
    </div>

    <!-- TAB 1: THẺ HỌC SINH -->
    <div id="tab-cards" class="tab-content active">
      <p style="color:var(--text-muted); font-size:13px; margin-bottom:18px;">
        Mỗi thẻ học sinh dưới đây được thiết kế hoàn chỉnh gồm <b>Tên trường, Ảnh/Chân dung, Họ tên in đậm, Mã học sinh, Lớp, SĐT phụ huynh, Điểm nề nếp và Mã QR điểm danh</b>. Bạn có thể tải ảnh về hoặc bấm <b>In Thẻ</b>.
      </p>
      <div class="card-grid">
"""

for st in students_data:
    html += f"""
        <div class="id-card-wrapper">
          <img class="id-card-img" src="data:image/png;base64,{st['card_b64']}" alt="Thẻ {st['name']}">
          <div class="card-actions">
            <a class="btn" href="data:image/png;base64,{st['card_b64']}" download="{st['scode']}_{st['name']}.png">📥 Tải Ảnh Thẻ</a>
          </div>
        </div>
    """

html += """
      </div>
    </div>

    <!-- TAB 2: QR THÔNG TIN CHI TIẾT KHI QUÉT -->
    <div id="tab-qr-text" class="tab-content">
      <p style="color:var(--text-muted); font-size:13px; margin-bottom:18px;">
        Các mã QR dưới đây khi dùng <b>Camera iPhone, Android, ứng dụng Zalo hoặc Google Lens</b> quét sẽ hiển thị ngay lập tức văn bản tiếng Việt đầy đủ thông tin: Họ tên, Lớp, Trường, SĐT Phụ huynh và Mã điểm danh.
      </p>
      <div class="card-grid">
"""

for st in students_data:
    formatted_preview = st['info_qr_text'].replace('\n', '<br>')
    html += f"""
        <div class="id-card-wrapper" style="text-align:center;">
          <div style="background:#ffffff; padding:12px; border-radius:12px; margin-bottom:12px;">
            <img src="data:image/png;base64,{st['info_qr_b64']}" style="width:180px; height:180px; display:block;">
          </div>
          <div style="font-weight:800; font-size:16px; color:#fff;">{st['name']}</div>
          <div style="font-size:12px; color:#38bdf8; margin-top:2px;">Mã HS: <code>{st['scode']}</code> — Lớp: <b>{st['cls']}</b></div>
          <div style="text-align:left; background:rgba(0,0,0,0.3); border:1px solid rgba(255,255,255,0.08); border-radius:8px; padding:10px; font-size:11px; margin-top:10px; width:100%; color:#cbd5e1; line-height:1.6;">
            <b>Nội dung xuất hiện khi quét Zalo/Camera:</b><br>
            {formatted_preview}
          </div>
          <div class="card-actions">
            <a class="btn" href="data:image/png;base64,{st['info_qr_b64']}" download="{st['scode']}_qr_thong_tin.png">📥 Tải Mã QR Này</a>
          </div>
        </div>
    """

html += f"""
      </div>
    </div>

    <!-- TAB 3: TÀI KHOẢN -->
    <div id="tab-accounts" class="tab-content">
      <h3 style="margin-bottom:12px; font-size:16px;">Danh Sách Tài Khoản Người Dùng (Users)</h3>
      <table>
        <thead>
          <tr>
            <th>#</th>
            <th>Họ Và Tên</th>
            <th>Tên Đăng Nhập (Username)</th>
            <th>Vai Trò (Role)</th>
            <th>Số Điện Thoại</th>
            <th>Xác Thực</th>
            <th>Đăng Nhập Gần Nhất</th>
          </tr>
        </thead>
        <tbody>
"""

role_badge_map = {
    "HEADMASTER": ('badge-red', 'Hiệu Trưởng'),
    "TEACHER": ('badge-purple', 'Giáo Viên'),
    "ADMIN": ('badge-blue', 'Quản Trị Viên'),
    "STUDENT": ('badge-green', 'Học Sinh'),
}

for idx, u in enumerate(users):
    r_cls, r_lbl = role_badge_map.get(u["role"], ('badge-blue', u["role"]))
    v_badge = '<span class="badge badge-green">✓ Đã Xác Minh</span>' if u["verified_status"] == "VERIFIED" else '<span class="badge badge-amber">Chờ duyệt</span>'
    phone_str = u["phone"] or "—"
    last_login = u["last_login_at"] or "Chưa đăng nhập"
    html += f"""
          <tr>
            <td>{idx + 1}</td>
            <td><b>{u["full_name"]}</b></td>
            <td><code>{u["username"]}</code></td>
            <td><span class="badge {r_cls}">{r_lbl}</span></td>
            <td>{phone_str}</td>
            <td>{v_badge}</td>
            <td style="color:var(--text-muted); font-size:12px;">{last_login}</td>
          </tr>
    """

html += """
        </tbody>
      </table>
    </div>

  </div>

  <script>
    function switchTab(tabId, btn) {
      document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
      document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
      document.getElementById(tabId).classList.add('active');
      btn.classList.add('active');
    }
  </script>
</body>
</html>
"""

with open(OUT_HTML, "w", encoding="utf-8") as f:
    f.write(html)

print("Generated comprehensive HTML and cards successfully!")
