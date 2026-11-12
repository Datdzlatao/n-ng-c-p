/**
 * src/services/userService.js — Quản lý Nhân sự & Phân quyền Trường Học
 */
import { api } from './api';

export const userService = {
  /** Lấy danh sách thành viên trong trường */
  getSchoolUsers: (schoolId, params = {}) => {
    const searchParams = new URLSearchParams();
    if (params.role) searchParams.append('role', params.role);
    if (params.status) searchParams.append('status', params.status);
    if (params.q) searchParams.append('q', params.q);
    if (params.subordinate_only) searchParams.append('subordinate_only', 'true');
    if (params.page) searchParams.append('page', params.page);
    if (params.limit) searchParams.append('limit', params.limit);

    const qs = searchParams.toString() ? `?${searchParams.toString()}` : '';
    return api.get(`/api/v1/s/${schoolId}/users${qs}`);
  },

  /** Lấy chi tiết hồ sơ thành viên */
  getSchoolUserDetail: (schoolId, userId) =>
    api.get(`/api/v1/s/${schoolId}/users/${userId}`),

  /** Hiệu trưởng cập nhật chủ động thông tin thành viên cấp dưới */
  updateSchoolUser: (schoolId, userId, payload) =>
    api.put(`/api/v1/s/${schoolId}/users/${userId}`, payload),

  /** Hiệu trưởng đặt lại mật khẩu cho thành viên cấp dưới */
  resetSchoolUserPassword: (schoolId, userId, newPassword) =>
    api.post(`/api/v1/s/${schoolId}/users/${userId}/reset-password`, { new_password: newPassword }),

  /** Khóa hoặc mở khóa trạng thái hoạt động của thành viên cấp dưới */
  toggleSchoolUserStatus: (schoolId, userId, status = null) =>
    api.post(`/api/v1/s/${schoolId}/users/${userId}/toggle-status`, { status }),
};
