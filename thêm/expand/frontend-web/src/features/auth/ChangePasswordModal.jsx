import React, { useState } from 'react';
import { Modal } from '../../components/common/Modal';
import { Button } from '../../components/common/Button';
import { authService } from '../../services/authService';
import { CheckCircle2, ShieldCheck, Eye, EyeOff } from 'lucide-react';

export function ChangePasswordModal({ isOpen, onClose, user }) {
  const [oldPassword, setOldPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showOld, setShowOld] = useState(false);
  const [showNew, setShowNew] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  const handleClose = () => {
    setOldPassword('');
    setNewPassword('');
    setConfirmPassword('');
    setError('');
    setSuccess(false);
    onClose();
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess(false);

    if (!oldPassword) {
      setError('Vui lòng nhập mật khẩu hiện tại.');
      return;
    }
    if (!newPassword || newPassword.length < 6) {
      setError('Mật khẩu mới phải có tối thiểu 6 ký tự.');
      return;
    }
    if (newPassword === oldPassword) {
      setError('Mật khẩu mới không được trùng với mật khẩu cũ.');
      return;
    }
    if (newPassword !== confirmPassword) {
      setError('Xác nhận mật khẩu mới không khớp.');
      return;
    }

    setLoading(true);
    try {
      const res = await authService.changePassword(oldPassword, newPassword);
      if (res.status === 'success' || res.message) {
        setSuccess(true);
        setTimeout(() => {
          handleClose();
        }, 1800);
      } else {
        setError(res.detail || res.message || 'Đổi mật khẩu thất bại.');
      }
    } catch (err) {
      setError(err.message || 'Lỗi khi đổi mật khẩu.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title="Đổi Mật Khẩu"
      subtitle={`Cập nhật mật khẩu cho tài khoản ${user?.fullName || user?.username || ''}`}
    >
      {success ? (
        <div className="py-6 text-center space-y-3">
          <div className="w-12 h-12 rounded-full bg-green-500/20 text-green-400 flex items-center justify-center mx-auto">
            <CheckCircle2 className="w-7 h-7" />
          </div>
          <h4 className="text-base font-bold text-white">Đổi Mật Khẩu Thành Công!</h4>
          <p className="text-xs text-gray-300">
            Mật khẩu mới của bạn đã được cập nhật an toàn vào hệ thống.
          </p>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-xs">
              {error}
            </div>
          )}

          {/* Old Password */}
          <div className="space-y-1">
            <label className="text-xs font-semibold text-gray-300">Mật khẩu hiện tại</label>
            <div className="relative">
              <input
                type={showOld ? 'text' : 'password'}
                value={oldPassword}
                onChange={(e) => setOldPassword(e.target.value)}
                placeholder="Nhập mật khẩu đang dùng..."
                className="w-full bg-[#0f1117] border border-white/10 rounded-xl px-3 py-2 pr-10 text-sm text-white focus:outline-none focus:border-blue-500"
                required
              />
              <button
                type="button"
                onClick={() => setShowOld(!showOld)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-white transition cursor-pointer p-1"
                aria-label="Ẩn hiện mật khẩu cũ"
              >
                {showOld ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>

          {/* New Password */}
          <div className="space-y-1">
            <label className="text-xs font-semibold text-gray-300">Mật khẩu mới</label>
            <div className="relative">
              <input
                type={showNew ? 'text' : 'password'}
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                placeholder="Tối thiểu 6 ký tự..."
                className="w-full bg-[#0f1117] border border-white/10 rounded-xl px-3 py-2 pr-10 text-sm text-white focus:outline-none focus:border-blue-500"
                required
              />
              <button
                type="button"
                onClick={() => setShowNew(!showNew)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-white transition cursor-pointer p-1"
                aria-label="Ẩn hiện mật khẩu mới"
              >
                {showNew ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>

          {/* Confirm New Password */}
          <div className="space-y-1">
            <label className="text-xs font-semibold text-gray-300">Xác nhận mật khẩu mới</label>
            <input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="Nhập lại mật khẩu mới..."
              className="w-full bg-[#0f1117] border border-white/10 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
              required
            />
          </div>

          <div className="pt-2 flex items-center justify-between border-t border-white/10">
            <span className="text-xs text-gray-400 flex items-center gap-1 font-medium">
              <ShieldCheck className="w-3.5 h-3.5 text-blue-400" /> Mã hóa PBKDF2 an toàn
            </span>
            <div className="flex gap-2">
              <Button type="button" variant="ghost" size="sm" onClick={handleClose} className="cursor-pointer transition">
                Hủy
              </Button>
              <Button type="submit" size="sm" loading={loading} className="cursor-pointer transition">
                Lưu Mật Khẩu
              </Button>
            </div>
          </div>
        </form>
      )}
    </Modal>
  );
}
