import React, { useState, useEffect, useRef } from 'react';
import { Bell, CheckSquare, UserCheck, Megaphone, Inbox, X, ChevronDown, ChevronUp, Clock, Check, ShieldAlert } from 'lucide-react';
import { notifService } from '../../services/notifService';

// Hook để đóng dropdown khi click ra ngoài
function useClickOutside(ref, handler) {
  useEffect(() => {
    const listener = (e) => { if (!ref.current || ref.current.contains(e.target)) return; handler(e); };
    document.addEventListener('mousedown', listener);
    return () => document.removeEventListener('mousedown', listener);
  }, [ref, handler]);
}

function formatNotifTime(dateStr) {
  if (!dateStr) return '';
  try {
    const date = new Date(dateStr);
    if (isNaN(date.getTime())) return String(dateStr);
    const now = new Date();
    const diffMs = now - date;
    const diffMin = Math.floor(diffMs / 60000);
    if (diffMin < 1) return 'Vừa xong';
    if (diffMin < 60) return `${diffMin} phút trước`;
    const hhmm = date.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' });
    if (diffMs < 86400000 && now.getDate() === date.getDate()) {
      return `Hôm nay ${hhmm}`;
    }
    return `${hhmm} ${date.toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit' })}`;
  } catch {
    return String(dateStr);
  }
}

