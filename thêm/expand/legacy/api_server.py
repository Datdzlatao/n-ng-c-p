import os
import sqlite3
import time
import json
import socket
from flask import Flask, Response, jsonify, send_from_directory, request
from flask_cors import CORS
from datetime import datetime

app = Flask(__name__)
CORS(app)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "database.db")
VIOLATIONS_DIR = os.path.join(BASE_DIR, "data", "violations")
STATIC_DIR = os.path.join(BASE_DIR, "static")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn

def get_report_data(target_date):
    conn = get_db_connection()
    try:
        stu_rows = conn.execute("SELECT ma_hs, ho_ten, lop FROM HocSinh").fetchall()
        students = {r['ma_hs'].strip(): {"name": r['ho_ten'].strip(), "class": (r['lop'] or "").strip()} for r in stu_rows}

        log_rows = conn.execute(
            "SELECT thoi_gian, ma_hs, ho_ten, trang_thai FROM offline_log WHERE thoi_gian LIKE ? ORDER BY id ASC",
            (f"{target_date}%",)
        ).fetchall()
        logs = [[r['thoi_gian'], r['ma_hs'].strip(), r['ho_ten'].strip(), r['trang_thai']] for r in log_rows]

        vio_rows = conn.execute(
            "SELECT thoi_gian, ma_hs, ho_ten, mo_ta, ten_file, duong_dan FROM offline_violation WHERE thoi_gian LIKE ? ORDER BY id ASC",
            (f"{target_date}%",)
        ).fetchall()
        violations = [[r['thoi_gian'], r['ma_hs'].strip(), r['ho_ten'].strip(), r['mo_ta'].strip(), r['ten_file'], r['duong_dan']] for r in vio_rows]

        return students, logs, violations
    finally:
        conn.close()

