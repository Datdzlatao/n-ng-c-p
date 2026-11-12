import React, { useState, useEffect, useRef } from 'react';
import { Modal } from '../../components/common/Modal';
import { Button } from '../../components/common/Button';
import { authService } from '../../services/authService';
import { Eye, EyeOff, AlertCircle, CheckCircle2, Lock, User } from 'lucide-react';

export function LoginModal({ isOpen, onClose, onLoginSuccess, onSwitchToRegister, onNeedJoinSchool }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState({});
  const [generalError, setGeneralError] = useState('');
  const [successToast, setSuccessToast] = useState('');

  const usernameInputRef = useRef(null);

  // 1. Tự động focus vào ô đầu tiên khi mở modal
  useEffect(() => {
    if (isOpen) {
      setUsername('');
      setPassword('');
      setShowPassword(false);
      setErrors({});
      setGeneralError('');
      setSuccessToast('');
      const timer = setTimeout(() => {
        usernameInputRef.current?.focus();
      }, 80);
      return () => clearTimeout(timer);
    }
  }, [isOpen]);

  const validate = () => {
    const newErrors = {};
    if (!username.trim()) {
      newErrors.username = 'Vui lòng nhập tên đăng nhập hoặc số điện thoại.';
    }
    if (!password) {
      newErrors.password = 'Vui lòng nhập mật khẩu tài khoản.';
    }
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setGeneralError('');
    if (!validate()) return;

    setLoading(true);
    try {
      const res = await authService.login(null, username.trim(), password);
      if (res.status === 'success') {
        localStorage.setItem('stem_auth_token', res.access_token);
        if (res.refresh_token) {
          localStorage.setItem('stem_refresh_token', res.refresh_token);
        }

        // 3. Thông báo Toast thành công xanh lá trước khi đóng modal
        setSuccessToast('Đăng nhập thành công! Đang chuyển hướng...');

        setTimeout(() => {
          const userSchoolId = res.user?.school_id;
          onClose();
          if (onLoginSuccess) onLoginSuccess(res.user);

          if (userSchoolId) {
            localStorage.setItem('stem_school_id', userSchoolId);
            if (['HEADMASTER', 'ADMIN', 'PLATFORM_ADMIN', 'TEACHER', 'INSPECTOR'].includes(res.user?.role)) {
              window.location.href = `/app/index.html?school_id=${userSchoolId}`;
            } else {
              window.location.reload();
            }
          } else {
            localStorage.removeItem('stem_school_id');
            if (onNeedJoinSchool) {
              onNeedJoinSchool(res.user);
            } else {
              window.location.reload();
            }
          }
        }, 800);
      } else {
        setGeneralError(res.detail || res.message || 'Tên đăng nhập hoặc mật khẩu không chính xác.');
      }
    } catch (err) {
      setGeneralError(err.message || 'Lỗi kết nối đến máy chủ. Vui lòng thử lại sau.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Đăng Nhập" subtitle="Đăng nhập tài khoản cá nhân của bạn">
      <form onSubmit={handleSubmit} className="space-y-4" noValidate>
        {/* Toast thành công */}
        {successToast && (
          <div className="p-3.5 rounded-xl bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 text-xs flex items-center gap-2.5 animate-fadeIn">
            <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-400" />
            <span className="font-semibold">{successToast}</span>
          </div>
        )}

        {/* Lỗi tổng quát từ máy chủ */}
        {generalError && (
          <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
            <span>{generalError}</span>
          </div>
        )}

        {/* 1. Trường Tên đăng nhập */}
        <div className="space-y-1">
          <label htmlFor="login-username" className="block text-xs font-semibold text-gray-200">
            Tên đăng nhập / Số điện thoại <span className="text-rose-400">*</span>
          </label>
          <div className="relative">
            <input
              id="login-username"
              ref={usernameInputRef}
              type="text"
              value={username}
              onChange={(e) => {
                setUsername(e.target.value);
                if (errors.username) setErrors(prev => ({ ...prev, username: '' }));
              }}
              placeholder="Ví dụ: nguyenvana hoặc 0901xxxxxx"
              className={`w-full bg-[#0f1117] border rounded-xl px-3.5 py-2.5 text-sm text-white placeholder-gray-500 transition focus:outline-none ${
                errors.username
                  ? 'border-rose-500/60 bg-rose-500/5 focus:border-rose-500'
                  : 'border-white/10 focus:border-blue-500 focus:bg-white/[0.02]'
              }`}
              disabled={loading || !!successToast}
              aria-invalid={!!errors.username}
              aria-describedby={errors.username ? 'username-error' : undefined}
            />
          </div>
          {/* Báo lỗi tức thời bên dưới */}
          {errors.username && (
            <p id="username-error" className="text-rose-400 text-xs mt-1 flex items-center gap-1.5 animate-fadeIn">
              <AlertCircle className="w-3.5 h-3.5 shrink-0" />
              <span>{errors.username}</span>
            </p>
          )}
        </div>

        {/* 2. Trường Mật khẩu có nút mắt ẩn/hiện */}
        <div className="space-y-1">
          <div className="flex items-center justify-between">
            <label htmlFor="login-password" className="block text-xs font-semibold text-gray-200">
              Mật khẩu <span className="text-rose-400">*</span>
            </label>
          </div>
          <div className="relative">
            <input
              id="login-password"
              type={showPassword ? 'text' : 'password'}
              value={password}
              onChange={(e) => {
                setPassword(e.target.value);
                if (errors.password) setErrors(prev => ({ ...prev, password: '' }));
              }}
              placeholder="Nhập mật khẩu tài khoản"
              className={`w-full bg-[#0f1117] border rounded-xl pl-3.5 pr-11 py-2.5 text-sm text-white placeholder-gray-500 transition focus:outline-none ${
                errors.password
                  ? 'border-rose-500/60 bg-rose-500/5 focus:border-rose-500'
                  : 'border-white/10 focus:border-blue-500 focus:bg-white/[0.02]'
              }`}
              disabled={loading || !!successToast}
              aria-invalid={!!errors.password}
              aria-describedby={errors.password ? 'password-error' : undefined}
            />
            {/* Nút ẩn / hiện mật khẩu */}
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-white p-1 rounded-md transition focus:outline-none focus:ring-1 focus:ring-blue-500"
              aria-label={showPassword ? 'Ẩn mật khẩu' : 'Hiện mật khẩu'}
              tabIndex={0}
            >
              {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            </button>
          </div>
          {/* Báo lỗi tức thời bên dưới */}
          {errors.password && (
            <p id="password-error" className="text-rose-400 text-xs mt-1 flex items-center gap-1.5 animate-fadeIn">
              <AlertCircle className="w-3.5 h-3.5 shrink-0" />
              <span>{errors.password}</span>
            </p>
          )}
        </div>

        {/* Nút thao tác với trạng thái xoay vòng Spinner */}
        <div className="pt-2 flex justify-end gap-3">
          <Button type="button" variant="ghost" onClick={onClose} disabled={loading || !!successToast}>
            Hủy
          </Button>
          <Button type="submit" loading={loading} disabled={loading || !!successToast}>
            {loading ? 'Đang đăng nhập...' : 'Đăng Nhập →'}
          </Button>
        </div>

        <p className="text-center text-xs text-gray-400 pt-2 border-t border-white/5">
          Chưa có tài khoản?{' '}
          <button
            type="button"
            onClick={onSwitchToRegister}
            className="text-blue-400 font-semibold hover:underline"
            disabled={loading || !!successToast}
          >
            Đăng ký ngay →
          </button>
        </p>
      </form>
    </Modal>
  );
}
