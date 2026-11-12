/**
 * src/services/attendanceService.js — Attendance & Leave API
 */
import { api } from './api';

export const attendanceService = {
  /** Lịch sử điểm danh của học sinh (student tự xem hoặc phụ huynh xem) */
  getStudentHistory: (schoolId, studentId, limit = 30) =>
    api.get(`/api/v1/s/${schoolId}/attendance/student/${studentId}?limit=${limit}`),

  /** Tổng kết hôm nay (cho Teacher/Inspector) */
  getToday: (schoolId) =>
    api.get(`/api/v1/s/${schoolId}/attendance/today`),
};

export const leaveService = {
  /** Nộp đơn xin nghỉ */
  create: (schoolId, payload) =>
    api.post(`/api/v1/s/${schoolId}/leaves`, payload),

  /** Danh sách đơn xin nghỉ (cho giáo viên/HT) */
  list: (schoolId) =>
    api.get(`/api/v1/s/${schoolId}/leaves`),

  /** Duyệt/từ chối đơn */
  action: (schoolId, leaveId, action, note = '') =>
    api.put(`/api/v1/s/${schoolId}/leaves/${leaveId}/approve`, { action, note }),
};

export const studentService = {
  /** Lấy thông tin học sinh theo user_id (học sinh tự xem) */
  getMyProfile: (schoolId) =>
    api.get(`/api/v1/s/${schoolId}/students/me`),

  /** Lấy danh sách con của phụ huynh */
  getMyChildren: (schoolId) =>
    api.get(`/api/v1/s/${schoolId}/students/my-children`),
};
