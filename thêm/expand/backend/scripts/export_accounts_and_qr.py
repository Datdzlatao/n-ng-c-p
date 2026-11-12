import sqlite3, os, base64, io, qrcode

DB_PATH = "backend/data/stem_platform.db"
OUT_HTML = "exports/danh_sach_tai_khoan_va_ma_qr.html"
os.makedirs("exports", exist_ok=True)

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

# Get School 10 info
school = conn.execute("SELECT * FROM schools WHERE id=10").fetchone()
school = dict(school) if school else {}

# Get Users for School 10
users = conn.execute("""
    SELECT u.id, u.username, u.full_name, u.role, u.phone, u.status, u.verified_status, u.last_login_at, u.created_at
    FROM users u
    WHERE u.school_id = 10
    ORDER BY CASE u.role
        WHEN 'HEADMASTER' THEN 1
        WHEN 'TEACHER' THEN 2
        WHEN 'ADMIN' THEN 3
        WHEN 'STUDENT' THEN 4
        ELSE 5 END, u.id ASC
""").fetchall()

# Get Students with QR for School 10
students = conn.execute("""
    SELECT s.id, s.student_code, s.full_name, c.name as class_name, s.qr_token, s.parent_phone, s.current_points, s.face_approved
    FROM students s
    LEFT JOIN classes c ON s.class_id = c.id
    WHERE s.school_id = 10
    ORDER BY s.id ASC
""").fetchall()

def make_qr_b64(data_str):
    qr = qrcode.QRCode(version=1, box_size=8, border=2, error_correction=qrcode.constants.ERROR_CORRECT_M)
    qr.add_data(data_str)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#0f172a", back_color="#ffffff")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()

