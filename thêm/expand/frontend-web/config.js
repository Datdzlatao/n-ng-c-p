/**
 * frontend-web/config.js — Frontend Configuration
 * Import file này trước mọi script khác trong HTML.
 *
 * Development: Backend chạy port 8000, Frontend chạy port 5173
 * Production:  Cùng domain (Nginx proxy /api/* → backend)
 */

const isDevFrontendPort = ['5173', '3000'].includes(window.location.port);
const isLocalHostname = ['localhost', '127.0.0.1', '0.0.0.0'].includes(window.location.hostname);
const isLanHostname = /^(192\.168\.|10\.|172\.(1[6-9]|2\d|3[01])\.)/.test(window.location.hostname);
// Chỉ khi chạy Frontend độc lập (Vite port 5173/3000) mới cần gọi tường minh sang port 8000
const isSeparateDevServer = isDevFrontendPort && (isLocalHostname || isLanHostname);

const STEM_CONFIG = {
  // Development (Vite): Gọi sang Backend FastAPI port 8000
  // All-in-one / Production: Gọi relative ('') do FastAPI hoặc Nginx phục vụ trực tiếp
  API_BASE: isSeparateDevServer
    ? `http://${window.location.hostname}:8000`
    : '',

  WS_BASE: isSeparateDevServer
    ? `ws://${window.location.hostname}:8000`
    : `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}`,

  APP_NAME: 'Điểm Danh STEM',
  APP_VERSION: '1.0.0',
};

// Helper: gọi API với đúng base URL
async function stemAPI(method, path, body = null, token = null) {
  const url  = STEM_CONFIG.API_BASE + path;
  const opts = {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
    },
  };
  if (body) opts.body = JSON.stringify(body);
  const res  = await fetch(url, opts);
  const data = await res.json();
  if (!res.ok) throw data;
  return data;
}
