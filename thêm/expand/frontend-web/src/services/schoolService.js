/**
 * src/services/schoolService.js — School Domain Services
 */
import { api } from './api';

export const schoolService = {
  getSchools: (q = '', province = '') => {
    const params = new URLSearchParams();
    if (q) params.append('q', q);
    if (province) params.append('province', province);
    const query = params.toString() ? `?${params.toString()}` : '';
    return api.get(`/api/v1/schools${query}`);
  },

  getSchoolById: (id) => api.get(`/api/v1/schools/${id}`),

  sendJoinRequest: (schoolId) => api.post(`/api/v1/schools/${schoolId}/join-request`, {}),

  getPendingRequests: (schoolId) => api.get(`/api/v1/schools/${schoolId}/requests`),

  handleRequestAction: (requestId, action, rejectNote = '') =>
    api.post(`/api/v1/schools/requests/${requestId}/action`, { action, rejectNote }),
};
