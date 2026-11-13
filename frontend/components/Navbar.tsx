'use client';

import React, { useState } from 'react';
import { 
  Sprout, 
  Search, 
  Bell, 
  MessageCircle, 
  Volume2, 
  VolumeX, 
  LogOut, 
  Layers, 
  AlertTriangle,
  CheckCircle2,
  ChevronDown
} from 'lucide-react';

interface NavbarProps {
  currentMode: 'livestock' | 'cultivation';
  onModeChange: (mode: 'livestock' | 'cultivation') => void;
  pens: Array<{ id: string; name: string; type: string }>;
  currentPenId: string;
  onPenChange: (penId: string) => void;
  userEmail: string;
  onLogout: () => void;
  alerts: Array<{ id: string; penName: string; issues: string[]; time: string }>;
  onOpenMessenger: () => void;
  isMuted: boolean;
  onToggleMute: () => void;
  unreadAlertsCount: number;
  wsConnected?: boolean;
  onTriggerBriefing?: () => void;
}

export default function Navbar({
  currentMode,
  onModeChange,
  pens,
  currentPenId,
  onPenChange,
  userEmail,
  onLogout,
  alerts,
  onOpenMessenger,
  isMuted,
  onToggleMute,
  unreadAlertsCount,
  wsConnected = false,
  onTriggerBriefing,
}: NavbarProps) {
  const [showNotifications, setShowNotifications] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  return (
    <header className="sticky top-0 z-40 bg-fb-card border-b border-fb-divider shadow-fb-card h-14 px-3 sm:px-4 flex items-center justify-between">
      {/* Cột trái: Biểu tượng nông trại & Ô tìm kiếm */}
      <div className="flex items-center gap-2 md:gap-4">
        <div className="flex items-center gap-2 cursor-pointer select-none">
          <div className="w-9 h-9 sm:w-10 sm:h-10 rounded-full bg-gradient-to-tr from-emerald-600 to-green-500 flex items-center justify-center text-white shadow">
            <Sprout className="w-5 h-5 sm:w-6 sm:h-6" />
          </div>
          <span className="hidden sm:inline font-bold text-lg lg:text-xl tracking-tight bg-gradient-to-r from-emerald-700 to-teal-700 bg-clip-text text-transparent">
            Nông Trại Thông Minh
          </span>
        </div>

        <div className="relative hidden md:block">
          <Search className="w-4 h-4 text-fb-muted absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Tìm kiếm chuồng trại, đàn nuôi, kho..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="bg-fb-bg text-sm rounded-full pl-9 pr-4 py-1.5 w-48 lg:w-64 focus:outline-none focus:ring-2 focus:ring-emerald-500 transition border border-transparent focus:border-emerald-300"
          />
        </div>
      </div>

      {/* Cột giữa: Chuyển đổi phân hệ Chăn nuôi & Trồng trọt */}
      <div className="flex items-center gap-1 sm:gap-2 h-full">
        <button
          onClick={() => onModeChange('livestock')}
          className={`h-full px-3 sm:px-6 flex items-center gap-2 border-b-4 font-bold text-xs sm:text-sm transition cursor-pointer ${
            currentMode === 'livestock'
              ? 'border-emerald-600 text-emerald-700'
              : 'border-transparent text-fb-muted hover:bg-fb-hover'
          }`}
        >
          <span className="text-base sm:text-lg">🐖</span>
          <span>Chăn Nuôi</span>
        </button>

        <button
          onClick={() => onModeChange('cultivation')}
          className={`h-full px-3 sm:px-6 flex items-center gap-2 border-b-4 font-bold text-xs sm:text-sm transition cursor-pointer ${
            currentMode === 'cultivation'
              ? 'border-emerald-600 text-emerald-700'
              : 'border-transparent text-fb-muted hover:bg-fb-hover'
          }`}
        >
          <span className="text-base sm:text-lg">🌿</span>
          <span>Trồng Trọt</span>
        </button>
      </div>

      {/* Cột phải: Trạng thái máy chủ, Cảnh báo & Tài khoản */}
      <div className="flex items-center gap-1.5 sm:gap-2">
        {/* Huy hiệu trạng thái kết nối máy chủ */}
        <div
          title={wsConnected ? 'Đã kết nối máy chủ trực tiếp theo thời gian thực' : 'Chưa kết nối máy chủ quản lý'}
          className={`hidden xl:flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold border transition ${
            wsConnected
              ? 'bg-emerald-50 text-emerald-700 border-emerald-300'
              : 'bg-amber-50 text-amber-700 border-amber-300'
          }`}
        >
          <span
            className={`w-2 h-2 rounded-full ${
              wsConnected ? 'bg-emerald-500 animate-pulse' : 'bg-amber-500'
            }`}
          />
          <span>{wsConnected ? 'Trợ Lý Trực Tuyến' : 'Mất Kết Nối Máy Chủ'}</span>
        </div>

        {/* Nút yêu cầu tổng hợp bản tin sáng */}
        {onTriggerBriefing && (
          <button
            onClick={onTriggerBriefing}
            title="Kích hoạt trợ lý tổng hợp bản tin toàn trang trại"
            className="hidden sm:flex items-center gap-1 px-3 py-1.5 rounded-full bg-gradient-to-r from-emerald-600 to-teal-600 text-white text-xs font-bold shadow hover:opacity-95 transition cursor-pointer"
          >
            <span>🌅</span>
            <span>Bản Tin Sáng</span>
          </button>
        )}

        {/* Bộ chọn nhanh khu vực chuồng trại */}
        <div className="relative hidden lg:flex items-center bg-fb-bg px-2.5 py-1.5 rounded-full border border-fb-divider text-xs">
          <Layers className="w-3.5 h-3.5 text-emerald-600 mr-1.5 shrink-0" />
          <select
            value={currentPenId}
            onChange={(e) => onPenChange(e.target.value)}
            className="bg-transparent font-semibold text-fb-text focus:outline-none cursor-pointer pr-3"
            aria-label="Chọn khu vực chuồng trại"
          >
            {pens.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        </div>

        {/* Nút bật/tắt chuông báo động */}
        <button
          onClick={onToggleMute}
          title={isMuted ? 'Bật chuông báo động' : 'Tắt chuông báo động'}
          className="w-9 h-9 rounded-full bg-fb-bg hover:bg-fb-hover flex items-center justify-center text-fb-text transition cursor-pointer"
          aria-label={isMuted ? 'Bật chuông báo động' : 'Tắt chuông báo động'}
        >
          {isMuted ? <VolumeX className="w-4 h-4 text-red-500" /> : <Volume2 className="w-4 h-4 text-emerald-600" />}
        </button>

        {/* Chuông thông báo */}
        <div className="relative">
          <button
            onClick={() => setShowNotifications(!showNotifications)}
            className="w-9 h-9 rounded-full bg-fb-bg hover:bg-fb-hover flex items-center justify-center text-fb-text transition relative cursor-pointer"
            aria-label="Xem thông báo trang trại"
          >
            <Bell className="w-4 h-4" />
            {unreadAlertsCount > 0 && (
              <span className="absolute -top-1 -right-1 bg-red-600 text-white text-[10px] font-bold px-1.5 py-0.2 rounded-full animate-bounce">
                {unreadAlertsCount}
              </span>
            )}
          </button>

          {showNotifications && (
            <div className="absolute right-0 mt-2 w-80 sm:w-96 bg-fb-card rounded-2xl shadow-fb-popover border border-fb-divider p-3 z-50">
              <div className="flex items-center justify-between pb-2 border-b border-fb-divider mb-2">
                <h3 className="font-bold text-sm text-fb-text">Thông Báo Trang Trại</h3>
                <span className="text-xs text-emerald-700 font-bold">
                  {unreadAlertsCount} thông báo cần chú ý
                </span>
              </div>

              <div className="max-h-72 overflow-y-auto space-y-2">
                {alerts.length === 0 ? (
                  <div className="text-center py-6 text-fb-muted text-xs">
                    <CheckCircle2 className="w-8 h-8 text-emerald-500 mx-auto mb-1 opacity-80" />
                    Mọi khu vực chuồng trại đều an toàn và ổn định!
                  </div>
                ) : (
                  alerts.map((alert, idx) => (
                    <div
                      key={alert.id || idx}
                      className="flex items-start gap-2.5 p-2.5 rounded-xl bg-red-50 hover:bg-red-100 transition border border-red-200 cursor-pointer"
                    >
                      <div className="w-7 h-7 rounded-full bg-red-500 text-white flex items-center justify-center shrink-0 mt-0.5">
                        <AlertTriangle className="w-3.5 h-3.5" />
                      </div>
                      <div className="text-xs flex-1">
                        <p className="font-bold text-red-800">{alert.penName}</p>
                        <p className="text-red-700 mt-0.5">Vấn đề: {alert.issues.join(', ')}</p>
                        <span className="text-[10px] text-red-500 mt-1 block">{alert.time}</span>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}
        </div>

        {/* Nút mở hộp thoại trợ lý ảo */}
        <button
          onClick={onOpenMessenger}
          title="Mở hộp thoại trợ lý nông nghiệp"
          className="w-9 h-9 rounded-full bg-fb-bg hover:bg-fb-hover flex items-center justify-center text-fb-blue transition relative cursor-pointer"
          aria-label="Mở hộp thoại trợ lý nông nghiệp"
        >
          <MessageCircle className="w-4 h-4" />
          <span className="w-2 h-2 rounded-full bg-emerald-500 absolute top-1.5 right-1.5 ring-2 ring-white" />
        </button>

        {/* Thông tin người dùng & Nút Đăng xuất */}
        <div className="flex items-center gap-1.5 pl-1.5 border-l border-fb-divider ml-1">
          <div className="w-8 h-8 rounded-full bg-emerald-700 text-white font-bold text-xs flex items-center justify-center shadow select-none">
            {userEmail ? userEmail.charAt(0).toUpperCase() : 'N'}
          </div>
          <button
            onClick={onLogout}
            title="Đăng xuất tài khoản"
            className="w-8 h-8 rounded-full hover:bg-fb-hover flex items-center justify-center text-fb-muted hover:text-red-600 transition cursor-pointer"
            aria-label="Đăng xuất tài khoản"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </header>
  );
}
