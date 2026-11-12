/**
 * src/services/notifService.js — Notification API & WebSocket Service
 */
import { api } from './api';

export const notifService = {
  getNotifications: () => api.get('/api/v1/notifications'),

  markAsRead: (notificationId) =>
    api.put(`/api/v1/notifications/${notificationId}/read`, {}),

  markAllAsRead: () =>
    api.put('/api/v1/notifications/read-all', {}),
};