html = f"""<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="UTF-8">
  <title>Báo Cáo Tài Khoản & Mã QR Thực Tế — EduSAMS</title>
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
      --red: #ef4444;
      --purple: #8b5cf6;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }}
    body {{ background: var(--bg); color: var(--text); padding: 32px 20px; line-height: 1.5; }}
    .container {{ max-width: 1200px; margin: 0 auto; }}
    .header {{ margin-bottom: 32px; border-bottom: 1px solid var(--card-border); padding-bottom: 24px; }}
    .title {{ font-size: 26px; font-weight: 800; color: #fff; display: flex; align-items: center; gap: 12px; }}
    .subtitle {{ color: var(--text-muted); font-size: 14px; margin-top: 6px; }}
    .badge {{ display: inline-block; padding: 4px 10px; border-radius: 999px; font-size: 12px; font-weight: 600; }}
    .badge-blue {{ background: rgba(59, 130, 246, 0.15); color: #60a5fa; border: 1px solid rgba(59, 130, 246, 0.3); }}
    .badge-green {{ background: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.3); }}
    .badge-amber {{ background: rgba(245, 158, 11, 0.15); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.3); }}
    .badge-purple {{ background: rgba(139, 92, 246, 0.15); color: #c084fc; border: 1px solid rgba(139, 92, 246, 0.3); }}
    .badge-red {{ background: rgba(239, 68, 68, 0.15); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.3); }}
    
    .section-title {{ font-size: 18px; font-weight: 700; margin: 36px 0 16px; color: #fff; display: flex; align-items: center; gap: 8px; }}
    
    table {{ width: 100%; border-collapse: collapse; background: var(--card-bg); border-radius: 12px; overflow: hidden; border: 1px solid var(--card-border); margin-bottom: 24px; }}
    th, td {{ padding: 12px 16px; text-align: left; font-size: 13px; border-bottom: 1px solid var(--card-border); }}
    th {{ background: #1a233a; color: #cbd5e1; font-weight: 700; text-transform: uppercase; font-size: 11px; letter-spacing: 0.5px; }}
    tr:last-child td {{ border-bottom: none; }}
    tr:hover td {{ background: rgba(255,255,255,0.02); }}
    
    code {{ font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; background: rgba(0,0,0,0.3); padding: 2px 6px; border-radius: 4px; color: #38bdf8; font-size: 12px; }}
    
    /* QR Grid */
    .qr-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 20px; }}
    .qr-card {{ background: var(--card-bg); border: 1px solid var(--card-border); border-radius: 16px; padding: 20px; text-align: center; display: flex; flex-direction: column; align-items: center; transition: transform 0.2s, border-color 0.2s; }}
    .qr-card:hover {{ transform: translateY(-3px); border-color: var(--blue); }}
    .qr-img-box {{ background: #ffffff; padding: 10px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.3); margin-bottom: 14px; }}
    .qr-img-box img {{ display: block; width: 150px; height: 150px; }}
    .card-name {{ font-size: 15px; font-weight: 700; color: #fff; margin-bottom: 4px; }}
    .card-sub {{ font-size: 12px; color: var(--text-muted); margin-bottom: 8px; }}
    .card-token {{ font-size: 11px; word-break: break-all; color: #94a3b8; background: #0f172a; padding: 4px 8px; border-radius: 6px; margin-top: 8px; font-family: monospace; border: 1px solid rgba(255,255,255,0.06); }}

    .actions {{ display: flex; gap: 10px; margin-bottom: 20px; }}
    .btn {{ background: var(--blue); color: #fff; border: none; padding: 8px 16px; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; text-decoration: none; display: inline-flex; align-items: center; gap: 6px; }}
    .btn:hover {{ background: #2563eb; }}
    .btn-outline {{ background: transparent; border: 1px solid var(--card-border); color: #cbd5e1; }}
    .btn-outline:hover {{ background: rgba(255,255,255,0.05); color: #fff; }}

    @media print {{
      body {{ background: #fff; color: #000; padding: 0; }}
      .actions {{ display: none; }}
      .qr-card {{ border: 1px solid #ddd; background: #fff; break-inside: avoid; }}
      .card-name {{ color: #000; }}
      .card-sub {{ color: #555; }}
      .card-token {{ color: #333; background: #f1f5f9; border: 1px solid #ccc; }}
      table {{ border: 1px solid #ccc; background: #fff; }}
      th {{ background: #eee; color: #000; }}
      td {{ color: #000; border-bottom: 1px solid #eee; }}
    }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:16px;">
        <div>
          <h1 class="title">🏫 {school.get("name", "Trường Học")}</h1>
          <p class="subtitle">Mã trường: <code>{school.get("school_code")}</code> | Niên khóa: <b>{school.get("academic_year")}</b> | Địa chỉ: {school.get("address")}</p>
        </div>
        <div class="actions">
          <button class="btn" onclick="window.print()">🖨️ In Danh Sách / Thẻ QR</button>
        </div>
      </div>
    </div>

    <!-- MÃ MỜI THAM GIA HỆ THỐNG -->
    <h2 class="section-title">🔑 Mã Mời Gia Nhập Trường & Lớp (Invite Codes)</h2>
    <table>
      <thead>
        <tr>
          <th>Loại Mã Mời</th>
          <th>Mã Ký Tự (Code)</th>
          <th>Mục Đích Sử Dụng</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td><span class="badge badge-purple">Mã Giáo Viên</span></td>
          <td><code>{school.get("teacher_invite_code")}</code></td>
          <td>Dùng để giáo viên đăng ký tài khoản tự động gia nhập trường</td>
        </tr>
        <tr>
          <td><span class="badge badge-amber">Mã Giám Thị</span></td>
          <td><code>{school.get("inspector_invite_code")}</code></td>
          <td>Dành cho cán bộ ban thi đua / giám thị</td>
        </tr>
        <tr>
          <td><span class="badge badge-blue">Mã Ban Giám Hiệu</span></td>
          <td><code>{school.get("bgh_invite_code")}</code></td>
          <td>Dành cho Hiệu trưởng / Phó hiệu trưởng</td>
        </tr>
        <tr>
          <td><span class="badge badge-green">Mã Lớp 12C1</span></td>
          <td><code>INVITE_12C1_E124DEA9</code></td>
          <td>Học sinh nhập mã này để tự động vào danh sách lớp 12C1 (GVCN: Cô Nguyễn Thị Thúy Hạnh)</td>
        </tr>
      </tbody>
    </table>

    <!-- DANH SÁCH TÀI KHOẢN NGƯỜI DÙNG -->
    <h2 class="section-title">👤 Danh Sách Tài Khoản Đã Tạo Trong Hệ Thống (Users)</h2>
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

    <!-- THẺ QR ĐIỂM DANH HỌC SINH THỰC TẾ -->
    <h2 class="section-title">📱 Mã QR Điểm Danh Thực Tế Cho Từng Học Sinh</h2>
    <p style="color:var(--text-muted); font-size:13px; margin-bottom:18px;">
      Mã QR này được camera AI hoặc thiết bị quét QR tại cổng trường / lớp học đọc để ghi nhận điểm danh tức thì.
    </p>
    <div class="qr-grid">
"""

for s in students:
    token = s["qr_token"]
    if not token:
        continue
    b64_qr = make_qr_b64(token)
    cls_name = s["class_name"] or "Chưa xếp lớp"
    html += f"""
      <div class="qr-card">
        <div class="qr-img-box">
          <img src="data:image/png;base64,{b64_qr}" alt="QR {s['student_code']}">
        </div>
        <div class="card-name">{s['full_name']}</div>
        <div class="card-sub">Mã HS: <code>{s['student_code']}</code> | Lớp: <b>{cls_name}</b></div>
        <div style="font-size:11px; color:#10b981;">Điểm nề nếp: {s['current_points']}đ</div>
        <div class="card-token">{token}</div>
      </div>
    """

html += """
    </div>
  </div>
</body>
</html>
"""

with open(OUT_HTML, "w", encoding="utf-8") as f:
    f.write(html)

print(f"Generated complete HTML export: {OUT_HTML}")