def build_html_report(target_date, students, logs, violations):
    seen = {}
    for row in logs:
        sid = row[1]
        seen[sid] = seen.get(sid, 0) + 1

    present_ids = {sid for sid, cnt in seen.items() if cnt % 2 == 1}
    present     = len(present_ids)
    total       = len(students)
    absent      = total - present

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
    
    vio_rows = ""
    for r in violations:
        photo_link = f"<a href='/api/violations/photo/{r[4]}' target='_blank' style='color:#58a6ff;text-decoration:underline;'>Xem ảnh</a>" if r[4] else "Không ảnh"
        vio_rows += (
            f'<tr><td>{r[0]}</td>'
            f'<td>{r[1]}</td>'
            f'<td>{r[2]}</td>'
            f'<td>{r[3]}</td>'
            f'<td>{photo_link}</td></tr>'
        )

    html = f"""<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Báo Cáo Điểm Danh — {target_date}</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@300;400;600;700&display=swap');
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: 'Be Vietnam Pro', sans-serif;
    background: #0d1117;
    color: #c9d1d9;
    min-height: 100vh;
  }}
  header {{
    background: linear-gradient(135deg, #1f6feb 0%, #238636 100%);
    color: white;
    padding: 16px;
    display: flex; align-items: center; justify-content: space-between;
    border-bottom: 1px solid #30363d;
  }}
  header h1 {{ font-size: 1.2rem; font-weight: 700; }}
  header p  {{ font-size: 0.75rem; opacity: 0.85; margin-top: 2px; }}
  .badge {{
    background: rgba(255,255,255,0.2);
    border-radius: 20px; padding: 4px 10px;
    font-weight: 600; font-size: 0.75rem;
  }}
  .container {{ max-width: 100%; margin: 0 auto; padding: 12px; }}
  .stat-grid {{
    display: grid; grid-template-columns: repeat(2, 1fr);
    gap: 10px; margin-bottom: 16px;
  }}
  .stat-card {{
    background: #161b22; border-radius: 12px; padding: 12px;
    border: 1px solid #30363d;
    display: flex; flex-direction: column; align-items: flex-start;
  }}
  .stat-card .label {{ font-size: 0.7rem; color: #8b949e; font-weight: 600; text-transform: uppercase; }}
  .stat-card .value {{ font-size: 1.6rem; font-weight: 700; margin-top: 4px; }}
  .stat-card.green .value {{ color: #3fb950; }}
  .stat-card.red   .value {{ color: #f85149; }}
  .stat-card.blue  .value {{ color: #58a6ff; }}
  .stat-card.orange .value {{ color: #db6d28; }}
  
  .charts-grid {{
    display: grid; grid-template-columns: 1fr;
    gap: 12px; margin-bottom: 16px;
  }}
  .card {{
    background: #161b22; border-radius: 12px; padding: 12px;
    border: 1px solid #30363d;
    margin-bottom: 12px;
  }}
  .card h2 {{ font-size: 0.85rem; font-weight: 700; color: #f0f6fc; margin-bottom: 10px; }}
  .table-wrapper {{ overflow-x: auto; width: 100%; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 0.8rem; text-align: left; }}
  th {{ background: #21262d; color: #58a6ff; font-weight: 600; padding: 8px; }}
  td {{ padding: 8px; border-bottom: 1px solid #30363d; color: #c9d1d9; }}
  tr:hover td {{ background: #21262d; }}
  .pct {{ font-size: 0.65rem; color: #8b949e; margin-top: 2px; }}
  .empty {{ color: #8b949e; font-style: italic; text-align: center; padding: 12px; font-size: 0.8rem; }}
  footer {{ text-align: center; color: #8b949e; font-size: 0.7rem; padding: 12px; }}
</style>
</head>
<body>
<header>
  <div>
    <h1>Báo Cáo Điểm Danh</h1>
    <p>Ngày: {target_date} &nbsp;|&nbsp; Cập nhật: {datetime.now().strftime('%H:%M:%S')}</p>
  </div>
  <span class="badge">Live API</span>
</header>

<div class="container">
  <div class="stat-grid">
    <div class="stat-card blue">
      <span class="label">Tổng Học Sĩ</span>
      <span class="value">{total}</span>
    </div>
    <div class="stat-card green">
      <span class="label">Có Mặt</span>
      <span class="value">{present}</span>
      <span class="pct">{present*100//total if total else 0}% sĩ số</span>
    </div>
    <div class="stat-card red">
      <span class="label">Vắng Mặt</span>
      <span class="value">{absent}</span>
      <span class="pct">{absent*100//total if total else 0}% sĩ số</span>
    </div>
    <div class="stat-card orange">
      <span class="label">Vi Phạm</span>
      <span class="value">{len(violations)}</span>
      <span class="pct">Chưa quét / người lạ</span>
    </div>
  </div>

  <div class="charts-grid">
    <div class="card">
      <h2>Lượt Quét QR Theo Giờ</h2>
      <canvas id="hourChart" height="150"></canvas>
    </div>
    <div class="card" style="max-height: 250px;">
      <h2>Tỉ Lệ Điểm Danh</h2>
      <canvas id="pieChart" height="150"></canvas>
    </div>
  </div>

  <div class="card">
    <h2>Danh Sách Vắng Mặt ({absent})</h2>
    <div class="table-wrapper">
      {'<table><thead><tr><th>Mã HS</th><th>Họ Tên</th><th>Lớp</th></tr></thead><tbody>' + absent_rows + '</tbody></table>' if absent_rows else '<p class="empty">Tất cả học sinh đã có mặt!</p>'}
    </div>
  </div>
  
  <div class="card">
    <h2>Vi Phạm & Người Lạ ({len(violations)})</h2>
    <div class="table-wrapper">
      {'<table><thead><tr><th>Thời Gian</th><th>Mã</th><th>Họ Tên</th><th>Chi Tiết</th><th>Ảnh</th></tr></thead><tbody>' + vio_rows + '</tbody></table>' if vio_rows else '<p class="empty">Không có vi phạm nào hôm nay!</p>'}
    </div>
  </div>
</div>

<footer>Hệ Thống Điểm Danh STEM &mdash; Live Realtime Report</footer>

<script>
const hourLabels = {hour_data_js};
const hourData   = {hour_count_js};

new Chart(document.getElementById('hourChart'), {{
  type: 'bar',
  data: {{
    labels: hourLabels.length ? hourLabels : ['Chưa có dữ liệu'],
    datasets: [{{
      label: 'Lượt quét',
      data: hourData.length ? hourData : [0],
      backgroundColor: 'rgba(56, 139, 253, 0.7)',
      borderRadius: 4,
    }}]
  }},
  options: {{
    responsive: true, plugins: {{ legend: {{ display: false }} }},
    scales: {{ 
      y: {{ beginAtZero: true, ticks: {{ stepSize: 1, color: '#8b949e' }}, grid: {{ color: '#21262d' }} }},
      x: {{ ticks: {{ color: '#8b949e' }}, grid: {{ color: '#21262d' }} }}
    }}
  }}
}});

new Chart(document.getElementById('pieChart'), {{
  type: 'doughnut',
  data: {{
    labels: ['Có Mặt', 'Vắng'],
    datasets: [{{
      data: [{present}, {absent}],
      backgroundColor: ['#238636', '#da3637'],
      borderWidth: 1, borderColor: '#0d1117',
    }}]
  }},
  options: {{
    responsive: true,
    maintainAspectRatio: false,
    plugins: {{
      legend: {{ position: 'bottom', labels: {{ boxWidth: 12, color: '#8b949e', font: {{ size: 10 }} }} }},
    }}
  }}
}});
</script>
</body>
</html>"""
    return html

