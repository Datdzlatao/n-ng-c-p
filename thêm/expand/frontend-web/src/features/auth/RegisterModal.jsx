import React, { useState, useEffect, useRef } from 'react';
import { Modal } from '../../components/common/Modal';
import { Button } from '../../components/common/Button';
import { authService } from '../../services/authService';
import { User, Lock, Phone, GraduationCap, Users, ShieldAlert, Eye, EyeOff, AlertCircle, CheckCircle2 } from 'lucide-react';

export function RegisterModal({ isOpen, onClose, onRegisterSuccess, onSwitchToLogin }) {
  const [fullName, setFullName] = useState('');
  const [username, setUsername] = useState('');
  const [phone, setPhone] = useState('');
  const [role, setRole] = useState('STUDENT');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  
  const [errors, setErrors] = useState({});
  const [generalError, setGeneralError] = useState('');
  const [successToast, setSuccessToast] = useState('');

  const fullNameInputRef = useRef(null);

  const roles = [
    { id: 'STUDENT', label: 'Học Sinh', icon: GraduationCap, desc: 'Điểm danh AI, nộp đơn xin phép' },
    { id: 'TEACHER', label: 'Giáo Viên', icon: Users, desc: 'Quản lý điểm danh lớp, phê duyệt' },
    { id: 'PARENT', label: 'Phụ Huynh', icon: User, desc: 'Theo dõi con em, nhận thông báo' },
    { id: 'INSPECTOR', label: 'Giám Thị', icon: ShieldAlert, desc: 'Giám sát trật tự, đối chiếu camera' },
  ];

  // 1. Tự động focus vào ô đầu tiên khi mở modal
  useEffect(() => {
    if (isOpen) {
      setFullName('');
      setUsername('');
      setPhone('');
      setRole('STUDENT');
      setPassword('');
      setConfirmPassword('');
      setShowPassword(false);
      setShowConfirmPassword(false);
      setErrors({});
      setGeneralError('');
      setSuccessToast('');

      const timer = setTimeout(() => {
        fullNameInputRef.current?.focus();
      }, 80);
      return () => clearTimeout(timer);
    }
  }, [isOpen]);

  const validate = () => {
    const newErrors = {};
    if (!fullName.trim()) {
      newErrors.fullName = 'Vui lòng nhập họ và tên đầy đủ.';
    } else if (fullName.trim().split(/\s+/).length < 2) {
      newErrors.fullName = 'Vui lòng nhập cả họ và tên (ít nhất 2 từ).';
    }

    if (!username.trim()) {
      newErrors.username = 'Vui lòng nhập tên đăng nhập.';
    } else if (!/^[a-zA-Z0-9._]+$/.test(username.trim())) {
      newErrors.username = 'Tên đăng nhập chỉ gồm chữ không dấu, số, dấu chấm hoặc gạch dưới.';
    } else if (username.trim().length < 3) {
      newErrors.username = 'Tên đăng nhập phải có ít nhất 3 ký tự.';
    }

    if (phone.trim() && !/^[0-9+]{9,12}$/.test(phone.trim())) {
      newErrors.phone = 'Số điện thoại không hợp lệ (từ 9-12 chữ số).';
    }

    if (!password) {
      newErrors.password = 'Vui lòng nhập mật khẩu.';
    } else if (password.length < 6) {
      newErrors.password = 'Mật khẩu phải có ít nhất 6 ký tự.';
    }

    if (!confirmPassword) {
      newErrors.confirmPassword = 'Vui lòng nhập lại mật khẩu để xác nhận.';
    } else if (password !== confirmPassword) {
      newErrors.confirmPassword = 'Mật khẩu xác nhận không khớp.';
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
      const payload = {
        full_name: fullName.trim(),
        username: username.trim().toLowerCase(),
        phone: phone.trim() || null,
        role: role,
        password: password,
      };

      const res = await authService.register(payload);
      if (res.status === 'success') {
        if (res.access_token) {
          localStorage.setItem('stem_auth_token', res.access_token);
        }

        // 3. Thông báo Toast thành công xanh lá trước khi đóng modal
        setSuccessToast('Đăng ký tài khoản thành công! Đang thiết lập phiên làm việc...');

        setTimeout(() => {
          onClose();
          if (onRegisterSuccess) {
            onRegisterSuccess(res.user);
          }
        }, 900);
      } else {
        setGeneralError(res.detail || res.message || 'Đăng ký không thành công. Tên đăng nhập có thể đã tồn tại.');
      }
    } catch (err) {
      setGeneralError(err.message || 'Lỗi máy chủ khi đăng ký tài khoản.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Đăng Ký Tài Khoản"
      subtitle="Tạo tài khoản cá nhân để bắt đầu sử dụng hệ thống EduSAMS"
      maxWidth="max-w-lg"
    >
      <form onSubmit={handleSubmit} className="space-y-4" noValidate>
        {/* Toast thành công */}
        {successToast && (
          <div className="p-3.5 rounded-xl bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 text-xs flex items-center gap-2.5 animate-fadeIn">
            <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-400" />
            <span className="font-semibold">{successToast}</span>
          </div>
        )}

        {/* Lỗi tổng quát */}
        {generalError && (
          <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center gap-2 animate-fadeIn">
            <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
            <span>{generalError}</span>
          </div>
        )}

        {/* 1. Họ và Tên */}
        <div className="space-y-1">
          <label htmlFor="reg-fullname" className="block text-xs font-semibold text-gray-200">
            Họ và Tên đầy đủ <span className="text-rose-400">*</span>
          </label>
          <input
            id="reg-fullname"
            ref={fullNameInputRef}
            type="text"
            value={fullName}
            onChange={(e) => {
              setFullName(e.target.value);
              if (errors.fullName) setErrors(prev => ({ ...prev, fullName: '' }));
            }}
            placeholder="Ví dụ: Nguyễn Văn An"
            className={`w-full bg-[#0f1117] border rounded-xl px-3.5 py-2.5 text-sm text-white placeholder-gray-500 transition focus:outline-none ${
              errors.fullName
                ? 'border-rose-500/60 bg-rose-500/5 focus:border-rose-500'
                : 'border-white/10 focus:border-blue-500 focus:bg-white/[0.02]'
            }`}
            disabled={loading || !!successToast}
            aria-invalid={!!errors.fullName}
            aria-describedby={errors.fullName ? 'fullname-error' : undefined}
          />
          {errors.fullName && (
            <p id="fullname-error" className="text-rose-400 text-xs mt-1 flex items-center gap-1.5 animate-fadeIn">
              <AlertCircle className="w-3.5 h-3.5 shrink-0" />
              <span>{errors.fullName}</span>
            </p>
          )}
        </div>

        {/* 2. Tên đăng nhập & Số điện thoại */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div className="space-y-1">
            <label htmlFor="reg-username" className="block text-xs font-semibold text-gray-200">
              Tên đăng nhập <span className="text-rose-400">*</span>
            </label>
            <input
              id="reg-username"
              type="text"
              value={username}
              onChange={(e) => {
                setUsername(e.target.value);
                if (errors.username) setErrors(prev => ({ ...prev, username: '' }));
              }}
              placeholder="nguyenvanan"
              className={`w-full bg-[#0f1117] border rounded-xl px-3.5 py-2.5 text-sm text-white placeholder-gray-500 transition focus:outline-none ${
                errors.username
                  ? 'border-rose-500/60 bg-rose-500/5 focus:border-rose-500'
                  : 'border-white/10 focus:border-blue-500 focus:bg-white/[0.02]'
              }`}
              disabled={loading || !!successToast}
              aria-invalid={!!errors.username}
              aria-describedby={errors.username ? 'reg-username-error' : undefined}
            />
            {errors.username && (
              <p id="reg-username-error" className="text-rose-400 text-xs mt-1 flex items-center gap-1.5 animate-fadeIn">
                <AlertCircle className="w-3.5 h-3.5 shrink-0" />
                <span>{errors.username}</span>
              </p>
            )}
          </div>

          <div className="space-y-1">
            <label htmlFor="reg-phone" className="block text-xs font-semibold text-gray-200">
              Số điện thoại liên hệ
            </label>
            <input
              id="reg-phone"
              type="tel"
              value={phone}
              onChange={(e) => {
                setPhone(e.target.value);
                if (errors.phone) setErrors(prev => ({ ...prev, phone: '' }));
              }}
              placeholder="0912345678"
              className={`w-full bg-[#0f1117] border rounded-xl px-3.5 py-2.5 text-sm text-white placeholder-gray-500 transition focus:outline-none ${
                errors.phone
                  ? 'border-rose-500/60 bg-rose-500/5 focus:border-rose-500'
                  : 'border-white/10 focus:border-blue-500 focus:bg-white/[0.02]'
              }`}
              disabled={loading || !!successToast}
              aria-invalid={!!errors.phone}
              aria-describedby={errors.phone ? 'phone-error' : undefined}
            />
            {errors.phone && (
              <p id="phone-error" className="text-rose-400 text-xs mt-1 flex items-center gap-1.5 animate-fadeIn">
                <AlertCircle className="w-3.5 h-3.5 shrink-0" />
                <span>{errors.phone}</span>
              </p>
            )}
          </div>
        </div>

        {/* 3. Lựa chọn vai trò (Role Cards) */}
        <div className="space-y-1.5">
          <label className="block text-xs font-semibold text-gray-200">
            Vai trò của bạn trong trường <span className="text-rose-400">*</span>
          </label>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            {roles.map((r) => {
              const Icon = r.icon;
              const isSelected = role === r.id;
              return (
                <button
                  type="button"
                  key={r.id}
                  onClick={() => setRole(r.id)}
                  disabled={loading || !!successToast}
                  className={`flex flex-col items-center justify-center p-2.5 rounded-xl border text-xs font-medium transition cursor-pointer ${
                    isSelected
                      ? 'bg-blue-600/25 border-blue-500 text-blue-300 shadow-md shadow-blue-500/20 ring-1 ring-blue-500'
                      : 'bg-white/5 border-white/10 text-gray-400 hover:bg-white/10 hover:text-white'
                  }`}
                >
                  <Icon className="w-4 h-4 mb-1" />
                  <span className="font-semibold">{r.label}</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* 4. Mật khẩu & Xác nhận mật khẩu kèm nút con mắt */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {/* Mật khẩu */}
          <div className="space-y-1">
            <label htmlFor="reg-password" className="block text-xs font-semibold text-gray-200">
              Mật khẩu <span className="text-rose-400">*</span>
            </label>
            <div className="relative">
              <input
                id="reg-password"
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => {
                  setPassword(e.target.value);
                  if (errors.password) setErrors(prev => ({ ...prev, password: '' }));
                }}
                placeholder="Tối thiểu 6 ký tự"
                className={`w-full bg-[#0f1117] border rounded-xl pl-3.5 pr-11 py-2.5 text-sm text-white placeholder-gray-500 transition focus:outline-none ${
                  errors.password
                    ? 'border-rose-500/60 bg-rose-500/5 focus:border-rose-500'
                    : 'border-white/10 focus:border-blue-500 focus:bg-white/[0.02]'
                }`}
                disabled={loading || !!successToast}
                aria-invalid={!!errors.password}
                aria-describedby={errors.password ? 'reg-pass-error' : undefined}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-white p-1 rounded-md transition focus:outline-none"
                aria-label={showPassword ? 'Ẩn mật khẩu' : 'Hiện mật khẩu'}
                tabIndex={0}
              >
                {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
            {errors.password && (
              <p id="reg-pass-error" className="text-rose-400 text-xs mt-1 flex items-center gap-1.5 animate-fadeIn">
                <AlertCircle className="w-3.5 h-3.5 shrink-0" />
                <span>{errors.password}</span>
              </p>
            )}
          </div>

          {/* Xác nhận mật khẩu */}
          <div className="space-y-1">
            <label htmlFor="reg-confirm-password" className="block text-xs font-semibold text-gray-200">
              Xác nhận mật khẩu <span className="text-rose-400">*</span>
            </label>
            <div className="relative">
              <input
                id="reg-confirm-password"
                type={showConfirmPassword ? 'text' : 'password'}
                value={confirmPassword}
                onChange={(e) => {
                  setConfirmPassword(e.target.value);
                  if (errors.confirmPassword) setErrors(prev => ({ ...prev, confirmPassword: '' }));
                }}
                placeholder="Nhập lại mật khẩu"
                className={`w-full bg-[#0f1117] border rounded-xl pl-3.5 pr-11 py-2.5 text-sm text-white placeholder-gray-500 transition focus:outline-none ${
                  errors.confirmPassword
                    ? 'border-rose-500/60 bg-rose-500/5 focus:border-rose-500'
                    : 'border-white/10 focus:border-blue-500 focus:bg-white/[0.02]'
                }`}
                disabled={loading || !!successToast}
                aria-invalid={!!errors.confirmPassword}
                aria-describedby={errors.confirmPassword ? 'reg-conf-pass-error' : undefined}
              />
              <button
                type="button"
                onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-white p-1 rounded-md transition focus:outline-none"
                aria-label={showConfirmPassword ? 'Ẩn mật khẩu' : 'Hiện mật khẩu'}
                tabIndex={0}
              >
                {showConfirmPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
            {errors.confirmPassword && (
              <p id="reg-conf-pass-error" className="text-rose-400 text-xs mt-1 flex items-center gap-1.5 animate-fadeIn">
                <AlertCircle className="w-3.5 h-3.5 shrink-0" />
                <span>{errors.confirmPassword}</span>
              </p>
            )}
          </div>
        </div>

        {/* Nút thao tác với trạng thái xoay vòng Spinner */}
        <div className="pt-2 flex justify-end gap-3">
          <Button type="button" variant="ghost" onClick={onClose} disabled={loading || !!successToast}>
            Hủy
          </Button>
          <Button type="submit" loading={loading} disabled={loading || !!successToast}>
            {loading ? 'Đang tạo tài khoản...' : 'Đăng Ký & Tiếp Tục →'}
          </Button>
        </div>

        <p className="text-center text-xs text-gray-400 pt-1 border-t border-white/5">
          Đã có tài khoản?{' '}
          <button
            type="button"
            onClick={onSwitchToLogin}
            className="text-blue-400 font-semibold hover:underline"
            disabled={loading || !!successToast}
          >
            Đăng nhập ngay →
          </button>
        </p>
      </form>
    </Modal>
  );
}
