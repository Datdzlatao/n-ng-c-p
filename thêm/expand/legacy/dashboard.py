"""
=================================================
  DASHBOARD.PY — BAO CAO DIEM DANH TRUC QUAN
=================================================
[MOI] Script tao bao cao HTML/PNG tu Google Sheets.
Cac bieu do:
  - Bieu do cot: so hoc sinh vao theo tung gio
  - Bieu do tron: co mat / vang mat
  - Bang xep hang: hoc sinh vang mat nhieu nhat
  - Bieu do vi pham theo ngay

Cach dung:
    python dashboard.py             # Tao bao cao hom nay
    python dashboard.py --date 21/04/2026
    python dashboard.py --open      # Mo trinh duyet sau khi tao
"""

import argparse
import os
import sys
from datetime import date, datetime

try:
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials
except ImportError:
    print("[!!] Can cai: pip install gspread oauth2client")
    sys.exit(1)

from config import (
    CREDENTIALS_FILE, SPREADSHEET_ID, SPREADSHEET_NAME,
    SHEET_LOG, SHEET_STUDENTS, SHEET_VIOLATIONS
)


# =============================================================================
# Lay du lieu tu Sheets
# =============================================================================
def connect():
    scope  = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds  = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
    client = gspread.authorize(creds)
    ss     = client.open_by_key(SPREADSHEET_ID) if SPREADSHEET_ID else client.open(SPREADSHEET_NAME)
    return ss


def get_data(target_date: str):
    """Lay du lieu diem danh va vi pham theo ngay."""
    ss  = connect()
    log_ws = ss.worksheet(SHEET_LOG)
    stu_ws = ss.worksheet(SHEET_STUDENTS)
    vio_ws = ss.worksheet(SHEET_VIOLATIONS)

    all_log = log_ws.get_all_values()
    all_stu = stu_ws.get_all_values()
    all_vio = vio_ws.get_all_values()

    # Hoc sinh
    students = {}
    for row in all_stu[1:]:
        if len(row) >= 2 and row[0].strip():
            students[row[0].strip()] = {"name": row[1].strip(), "class": row[2].strip() if len(row) > 2 else ""}

    # Log hom nay
    today_logs = [row for row in all_log[1:] if len(row) >= 4 and row[0].startswith(target_date)]

    # Vi pham hom nay
    today_vios = [row for row in all_vio[1:] if len(row) >= 2 and row[0].startswith(target_date)]

    return students, today_logs, today_vios


