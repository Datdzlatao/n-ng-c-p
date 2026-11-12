/**
 * src/services/api.js — Centralized API Client & Token Interceptors
 */

const API_BASE = import.meta.env.VITE_API_URL || '';

let isRefreshing = false;
let refreshSubscribers = [];

function subscribeTokenRefresh(cb) {
  refreshSubscribers.push(cb);
}

function onRefreshed(token) {
  refreshSubscribers.forEach((cb) => cb(token));
  refreshSubscribers = [];
}

export async function request(endpoint, options = {}) {
  const token = localStorage.getItem('stem_auth_token');
  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  };

  const config = {
    ...options,
    headers,
  };

  if (options.body && typeof options.body === 'object') {
    config.body = JSON.stringify(options.body);
  }

  let response;
  try {
    response = await fetch(`${API_BASE}${endpoint}`, config);
  } catch (err) {
    if (err?.name === 'TypeError' || err?.message?.includes('Failed to fetch')) {
      const netErr = new Error('Không thể kết nối đến máy chủ Backend (Máy chủ chưa khởi động hoặc mất mạng). Vui lòng thử lại sau.');
      netErr.status = 0;
      netErr.isNetworkError = true;
      throw netErr;
    }
    throw err;
  }

  // Xử lý tự động Refresh Token khi Access Token hết hạn (HTTP 401)
  if (response.status === 401 && !endpoint.includes('/auth/login') && !endpoint.includes('/auth/refresh')) {
    const refreshToken = localStorage.getItem('stem_refresh_token');
    if (refreshToken) {
      if (!isRefreshing) {
        isRefreshing = true;
        try {
          const refreshRes = await fetch(`${API_BASE}/api/v1/auth/refresh`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ refresh_token: refreshToken }),
          });
          const refreshData = await refreshRes.json();
          if (refreshRes.ok && refreshData?.access_token) {
            localStorage.setItem('stem_auth_token', refreshData.access_token);
            onRefreshed(refreshData.access_token);
            // Retry request ban đầu với token mới
            config.headers.Authorization = `Bearer ${refreshData.access_token}`;
            const retryRes = await fetch(`${API_BASE}${endpoint}`, config);
            return await retryRes.json().catch(() => null);
          } else {
            localStorage.removeItem('stem_auth_token');
            localStorage.removeItem('stem_refresh_token');
          }
        } catch {
          localStorage.removeItem('stem_auth_token');
          localStorage.removeItem('stem_refresh_token');
        } finally {
          isRefreshing = false;
        }
      } else {
        // Đang có request khác refresh, đợi token mới rồi retry
        return new Promise((resolve, reject) => {
          subscribeTokenRefresh(async (newToken) => {
            if (!newToken) {
              reject(new Error('Session expired'));
              return;
            }
            config.headers.Authorization = `Bearer ${newToken}`;
            try {
              const retryRes = await fetch(`${API_BASE}${endpoint}`, config);
              const retryData = await retryRes.json().catch(() => null);
              resolve(retryData);
            } catch (err) {
              reject(err);
            }
          });
        });
      }
    }
  }

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    let errMsg = `HTTP ${response.status}`;
    if (data?.detail) {
      if (typeof data.detail === 'string') {
        errMsg = data.detail;
      } else if (Array.isArray(data.detail)) {
        errMsg = data.detail
          .map((item) => (typeof item === 'object' && item !== null ? (item.msg || JSON.stringify(item)) : String(item)))
          .join(', ');
      } else if (typeof data.detail === 'object') {
        errMsg = data.detail.msg || data.detail.message || JSON.stringify(data.detail);
      }
    } else if (data?.message) {
      errMsg = typeof data.message === 'string' ? data.message : JSON.stringify(data.message);
    }
    const error = new Error(errMsg);
    error.status = response.status;
    error.data = data;
    throw error;
  }

  return data;
}

export const api = {
  get: (endpoint, options) => request(endpoint, { ...options, method: 'GET' }),
  post: (endpoint, body, options) => request(endpoint, { ...options, method: 'POST', body }),
  put: (endpoint, body, options) => request(endpoint, { ...options, method: 'PUT', body }),
  delete: (endpoint, options) => request(endpoint, { ...options, method: 'DELETE' }),
};
