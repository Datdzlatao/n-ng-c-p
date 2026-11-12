/**
 * js/services/schoolService.js — School Domain API Services
 */
import { apiClient } from './api.js';

export async function getSchools(q = '', province = '') {
  const queryParams = new URLSearchParams();
  if (q) queryParams.append('q', q);
  if (province) queryParams.append('province', province);
  const queryStr = queryParams.toString() ? `?${queryParams.toString()}` : '';
  return await apiClient('GET', `/api/v1/schools${queryStr}`);
}

export async function getSchoolById(id) {
  return await apiClient('GET', `/api/v1/schools/${id}`);
}

export async function createSchool(payload) {
  return await apiClient('POST', '/api/v1/schools', payload);
}

export async function registerSchoolUser(payload) {
  return await apiClient('POST', '/api/v1/auth/register', payload);
}
