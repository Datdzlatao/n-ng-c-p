// app/js/core/api.js — Fetch API Client with Auto-Refresh & Connection State
// ── API Helper ───────────────────────────────────
let isRefreshing = false;

async function api(method, path, body = null, isRetry = false) {
  const token = localStorage.getItem(AUTH_KEY);
  const apiBase = (typeof STEM_CONFIG !== 'undefined' && STEM_CONFIG.API_BASE) ? STEM_CONFIG.API_BASE : '';
  const url = path.startsWith('http') ? path : `${apiBase}${path}`;
  const opts  = {
    method,
    headers: { 'Content-Type': 'application/json', ...(token ? { 'Authorization': `Bearer ${token}` } : {}) }
  };
  if (body) {
    if (typeof FormData !== 'undefined' && body instanceof FormData) {
      delete opts.headers['Content-Type'];
      opts.body = body;
    } else {
      opts.body = typeof body === 'string' ? body : JSON.stringify(body);
    }
  }
  let res;
  try {
    res = await fetch(url, opts);
    if (typeof updateConnectionBanner === 'function') updateConnectionBanner(true);
  } catch (netErr) {
    if (typeof updateConnectionBanner === 'function') updateConnectionBanner(false);
    const err = new Error('Mất kết nối máy chủ (Backend chưa sẵn sàng hoặc rớt mạng).');
    err.isNetworkError = true;
    err.original = netErr;
    throw err;
  }

  // Auto-refresh on 401 Unauthorized
  if (res.status === 401 && !isRetry && !path.includes('/auth/login') && !path.includes('/auth/refresh')) {
    const refreshToken = localStorage.getItem(REFRESH_KEY);
    if (refreshToken && !isRefreshing) {
      isRefreshing = true;
      try {
        const refreshRes = await fetch(`${apiBase}/api/v1/auth/refresh`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh_token: refreshToken })
        });
        if (refreshRes.ok) {
          const refreshData = await refreshRes.json();
          if (refreshData.access_token) {
            localStorage.setItem(AUTH_KEY, refreshData.access_token);
            isRefreshing = false;
            return await api(method, path, body, true);
          }
        }
      } catch (err) {}
      isRefreshing = false;
      localStorage.removeItem(AUTH_KEY);
      localStorage.removeItem(REFRESH_KEY);
      location.href = '/';
      return;
    }
  }

  const data = await res.json().catch(() => null);
  if (!res.ok) throw (data || { detail: `HTTP ${res.status}` });
  return data;
}



export { api };
