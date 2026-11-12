/**
 * src/services/honorService.js — Honor Board & Streaks Service
 */
import { api } from './api';

export const honorService = {
  /** Lấy toàn bộ dữ liệu Bảng Vinh Danh, Chuỗi Lửa và Xếp Hạng */
  getHonorBoard: (schoolId) =>
    api.get(`/api/v1/s/${schoolId}/honor`),
};
