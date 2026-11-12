/**
 * js/services/authService.js — Authentication & Session Management
 */
import { apiClient } from './api.js';
import { AUTH_KEY, ADMIN_TOKEN_KEY, REFRESH_TOKEN_KEY, SCHOOL_ID_KEY } from '../config.js';

export async function login(school_id, username_or_phone, password) {
  return await apiClient('POST', '/api/v1/auth/login', {
    school_id,
    username_or_phone,
    password,
  });
}

export async function platformLogin(username_or_email, password) {
  return await apiClient('POST', '/api/v1/platform/login', {
    username_or_email,
    password,
  });
}

export function logoutAll() {
  localStorage.removeItem(AUTH_KEY);
  localStorage.removeItem(ADMIN_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
  localStorage.removeItem(SCHOOL_ID_KEY);
  window.location.reload();
}

export function goToDashboard(schoolId, fallbackSchools = []) {
  let sid = parseInt(schoolId);
  if (isNaN(sid) || sid <= 0) {
    sid = fallbackSchools.length > 0 ? fallbackSchools[0].id : 1;
  }
  window.location.href = `/app/index.html?school_id=${sid}`;
}

export function checkAuth(fallbackSchools = []) {
  const adminToken = localStorage.getItem(ADMIN_TOKEN_KEY);
  const token = localStorage.getItem(AUTH_KEY);
  const storedId = localStorage.getItem(SCHOOL_ID_KEY);
  const schoolId = storedId && !isNaN(parseInt(storedId))
    ? parseInt(storedId)
    : (fallbackSchools[0]?.id || 1);

  const navActions = document.querySelector('.nav-actions');
  if (!navActions) return;

  if (adminToken) {
    navActions.innerHTML = `
      <button class="btn btn-outline btn-sm" onclick="openAdminDashboard()" style="border-color:var(--purple);color:var(--purple);font-weight:700;">👑 Quản Trị Hệ Thống</button>
      <button class="btn btn-outline btn-sm" onclick="logoutAll()">Đăng Xuất</button>
      <button class="btn btn-primary btn-sm" onclick="goToDashboard(${schoolId})">🚀 Vào Dashboard</button>
    `;
  } else if (token) {
    navActions.innerHTML = `
      <button class="btn btn-outline btn-sm" onclick="logoutAll()">Đăng Xuất</button>
      <button class="btn btn-primary btn-sm" onclick="goToDashboard(${schoolId})">🚀 Vào Dashboard</button>
    `;
  }
}

window.logoutAll = logoutAll;
window.goToDashboard = goToDashboard;
window.checkAuth = checkAuth;
