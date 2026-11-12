/**
 * src/hooks/useRoleAccess.js — RBAC Dynamic Navigation & Permissions
 */
import { useMemo } from 'react';
import { 
  Home, 
  Users, 
  Award, 
  Camera, 
  CheckSquare, 
  Settings, 
  Megaphone, 
  HeartHandshake 
} from 'lucide-react';

export const ROLE_TABS = {
  STUDENT: [
    { id: 'feed', label: 'Bảng Tin Trường', icon: Home },
    { id: 'classes', label: 'Lớp Học & Thảo Luận', icon: Users },
    { id: 'honor', label: 'Bảng Vinh Danh', icon: Award },
    { id: 'attendance_history', label: 'Điểm Danh Của Tôi', icon: CheckSquare },
  ],
  TEACHER: [
    { id: 'feed', label: 'Bảng Tin Trường', icon: Home },
    { id: 'class_attendance', label: 'Điểm Danh Lớp Phụ Trách', icon: CheckSquare },
    { id: 'class_announcements', label: 'Thông Báo Lớp', icon: Megaphone },
    { id: 'moderation', label: 'Duyệt Thảo Luận', icon: HeartHandshake },
  ],
  PARENT: [
    { id: 'feed', label: 'Bản Tin & Sự Kiện', icon: Home },
    { id: 'child_attendance', label: 'Điểm Danh Của Con', icon: Camera },
    { id: 'teacher_notes', label: 'Lời Nhắn GVCN', icon: Megaphone },
  ],
  SCHOOL_ADMIN: [
    { id: 'feed', label: 'Bảng Tin Trường', icon: Home },
    { id: 'members', label: 'Quản Lý Thành Viên', icon: Users },
    { id: 'announcements', label: 'Ghim Thông Báo Toàn Trường', icon: Megaphone },
    { id: 'approvals', label: 'Duyệt Thành Viên Mới', icon: Users, badgeKey: 'pendingRequests' },
    { id: 'ai_cameras', label: 'Hệ Thống AI Camera', icon: Camera },
    { id: 'settings', label: 'Cấu Hình Trường', icon: Settings },
  ],
  INSPECTOR: [
    { id: 'feed', label: 'Bảng Tin Trường', icon: Home },
    { id: 'approvals', label: 'Duyệt Hồ Sơ', icon: Users },
    { id: 'ai_cameras', label: 'Giám Sát AI Camera', icon: Camera },
  ],
};

ROLE_TABS.HEADMASTER = ROLE_TABS.SCHOOL_ADMIN;
ROLE_TABS.ADMIN = ROLE_TABS.SCHOOL_ADMIN;
ROLE_TABS.PLATFORM_ADMIN = ROLE_TABS.SCHOOL_ADMIN;

export function useRoleAccess(userRole = 'STUDENT') {
  const normalizedRole = (userRole || 'STUDENT').toUpperCase();
  const tabs = useMemo(() => {
    return ROLE_TABS[normalizedRole] || ROLE_TABS.STUDENT;
  }, [normalizedRole]);

  const canAccessTab = (tabId) => {
    return tabs.some((tab) => tab.id === tabId);
  };

  return {
    tabs,
    canAccessTab,
  };
}
