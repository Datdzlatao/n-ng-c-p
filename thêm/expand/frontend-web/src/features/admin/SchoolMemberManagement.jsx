import React, { useState, useEffect, useRef } from 'react';
import {
  Users, Search, Filter, RefreshCw, Edit3, Key, Lock, Unlock,
  Phone, Mail, Calendar, CheckCircle2, AlertCircle, X, Shield,
  UserCheck, UserX, ChevronRight, Loader2
} from 'lucide-react';
import { userService } from '../../services/userService';
import { Button } from '../../components/common/Button';
import { Modal } from '../../components/common/Modal';

const ROLE_BADGES = {
  HEADMASTER: { label: 'Hiệu Trưởng', color: 'bg-rose-500/15 border-rose-500/30 text-rose-400' },
  SCHOOL_ADMIN: { label: 'Quản Lý', color: 'bg-rose-500/15 border-rose-500/30 text-rose-400' },
  TEACHER: { label: 'Giáo Viên', color: 'bg-violet-500/15 border-violet-500/30 text-violet-400' },
  INSPECTOR: { label: 'Giám Thị', color: 'bg-orange-500/15 border-orange-500/30 text-orange-400' },
  PARENT: { label: 'Phụ Huynh', color: 'bg-emerald-500/15 border-emerald-500/30 text-emerald-400' },
  STUDENT: { label: 'Học Sinh', color: 'bg-sky-500/15 border-sky-500/30 text-sky-400' },
  ADMIN: { label: 'Super Admin', color: 'bg-red-500/15 border-red-500/30 text-red-400' },
  PLATFORM_ADMIN: { label: 'Super Admin', color: 'bg-red-500/15 border-red-500/30 text-red-400' },
};

