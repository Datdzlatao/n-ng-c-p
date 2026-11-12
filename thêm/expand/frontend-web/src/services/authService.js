/**
 * src/services/authService.js — Auth & Member Code Services
 */
import { api } from './api';

export const authService = {
  login: (school_id, username_or_phone, password) =>
    api.post('/api/v1/auth/login', { school_id, username_or_phone, password }),

  register: (payload) =>
    api.post('/api/v1/auth/register', payload),

  getProfile: () => api.get('/api/v1/auth/me'),

  changePassword: (oldPassword, newPassword) =>
    api.post('/api/v1/auth/change-password', {
      old_password: oldPassword,
      new_password: newPassword,
    }),

  adminResetPassword: (userId, newPassword = '123456') =>
    api.post('/api/v1/auth/admin-reset-password', {
      user_id: userId,
      new_password: newPassword,
    }),

  logout: () => {
    localStorage.removeItem('stem_auth_token');
    localStorage.removeItem('stem_refresh_token');
    localStorage.removeItem('stem_school_id');
    window.location.href = '/';
  },
};