# ── PWA STATIC FILE SERVING ──────────────────────────────────────────────────
@app.route('/static/<path:filename>')
def serve_static(filename):
    """Serve PWA static assets (index.html, manifest.json, sw.js, icons…)"""
    return send_from_directory(STATIC_DIR, filename)

# ── PWA HOMEPAGE — redirects to static/index.html ────────────────────────────
@app.route('/')
def index_web_app():
    """Serves the new PWA Web Dashboard from static/index.html"""
    return send_from_directory(STATIC_DIR, 'index.html')

# ── LEGACY DASHBOARD (kept for compatibility) ─────────────────────────────────
@app.route('/legacy')
def index_legacy():
    """Legacy inline dashboard — kept for backwards-compatibility."""
    html = """<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>STEM Camera Monitor</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;600;700&display=swap');
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: 'Be Vietnam Pro', sans-serif;
    background-color: #0d1117;
    color: #c9d1d9;
    padding-bottom: 60px; /* Space for navbar */
    min-height: 100vh;
  }
  .app-header {
    background-color: #161b22;
    padding: 14px 16px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid #30363d;
    position: sticky; top: 0; z-index: 100;
  }
  .app-header h1 { font-size: 1.1rem; font-weight: 700; color: #f0f6fc; }
  .status-badge {
    display: flex; align-items: center; gap: 6px;
    font-size: 0.75rem; font-weight: 600; color: #8b949e;
  }
  .dot { width: 8px; height: 8px; background-color: #3fb950; display: inline-block; border-radius: 50%; }
  .dot.offline { background-color: #f85149; }
  
  .view-panel { display: none; padding: 12px; }
  .view-panel.active { display: block; }
  
  .stream-container {
    width: 100%; border-radius: 12px; overflow: hidden;
    border: 1px solid #30363d; background-color: black;
    aspect-ratio: 16/9; margin-bottom: 16px;
    display: flex; justify-content: center; align-items: center;
  }
  .stream-img { width: 100%; height: 100%; object-fit: contain; }
  
  .panel-title { font-size: 0.95rem; font-weight: 700; color: #8b949e; margin-bottom: 10px; text-transform: uppercase; letter-spacing: 0.05em; }
  
  .list-wrapper { display: flex; flex-direction: column; gap: 8px; }
  .card {
    background-color: #161b22; border-radius: 8px; padding: 10px;
    border: 1px solid #30363d;
  }
  .log-card { border-left: 4px solid #238636; }
  .vio-card { border-left: 4px solid #f85149; background-color: #211314; }
  .card-header { display: flex; justify-content: space-between; align-items: center; }
  .card-title { font-weight: 600; font-size: 0.85rem; color: #f0f6fc; }
  .card-sub { font-size: 0.75rem; color: #8b949e; margin-top: 4px; }
  .badge {
    font-size: 0.65rem; font-weight: 700; padding: 2px 6px; border-radius: 4px; color: white;
  }
  .badge.in { background-color: #238636; }
  .badge.out { background-color: #da3637; }
  .badge.vio { background-color: #f85149; }
  
  .vio-item-flex { display: flex; gap: 8px; align-items: center; }
  .vio-thumbnail { width: 42px; height: 42px; border-radius: 4px; object-fit: cover; border: 1px solid #30363d; }
  
  /* Bottom navigation bar */
  .bottom-nav {
    position: fixed; bottom: 0; left: 0; right: 0;
    height: 56px; background-color: #161b22;
    border-top: 1px solid #30363d;
    display: flex; justify-content: space-around; align-items: center;
    z-index: 100;
  }
  .nav-btn {
    background: none; border: none; color: #8b949e;
    font-family: inherit; font-size: 0.7rem; font-weight: 600;
    display: flex; flex-direction: column; align-items: center; gap: 4px;
    flex: 1; height: 100%; justify-content: center;
    cursor: pointer;
  }
  .nav-btn.active { color: #58a6ff; border-top: 2px solid #58a6ff; padding-top: -2px; }
  .nav-icon { font-size: 1.25rem; }
  
  iframe { width: 100%; height: calc(100vh - 130px); border: none; border-radius: 12px; background-color: #f0f4f8; }
</style>
</head>
<body>

  <div class="app-header">
    <h1>STEM Giám Sát</h1>
    <div class="status-badge">
      <span class="dot" id="statusDot"></span>
      <span id="statusText">ONLINE</span>
    </div>
  </div>

  <!-- VIEW 1: LIVE FEED MONITORING -->
  <div id="liveView" class="view-panel active">
    <div class="stream-container">
      <img id="streamImg" class="stream-img" onerror="handleStreamError(this)" />
    </div>
    
    <div style="display:grid; grid-template-columns: 1fr; gap: 16px;">
      <div>
        <h2 class="panel-title">⚠️ Vi Phạm / Người Lạ</h2>
        <div class="list-wrapper" id="violationsList">
          <div class="empty" id="noVios" style="text-align:center; padding:15px; color:#8b949e; font-style:italic; font-size:0.8rem;">Chưa có vi phạm nào hôm nay.</div>
        </div>
      </div>
      
      <div>
        <h2 class="panel-title">📝 Nhật Ký Điểm Danh</h2>
        <div class="list-wrapper" id="logsList">
          <div class="empty" id="noLogs" style="text-align:center; padding:15px; color:#8b949e; font-style:italic; font-size:0.8rem;">Chưa có lượt quét thẻ nào.</div>
        </div>
      </div>
    </div>
  </div>

  <!-- VIEW 2: REAL-TIME DAILY REPORT (bao_cao.html) -->
  <div id="reportView" class="view-panel">
    <iframe src="/api/report/html" id="reportFrame"></iframe>
  </div>

  <!-- BOTTOM NAVIGATION BAR -->
  <div class="bottom-nav">
    <button class="nav-btn active" onclick="switchView('live', this)">
      <span class="nav-icon">🎥</span>
      <span>Live Camera</span>
    </button>
    <button class="nav-btn" onclick="switchView('report', this)">
      <span class="nav-icon">📊</span>
      <span>Báo Cáo Ngày</span>
    </button>
  </div>

  <script>
    const logsList = document.getElementById('logsList');
    const violationsList = document.getElementById('violationsList');
    const noLogs = document.getElementById('noLogs');
    const noVios = document.getElementById('noVios');
    const reportFrame = document.getElementById('reportFrame');

    // Set stream source dynamically based on client connection host
    document.getElementById('streamImg').src = 'http://' + window.location.hostname + ':8080/stream';

    function switchView(viewName, button) {
      document.querySelectorAll('.view-panel').forEach(p => p.classList.remove('active'));
      document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
      
      button.classList.add('active');
      if (viewName === 'live') {
        document.getElementById('liveView').classList.add('active');
      } else {
        document.getElementById('reportView').classList.add('active');
        reportFrame.src = "/api/report/html?t=" + new Date().getTime();
      }
    }

    function handleStreamError(img) {
      img.parentNode.innerHTML = "<p style='color:#8b949e;font-size:0.8rem;text-align:center;'>Không tải được live stream camera.<br>Hãy chắc chắn main.py đang chạy.</p>";
    }

    // Load initial logs
    fetch('/api/logs')
      .then(res => res.json())
      .then(data => {
        if (data.length > 0) {
          noLogs.style.display = 'none';
          data.forEach(log => prependLog(log, false));
        }
      });

    fetch('/api/violations')
      .then(res => res.json())
      .then(data => {
        if (data.length > 0) {
          noVios.style.display = 'none';
          data.forEach(vio => prependViolation(vio, false));
        }
      });

    // Subscribe to SSE realtime alerts
    const sse = new EventSource('/api/events');
    
    sse.onopen = () => {
      document.getElementById('statusDot').className = "dot";
      document.getElementById('statusText').innerText = "ONLINE";
    };

    sse.onerror = () => {
      document.getElementById('statusDot').className = "dot offline";
      document.getElementById('statusText').innerText = "OFFLINE";
    };

    sse.addEventListener('log', (event) => {
      const log = JSON.parse(event.data);
      prependLog(log, true);
    });

    sse.addEventListener('violation', (event) => {
      const vio = JSON.parse(event.data);
      prependViolation(vio, true);
      if (navigator.vibrate) {
        navigator.vibrate([200, 100, 200]);
      }
    });

    function prependLog(log, highlight) {
      noLogs.style.display = 'none';
      const card = document.createElement('div');
      card.className = "card log-card";
      if (highlight) card.style.backgroundColor = '#1f2937';
      
      const badgeClass = log.trang_thai === 'Vao' ? 'in' : 'out';
      const badgeText = log.trang_thai === 'Vao' ? 'VÀO' : 'RA';
      
      card.innerHTML = `
        <div class="card-header">
          <span class="card-title">${log.ho_ten}</span>
          <span class="badge ${badgeClass}">${badgeText}</span>
        </div>
        <div class="card-sub">Mã HS: ${log.ma_hs} | ${log.thoi_gian}</div>
      `;
      
      logsList.insertBefore(card, logsList.firstChild);
      if (logsList.children.length > 30) {
        logsList.removeChild(logsList.lastChild);
      }
    }

    function prependViolation(vio, highlight) {
      noVios.style.display = 'none';
      const card = document.createElement('div');
      card.className = "card vio-card";
      if (highlight) card.style.backgroundColor = '#3b1c1d';
      
      const photoHtml = vio.photo_url 
        ? `<img src="${vio.photo_url}" class="vio-thumbnail" onclick="window.open('${vio.photo_url}', '_blank')"/>` 
        : ``;
      
      card.innerHTML = `
        <div class="vio-item-flex">
          ${photoHtml}
          <div style="flex:1;">
            <div class="card-header">
              <span class="card-title" style="color:#f85149;">${vio.ho_ten}</span>
              <span class="badge vio">CẢNH BÁO</span>
            </div>
            <div class="card-sub" style="color:#c9d1d9;">${vio.mo_ta}</div>
            <div class="card-sub" style="font-size:0.65rem;">${vio.thoi_gian}</div>
          </div>
        </div>
      `;
      
      violationsList.insertBefore(card, violationsList.firstChild);
      if (violationsList.children.length > 20) {
        violationsList.removeChild(violationsList.lastChild);
      }
    }
  </script>
</body>
</html>
"""
    return Response(html, mimetype='text/html')

