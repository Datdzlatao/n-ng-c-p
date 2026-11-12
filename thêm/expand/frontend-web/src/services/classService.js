/**
 * src/services/classService.js — Class Hub & Discussions Service
 */
import { api } from './api';

export const classService = {
  /** Lấy thông tin lớp học, GVCN, danh sách bạn cùng lớp, điểm nề nếp của học sinh */
  getMyClass: (schoolId) =>
    api.get(`/api/v1/s/${schoolId}/classes/my-class`),

  /** Học sinh nhập mã mời để tham gia lớp */
  joinClass: (schoolId, inviteCode) =>
    api.post(`/api/v1/s/${schoolId}/classes/join`, { invite_code: inviteCode }),

  /** Lấy danh sách thảo luận của lớp */
  getClassPosts: (schoolId, classId, category = '') => {
    let url = `/api/v1/posts?school_id=${schoolId}&class_id=${classId}`;
    if (category) url += `&category=${category}`;
    return api.get(url);
  },

  /** Đăng bài thảo luận mới trong lớp */
  createClassPost: (schoolId, classId, content, category = 'DISCUSSION') => {
    return api.post('/api/v1/posts', {
      school_id: schoolId,
      class_id: classId,
      content,
      category,
    });
  },

  /** Lấy danh sách bình luận của bài viết */
  getComments: (postId) =>
    api.get(`/api/v1/posts/${postId}/comments`),

  /** Thêm bình luận cho bài viết */
  addComment: (postId, content) =>
    api.post(`/api/v1/posts/${postId}/comments`, { content }),

  /** Xóa bình luận */
  deleteComment: (commentId) =>
    api.delete(`/api/v1/posts/comments/${commentId}`),
};
