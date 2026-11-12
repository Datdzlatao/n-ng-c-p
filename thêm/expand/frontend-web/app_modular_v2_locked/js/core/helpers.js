// app/js/core/helpers.js — Utilities & Sanitizers
// ── Security: HTML Escape Helper (Ngăn chặn DOM XSS) ──
function escHtml(str) {
  if (str === null || str === undefined) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}



// ── Helpers ───────────────────────────────────────
function emptyRow(msg, cols) { return `<tr><td colspan="${cols}"><div class="empty"><div class="empty-icon">📭</div><div class="empty-text">${msg}</div></div></td></tr>`; }
let isOfflineBannerActive = false;
let autoReconnectTimer = null;

function updateConnectionBanner(isOnline) {
  const el = document.getElementById('connectionBanner');
  if (!el) return;
  if (isOnline) {
    if (isOfflineBannerActive) {
      isOfflineBannerActive = false;
      el.style.background = '#16a34a';
      el.innerHTML = '<span>✅ Đã kết nối lại máy chủ thành công!</span>';
      setTimeout(() => {
        el.style.display = 'none';
        el.style.background = '#dc2626';
        el.innerHTML = `<span>⚠️ Mất kết nối đến máy chủ Backend (Port 8000). Đang tự động kết nối lại...</span>
        <button onclick="location.reload()" style="background:rgba(255,255,255,0.2);border:1px solid #ffffff;color:#fff;padding:3px 10px;border-radius:6px;cursor:pointer;font-size:0.75rem;font-weight:700;">🔄 Thử lại ngay</button>`;
      }, 2000);
      if (autoReconnectTimer) {
        clearInterval(autoReconnectTimer);
        autoReconnectTimer = null;
      }
    }
  } else {
    if (!isOfflineBannerActive) {
      isOfflineBannerActive = true;
      el.style.display = 'flex';
      if (!autoReconnectTimer) {
        autoReconnectTimer = setInterval(async () => {
          try {
            const apiBase = (typeof STEM_CONFIG !== 'undefined' && STEM_CONFIG.API_BASE) ? STEM_CONFIG.API_BASE : '';
            const res = await fetch(`${apiBase}/health/live`, { cache: 'no-store' });
            if (res.ok) {
              updateConnectionBanner(true);
              if (typeof loadStats === 'function') loadStats();
              if (typeof loadClasses === 'function') loadClasses();
            }
          } catch(e) {}
        }, 4000);
      }
    }
  }
}

function errorRow(e, cols) {
  let msg = 'Không tải được dữ liệu.';
  let isNetErr = false;
  if (typeof e === 'string') {
    msg = e;
    if (e.includes('Failed to fetch') || e.includes('NetworkError') || e.includes('Mất kết nối')) isNetErr = true;
  } else if (e?.detail) {
    msg = typeof e.detail === 'string' ? e.detail : JSON.stringify(e.detail);
  } else if (e?.message) {
    msg = e.message;
    if (e.message.includes('Failed to fetch') || e.name === 'TypeError' || e.isNetworkError) isNetErr = true;
  }

  if (isNetErr) {
    msg = 'Mất kết nối máy chủ (Backend chưa sẵn sàng hoặc rớt mạng).';
    if (typeof updateConnectionBanner === 'function') updateConnectionBanner(false);
  }

  return `<tr><td colspan="${cols}" style="text-align:center;padding:24px;color:var(--red);">
    <div style="display:flex;flex-direction:column;align-items:center;gap:8px;">
      <div style="font-weight:600;">⚠️ ${msg}</div>
      <button class="btn btn-outline" onclick="location.reload()" style="font-size:0.75rem;padding:4px 12px;border-color:var(--red);color:var(--red);cursor:pointer;">
        🔄 Tải lại dữ liệu
      </button>
    </div>
  </td></tr>`;
}


export {
  emptyRow, errorRow, escHtml, updateConnectionBanner
};