@app.route('/api/logs', methods=['GET'])
def get_logs():
    """Fetch recent attendance logs (both online and offline synced logs)"""
    conn = get_db_connection()
    try:
        rows = conn.execute(
            "SELECT id, thoi_gian, ma_hs, ho_ten, trang_thai, synced FROM offline_log ORDER BY id DESC LIMIT 30"
        ).fetchall()
        logs = [dict(r) for r in rows]
        return jsonify(logs)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@app.route('/api/violations', methods=['GET'])
def get_violations():
    """Fetch recent violation and stranger detection history with photo endpoints"""
    conn = get_db_connection()
    try:
        rows = conn.execute(
            "SELECT id, thoi_gian, ma_hs, ho_ten, mo_ta, ten_file, duong_dan, synced FROM offline_violation ORDER BY id DESC LIMIT 20"
        ).fetchall()
        violations = []
        for r in rows:
            d = dict(r)
            if d['ten_file']:
                d['photo_url'] = f"/api/violations/photo/{d['ten_file']}"
            else:
                d['photo_url'] = None
            violations.append(d)
        return jsonify(violations)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@app.route('/api/violations/photo/<filename>', methods=['GET'])
def get_violation_photo(filename):
    """Serve local violation images to the mobile client"""
    return send_from_directory(VIOLATIONS_DIR, filename)

