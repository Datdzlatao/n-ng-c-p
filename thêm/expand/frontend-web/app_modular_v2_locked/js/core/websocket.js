// app/js/core/websocket.js — Realtime WebSocket & Telemetry Dispatcher
// ── WebSocket ─────────────────────────────────────
let attLiveDebounceTimer = null;
function scheduleActiveAttendanceRefresh() {
  clearTimeout(attLiveDebounceTimer);
  attLiveDebounceTimer = setTimeout(() => {
    loadStats().then(updateBadges);
    if (document.getElementById('view-attendance')?.classList.contains('active')) {
      loadAttendance();
    }
    if (document.getElementById('view-my-attendance')?.classList.contains('active')) {
      loadMyAttendance();
    }
  }, 1200);
}

function connectWS() {
  const wsBase = (typeof STEM_CONFIG !== 'undefined' && STEM_CONFIG.WS_BASE)
    ? STEM_CONFIG.WS_BASE
    : `${location.protocol === 'https:' ? 'wss:' : 'ws:'}//${location.host}`;
  const tk = localStorage.getItem(AUTH_KEY) || localStorage.getItem('stem_admin_token') || '';
  const wsUrl = `${wsBase}/ws/${schoolId}/live${tk ? `?token=${encodeURIComponent(tk)}` : ''}`;
  ws = new WebSocket(wsUrl);
  ws.onopen = () => {
    document.getElementById('wsDot')?.classList.add('online');
    const lbl = document.getElementById('wsLabel');
    if (lbl) lbl.innerText = 'Live';
    if (typeof updateConnectionBanner === 'function') updateConnectionBanner(true);
  };
  ws.onmessage = (e) => {
    try {
      const msg = JSON.parse(e.data);
      // 🚨 CẢNH BÁO AN NINH CỔNG TRƯỜNG: Phát hiện người lạ
      if (msg.type === 'SECURITY_ALERT' || msg.alert_type === 'STRANGER') {
        const dirLabel = (msg.direction || 'IN').toUpperCase() === 'OUT' ? 'Lượt Ra Về' : 'Lượt Vào Cổng';
        const stName = msg.station_name || 'Cổng trường';
        toast('🚨 CẢNH BÁO: PHÁT HIỆN NGƯỜI LẠ!', `Tại ${stName} (${dirLabel}) — Đối tượng không có trong danh bạ trường!`, 'error');
        
        // Hiệu ứng cảnh báo đỏ khẩn cấp trên icon trạng thái Live
        const dot = document.getElementById('wsDot');
        if (dot) {
          dot.style.background = '#ef4444';
          dot.style.boxShadow = '0 0 14px #ef4444';
          setTimeout(() => { dot.style.background = ''; dot.style.boxShadow = ''; }, 4000);
        }
        return;
      }

      if (msg.type === 'ATTENDANCE_LOG' || msg.type === 'ATTENDANCE') {
        // Đã tắt thông báo popup/toast học sinh ra-vào cổng thường để tránh đơ/lag hệ thống giờ cao điểm
        // Chỉ làm mới dữ liệu chủ động cho màn hình đang mở (có chống dồn tải debounce)
        scheduleActiveAttendanceRefresh();

        // Cập nhật thẻ trực tiếp nếu người dùng đang chủ động xem màn hình camera AI
        if (typeof handleLiveWsAttendance === 'function' && document.getElementById('view-cameras')?.classList.contains('active')) {
          handleLiveWsAttendance(msg);
        }
      }
    } catch(err) {}
  };
  ws.onclose = () => {
    document.getElementById('wsDot')?.classList.remove('online');
    const lbl = document.getElementById('wsLabel');
    if (lbl) lbl.innerText = 'Mất kết nối';
    if (typeof updateConnectionBanner === 'function') updateConnectionBanner(false);
    setTimeout(connectWS, 5000);
  };
}



export {
  connectWS, scheduleActiveAttendanceRefresh
};