export function SchoolMemberManagement({ schoolId }) {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedRole, setSelectedRole] = useState('ALL');
  const [selectedStatus, setSelectedStatus] = useState('ALL');
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);

  // Edit Modal State
  const [editingUser, setEditingUser] = useState(null);
  const [editFormData, setEditFormData] = useState({
    full_name: '',
    phone: '',
    email: '',
    dob: '',
    gender: 'Nam',
    role: 'TEACHER',
    status: 'ACTIVE',
  });
  const [editLoading, setEditLoading] = useState(false);
  const [editError, setEditError] = useState('');
  const [editSuccess, setEditSuccess] = useState('');

  // Reset Password Modal State
  const [resetPwUser, setResetPwUser] = useState(null);
  const [newPassword, setNewPassword] = useState('123456');
  const [pwLoading, setPwLoading] = useState(false);
  const [pwError, setPwError] = useState('');
  const [pwSuccess, setPwSuccess] = useState('');

  const fetchUsers = async () => {
    if (!schoolId) return;
    setLoading(true);
    try {
      const params = {
        page,
        limit: 50,
      };
      if (selectedRole !== 'ALL') params.role = selectedRole;
      if (selectedStatus !== 'ALL') params.status = selectedStatus;
      if (searchQuery.trim()) params.q = searchQuery.trim();

      const res = await userService.getSchoolUsers(schoolId, params);
      if (res?.status === 'success') {
        setUsers(res.users || []);
        setTotal(res.total || 0);
      }
    } catch (err) {
      console.error('Lỗi khi tải danh sách thành viên:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const timer = setTimeout(() => {
      fetchUsers();
    }, 250);
    return () => clearTimeout(timer);
  }, [schoolId, selectedRole, selectedStatus, searchQuery, page]);

  // Open Edit Modal
  const handleOpenEdit = (user) => {
    setEditingUser(user);
    setEditFormData({
      full_name: user.full_name || '',
      phone: user.phone || '',
      email: user.email || '',
      dob: user.dob || '',
      gender: user.gender || 'Nam',
      role: user.role || 'TEACHER',
      status: user.status || 'ACTIVE',
    });
    setEditError('');
    setEditSuccess('');
  };

  // Submit Edit Form
  const handleSaveEdit = async (e) => {
    e.preventDefault();
    if (!editingUser) return;
    setEditLoading(true);
    setEditError('');
    setEditSuccess('');

    try {
      const res = await userService.updateSchoolUser(schoolId, editingUser.id, editFormData);
      if (res?.status === 'success') {
        setEditSuccess(res.message || 'Cập nhật thành công!');
        // Update local state
        setUsers((prev) =>
          prev.map((u) => (u.id === editingUser.id ? { ...u, ...res.user } : u))
        );
        setTimeout(() => {
          setEditingUser(null);
          setEditSuccess('');
        }, 1000);
      }
    } catch (err) {
      setEditError(err.message || 'Lỗi cập nhật thông tin thành viên.');
    } finally {
      setEditLoading(false);
    }
  };

  // Toggle User Status
  const handleToggleStatus = async (user) => {
    const nextStatus = user.status === 'ACTIVE' ? 'SUSPENDED' : 'ACTIVE';
    const actionLabel = nextStatus === 'ACTIVE' ? 'mở khóa' : 'tạm khóa';
    if (!window.confirm(`Bạn có chắc muốn ${actionLabel} tài khoản của "${user.full_name}"?`)) {
      return;
    }
    try {
      const res = await userService.toggleSchoolUserStatus(schoolId, user.id, nextStatus);
      if (res?.status === 'success') {
        setUsers((prev) =>
          prev.map((u) => (u.id === user.id ? { ...u, status: nextStatus } : u))
        );
      }
    } catch (err) {
      alert(err.message || 'Lỗi khi thay đổi trạng thái tài khoản.');
    }
  };

  // Reset Password Action
  const handleResetPassword = async (e) => {
    e.preventDefault();
    if (!resetPwUser) return;
    if (newPassword.length < 6) {
      setPwError('Mật khẩu mới phải có tối thiểu 6 ký tự.');
      return;
    }
    setPwLoading(true);
    setPwError('');
    setPwSuccess('');

    try {
      const res = await userService.resetSchoolUserPassword(schoolId, resetPwUser.id, newPassword);
      if (res?.status === 'success') {
        setPwSuccess(res.message || 'Đã đặt lại mật khẩu thành công!');
        setTimeout(() => {
          setResetPwUser(null);
          setPwSuccess('');
        }, 1200);
      }
    } catch (err) {
      setPwError(err.message || 'Lỗi khi đặt lại mật khẩu.');
    } finally {
      setPwLoading(false);
    }
  };

  const roleTabs = [
    { id: 'ALL', label: 'Tất cả' },
    { id: 'TEACHER', label: 'Giáo viên' },
    { id: 'INSPECTOR', label: 'Giám thị / Sao đỏ' },
    { id: 'PARENT', label: 'Phụ huynh' },
    { id: 'STUDENT', label: 'Học sinh' },
    { id: 'HEADMASTER', label: 'BGH / Hiệu trưởng' },
  ];

  return (
    <div className="bg-[#1a1d27] border border-white/10 rounded-2xl p-4 sm:p-6 shadow-xl space-y-5">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-white/10 pb-5">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="w-10 h-10 rounded-xl bg-purple-500/15 border border-purple-500/30 flex items-center justify-center text-purple-400">
              <Users className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-bold text-white text-lg leading-tight">
                Quản Lý Nhân Sự & Thành Viên Trường Học
              </h3>
              <p className="text-xs text-gray-400 mt-0.5">
                Hiệu trưởng chủ động cập nhật số điện thoại, email và hồ sơ các vai trò cấp dưới (Giáo viên, Giám thị, Phụ huynh, Học sinh)
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={fetchUsers} disabled={loading} className="gap-1.5">
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Tải Lại</span>
          </Button>
          <span className="text-xs bg-purple-500/20 text-purple-300 font-bold px-3 py-1.5 rounded-full border border-purple-500/30">
            {total} thành viên
          </span>
        </div>
      </div>

      {/* Role Filter Tabs */}
      <div className="flex gap-1.5 overflow-x-auto pb-1 scrollbar-none">
        {roleTabs.map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => {
              setSelectedRole(tab.id);
              setPage(1);
            }}
            className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold whitespace-nowrap transition cursor-pointer ${
              selectedRole === tab.id
                ? 'bg-purple-600 text-white shadow-md shadow-purple-600/20'
                : 'bg-white/5 hover:bg-white/10 text-gray-400 hover:text-white'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Search & Status Filter */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400 w-4 h-4 pointer-events-none" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              setPage(1);
            }}
            placeholder="Tìm theo họ tên, số điện thoại, email, mã định danh..."
            className="w-full bg-[#0f1117] border border-white/10 rounded-xl pl-10 pr-4 py-2.5 text-xs sm:text-sm text-white placeholder-gray-500 focus:outline-none focus:border-purple-500 transition"
          />
        </div>

        <select
          value={selectedStatus}
          onChange={(e) => {
            setSelectedStatus(e.target.value);
            setPage(1);
          }}
          className="bg-[#0f1117] border border-white/10 rounded-xl px-3 py-2.5 text-xs text-gray-300 focus:outline-none focus:border-purple-500"
        >
          <option value="ALL">Tất cả trạng thái</option>
          <option value="ACTIVE">Đang hoạt động</option>
          <option value="SUSPENDED">Tạm khóa</option>
          <option value="PENDING_APPROVAL">Chờ duyệt</option>
        </select>
      </div>

      {/* Members Table */}
      <div className="overflow-x-auto rounded-xl border border-white/10 bg-[#12141d]">
        <table className="w-full text-left border-collapse text-xs">
          <thead>
            <tr className="border-b border-white/10 bg-white/[0.02] text-gray-400 uppercase tracking-wider text-[10px]">
              <th className="p-3.5">Thành Viên</th>
              <th className="p-3.5">Vai Trò</th>
              <th className="p-3.5">Số Điện Thoại</th>
              <th className="p-3.5">Email</th>
              <th className="p-3.5">Trạng Thái</th>
              <th className="p-3.5 text-right">Thao Tác</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5">
            {loading ? (
              <tr>
                <td colSpan={6} className="py-12 text-center text-gray-400">
                  <Loader2 className="w-6 h-6 animate-spin mx-auto text-purple-400 mb-2" />
                  <span>Đang tải danh sách thành viên...</span>
                </td>
              </tr>
            ) : users.length === 0 ? (
              <tr>
                <td colSpan={6} className="py-12 text-center text-gray-400">
                  <Users className="w-8 h-8 mx-auto text-gray-600 mb-2" />
                  <span>Không tìm thấy thành viên nào phù hợp.</span>
                </td>
              </tr>
            ) : (
              users.map((u) => {
                const roleBadge = ROLE_BADGES[u.role] || ROLE_BADGES.STUDENT;
                return (
                  <tr key={u.id} className="hover:bg-white/[0.02] transition">
                    {/* User Info */}
                    <td className="p-3.5">
                      <div className="flex items-center gap-3">
                        <div className="w-9 h-9 rounded-xl bg-purple-500/20 text-purple-300 font-bold flex items-center justify-center shrink-0">
                          {u.full_name ? u.full_name[0].toUpperCase() : 'U'}
                        </div>
                        <div className="min-w-0">
                          <div className="font-semibold text-white truncate flex items-center gap-1.5">
                            <span>{u.full_name}</span>
                            {u.verified_status === 'VERIFIED' && (
                              <span className="text-[10px] text-blue-400 bg-blue-500/15 px-1 rounded border border-blue-500/30">
                                ✓
                              </span>
                            )}
                          </div>
                          <div className="flex items-center gap-2 mt-0.5">
                            <span className="text-[11px] font-mono text-gray-400">@{u.username}</span>
                            <span className="text-[10px] text-purple-300/80 font-mono bg-purple-500/10 px-1.5 py-0.2 rounded border border-purple-500/20">
                              #{u.member_code}
                            </span>
                          </div>
                        </div>
                      </div>
                    </td>

                    {/* Role */}
                    <td className="p-3.5 whitespace-nowrap">
                      <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold border uppercase ${roleBadge.color}`}>
                        {roleBadge.label}
                      </span>
                    </td>

                    {/* Phone */}
                    <td className="p-3.5 whitespace-nowrap">
                      {u.phone ? (
                        <span className="font-mono text-gray-200 flex items-center gap-1.5">
                          <Phone className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                          <span>{u.phone}</span>
                        </span>
                      ) : (
                        <span className="text-gray-500 italic text-[11px]">Chưa cập nhật</span>
                      )}
                    </td>

                    {/* Email */}
                    <td className="p-3.5">
                      {u.email ? (
                        <span className="text-gray-300 truncate max-w-[160px] inline-flex items-center gap-1.5" title={u.email}>
                          <Mail className="w-3.5 h-3.5 text-sky-400 shrink-0" />
                          <span className="truncate">{u.email}</span>
                        </span>
                      ) : (
                        <span className="text-gray-500 italic text-[11px]">Chưa cập nhật</span>
                      )}
                    </td>

                    {/* Status */}
                    <td className="p-3.5 whitespace-nowrap">
                      {u.status === 'ACTIVE' ? (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                          Hoạt động
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-red-500/15 text-red-400 border border-red-500/30">
                          <span className="w-1.5 h-1.5 rounded-full bg-red-400" />
                          Tạm khóa
                        </span>
                      )}
                    </td>

                    {/* Actions */}
                    <td className="p-3.5 text-right whitespace-nowrap">
                      <div className="inline-flex items-center gap-1.5 justify-end">
                        {u.can_edit ? (
                          <>
                            <button
                              type="button"
                              onClick={() => handleOpenEdit(u)}
                              title="Chỉnh sửa thông tin thành viên"
                              className="p-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-gray-300 hover:text-white transition cursor-pointer"
                            >
                              <Edit3 className="w-4 h-4" />
                            </button>

                            <button
                              type="button"
                              onClick={() => {
                                setResetPwUser(u);
                                setNewPassword('123456');
                                setPwError('');
                                setPwSuccess('');
                              }}
                              title="Đặt lại mật khẩu"
                              className="p-1.5 rounded-lg bg-amber-500/10 hover:bg-amber-500/20 text-amber-400 transition cursor-pointer"
                            >
                              <Key className="w-4 h-4" />
                            </button>

                            <button
                              type="button"
                              onClick={() => handleToggleStatus(u)}
                              title={u.status === 'ACTIVE' ? 'Khóa tài khoản' : 'Mở khóa tài khoản'}
                              className={`p-1.5 rounded-lg transition cursor-pointer ${
                                u.status === 'ACTIVE'
                                  ? 'bg-red-500/10 hover:bg-red-500/20 text-red-400'
                                  : 'bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400'
                              }`}
                            >
                              {u.status === 'ACTIVE' ? <Lock className="w-4 h-4" /> : <Unlock className="w-4 h-4" />}
                            </button>
                          </>
                        ) : (
                          <span className="text-[11px] text-gray-500 italic px-2 py-1 rounded bg-white/[0.02]">
                            Tài khoản BGH
                          </span>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Edit User Modal */}
      {editingUser && (
        <Modal
          isOpen={!!editingUser}
          onClose={() => setEditingUser(null)}
          title={`Chỉnh Sửa Thông Tin — ${editingUser.full_name}`}
          subtitle={`Hiệu trưởng chủ động cập nhật số điện thoại, email, vai trò cấp dưới cho tài khoản @${editingUser.username}`}
          maxWidth="max-w-lg"
        >
          <form onSubmit={handleSaveEdit} className="space-y-4">
            {editSuccess && (
              <div className="p-3 rounded-xl bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 text-xs flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                <span>{editSuccess}</span>
              </div>
            )}

            {editError && (
              <div className="p-3 rounded-xl bg-rose-500/15 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
                <span>{editError}</span>
              </div>
            )}

            <div className="space-y-1">
              <label className="block text-xs font-semibold text-gray-200">
                Họ và Tên đầy đủ <span className="text-rose-400">*</span>
              </label>
              <input
                type="text"
                required
                value={editFormData.full_name}
                onChange={(e) => setEditFormData({ ...editFormData, full_name: e.target.value })}
                className="w-full bg-[#0f1117] border border-white/10 rounded-xl px-3.5 py-2.5 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-purple-500"
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div className="space-y-1">
                <label className="block text-xs font-semibold text-gray-200 flex items-center gap-1.5">
                  <Phone className="w-3.5 h-3.5 text-emerald-400" />
                  <span>Số điện thoại liên hệ</span>
                </label>
                <input
                  type="tel"
                  placeholder="0912345678"
                  value={editFormData.phone}
                  onChange={(e) => setEditFormData({ ...editFormData, phone: e.target.value })}
                  className="w-full bg-[#0f1117] border border-white/10 rounded-xl px-3.5 py-2.5 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-purple-500 font-mono"
                />
              </div>

              <div className="space-y-1">
                <label className="block text-xs font-semibold text-gray-200 flex items-center gap-1.5">
                  <Mail className="w-3.5 h-3.5 text-sky-400" />
                  <span>Email liên hệ</span>
                </label>
                <input
                  type="email"
                  placeholder="name@school.edu.vn"
                  value={editFormData.email}
                  onChange={(e) => setEditFormData({ ...editFormData, email: e.target.value })}
                  className="w-full bg-[#0f1117] border border-white/10 rounded-xl px-3.5 py-2.5 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-purple-500"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div className="space-y-1">
                <label className="block text-xs font-semibold text-gray-200">Ngày sinh</label>
                <input
                  type="date"
                  value={editFormData.dob}
                  onChange={(e) => setEditFormData({ ...editFormData, dob: e.target.value })}
                  className="w-full bg-[#0f1117] border border-white/10 rounded-xl px-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-purple-500"
                />
              </div>

              <div className="space-y-1">
                <label className="block text-xs font-semibold text-gray-200">Giới tính</label>
                <select
                  value={editFormData.gender}
                  onChange={(e) => setEditFormData({ ...editFormData, gender: e.target.value })}
                  className="w-full bg-[#0f1117] border border-white/10 rounded-xl px-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-purple-500"
                >
                  <option value="Nam">Nam</option>
                  <option value="Nữ">Nữ</option>
                  <option value="Khác">Khác</option>
                </select>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div className="space-y-1">
                <label className="block text-xs font-semibold text-gray-200">Vai trò cấp dưới</label>
                <select
                  value={editFormData.role}
                  onChange={(e) => setEditFormData({ ...editFormData, role: e.target.value })}
                  className="w-full bg-[#0f1117] border border-white/10 rounded-xl px-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-purple-500"
                >
                  <option value="TEACHER">Giáo Viên (TEACHER)</option>
                  <option value="INSPECTOR">Giám Thị / Sao Đỏ (INSPECTOR)</option>
                  <option value="PARENT">Phụ Huynh (PARENT)</option>
                  <option value="STUDENT">Học Sinh (STUDENT)</option>
                </select>
              </div>

              <div className="space-y-1">
                <label className="block text-xs font-semibold text-gray-200">Trạng thái tài khoản</label>
                <select
                  value={editFormData.status}
                  onChange={(e) => setEditFormData({ ...editFormData, status: e.target.value })}
                  className="w-full bg-[#0f1117] border border-white/10 rounded-xl px-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-purple-500"
                >
                  <option value="ACTIVE">Hoạt động bình thường</option>
                  <option value="SUSPENDED">Tạm khóa tài khoản</option>
                  <option value="PENDING_APPROVAL">Chờ duyệt</option>
                </select>
              </div>
            </div>

            <div className="pt-3 flex justify-end gap-3 border-t border-white/10">
              <Button type="button" variant="ghost" onClick={() => setEditingUser(null)} disabled={editLoading}>
                Hủy
              </Button>
              <Button type="submit" loading={editLoading} className="bg-purple-600 hover:bg-purple-500 text-white">
                Lưu Thay Đổi
              </Button>
            </div>
          </form>
        </Modal>
      )}

      {/* Reset Password Modal */}
      {resetPwUser && (
        <Modal
          isOpen={!!resetPwUser}
          onClose={() => setResetPwUser(null)}
          title={`Đặt Lại Mật Khẩu — ${resetPwUser.full_name}`}
          subtitle={`Hiệu trưởng cấp lại mật khẩu cho tài khoản @${resetPwUser.username}`}
          maxWidth="max-w-md"
        >
          <form onSubmit={handleResetPassword} className="space-y-4">
            {pwSuccess && (
              <div className="p-3 rounded-xl bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 text-xs flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                <span>{pwSuccess}</span>
              </div>
            )}

            {pwError && (
              <div className="p-3 rounded-xl bg-rose-500/15 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
                <span>{pwError}</span>
              </div>
            )}

            <div className="space-y-1.5">
              <label className="block text-xs font-semibold text-gray-200">
                Mật khẩu mới (tối thiểu 6 ký tự)
              </label>
              <div className="flex gap-2">
                <input
                  type="text"
                  required
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  className="flex-1 bg-[#0f1117] border border-white/10 rounded-xl px-3.5 py-2.5 text-sm text-white font-mono focus:outline-none focus:border-purple-500"
                />
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setNewPassword('123456')}
                  title="Đặt mặc định là 123456"
                >
                  123456
                </Button>
              </div>
              <p className="text-[11px] text-gray-400">
                Tất cả các phiên đăng nhập cũ của tài khoản này sẽ tự động bị thu hồi.
              </p>
            </div>

            <div className="pt-3 flex justify-end gap-3 border-t border-white/10">
              <Button type="button" variant="ghost" onClick={() => setResetPwUser(null)} disabled={pwLoading}>
                Hủy
              </Button>
              <Button type="submit" loading={pwLoading} className="bg-amber-600 hover:bg-amber-500 text-white">
                Cập Nhật Mật Khẩu
              </Button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  );
}