@app.route('/api/report/html', methods=['GET'])
def get_report_html():
    """Dynamically build and serve the daily report (bao_cao.html) directly from local database in real-time."""
    target_date = request.args.get('date', datetime.now().strftime("%d/%m/%Y"))
    try:
        students, logs, violations = get_report_data(target_date)
        html_content = build_html_report(target_date, students, logs, violations)
        return Response(html_content, mimetype='text/html')
    except Exception as e:
        return f"<h3>Lỗi tạo báo cáo: {str(e)}</h3>", 500

@app.route('/api/events', methods=['GET'])
def sse_events():
    """
    Real-time Server-Sent Events (SSE) stream.
    Pushes notifications to the mobile app instantly when a QR scan or stranger is detected.
    """
    def event_stream():
        conn = get_db_connection()
        try:
            last_log_id = conn.execute("SELECT MAX(id) FROM offline_log").fetchone()[0] or 0
            last_vio_id = conn.execute("SELECT MAX(id) FROM offline_violation").fetchone()[0] or 0
        except Exception:
            last_log_id = 0
            last_vio_id = 0
        finally:
            conn.close()

        print("[SSE] Mobile client connected to notification stream.")

        while True:
            time.sleep(1.0) # Poll local database for updates every 1 second
            conn = get_db_connection()
            try:
                # 1. Check for new logs (QR check-ins)
                new_logs = conn.execute(
                    "SELECT id, thoi_gian, ma_hs, ho_ten, trang_thai FROM offline_log WHERE id > ? ORDER BY id ASC",
                    (last_log_id,)
                ).fetchall()
                for log in new_logs:
                    last_log_id = log['id']
                    yield f"event: log\ndata: {json.dumps(dict(log))}\n\n"

                # 2. Check for new violations (strangers / warning mismatch)
                new_vios = conn.execute(
                    "SELECT id, thoi_gian, ma_hs, ho_ten, mo_ta, ten_file, duong_dan FROM offline_violation WHERE id > ? ORDER BY id ASC",
                    (last_vio_id,)
                ).fetchall()
                for vio in new_vios:
                    last_vio_id = vio['id']
                    d = dict(vio)
                    if d['ten_file']:
                        d['photo_url'] = f"/api/violations/photo/{d['ten_file']}"
                    else:
                        d['photo_url'] = None
                    yield f"event: violation\ndata: {json.dumps(d)}\n\n"
            except Exception as e:
                yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
            finally:
                conn.close()

    return Response(event_stream(), content_type='text/event-stream')

if __name__ == '__main__':
    # Listen on port 5000 and bind to all interfaces (accessible via computer IP on local network)
    print("=" * 60)
    print("  AI CAMERA MONITORING API SERVER FOR MOBILE APP")
    print("=" * 60)
    app.run(host='0.0.0.0', port=5000, debug=True)
