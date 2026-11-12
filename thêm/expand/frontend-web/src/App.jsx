import React, { useState } from 'react';
import { Navbar } from './components/layout/Navbar';
import { SchoolSearchModal } from './components/schools/SchoolSearchModal';
import { LoginModal } from './features/auth/LoginModal';
import { RegisterModal } from './features/auth/RegisterModal';
import { ChangePasswordModal } from './features/auth/ChangePasswordModal';
import { SchoolFeed } from './features/feed/SchoolFeed';
import { useAuth } from './hooks/useAuth';
import { Button } from './components/common/Button';
import { ErrorBoundary } from './components/common/ErrorBoundary';
import { GraduationCap, ShieldCheck, Sparkles, UserPlus, LogIn, Compass } from 'lucide-react';

export default function App() {
  const { user, isAuthenticated, logout } = useAuth();
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [isLoginOpen, setIsLoginOpen] = useState(false);
  const [isRegisterOpen, setIsRegisterOpen] = useState(false);
  const [isChangePasswordOpen, setIsChangePasswordOpen] = useState(false);

  return (
    <ErrorBoundary>
      <div className="min-h-screen bg-[#0f1117] text-gray-100 flex flex-col font-sans">
      {/* Navigation Header */}
      <Navbar
        user={user}
        onOpenLogin={() => setIsLoginOpen(true)}
        onOpenRegister={() => setIsRegisterOpen(true)}
        onOpenSearchSchool={() => setIsSearchOpen(true)}
        onOpenChangePassword={() => setIsChangePasswordOpen(true)}
        onLogout={logout}
      />

      {/* Main Content Area */}
      <main className="flex-1 pt-16">
        {isAuthenticated ? (
          <SchoolFeed
            currentUser={user}
            onOpenSearchSchool={() => setIsSearchOpen(true)}
          />
        ) : (
          /* Guest Hero Showcase */
          <div className="max-w-5xl mx-auto px-4 sm:px-6 py-10 sm:py-20 text-center space-y-6 sm:space-y-8">
            <div className="inline-flex items-center gap-2 px-3 sm:px-4 py-1.5 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-400 text-[11px] sm:text-xs font-semibold">
              <Sparkles className="w-3.5 h-3.5" /> Nền Tảng Mạng Xã Hội Nội Bộ Trường Học
            </div>

            <h1 className="text-2xl sm:text-5xl md:text-6xl font-extrabold tracking-tight leading-tight">
              Kết Nối Học Đường & <br />
              <span className="bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
                Điểm Danh AI Tự Động
              </span>
            </h1>

            <p className="text-gray-300 text-sm sm:text-lg max-w-2xl mx-auto leading-relaxed">
              Mỗi trường học một không gian số độc lập. Quản lý điểm danh camera AI, trao đổi học tập, kết nối phụ huynh và phân quyền vai trò chặt chẽ.
            </p>

            <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-center gap-3 sm:gap-4 pt-2 sm:pt-4 max-w-xs sm:max-w-none mx-auto">
              <Button size="lg" onClick={() => setIsRegisterOpen(true)} className="cursor-pointer transition justify-center">
                <UserPlus className="w-5 h-5" />
                <span>Đăng Ký Tài Khoản</span>
              </Button>
              <Button variant="outline" size="lg" onClick={() => setIsLoginOpen(true)} className="cursor-pointer transition justify-center">
                <LogIn className="w-5 h-5" />
                <span>Đăng Nhập</span>
              </Button>
              <Button variant="ghost" size="lg" onClick={() => setIsSearchOpen(true)} className="cursor-pointer transition justify-center">
                <Compass className="w-5 h-5" />
                <span>Khám Phá Trường Học</span>
              </Button>
            </div>

            {/* Feature Badges */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 sm:gap-6 pt-10 sm:pt-16 text-left">
              <div className="bg-white/5 border border-white/10 hover:border-white/20 p-6 rounded-2xl space-y-2 transition-all duration-200">
                <ShieldCheck className="w-6 h-6 text-green-400" />
                <h3 className="font-bold text-white text-sm">Mã Định Danh Tự Động</h3>
                <p className="text-xs text-gray-300 leading-relaxed">Tự cấp mã chuẩn HS, GV, PH ngay khi đăng ký, không cần tạo thủ công.</p>
              </div>
              <div className="bg-white/5 border border-white/10 hover:border-white/20 p-6 rounded-2xl space-y-2 transition-all duration-200">
                <GraduationCap className="w-6 h-6 text-blue-400" />
                <h3 className="font-bold text-white text-sm">Hiệu Trưởng 1-Click Duyệt</h3>
                <p className="text-xs text-gray-300 leading-relaxed">Kiểm soát chặt chẽ thành viên gia nhập với 2 nút Chấp thuận hoặc Từ chối dứt khoát.</p>
              </div>
              <div className="bg-white/5 border border-white/10 hover:border-white/20 p-6 rounded-2xl space-y-2 transition-all duration-200">
                <Sparkles className="w-6 h-6 text-purple-400" />
                <h3 className="font-bold text-white text-sm">Tabs Phân Quyền Theo Role</h3>
                <p className="text-xs text-gray-300 leading-relaxed">Giao diện mạng xã hội & chuông thông báo render linh hoạt theo từng quyền hạn.</p>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Global Modals */}
      <SchoolSearchModal
        isOpen={isSearchOpen}
        onClose={() => setIsSearchOpen(false)}
        currentUser={user || {}}
        onOpenLogin={() => {
          setIsSearchOpen(false);
          setIsLoginOpen(true);
        }}
        onOpenRegister={() => {
          setIsSearchOpen(false);
          setIsRegisterOpen(true);
        }}
        onJoinedSuccess={() => {
          setIsSearchOpen(false);
        }}
      />

      <LoginModal
        isOpen={isLoginOpen}
        onClose={() => setIsLoginOpen(false)}
        onSwitchToRegister={() => {
          setIsLoginOpen(false);
          setIsRegisterOpen(true);
        }}
        onNeedJoinSchool={() => {
          setIsSearchOpen(true);
        }}
      />

      <RegisterModal
        isOpen={isRegisterOpen}
        onClose={() => setIsRegisterOpen(false)}
        onRegisterSuccess={() => {
          // Đăng ký xong -> ngay lập tức mở modal tham gia trường
          setIsRegisterOpen(false);
          setIsSearchOpen(true);
        }}
        onSwitchToLogin={() => {
          setIsRegisterOpen(false);
          setIsLoginOpen(true);
        }}
      />

      <ChangePasswordModal
        isOpen={isChangePasswordOpen}
        onClose={() => setIsChangePasswordOpen(false)}
        user={user}
      />
    </div>
    </ErrorBoundary>
  );
}