export function NotificationBell({ userRole = 'STUDENT', notifications = [], onSelectCategory }) {
  const [isOpen, setIsOpen] = useState(false);
  const [activeTab, setActiveTab] = useState('ALL');
  const [items, setItems] = useState(notifications);
  const [shake, setShake] = useState(false);
  const [expandedId, setExpandedId] = useState(null);
  const wrapperRef = useRef(null);

  useClickOutside(wrapperRef, () => setIsOpen(false));

  useEffect(() => {
    notifService.getNotifications()
      .then((res) => { if (res?.data) setItems(res.data); })
      .catch(() => {});
  }, [userRole]);

  // Hiệu ứng rung nhẹ khi có thông báo mới
  useEffect(() => {
    if (items.some(n => !n.isRead)) {
      setShake(true);
      const t = setTimeout(() => setShake(false), 700);
      return () => clearTimeout(t);
    }
  }, [items.length]);

  const handleMarkAllRead = async () => {
    try {
      await notifService.markAllAsRead();
      setItems((prev) => prev.map((item) => ({ ...item, isRead: true })));
    } catch {}
  };

  const handleNotificationClick = async (n) => {
    // Đánh dấu đã đọc nếu chưa đọc
    if (!n.isRead) {
      try {
        await notifService.markAsRead(n.id);
        setItems((prev) => prev.map((item) => item.id === n.id ? { ...item, isRead: true } : item));
      } catch {}
    }
    // Chuyển trạng thái xem toàn bộ nội dung
    setExpandedId((prev) => (prev === n.id ? null : n.id));
    if (onSelectCategory) onSelectCategory(n);
  };

  const unreadCount = items.filter((n) => !n.isRead).length;

  const filterTabs = [
    { id: 'ALL', label: 'Tất cả' },
    ...(['SCHOOL_ADMIN','HEADMASTER','ADMIN','PLATFORM_ADMIN','INSPECTOR','TEACHER'].includes(userRole)
      ? [{ id: 'SECURITY', label: 'An ninh 🚨', icon: ShieldAlert }] : []),
    ...(['SCHOOL_ADMIN','HEADMASTER','ADMIN','PLATFORM_ADMIN','INSPECTOR'].includes(userRole)
      ? [{ id: 'APPROVALS', label: 'Duyệt đơn', icon: UserCheck }] : []),
    ...(['STUDENT','PARENT'].includes(userRole)
      ? [{ id: 'ATTENDANCE', label: 'Điểm danh', icon: CheckSquare }] : []),
    ...(userRole === 'TEACHER'
      ? [{ id: 'CLASS_UPDATES', label: 'Báo cáo lớp', icon: Megaphone }] : []),
  ];

  const filteredNotifications = activeTab === 'ALL' ? items : items.filter((n) => n.category === activeTab);

  return (
    <div className="relative" ref={wrapperRef}>
      {/* Mobile Backdrop khi mở tab thông báo */}
      {isOpen && (
        <div 
          className="fixed inset-0 bg-black/60 backdrop-blur-sm sm:hidden z-40 animate-in fade-in duration-200"
          onClick={() => setIsOpen(false)}
        />
      )}

      {/* Bell Button */}
      <button
        onClick={() => setIsOpen((o) => !o)}
        className={`relative p-2.5 rounded-xl bg-white/5 hover:bg-white/10 text-gray-300 hover:text-white transition-all duration-200 ${shake ? 'animate-[wiggle_0.5s_ease-in-out]' : ''}`}
        aria-label="Thông báo"
        title="Thông báo hệ thống"
      >
        <Bell className={`w-5 h-5 transition-transform ${shake ? 'rotate-12' : ''}`} />
        {unreadCount > 0 && (
          <span className="absolute -top-1 -right-1 bg-red-500 text-white text-[9px] font-extrabold min-w-[18px] h-[18px] px-0.5 rounded-full flex items-center justify-center border-2 border-[#0f1117] shadow-sm animate-pulse">
            {unreadCount > 99 ? '99+' : unreadCount}
          </span>
        )}
      </button>

      {/* Dropdown Panel: Trên mobile cố định giữa màn hình (inset-x-3 top-16), không bị tràn ra ngoài viền */}
      {isOpen && (
        <div className="fixed inset-x-3 top-16 sm:absolute sm:inset-x-auto sm:top-full sm:right-0 sm:mt-2.5 sm:w-96 sm:max-w-sm bg-[#161822]/98 backdrop-blur-2xl border border-white/10 rounded-2xl shadow-2xl shadow-black/60 z-50 overflow-hidden flex flex-col max-h-[82vh] sm:max-h-[560px] animate-in fade-in zoom-in-95 duration-150">
          {/* Header */}
          <div className="px-4 py-3 border-b border-white/10 flex items-center justify-between bg-black/20 shrink-0">
            <div className="flex items-center gap-2">
              <h4 className="text-sm font-bold text-white flex items-center gap-1.5">
                <span>Thông Báo</span>
              </h4>
              {unreadCount > 0 && (
                <span className="px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-400 text-[10px] font-bold border border-blue-500/30">
                  {unreadCount} mới
                </span>
              )}
            </div>
            <div className="flex items-center gap-2">
              {unreadCount > 0 && (
                <button 
                  onClick={handleMarkAllRead} 
                  className="text-[11px] text-blue-400 font-medium hover:text-blue-300 transition flex items-center gap-1 cursor-pointer bg-blue-500/10 hover:bg-blue-500/20 px-2 py-1 rounded-lg"
                  title="Đánh dấu tất cả đã đọc"
                >
                  <Check className="w-3 h-3" />
                  <span>Đã đọc hết</span>
                </button>
              )}
              <button 
                onClick={() => setIsOpen(false)} 
                className="p-1 rounded-lg text-gray-400 hover:text-white hover:bg-white/10 transition cursor-pointer" 
                aria-label="Đóng thông báo"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Filter Tabs: Cuộn ngang mượt mà, không bị ép chữ hay tràn mép */}
          {filterTabs.length > 1 && (
            <div className="flex bg-black/40 px-2 py-1.5 gap-1.5 border-b border-white/5 overflow-x-auto no-scrollbar scroll-smooth shrink-0">
              {filterTabs.map((tab) => {
                const TabIcon = tab.icon;
                const active = activeTab === tab.id;
                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`flex items-center gap-1.5 py-1.5 px-3 text-[11px] font-semibold rounded-lg transition shrink-0 whitespace-nowrap cursor-pointer ${
                      active
                        ? 'bg-blue-600 text-white shadow-sm shadow-blue-500/20'
                        : 'text-gray-300 hover:text-white hover:bg-white/5'
                    }`}
                  >
                    {TabIcon && <TabIcon className="w-3 h-3 shrink-0" />}
                    <span>{tab.label}</span>
                  </button>
                );
              })}
            </div>
          )}

          {/* Items List: Xem toàn bộ nội dung, mở rộng/thu gọn thông minh */}
          <div className="flex-1 overflow-y-auto divide-y divide-white/5 overscroll-contain">
            {filteredNotifications.length === 0 ? (
              <div className="py-12 text-center text-gray-400 flex flex-col items-center gap-2.5">
                <div className="w-12 h-12 rounded-2xl bg-white/[0.03] border border-white/5 flex items-center justify-center">
                  <Inbox className="w-6 h-6 text-gray-500" />
                </div>
                <p className="text-xs text-gray-300">Không có thông báo nào trong mục này.</p>
              </div>
            ) : (
              filteredNotifications.map((n) => {
                const isExpanded = expandedId === n.id;
                const timeText = formatNotifTime(n.createdAt || n.created_at);
                const isLong = (n.content && n.content.length > 70);

                return (
                  <div
                    key={n.id}
                    className={`p-3.5 flex items-start gap-3 cursor-pointer hover:bg-white/[0.04] transition-colors ${!n.isRead ? 'bg-blue-500/[0.07]' : ''}`}
                    onClick={() => handleNotificationClick(n)}
                  >
                    {/* Unread indicator dot */}
                    <div className={`w-2 h-2 rounded-full mt-1.5 shrink-0 ${!n.isRead ? 'bg-blue-500 shadow-sm shadow-blue-500' : 'bg-gray-600/60'}`} />
                    
                    {/* Content area */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-start justify-between gap-2">
                        <p className={`text-xs font-semibold leading-snug break-words ${!n.isRead ? 'text-white' : 'text-gray-300'}`}>
                          {n.title}
                        </p>
                        {timeText && (
                          <span className="text-[10px] text-gray-400 font-mono shrink-0 flex items-center gap-0.5">
                            <Clock className="w-2.5 h-2.5" />
                            {timeText}
                          </span>
                        )}
                      </div>

                      {/* Notification body with full viewing capability */}
                      <p className={`text-[11.5px] mt-1 leading-relaxed break-words whitespace-pre-line ${
                        isExpanded ? 'text-gray-200' : 'text-gray-400 line-clamp-2'
                      }`}>
                        {n.content}
                      </p>

                      {n.proof_image_url && (
                        <div className="mt-2">
                          <a 
                            href={n.proof_image_url} 
                            target="_blank" 
                            rel="noopener noreferrer"
                            onClick={(e) => e.stopPropagation()}
                            className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-red-500/15 border border-red-500/30 text-red-400 hover:bg-red-500/25 text-[11px] font-semibold transition cursor-pointer"
                          >
                            <span>📷 Xem ảnh chụp đối tượng</span>
                          </a>
                        </div>
                      )}

                      {/* Xem thêm / Thu gọn toggle button */}
                      {isLong && (
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            setExpandedId(isExpanded ? null : n.id);
                          }}
                          className="mt-1.5 text-[10.5px] font-semibold text-blue-400 hover:text-blue-300 inline-flex items-center gap-1 cursor-pointer"
                        >
                          <span>{isExpanded ? 'Thu gọn nội dung' : 'Xem toàn bộ nội dung'}</span>
                          {isExpanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                        </button>
                      )}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      )}
    </div>
  );
}
