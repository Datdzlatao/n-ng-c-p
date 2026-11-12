/**
 * js/services/adminService.js — Platform Super Admin Services
 */
import { apiClient } from './api.js';
import { ADMIN_TOKEN_KEY } from '../config.js';

export async function getAdminStats() {
  const token = localStorage.getItem(ADMIN_TOKEN_KEY);
  if (!token) throw new Error('Chưa đăng nhập quyền Admin');
  return await apiClient('GET', '/api/v1/platform/stats', null, token);
}

export async function getAdminSchools() {
  const token = localStorage.getItem(ADMIN_TOKEN_KEY);
  if (!token) throw new Error('Chưa đăng nhập quyền Admin');
  return await apiClient('GET', '/api/v1/platform/schools', null, token);
}

export async function updateSchoolStatus(schoolId, newStatus) {
  const token = localStorage.getItem(ADMIN_TOKEN_KEY);
  if (!token) throw new Error('Chưa đăng nhập quyền Admin');
  return await apiClient('PUT', `/api/v1/platform/schools/${schoolId}/status`, { status: newStatus }, token);
}
