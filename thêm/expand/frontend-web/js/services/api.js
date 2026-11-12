/**
 * js/services/api.js — Central HTTP Client
 */
import { STEM_CONFIG } from '../config.js';

/**
 * Execute HTTP request to backend
 * @param {'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH'} method 
 * @param {string} path 
 * @param {object | null} body 
 * @param {string | null} token 
 * @returns {Promise<any>}
 */
export async function apiClient(method, path, body = null, token = null) {
  const url = `${STEM_CONFIG.API_BASE}${path}`;
  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };

  const options = {
    method,
    headers,
  };

  if (body) {
    options.body = JSON.stringify(body);
  }

  const res = await fetch(url, options);
  const data = await res.json().catch(() => null);

  if (!res.ok) {
    const error = new Error(data?.detail || data?.message || `HTTP ${res.status}`);
    error.status = res.status;
    error.data = data;
    throw error;
  }

  return data;
}

window.apiClient = apiClient;
