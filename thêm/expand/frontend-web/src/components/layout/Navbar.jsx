import React, { useState, useRef, useEffect } from 'react';
import { NotificationBell } from '../notifications/NotificationBell';
import { Button } from '../common/Button';
import { GraduationCap, LogOut, LayoutDashboard, KeyRound, School, ChevronDown, Search } from 'lucide-react';

// Role config: màu sắc & label Việt
const ROLE_CONFIG = {
  STUDENT:       { label: 'Học Sinh',       color: 'from-emerald-500 to-teal-500',   bg: 'bg-emerald-500/15 border-emerald-500/30 text-emerald-400' },
  PARENT:        { label: 'Phụ Huynh',      color: 'from-sky-500 to-blue-500',       bg: 'bg-sky-500/15 border-sky-500/30 text-sky-400' },
  TEACHER:       { label: 'Giáo Viên',      color: 'from-violet-500 to-purple-600',  bg: 'bg-violet-500/15 border-violet-500/30 text-violet-400' },
  INSPECTOR:     { label: 'Giám Thị',       color: 'from-orange-500 to-amber-500',   bg: 'bg-orange-500/15 border-orange-500/30 text-orange-400' },
  HEADMASTER:    { label: 'Hiệu Trưởng',    color: 'from-rose-500 to-red-600',       bg: 'bg-rose-500/15 border-rose-500/30 text-rose-400' },
  SCHOOL_ADMIN:  { label: 'Quản Lý',        color: 'from-rose-500 to-red-600',       bg: 'bg-rose-500/15 border-rose-500/30 text-rose-400' },
  ADMIN:         { label: 'Super Admin',     color: 'from-red-600 to-pink-600',       bg: 'bg-red-500/15 border-red-500/30 text-red-400' },
  PLATFORM_ADMIN:{ label: 'Super Admin',     color: 'from-red-600 to-pink-600',       bg: 'bg-red-500/15 border-red-500/30 text-red-400' },
};

function getInitials(name = '') {
  return name.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2) || '?';
}

