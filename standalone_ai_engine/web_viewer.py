# -*- coding: utf-8 -*-
"""
WEB VIEWER HTML TEMPLATE
Giao diện trực quan xem camera AI online trực tiếp trên trình duyệt.
"""

VIEWER_HTML = """<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Vision Live Stream & Inspection</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: #090d16;
            color: #e2e8f0;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
        }
        header {
            background: #0f172a;
            border-bottom: 1px solid #1e293b;
            padding: 12px 24px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        .logo {
            display: flex;
            align-items: center;
            gap: 12px;
            font-weight: 700;
            font-size: 1.15rem;
            color: #38bdf8;
        }
        .badge-live {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background: rgba(16, 185, 129, 0.15);
            color: #10b981;
            border: 1px solid rgba(16, 185, 129, 0.3);
            padding: 4px 10px;
            border-radius: 999px;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
        }
        .pulse-dot {
            width: 8px;
            height: 8px;
            background: #10b981;
            border-radius: 50%;
            animation: pulse 1.5s infinite;
        }
        @keyframes pulse {
            0% { transform: scale(0.95); opacity: 0.8; }
            50% { transform: scale(1.3); opacity: 1; }
            100% { transform: scale(0.95); opacity: 0.8; }
        }
        .container {
            display: grid;
            grid-template-columns: 1fr 380px;
            gap: 20px;
            padding: 20px;
            flex: 1;
            max-width: 1600px;
            margin: 0 auto;
            width: 100%;
        }
        @media (max-width: 1024px) {
            .container { grid-template-columns: 1fr; }
        }
        .video-panel {
            background: #0f172a;
            border: 1px solid #1e293b;
            border-radius: 16px;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            position: relative;
        }
        .video-wrapper {
            position: relative;
            background: #000;
            flex: 1;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 480px;
        }
        .video-wrapper img {
            width: 100%;
            height: 100%;
            object-fit: contain;
            display: block;
        }
        .video-controls {
            padding: 14px 20px;
            background: #0b1120;
            border-top: 1px solid #1e293b;
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 12px;
        }
        .btn-group { display: flex; gap: 8px; }
        button {
            cursor: pointer;
            border: none;
            outline: none;
            padding: 8px 16px;
            border-radius: 8px;
            font-weight: 600;
            font-size: 0.85rem;
            transition: all 0.2s;
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }
        .btn-primary { background: #2563eb; color: #fff; }
        .btn-primary:hover { background: #1d4ed8; }
        .btn-danger { background: #dc2626; color: #fff; }
        .btn-danger:hover { background: #b91c1c; }
        .btn-secondary { background: #1e293b; color: #cbd5e1; border: 1px solid #334155; }
        .btn-secondary:hover { background: #334155; }
        .side-panel {
            display: flex;
            flex-direction: column;
            gap: 16px;
        }
        .card {
            background: #0f172a;
            border: 1px solid #1e293b;
            border-radius: 14px;
            padding: 16px;
        }
        .card-title {
            font-size: 0.85rem;
            font-weight: 700;
            color: #94a3b8;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 12px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .stat-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 10px;
        }
        .stat-item {
            background: #1e293b80;
            border-radius: 8px;
            padding: 10px;
            border: 1px solid #33415540;
        }
        .stat-label { font-size: 0.75rem; color: #64748b; margin-bottom: 4px; }
        .stat-value { font-size: 1.1rem; font-weight: 700; color: #f8fafc; }
        .stat-value.ok { color: #10b981; }
        .stat-value.warn { color: #f59e0b; }
        .stat-value.danger { color: #ef4444; }
        .form-row {
            display: flex;
            flex-direction: column;
            gap: 6px;
            margin-bottom: 12px;
        }
        .form-row label {
            font-size: 0.78rem;
            color: #94a3b8;
            font-weight: 500;
        }
        select, input {
            background: #1e293b;
            border: 1px solid #334155;
            color: #f8fafc;
            padding: 8px 12px;
            border-radius: 8px;
            font-size: 0.85rem;
            outline: none;
        }
        select:focus, input:focus { border-color: #38bdf8; }
        .tag-status {
            display: inline-block;
            padding: 3px 8px;
            border-radius: 6px;
            font-size: 0.75rem;
            font-weight: 600;
        }
        .tag-ok { background: rgba(16,185,129,0.2); color: #34d399; }
        .tag-stranger { background: rgba(245,158,11,0.2); color: #fbbf24; }
        .tag-spoof { background: rgba(239,68,68,0.2); color: #f87171; }
        .face-list {
            display: flex;
            flex-direction: column;
            gap: 8px;
            max-height: 180px;
            overflow-y: auto;
        }
        .face-card {
            background: #1e293b60;
            border: 1px solid #33415560;
            border-radius: 8px;
            padding: 10px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .face-info h4 { font-size: 0.9rem; color: #f1f5f9; font-weight: 600; }
        .face-info p { font-size: 0.75rem; color: #64748b; margin-top: 2px; }
    </style>
</head>
<body>
    <header>
        <div class="logo">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10"></circle>
                <path d="M12 16v-4"></path>
                <path d="M12 8h.01"></path>
            </svg>
            <span>STANDALONE AI VISION — CAMERA LIVE FEED</span>
        </div>
        <div class="badge-live" id="liveBadge">
            <span class="pulse-dot"></span>
            <span id="liveStatusText">CAMERA ONLINE</span>
        </div>
    </header>

    <div class="container">
        <!-- Panel luồng Video -->
        <div class="video-panel">
            <div class="video-wrapper">
                <img id="streamImg" src="/api/v1/camera/video_feed" alt="Đang kết nối camera...">
            </div>
            <div class="video-controls">
                <div class="btn-group">
                    <button class="btn-primary" id="btnStart" onclick="startCamera()">▶ Bật Camera</button>
                    <button class="btn-danger" id="btnStop" onclick="stopCamera()">⏹ Dừng Camera</button>
                    <button class="btn-secondary" onclick="takeSnapshot()">📷 Chụp Snapshot</button>
                </div>
                <div style="display: flex; align-items: center; gap: 8px; font-size: 0.85rem; color: #94a3b8;">
                    <label style="display: flex; align-items: center; gap: 6px; cursor: pointer;">
                        <input type="checkbox" id="chkOverlay" checked onchange="toggleOverlay()">
                        Hiện khung vẽ AI (HUD Overlay)
                    </label>
                </div>
            </div>
        </div>

        <!-- Panel điều khiển và thông số -->
        <div class="side-panel">
            <!-- Điều khiển Nguồn Camera -->
            <div class="card">
                <div class="card-title">Cấu hình Nguồn Camera</div>
                <div class="form-row">
                    <label>Nguồn Camera (Webcam / RTSP):</label>
                    <input type="text" id="cameraSource" value="0" placeholder="0 (Webcam) hoặc rtsp://...">
                </div>
                <div class="form-row">
                    <label>Chế độ chấm công:</label>
                    <select id="weekdaySelect" onchange="updateWeekday()">
                        <option value="-1" selected>🟢 Chấm công 24/7 mọi lúc (Trang trại - Không giới hạn giờ)</option>
                        <option value="">Tự động theo ngày hiện tại</option>
                        <option value="0">Thứ 2 (Trang phục dân tộc)</option>
                        <option value="1">Thứ 3 (Áo trắng + Quần tối)</option>
                        <option value="2">Thứ 4 (Áo trắng + Quần tối)</option>
                        <option value="3">Thứ 5 (Áo trắng + Quần tối)</option>
                        <option value="4">Thứ 6 (Áo Đoàn thanh niên)</option>
                        <option value="5">Thứ 7 (Hoạt động ngoại khóa)</option>
                        <option value="6">Chủ nhật (Nghỉ)</option>
                    </select>
                </div>
                <button class="btn-secondary" style="width: 100%; justify-content: center;" onclick="applyConfig()">Áp dụng Cấu hình</button>
            </div>

            <!-- Trạng thái Nhận diện Khuôn mặt -->
            <div class="card">
                <div class="card-title">
                    <span>Nhận diện Khuôn mặt</span>
                    <span id="faceCountBadge" class="tag-status tag-ok">0 người</span>
                </div>
                <div class="face-list" id="faceList">
                    <div style="color: #64748b; font-size: 0.82rem; text-align: center; padding: 12px;">Chưa phát hiện khuôn mặt...</div>
                </div>
            </div>

            <!-- Trạng thái Kiểm tra Đồng phục -->
            <div class="card">
                <div class="card-title">Kiểm tra Trang phục</div>
                <div class="stat-grid" style="margin-bottom: 10px;">
                    <div class="stat-item">
                        <div class="stat-label">Kết quả</div>
                        <div class="stat-value" id="uniResult">--</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">Màu áo / Quần</div>
                        <div class="stat-value" style="font-size: 0.85rem;" id="uniColors">--</div>
                    </div>
                </div>
                <div style="font-size: 0.8rem; color: #94a3b8;" id="uniMessage">Đang chờ dữ liệu...</div>
                <div style="font-size: 0.75rem; color: #64748b; margin-top: 4px;" id="uniRule"></div>
            </div>

            <!-- Hiệu năng hệ thống -->
            <div class="card">
                <div class="card-title">Hiệu năng & Telemetry</div>
                <div class="stat-grid">
                    <div class="stat-item">
                        <div class="stat-label">Camera FPS</div>
                        <div class="stat-value ok" id="statFps">0.0</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">Độ trễ AI</div>
                        <div class="stat-value" id="statLatency">0 ms</div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        let overlayEnabled = true;

        function updateStreamUrl() {
            const img = document.getElementById("streamImg");
            img.src = `/api/v1/camera/video_feed?overlay=${overlayEnabled}&t=${Date.now()}`;
        }

        function toggleOverlay() {
            overlayEnabled = document.getElementById("chkOverlay").checked;
            updateStreamUrl();
        }

        async function startCamera() {
            const src = document.getElementById("cameraSource").value;
            const weekday = document.getElementById("weekdaySelect").value;
            const res = await fetch("/api/v1/camera/start", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    source: src,
                    weekday_override: weekday ? parseInt(weekday) : null
                })
            });
            const data = await res.json();
            if (data.status === "success") {
                updateStreamUrl();
            } else {
                alert("Lỗi bật camera: " + data.message);
            }
        }

        async function stopCamera() {
            await fetch("/api/v1/camera/stop", { method: "POST" });
            const img = document.getElementById("streamImg");
            img.src = "";
            document.getElementById("liveBadge").style.display = "none";
        }

        function takeSnapshot() {
            window.open(`/api/v1/camera/snapshot?overlay=${overlayEnabled}&t=${Date.now()}`, "_blank");
        }

        function applyConfig() {
            startCamera();
        }

        function updateWeekday() {
            startCamera();
        }

        // Định kỳ 500ms lấy kết quả phân tích AI mới nhất
        setInterval(async () => {
            try {
                const res = await fetch("/api/v1/camera/latest");
                if (!res.ok) return;
                const data = await res.json();

                // Cập nhật telemetry
                document.getElementById("statFps").innerText = (data.capture_fps || 0).toFixed(1);
                document.getElementById("statLatency").innerText = Math.round(data.process_time_ms || 0) + " ms";

                // Badge Live
                const badge = document.getElementById("liveBadge");
                if (data.is_running) {
                    badge.style.display = "inline-flex";
                } else {
                    badge.style.display = "none";
                }

                // Cập nhật khuôn mặt
                const faceListEl = document.getElementById("faceList");
                const faces = data.faces || [];
                document.getElementById("faceCountBadge").innerText = `${faces.length} người`;

                if (faces.length === 0) {
                    faceListEl.innerHTML = '<div style="color: #64748b; font-size: 0.82rem; text-align: center; padding: 12px;">Không có khuôn mặt nào</div>';
                } else {
                    faceListEl.innerHTML = faces.map(f => {
                        const isOk = f.status === "ok";
                        const isReal = f.liveness && f.liveness.is_real;
                        let tagClass = isOk ? "tag-ok" : "tag-stranger";
                        let tagText = isOk ? (f.student_id ? `${f.student_id}` : "HỢP LỆ") : "NGƯỜI LẠ";

                        let liveTag = isReal ? '<span style="color: #34d399;">✓ Thật</span>' : '<span style="color: #f87171;">✕ Giả mạo</span>';

                        return `
                            <div class="face-card">
                                <div class="face-info">
                                    <h4>${f.name}</h4>
                                    <p>Tin cậy: ${(f.confidence * 100).toFixed(1)}% | Liveness: ${liveTag}</p>
                                </div>
                                <span class="tag-status ${tagClass}">${tagText}</span>
                            </div>
                        `;
                    }).join("");
                }

                // Cập nhật đồng phục
                const uni = data.uniform;
                if (uni) {
                    const uniResEl = document.getElementById("uniResult");
                    uniResEl.innerText = uni.status;
                    uniResEl.className = "stat-value " + (uni.is_correct ? "ok" : "danger");

                    document.getElementById("uniColors").innerText = `Áo: ${uni.shirt_color || '-'} / Quần: ${uni.pants_color || '-'}`;
                    document.getElementById("uniMessage").innerText = uni.message || '';
                    document.getElementById("uniRule").innerText = `Quy định: ${uni.rule || ''}`;
                }
            } catch (e) {
                // Ignore network glitch
            }
        }, 500);
    </script>
</body>
</html>
"""
