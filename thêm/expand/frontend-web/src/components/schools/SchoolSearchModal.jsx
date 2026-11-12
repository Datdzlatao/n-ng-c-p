import React, { useState, useEffect, useRef } from 'react';
import { 
  Search, 
  MapPin, 
  Users, 
  X, 
  Send, 
  CheckCircle2, 
  Building2, 
  AlertCircle, 
  ChevronRight, 
  ArrowLeft, 
  Loader2, 
  Sparkles 
} from 'lucide-react';
import { schoolService } from '../../services/schoolService';
import { Button } from '../common/Button';

export function SchoolSearchModal({ 
  isOpen, 
  onClose, 
  currentUser = {}, 
  onJoinedSuccess, 
  onOpenLogin, 
  onOpenRegister 
}) {
  const [query, setQuery] = useState('');
  const [schools, setSchools] = useState([]);
  const [selectedSchool, setSelectedSchool] = useState(null);
  const [isSearching, setIsSearching] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [requestSent, setRequestSent] = useState(false);
  const [searchError, setSearchError] = useState('');
  const [submitError, setSubmitError] = useState('');
  const [successToast, setSuccessToast] = useState('');

  const searchInputRef = useRef(null);
  const isLoggedIn = !!localStorage.getItem('stem_auth_token');

  // 1. Tự động focus vào ô tìm kiếm và reset trạng thái khi mở modal
  useEffect(() => {
    if (isOpen) {
      setQuery('');
      setSelectedSchool(null);
      setRequestSent(false);
      setSearchError('');
      setSubmitError('');
      setSuccessToast('');

      const timer = setTimeout(() => {
        searchInputRef.current?.focus();
      }, 80);
      return () => clearTimeout(timer);
    }
  }, [isOpen]);

  // 2. Tìm kiếm trường học tức thời có Debounce 300ms
  useEffect(() => {
    if (!isOpen) return;

    setIsSearching(true);
    setSearchError('');

    const debounceTimer = setTimeout(async () => {
      try {
        const data = await schoolService.getSchools(query.trim());
        setSchools(Array.isArray(data) ? data : []);
      } catch (err) {
        console.error('Lỗi tìm kiếm trường:', err);
        setSearchError('Không thể kết nối đến máy chủ để tải danh sách trường.');
        setSchools([]);
      } finally {
        setIsSearching(false);
      }
    }, 300);

    return () => clearTimeout(debounceTimer);
  }, [query, isOpen]);

  // 3. Gửi yêu cầu gia nhập trường với Spinner phản hồi và Toast thành công
  const handleSendJoinRequest = async () => {
    if (!selectedSchool) return;
    setSubmitError('');

    if (!isLoggedIn) {
      if (onOpenRegister) {
        onClose();
        onOpenRegister();
      } else if (onOpenLogin) {
        onClose();
        onOpenLogin();
      } else {
        setSubmitError('Vui lòng đăng ký hoặc đăng nhập tài khoản trước khi tham gia trường.');
      }
      return;
    }

    setSubmitting(true);
    try {
      const res = await schoolService.sendJoinRequest(selectedSchool.id);
      setRequestSent(true);
      setSuccessToast(`Đã gửi yêu cầu gia nhập ${selectedSchool.name} thành công! Đang chuyển vào không gian trường...`);

      if (res?.access_token) {
        localStorage.setItem('stem_auth_token', res.access_token);
      }
      localStorage.setItem('stem_school_id', selectedSchool.id);

      if (onJoinedSuccess) {
        onJoinedSuccess(selectedSchool, res?.user);
      }

      setTimeout(() => {
        if (['HEADMASTER', 'ADMIN', 'PLATFORM_ADMIN', 'TEACHER', 'INSPECTOR'].includes(currentUser?.role)) {
          window.location.href = `/app/index.html?school_id=${selectedSchool.id}`;
        } else {
          window.location.reload();
        }
      }, 1200);
    } catch (error) {
      setSubmitError(error.message || 'Lỗi gửi yêu cầu gia nhập. Vui lòng thử lại sau.');
    } finally {
      setSubmitting(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 animate-fadeIn">
      <div className="bg-[#1a1d27] border border-white/10 w-full max-w-2xl rounded-2xl overflow-hidden shadow-2xl flex flex-col max-h-[90vh]">
        {/* Modal Header */}
        <div className="p-4 sm:px-6 border-b border-white/10 flex items-center justify-between bg-[#14161f]">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-blue-500/15 border border-blue-500/30 flex items-center justify-center text-blue-400">
              <Building2 className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-bold text-white text-base leading-tight">Tìm & Chọn Trường Học</h3>
              <p className="text-xs text-gray-400 mt-0.5">Tham gia hệ thống trường trên nền tảng EduSAMS</p>
            </div>
          </div>
          <button 
            type="button"
            onClick={onClose} 
            className="p-1.5 hover:bg-white/10 rounded-lg text-gray-400 hover:text-white transition"
            aria-label="Đóng cửa sổ"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4">
          {/* Thông báo Toast thành công xanh lá */}
          {successToast && (
            <div className="p-3.5 rounded-xl bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 text-xs flex items-center gap-2.5 animate-fadeIn">
              <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-400" />
              <span className="font-semibold">{successToast}</span>
            </div>
          )}

          {/* Báo lỗi gửi yêu cầu gia nhập inline */}
          {submitError && (
            <div className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center gap-2 animate-fadeIn">
              <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
              <span>{submitError}</span>
            </div>
          )}

          {/* Banner hướng dẫn nếu chưa đăng nhập */}
          {!isLoggedIn ? (
            <div className="p-3.5 rounded-xl bg-blue-500/10 border border-blue-500/20 text-xs text-blue-200 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-blue-400 shrink-0" />
                <span>Bạn cần có tài khoản trước khi gửi yêu cầu tham gia trường học.</span>
              </div>
              <div className="flex items-center gap-2 self-end sm:self-auto shrink-0">
                <button
                  type="button"
                  onClick={() => { onClose(); if (onOpenLogin) onOpenLogin(); }}
                  className="px-3 py-1.5 bg-white/10 hover:bg-white/20 rounded-lg text-white font-medium transition"
                >
                  Đăng Nhập
                </button>
                <button
                  type="button"
                  onClick={() => { onClose(); if (onOpenRegister) onOpenRegister(); }}
                  className="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 rounded-lg text-white font-medium shadow-sm transition"
                >
                  Đăng Ký Tài Khoản
                </button>
              </div>
            </div>
          ) : !currentUser?.schoolId && !currentUser?.school_id ? (
            <div className="p-3 rounded-xl bg-purple-500/10 border border-purple-500/20 text-xs text-purple-300 flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-purple-400 shrink-0" />
              <span>
                Xin chào <strong className="text-white">{currentUser.fullName || currentUser.username}</strong>! Hãy chọn trường học của bạn bên dưới và bấm <strong>Gửi yêu cầu tham gia</strong>.
              </span>
            </div>
          ) : null}

          {/* Ô tìm kiếm trường học có nhãn và icon kính lúp */}
          {!selectedSchool && (
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <label htmlFor="school-search-input" className="block text-xs font-semibold text-gray-200">
                  Tìm kiếm trường học <span className="text-gray-400 font-normal ml-1">— Gõ tên trường, tỉnh thành hoặc mã @slug</span>
                </label>
                {schools.length > 0 && !isSearching && (
                  <span className="text-[11px] text-gray-400 font-medium">
                    Tìm thấy {schools.length} trường
                  </span>
                )}
              </div>

              <div className="relative">
                <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400 w-4 h-4 pointer-events-none" />
                <input
                  id="school-search-input"
                  ref={searchInputRef}
                  type="text"
                  className="w-full bg-[#0f1117] border border-white/10 rounded-xl pl-10 pr-10 py-2.5 text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition"
                  placeholder="Ví dụ: THPT Chuyên STEM, thpt-chuyen-stem, Hà Nội..."
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  autoComplete="off"
                />

                {/* Loading indicator hoặc Clear button */}
                <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center">
                  {isSearching ? (
                    <Loader2 className="w-4 h-4 text-blue-400 animate-spin" />
                  ) : query ? (
                    <button
                      type="button"
                      onClick={() => {
                        setQuery('');
                        searchInputRef.current?.focus();
                      }}
                      className="p-1 text-gray-400 hover:text-white rounded-md hover:bg-white/10 transition"
                      aria-label="Xoá từ khoá tìm kiếm"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  ) : null}
                </div>
              </div>

              {/* Báo lỗi tìm kiếm inline */}
              {searchError && (
                <p className="text-rose-400 text-xs mt-1 flex items-center gap-1.5 animate-fadeIn">
                  <AlertCircle className="w-3.5 h-3.5 shrink-0" />
                  <span>{searchError}</span>
                </p>
              )}
            </div>
          )}

          {/* Danh sách trường dạng thẻ bấm chọn trực quan */}
          {!selectedSchool ? (
            <div className="space-y-2.5">
              <div className="flex items-center justify-between pt-1">
                <span className="text-xs uppercase font-semibold text-gray-400 tracking-wider">
                  {query.trim() ? `Kết quả cho "${query.trim()}"` : 'Trường học gợi ý'}
                </span>
                <span className="text-[11px] text-gray-400 font-medium">Bấm thẻ để xem chi tiết</span>
              </div>

              {isSearching && schools.length === 0 ? (
                <div className="py-12 text-center text-gray-400 flex flex-col items-center justify-center gap-2">
                  <Loader2 className="w-6 h-6 text-blue-400 animate-spin" />
                  <span className="text-xs">Đang tìm kiếm trường học...</span>
                </div>
              ) : schools.length === 0 ? (
                <div className="py-12 px-4 text-center rounded-xl bg-white/[0.02] border border-white/5 flex flex-col items-center justify-center">
                  <Building2 className="w-10 h-10 text-gray-600 mb-2" />
                  <p className="text-sm font-medium text-gray-300">Không tìm thấy trường học phù hợp.</p>
                  <p className="text-xs text-gray-400 mt-1">
                    Thử tìm kiếm với tên viết tắt, mã @slug hoặc tỉnh thành khác.
                  </p>
                </div>
              ) : (
                <div className="space-y-2.5 max-h-[48vh] overflow-y-auto pr-1">
                  {schools.map((school) => {
                    const identifier = school.school_code || school.slug || 'stem';
                    const initials = school.name
                      ? school.name
                          .split(' ')
                          .filter(Boolean)
                          .slice(0, 2)
                          .map((w) => w[0])
                          .join('')
                          .toUpperCase()
                      : 'TR';

                    return (
                      <div
                        key={school.id}
                        onClick={() => {
                          setSelectedSchool(school);
                          setSubmitError('');
                        }}
                        className="group flex items-center gap-3.5 p-3.5 bg-white/[0.03] hover:bg-white/[0.08] border border-white/5 hover:border-blue-500/40 rounded-xl cursor-pointer transition-all duration-200 shadow-sm hover:shadow-md"
                        role="button"
                        tabIndex={0}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter' || e.key === ' ') {
                            e.preventDefault();
                            setSelectedSchool(school);
                            setSubmitError('');
                          }
                        }}
                      >
                        {/* Logo / Avatar trường */}
                        <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-blue-600/20 to-indigo-600/20 border border-blue-500/30 flex items-center justify-center font-bold text-blue-300 text-sm shrink-0 shadow-inner group-hover:scale-105 group-hover:border-blue-400/50 transition-transform">
                          {initials}
                        </div>

                        {/* Thông tin trường */}
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 flex-wrap">
                            <h4 className="text-sm font-bold text-white group-hover:text-blue-400 transition truncate">
                              {school.name}
                            </h4>
                            {/* Mã định danh @slug */}
                            <span className="font-mono text-[11px] bg-blue-500/15 border border-blue-500/30 text-blue-300 px-2 py-0.5 rounded-md font-semibold shrink-0">
                              @{identifier}
                            </span>
                          </div>

                          <div className="flex items-center gap-3 text-xs text-gray-400 mt-1 flex-wrap">
                            <span className="flex items-center gap-1 truncate max-w-[240px]">
                              <MapPin className="w-3.5 h-3.5 text-amber-400 shrink-0" />
                              <span className="truncate">{school.address || school.province_city || 'Toàn quốc'}</span>
                            </span>
                            <span className="text-gray-600">•</span>
                            <span className="flex items-center gap-1 shrink-0 text-gray-300">
                              <Users className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                              <span>{school.student_count ?? school.member_count ?? 0} thành viên</span>
                            </span>
                          </div>
                        </div>

                        {/* Nút bấm chọn trường trực quan */}
                        <div className="shrink-0 flex items-center gap-1 text-xs font-semibold text-blue-400 bg-blue-500/10 group-hover:bg-blue-600 group-hover:text-white px-3 py-1.5 rounded-lg border border-blue-500/20 group-hover:border-blue-500 transition-colors">
                          <span>Chọn</span>
                          <ChevronRight className="w-3.5 h-3.5" />
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          ) : (
            /* Thẻ hồ sơ trường học chi tiết khi được chọn (Bento Preview) */
            <div className="space-y-4 animate-fadeIn">
              {/* Banner Cover */}
              <div className="relative h-32 rounded-xl overflow-hidden bg-gradient-to-r from-blue-900/60 via-indigo-900/60 to-purple-900/60 border border-white/10 flex items-center p-4">
                <button
                  type="button"
                  onClick={() => {
                    setSelectedSchool(null);
                    setSubmitError('');
                  }}
                  className="bg-black/60 hover:bg-black/80 text-white text-xs px-3 py-1.5 rounded-lg backdrop-blur-sm transition flex items-center gap-1.5 border border-white/10"
                >
                  <ArrowLeft className="w-3.5 h-3.5" />
                  <span>Chọn trường khác</span>
                </button>
              </div>

              {/* Header chi tiết trường */}
              <div className="flex items-start gap-4 -mt-10 px-3 relative z-10">
                <div className="w-18 h-18 sm:w-20 sm:h-20 rounded-2xl border-4 border-[#1a1d27] bg-gradient-to-br from-blue-600 to-indigo-700 flex items-center justify-center font-bold text-xl sm:text-2xl text-white shadow-xl shrink-0">
                  {selectedSchool.name.slice(0, 2).toUpperCase()}
                </div>
                <div className="pt-6 sm:pt-7 flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <h3 className="text-base sm:text-lg font-bold text-white truncate">
                      {selectedSchool.name}
                    </h3>
                    <span className="font-mono text-xs bg-blue-500/20 border border-blue-500/40 text-blue-300 px-2.5 py-0.5 rounded-md font-semibold">
                      @{selectedSchool.school_code || selectedSchool.slug || 'stem'}
                    </span>
                  </div>
                  <p className="text-xs text-gray-400 flex items-center gap-1.5 mt-1 truncate">
                    <MapPin className="w-3.5 h-3.5 text-amber-400 shrink-0" />
                    <span>{selectedSchool.address || selectedSchool.province_city || 'Địa chỉ đang cập nhật'}</span>
                  </p>
                </div>
              </div>

              {/* Thông số trường */}
              <div className="px-2 space-y-3">
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5 p-3 rounded-xl bg-white/[0.02] border border-white/5 text-xs text-gray-300">
                  <div className="flex items-center gap-2">
                    <Users className="w-4 h-4 text-emerald-400 shrink-0" />
                    <div>
                      <p className="text-[10px] text-gray-400">Sĩ số / Thành viên</p>
                      <p className="font-semibold text-white">{selectedSchool.student_count ?? selectedSchool.member_count ?? 0}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <MapPin className="w-4 h-4 text-amber-400 shrink-0" />
                    <div className="truncate">
                      <p className="text-[10px] text-gray-400">Khu vực</p>
                      <p className="font-semibold text-white truncate">{selectedSchool.province_city || 'Toàn quốc'}</p>
                    </div>
                  </div>
                  <div className="col-span-2 sm:col-span-1 flex items-center gap-2">
                    <Building2 className="w-4 h-4 text-blue-400 shrink-0" />
                    <div>
                      <p className="text-[10px] text-gray-400">Trạng thái hệ thống</p>
                      <span className="inline-flex items-center gap-1 font-semibold text-emerald-400">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" /> Sẵn sàng
                      </span>
                    </div>
                  </div>
                </div>

                <div className="p-3.5 rounded-xl bg-white/[0.02] border border-white/5">
                  <p className="text-xs font-semibold text-gray-300 mb-1">Giới thiệu</p>
                  <p className="text-xs text-gray-400 leading-relaxed">
                    {selectedSchool.description || 'Hệ thống trường học chính thức trực thuộc nền tảng EduSAMS.'}
                  </p>
                </div>

                {/* Thông tin tài khoản người dùng đang yêu cầu */}
                {currentUser.role && (
                  <div className="bg-blue-500/10 border border-blue-500/20 rounded-xl p-3 flex items-center justify-between text-xs">
                    <div>
                      <span className="text-gray-400">Tài khoản yêu cầu:</span>{' '}
                      <span className="font-semibold text-white">{currentUser.fullName || currentUser.username}</span>
                      <span className="ml-2 font-mono text-[11px] bg-blue-500/20 text-blue-300 px-1.5 py-0.5 rounded uppercase">
                        {currentUser.role}
                      </span>
                    </div>
                    <div>
                      <span className="text-gray-400">Mã cá nhân:</span>{' '}
                      <code className="bg-blue-500/20 text-blue-300 px-2 py-0.5 rounded font-mono font-bold">
                        {currentUser.memberCode || currentUser.student_code || 'Tự động cấp'}
                      </code>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="p-4 sm:px-6 border-t border-white/10 bg-[#14161f] flex items-center justify-between gap-3">
          {selectedSchool ? (
            <button
              type="button"
              onClick={() => {
                setSelectedSchool(null);
                setSubmitError('');
              }}
              className="text-xs text-gray-400 hover:text-white flex items-center gap-1 px-2 py-1.5 rounded-lg hover:bg-white/5 transition"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              <span>Quay lại danh sách</span>
            </button>
          ) : (
            <div />
          )}

          <div className="flex items-center gap-2.5">
            <Button 
              type="button"
              variant="ghost" 
              onClick={onClose}
              disabled={submitting}
            >
              Đóng
            </Button>

            {selectedSchool && (
              <Button
                type="button"
                variant={requestSent ? 'success' : 'primary'}
                onClick={handleSendJoinRequest}
                loading={submitting}
                disabled={submitting || requestSent}
              >
                {requestSent ? (
                  <>
                    <CheckCircle2 className="w-4 h-4" />
                    <span>Đã gửi yêu cầu</span>
                  </>
                ) : (
                  <>
                    <Send className="w-4 h-4" />
                    <span>Gửi yêu cầu tham gia trường</span>
                  </>
                )}
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
