/**
 * src/services/postService.js — School Feed & Announcements API Service
 */
import { api } from './api';

export const postService = {
  getPosts: (schoolId) => {
    const query = schoolId ? `?school_id=${schoolId}` : '';
    return api.get(`/api/v1/posts${query}`);
  },

  createPost: (content, schoolId, options = {}) => {
    const text = typeof content === 'object' && content !== null ? (content.content || '') : String(content || '');
    const isUrgent = options?.urgent || (typeof content === 'object' && content?.isUrgent) || false;
    return api.post('/api/v1/posts', { content: text, school_id: schoolId, is_urgent: !!isUrgent });
  },

  toggleLike: (postId) =>
    api.post(`/api/v1/posts/${postId}/like`, {}),

  deletePost: (postId) =>
    api.delete(`/api/v1/posts/${postId}`),
};