export function Navbar({ user, onOpenLogin, onOpenRegister, onOpenSearchSchool, onOpenChangePassword, onLogout }) {
  const hasSchool = !!(user?.schoolId || user?.school_id);
  const isAdmin   = ['ADMIN', 'PLATFORM_ADMIN'].includes(user?.role);
  const roleConf  = ROLE_CONFIG[user?.role] || ROLE_CONFIG.STUDENT;
  const displayName = user?.fullName || user?.full_name || user?.username || '';
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef(null);

  // Đóng dropdown khi click ra ngoài
  useEffect(() => {
    const handler = (e) => { if (!menuRef.current?.contains(e.target)) setMenuOpen(false); };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  return (
    <nav className="fixed top-0 left-0 right-0 z-40 h-16 px-4 sm:px-6 flex items-center justify-between">
      {/* Glass background layer */}
      <div className="absolute inset-0 bg-[#0a0c14]/80 backdrop-blur-xl border-b border-white/[0.07] pointer-events-none" />

      {/* Logo */}
      <div className="relative flex items-center gap-3 shrink-0">
        <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-blue-500/30">
          <GraduationCap className="w-5 h-5 text-white" />
        </div>
        <div className="hidden sm:block">
          <h1 className="text-[15px] font-extrabold text-white tracking-tight leading-none">EduSAMS</h1>
          <p className="text-[10px] text-gray-400 mt-0.5 font-medium tracking-wide">School Attendance Platform</p>
        </div>
      </div>

      {/* Right Side */}
      <div className="relative flex items-center gap-2 sm:gap-3">
        {user ? (
          <>
            {/* Dashboard shortcut */}
            {isAdmin ? (
              <a
                href="/app/index.html?school_id=1&view=view-platform-admin"
                className="hidden sm:inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-gradient-to-r from-red-600 to-purple-600 hover:from-red-500 hover:to-purple-500 text-white text-xs font-bold shadow-md shadow-red-500/25 transition-all duration-150 cursor-pointer"
              >
                <LayoutDashboard className="w-3.5 h-3.5" />
                <span>Toàn Sàn ↗</span>
              </a>
            ) : hasSchool ? (
              <a
                href={`/app/index.html?school_id=${user.schoolId || user.school_id}`}
                className="hidden sm:inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white text-xs font-bold shadow-md shadow-blue-500/20 transition-all duration-150 cursor-pointer"
              >
                <LayoutDashboard className="w-3.5 h-3.5" />
                <span>Dashboard ↗</span>
              </a>
            ) : (
              <button
                onClick={onOpenSearchSchool}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-gradient-to-r from-amber-500 to-orange-500 hover:opacity-90 text-white text-xs font-bold shadow-md shadow-amber-500/25 transition-all duration-150 animate-pulse cursor-pointer"
              >
                <School className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">Chọn Trường</span>
              </button>
            )}

            {/* Notification Bell */}
            <NotificationBell userRole={user.role} notifications={[]} />

            {/* Avatar + Menu */}
            <div className="relative" ref={menuRef}>
              <button
                onClick={() => setMenuOpen((o) => !o)}
                className="flex items-center gap-2 pl-1 pr-2 py-1 rounded-2xl hover:bg-white/5 transition-all duration-150 group cursor-pointer"
              >
                {/* Avatar circle */}
                <div className={`w-8 h-8 rounded-full bg-gradient-to-br ${roleConf.color} flex items-center justify-center text-white text-xs font-extrabold shadow-md shrink-0`}>
                  {getInitials(displayName)}
                </div>
                {/* Name + Badge */}
                <div className="hidden sm:flex flex-col items-start leading-none">
                  <span className="text-[13px] font-semibold text-white truncate max-w-[120px]">{displayName}</span>
                  <span className={`mt-0.5 px-1.5 py-0.5 rounded text-[9px] font-bold uppercase border ${roleConf.bg}`}>
                    {roleConf.label}
                  </span>
                </div>
                <ChevronDown className={`w-3.5 h-3.5 text-gray-400 transition-transform duration-200 ${menuOpen ? 'rotate-180' : ''}`} />
              </button>

              {/* Dropdown Menu */}
              {menuOpen && (
                <div className="absolute right-0 mt-2 w-56 bg-[#1a1d27]/95 backdrop-blur-xl border border-white/10 rounded-2xl shadow-2xl shadow-black/40 overflow-hidden z-50 animate-fadeIn">
                  {/* User info header */}
                  <div className="p-4 border-b border-white/10">
                    <div className="flex items-center gap-3">
                      <div className={`w-10 h-10 rounded-full bg-gradient-to-br ${roleConf.color} flex items-center justify-center text-white text-sm font-extrabold shrink-0`}>
                        {getInitials(displayName)}
                      </div>
                      <div className="min-w-0">
                        <p className="text-sm font-bold text-white truncate">{displayName}</p>
                        <span className={`mt-0.5 px-2 py-0.5 rounded-full text-[9px] font-bold uppercase border inline-block ${roleConf.bg}`}>
                          {roleConf.label}
                        </span>
                      </div>
                    </div>
                    {user.memberCode && (
                      <p className="mt-2 text-xs font-mono text-gray-300 font-semibold">#{user.memberCode}</p>
                    )}
                  </div>

                  {/* Actions */}
                  <div className="p-1.5 space-y-0.5">
                    {(hasSchool || isAdmin) && (
                      <a
                        href={isAdmin ? "/app/index.html?school_id=1&view=view-platform-admin" : `/app/index.html?school_id=${user.schoolId || user.school_id}`}
                        className="sm:hidden w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs text-blue-400 font-semibold hover:bg-blue-500/10 transition cursor-pointer"
                      >
                        <LayoutDashboard className="w-4 h-4" />
                        Vào Bảng Quản Trị
                      </a>
                    )}
                    {!hasSchool && !isAdmin && (
                      <button
                        onClick={() => { onOpenSearchSchool(); setMenuOpen(false); }}
                        className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs text-amber-400 font-semibold hover:bg-amber-500/10 transition cursor-pointer"
                      >
                        <School className="w-4 h-4" />
                        Tham Gia Trường Học
                      </button>
                    )}
                    <button
                      onClick={() => { onOpenChangePassword(); setMenuOpen(false); }}
                      className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs text-gray-300 font-medium hover:bg-white/5 hover:text-white transition cursor-pointer"
                    >
                      <KeyRound className="w-4 h-4" />
                      Đổi Mật Khẩu
                    </button>
                    <div className="h-px bg-white/5 mx-2 my-1" />
                    <button
                      onClick={() => { onLogout(); setMenuOpen(false); }}
                      className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs text-red-400 font-semibold hover:bg-red-500/10 transition cursor-pointer"
                    >
                      <LogOut className="w-4 h-4" />
                      Đăng Xuất
                    </button>
                  </div>
                </div>
              )}
            </div>
          </>
        ) : (
          /* Guest actions */
          <>
            <button
              onClick={onOpenSearchSchool}
              className="hidden sm:inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-gray-300 hover:text-white hover:bg-white/5 text-xs font-medium transition cursor-pointer"
            >
              <Search className="w-3.5 h-3.5 text-blue-400" />
              <span>Khám Phá Trường</span>
            </button>
            <Button variant="outline" size="sm" onClick={onOpenLogin} className="cursor-pointer transition">
              Đăng Nhập
            </Button>
            <Button variant="primary" size="sm" onClick={onOpenRegister} className="cursor-pointer transition">
              Đăng Ký
            </Button>
          </>
        )}
      </div>
    </nav>
  );
}