# =============================================================================
# Tao bao cao HTML
# =============================================================================
def build_html(target_date: str, students: dict, logs: list, violations: list) -> str:
    # Thong ke co/vang mat
    seen = {}
    for row in logs:
        sid = row[1]
        seen[sid] = seen.get(sid, 0) + 1

    present_ids = {sid for sid, cnt in seen.items() if cnt % 2 == 1}
    present     = len(present_ids)
    total       = len(students)
    absent      = total - present

    # Phan phoi theo gio
    hour_count = {}
    for row in logs:
        try:
            hour = int(row[0].split(" ")[1].split(":")[0])
            hour_count[hour] = hour_count.get(hour, 0) + 1
        except (IndexError, ValueError):
            pass

    hours_sorted = sorted(hour_count.items())
    hour_labels  = [f"{h}h" for h, _ in hours_sorted]
    hour_values  = [c for _, c in hours_sorted]

    # DS vang mat
    absent_list = [
        (sid, info["name"], info["class"])
        for sid, info in students.items()
        if sid not in present_ids
    ]
    absent_list.sort(key=lambda x: x[2])

    hour_data_js  = str(hour_labels)
    hour_count_js = str(hour_values)

    absent_rows = "".join(
        f'<tr><td>{sid}</td><td>{name}</td><td>{cls}</td></tr>'
        for sid, name, cls in absent_list
    )
    vio_rows = "".join(
        f'<tr><td>{r[0] if len(r) > 0 else ""}</td>'
        f'<td>{r[1] if len(r) > 1 else ""}</td>'
        f'<td>{r[2] if len(r) > 2 else ""}</td>'
        f'<td>{r[3] if len(r) > 3 else ""}</td></tr>'
        for r in violations
    )

    html = f"""<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Bao Cao Diem Danh — {target_date}</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@300;400;600;700&display=swap');
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: 'Be Vietnam Pro', sans-serif;
    background: #f0f4f8;
    color: #1a202c;
    min-height: 100vh;
  }}
  header {{
    background: linear-gradient(135deg, #1a56db 0%, #0e9f6e 100%);
    color: white;
    padding: 28px 40px;
    display: flex; align-items: center; justify-content: space-between;
  }}
  header h1 {{ font-size: 1.7rem; font-weight: 700; }}
  header p  {{ font-size: 0.9rem; opacity: 0.85; margin-top: 4px; }}
  .badge {{
    background: rgba(255,255,255,0.2);
    border-radius: 20px; padding: 6px 16px;
    font-weight: 600; font-size: 0.9rem;
  }}
  .container {{ max-width: 1200px; margin: 0 auto; padding: 32px 24px; }}
  .stat-grid {{
    display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 20px; margin-bottom: 32px;
  }}
  .stat-card {{
    background: white; border-radius: 16px; padding: 24px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.08);
    display: flex; flex-direction: column; align-items: flex-start;
  }}
  .stat-card .label {{ font-size: 0.8rem; color: #718096; font-weight: 600; text-transform: uppercase; letter-spacing: .05em; }}
  .stat-card .value {{ font-size: 2.4rem; font-weight: 700; margin-top: 8px; }}
  .stat-card.green .value {{ color: #0e9f6e; }}
  .stat-card.red   .value {{ color: #e02424; }}
  .stat-card.blue  .value {{ color: #1a56db; }}
  .stat-card.orange .value {{ color: #d97706; }}
  .charts-grid {{
    display: grid; grid-template-columns: 2fr 1fr;
    gap: 20px; margin-bottom: 32px;
  }}
  @media (max-width: 768px) {{ .charts-grid {{ grid-template-columns: 1fr; }} }}
  .card {{
    background: white; border-radius: 16px; padding: 24px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.08);
  }}
  .card h2 {{ font-size: 1rem; font-weight: 700; color: #2d3748; margin-bottom: 16px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 0.9rem; }}
  th {{ background: #ebf4ff; color: #2b6cb0; font-weight: 600; padding: 10px 12px; text-align: left; }}
  td {{ padding: 9px 12px; border-bottom: 1px solid #edf2f7; }}
  tr:hover td {{ background: #f7fafc; }}
  .pct {{ font-size: 0.75rem; color: #718096; margin-top: 4px; }}
  .empty {{ color: #a0aec0; font-style: italic; text-align: center; padding: 20px; }}
  footer {{ text-align: center; color: #a0aec0; font-size: 0.8rem; padding: 24px; }}
</style>
</head>
<body>
<header>
  <div>
    <h1>Bao Cao Diem Danh STEM</h1>
    <p>Ngay: {target_date} &nbsp;|&nbsp; Tao luc: {datetime.now().strftime('%H:%M:%S')}</p>
  </div>
  <span class="badge">STEM Project</span>
</header>

<div class="container">
  <!-- Stat cards -->
  <div class="stat-grid">
    <div class="stat-card blue">
      <span class="label">Tong Hoc Sinh</span>
      <span class="value">{total}</span>
    </div>
    <div class="stat-card green">
      <span class="label">Co Mat</span>
      <span class="value">{present}</span>
      <span class="pct">{present*100//total if total else 0}% tong so</span>
    </div>
    <div class="stat-card red">
      <span class="label">Vang Mat</span>
      <span class="value">{absent}</span>
      <span class="pct">{absent*100//total if total else 0}% tong so</span>
    </div>
    <div class="stat-card orange">
      <span class="label">Vi Pham</span>
      <span class="value">{len(violations)}</span>
      <span class="pct">Khong deo the</span>
    </div>
  </div>

  <!-- Charts -->
  <div class="charts-grid">
    <div class="card">
      <h2>Luot Quet QR Theo Gio</h2>
      <canvas id="hourChart" height="200"></canvas>
    </div>
    <div class="card">
      <h2>Ti Le Co Mat / Vang</h2>
      <canvas id="pieChart" height="200"></canvas>
    </div>
  </div>

  <!-- Tables -->
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-bottom:32px;">
    <div class="card">
      <h2>Danh Sach Vang Mat ({absent})</h2>
      {'<table><thead><tr><th>Ma HS</th><th>Ho Ten</th><th>Lop</th></tr></thead><tbody>' + absent_rows + '</tbody></table>' if absent_rows else '<p class="empty">Tat ca hoc sinh da diem danh!</p>'}
    </div>
    <div class="card">
      <h2>Vi Pham Khong Deo The ({len(violations)})</h2>
      {'<table><thead><tr><th>Thoi Gian</th><th>Ma HS</th><th>Ho Ten</th><th>Mo Ta</th></tr></thead><tbody>' + vio_rows + '</tbody></table>' if vio_rows else '<p class="empty">Khong co vi pham nao!</p>'}
    </div>
  </div>
</div>

<footer>He Thong Diem Danh QR + Nhan Dien Mat — STEM Project v2.0</footer>

<script>
const hourLabels = {hour_data_js};
const hourData   = {hour_count_js};

new Chart(document.getElementById('hourChart'), {{
  type: 'bar',
  data: {{
    labels: hourLabels.length ? hourLabels : ['Chua co du lieu'],
    datasets: [{{
      label: 'Luot quet QR',
      data: hourData.length ? hourData : [0],
      backgroundColor: 'rgba(26, 86, 219, 0.7)',
      borderRadius: 6,
    }}]
  }},
  options: {{
    responsive: true, plugins: {{ legend: {{ display: false }} }},
    scales: {{ y: {{ beginAtZero: true, ticks: {{ stepSize: 1 }} }} }}
  }}
}});

new Chart(document.getElementById('pieChart'), {{
  type: 'doughnut',
  data: {{
    labels: ['Co Mat', 'Vang Mat'],
    datasets: [{{
      data: [{present}, {absent}],
      backgroundColor: ['#0e9f6e', '#e02424'],
      borderWidth: 2, borderColor: '#fff',
    }}]
  }},
  options: {{
    responsive: true,
    plugins: {{
      legend: {{ position: 'bottom' }},
    }}
  }}
}});
</script>
</body>
</html>"""
    return html


# =============================================================================
def main():
    parser = argparse.ArgumentParser(description="Tao bao cao diem danh STEM")
    parser.add_argument("--date", default=date.today().strftime("%d/%m/%Y"),
                        help="Ngay can bao cao (dinh dang dd/mm/yyyy)")
    parser.add_argument("--open", action="store_true",
                        help="Mo trinh duyet sau khi tao xong")
    parser.add_argument("--out",  default="bao_cao.html",
                        help="Ten file dau ra (mac dinh: bao_cao.html)")
    args = parser.parse_args()

    print(f"[->] Dang lay du lieu ngay {args.date}...")
    try:
        students, logs, violations = get_data(args.date)
    except Exception as e:
        print(f"[!!] Loi ket noi Sheets: {e}")
        sys.exit(1)

    html = build_html(args.date, students, logs, violations)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[OK] Da tao bao cao: {os.path.abspath(args.out)}")

    if args.open:
        import webbrowser
        webbrowser.open(f"file://{os.path.abspath(args.out)}")


if __name__ == "__main__":
    main()
