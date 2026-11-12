/**
 * ParentChildTimeline.jsx
 * Giao diện Timeline điểm danh của Con dành cho Phụ Huynh — Mobile First
 *
 * Tiêu chuẩn:
 *  - Touch target tối thiểu 44×44px
 *  - Sticky FAB "Nộp đơn xin nghỉ" ở đáy màn hình
 *  - Timeline trực quan: icon trạng thái, giờ vào, đồng phục
 *  - Modal nộp đơn xin nghỉ inline (không redirect)
 */
import React, { useState, useEffect } from 'react';
import {
  Clock, CheckCircle2, XCircle, AlertCircle, User,
  Shield, Calendar, ChevronDown, X, Loader2, CheckCheck,
  Shirt, Camera, FileText, Check, HelpCircle
} from 'lucide-react';
import { attendanceService, leaveService } from '../../services/attendanceService';

// ─── Status maps ──────────────────────────────────────────────────────────────
const STATUS = {
  ON_TIME:  { label: 'Đúng giờ',   Icon: CheckCircle2, dot: 'bg-emerald-500', ring: 'border-emerald-500/50 bg-emerald-500/10', text: 'text-emerald-400',   badge: 'bg-emerald-500/15 border-emerald-500/30 text-emerald-400' },
  LATE:     { label: 'Đi muộn',    Icon: AlertCircle,  dot: 'bg-amber-500',   ring: 'border-amber-500/50  bg-amber-500/10',   text: 'text-amber-400',     badge: 'bg-amber-500/15  border-amber-500/30  text-amber-400'   },
  ABSENT:   { label: 'Vắng mặt',   Icon: XCircle,      dot: 'bg-red-500',     ring: 'border-red-500/50    bg-red-500/10',     text: 'text-red-400',       badge: 'bg-red-500/15    border-red-500/30    text-red-400'     },
  EXCUSED:  { label: 'Có phép',    Icon: CheckCheck,   dot: 'bg-blue-500',    ring: 'border-blue-500/50   bg-blue-500/10',    text: 'text-blue-400',      badge: 'bg-blue-500/15   border-blue-500/30   text-blue-400'    },
};
const UNIFORM = {
  OK:        { label: 'Đúng đồng phục', Icon: Check,      cls: 'text-emerald-400' },
  VIOLATION: { label: 'Vi phạm ĐP',     Icon: X,          cls: 'text-rose-400' },
  UNKNOWN:   { label: 'Chưa xác định',  Icon: HelpCircle, cls: 'text-gray-400' },
};
const CHECK_TYPE = {
  FACE_AI: { label: 'AI Camera', Icon: Camera },
  QR_SCAN: { label: 'Quét QR',   Icon: Shield },
  MANUAL:  { label: 'Thủ công',  Icon: User },
};

function friendlyDate(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  const now = new Date();
  const diffD = Math.floor((now - d) / 86400000);
  const hhmm = d.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' });
  const ddmm = d.toLocaleDateString('vi-VN', { weekday: 'short', day: '2-digit', month: '2-digit' });
  if (diffD === 0) return { primary: `Hôm nay — ${hhmm}`, secondary: null };
  if (diffD === 1) return { primary: `Hôm qua — ${hhmm}`, secondary: null };
  return { primary: hhmm, secondary: ddmm };
}

// ─── Leave Request Modal ───────────────────────────────────────────────────────
function LeaveModal({ isOpen, onClose, onSubmit, children, loading }) {
  const today = new Date().toISOString().slice(0, 10);
  const [form, setForm] = useState({ student_id: '', start_date: today, end_date: today, reason: '' });

  // Nạp student_id từ prop children (danh sách con)
  useEffect(() => {
    if (children?.length > 0 && !form.student_id) {
      setForm(f => ({ ...f, student_id: String(children[0].id) }));
    }
  }, [children]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex flex-col justify-end sm:justify-center sm:items-center px-0 sm:px-4">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm cursor-pointer" onClick={onClose} />

      {/* Sheet — slides up from bottom on mobile */}
      <div className="relative w-full sm:max-w-md bg-[#1a1d27] border border-white/10 rounded-t-3xl sm:rounded-3xl shadow-2xl overflow-hidden">
        {/* Drag handle */}
        <div className="flex justify-center pt-3 pb-1 sm:hidden">
          <div className="w-10 h-1 rounded-full bg-white/20" />
        </div>

        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-white/[0.07]">
          <div className="flex items-center gap-2">
            <FileText className="w-4 h-4 text-blue-400" />
            <h3 className="text-sm font-bold text-white">Nộp Đơn Xin Nghỉ</h3>
          </div>
          <button
            onClick={onClose}
            className="w-9 h-9 flex items-center justify-center rounded-xl text-gray-400 hover:text-white hover:bg-white/5 transition cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Form */}
        <div className="px-5 py-4 space-y-4 max-h-[70vh] overflow-y-auto">
          {/* Chọn con */}
          {children?.length > 1 && (
            <div>
              <label className="text-xs font-semibold text-gray-300 mb-1.5 block">Học sinh</label>
              <select
                value={form.student_id}
                onChange={e => setForm(f => ({ ...f, student_id: e.target.value }))}
                className="w-full min-h-[48px] bg-white/5 border border-white/10 rounded-2xl px-4 text-sm text-white focus:outline-none focus:border-blue-500/60 appearance-none cursor-pointer"
              >
                {children.map(c => (
                  <option key={c.id} value={String(c.id)} className="bg-[#1a1d27]">
                    {c.full_name || c.fullName} — {c.student_code}
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Ngày bắt đầu */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-semibold text-gray-300 mb-1.5 block">Từ ngày</label>
              <input
                type="date"
                value={form.start_date}
                onChange={e => setForm(f => ({ ...f, start_date: e.target.value }))}
                className="w-full min-h-[48px] bg-white/5 border border-white/10 rounded-2xl px-3 text-sm text-white focus:outline-none focus:border-blue-500/60 cursor-pointer"
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-gray-300 mb-1.5 block">Đến ngày</label>
              <input
                type="date"
                value={form.end_date}
                onChange={e => setForm(f => ({ ...f, end_date: e.target.value }))}
                className="w-full min-h-[48px] bg-white/5 border border-white/10 rounded-2xl px-3 text-sm text-white focus:outline-none focus:border-blue-500/60 cursor-pointer"
              />
            </div>
          </div>

          {/* Lý do */}
          <div>
            <label className="text-xs font-semibold text-gray-300 mb-1.5 block">Lý do xin nghỉ</label>
            <textarea
              rows={3}
              value={form.reason}
              onChange={e => setForm(f => ({ ...f, reason: e.target.value }))}
              placeholder="Ghi rõ lý do (ốm đau, việc gia đình...)"
              className="w-full bg-white/5 border border-white/10 rounded-2xl p-3.5 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-blue-500/60 resize-none"
            />
          </div>

          {/* Submit button */}
          <div className="pt-1">
            <button
              type="button"
              disabled={loading || !form.reason.trim()}
              onClick={() => onSubmit(form)}
              className="w-full min-h-[50px] flex items-center justify-center gap-2 rounded-2xl bg-blue-600 hover:bg-blue-500 disabled:opacity-40 disabled:cursor-not-allowed text-white font-bold text-sm shadow-lg shadow-blue-600/30 transition-all cursor-pointer"
            >
              {loading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <FileText className="w-4 h-4" />
              )}
              {loading ? 'Đang gửi đơn...' : 'Gửi Đơn Xin Nghỉ'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Timeline record row ──────────────────────────────────────────────────────
function TimelineRecord({ record, isFirst, isLast }) {
  const st    = STATUS[record.status]       || STATUS.ABSENT;
  const uni   = UNIFORM[record.uniform_status] || UNIFORM.UNKNOWN;
  const chk   = CHECK_TYPE[record.check_type] || CHECK_TYPE.MANUAL;
  const ChkIcon = chk.Icon;
  const StIcon  = st.Icon;
  const time    = friendlyDate(record.timestamp);

  return (
    <div className="relative flex gap-4 group">
      {/* Left: timeline track */}
      <div className="flex flex-col items-center shrink-0" style={{ width: 44 }}>
        {/* Dot */}
        <div className={`w-10 h-10 rounded-full border-2 ${st.ring} flex items-center justify-center shrink-0 z-10 transition-transform group-hover:scale-105`}>
          <StIcon className={`w-4 h-4 ${st.text}`} />
        </div>
        {/* Connector line */}
        {!isLast && <div className="w-px flex-1 bg-white/[0.06] mt-1.5" style={{ minHeight: 24 }} />}
      </div>

      {/* Right: content */}
      <div className={`flex-1 pb-5 min-w-0 ${isFirst ? '' : ''}`}>
        {/* Status badge + time */}
        <div className="flex items-center gap-2 flex-wrap">
          <span className={`px-2.5 py-1 rounded-xl text-xs font-bold border ${st.badge}`}>
            {st.label}
          </span>
          {isFirst && (
            <span className="px-2 py-0.5 rounded-full bg-blue-500/15 border border-blue-500/30 text-blue-400 text-[10px] font-bold">
              MỚI NHẤT
            </span>
          )}
        </div>

        {/* Time */}
        <div className="mt-1.5 flex items-center gap-1.5 text-xs text-gray-300">
          <Clock className="w-3.5 h-3.5 shrink-0 text-gray-400" />
          <span className="font-medium">{typeof time === 'object' ? time.primary : time}</span>
          {typeof time === 'object' && time.secondary && (
            <span className="text-gray-400">· {time.secondary}</span>
          )}
        </div>

        {/* Details row */}
        <div className="mt-2 flex items-center gap-3 flex-wrap text-[11px]">
          {/* Uniform */}
          <div className="flex items-center gap-1.5">
            <Shirt className="w-3.5 h-3.5 text-gray-400 shrink-0" />
            <span className={`inline-flex items-center gap-1 font-medium ${uni.cls}`}>
              {uni.Icon && <uni.Icon className="w-3 h-3 shrink-0" />}
              <span>{uni.label}</span>
            </span>
          </div>
          {/* Check type */}
          <div className="flex items-center gap-1">
            <ChkIcon className="w-3.5 h-3.5 text-gray-400 shrink-0" />
            <span className="text-gray-300 font-medium">{chk.label}</span>
          </div>
          {/* Confidence */}
          {record.confidence_score > 0 && (
            <div className="flex items-center gap-1">
              <span className="text-gray-400">AI</span>
              <span className="text-gray-300 font-semibold">{Math.round(record.confidence_score * 100)}%</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────────
export function ParentChildTimeline({ currentUser }) {
  const schoolId = currentUser?.school_id || currentUser?.schoolId;

  const [children, setChildren]       = useState([]);
  const [activeChild, setActiveChild] = useState(null);
  const [history, setHistory]         = useState([]);
  const [loading, setLoading]         = useState(false);
  const [showModal, setShowModal]     = useState(false);
  const [submitting, setSubmitting]   = useState(false);
  const [submitOk, setSubmitOk]       = useState(false);
  const [submitErr, setSubmitErr]     = useState('');

  // Fetch danh sách con (fallback: dùng student_id từ profile nếu không có API)
  useEffect(() => {
    if (!schoolId) return;
    // Phụ huynh có thể có nhiều con — thử API, fallback về empty
    fetch(`/api/v1/s/${schoolId}/students/my-children`, {
      headers: { Authorization: `Bearer ${localStorage.getItem('stem_auth_token')}` }
    })
      .then(r => r.ok ? r.json() : null)
      .then(data => {
        if (Array.isArray(data?.data) && data.data.length > 0) {
          setChildren(data.data);
          setActiveChild(data.data[0]);
        } else if (currentUser?.linked_student_id) {
          // Fallback: nếu profile có linked_student_id
          const stub = { id: currentUser.linked_student_id, full_name: 'Con của bạn', student_code: '—' };
          setChildren([stub]);
          setActiveChild(stub);
        }
      })
      .catch(() => {
        if (currentUser?.linked_student_id) {
          const stub = { id: currentUser.linked_student_id, full_name: 'Con của bạn', student_code: '—' };
          setChildren([stub]);
          setActiveChild(stub);
        }
      });
  }, [schoolId, currentUser]);

  // Fetch history khi đổi con
  useEffect(() => {
    if (!schoolId || !activeChild?.id) return;
    setLoading(true);
    attendanceService.getStudentHistory(schoolId, activeChild.id, 20)
      .then(rows => setHistory(Array.isArray(rows) ? rows : []))
      .catch(() => setHistory([]))
      .finally(() => setLoading(false));
  }, [schoolId, activeChild]);

  const handleSubmitLeave = async (form) => {
    setSubmitting(true);
    setSubmitErr('');
    try {
      await leaveService.create(schoolId, form);
      setSubmitOk(true);
      setShowModal(false);
      setTimeout(() => setSubmitOk(false), 3000);
    } catch (err) {
      setSubmitErr(err?.message || 'Không thể gửi đơn. Vui lòng thử lại.');
    } finally {
      setSubmitting(false);
    }
  };

  const todayRecord = history[0];
  const hasTodayRecord = todayRecord && new Date(todayRecord.timestamp).toDateString() === new Date().toDateString();

  return (
    <div className="pb-32 space-y-4">

      {/* ── Today summary card ─────────────────────────────────── */}
      {activeChild && (
        <div className={`rounded-3xl p-5 space-y-3 border ${
          hasTodayRecord
            ? todayRecord.status === 'ON_TIME' ? 'bg-emerald-500/5 border-emerald-500/20'
            : todayRecord.status === 'LATE'    ? 'bg-amber-500/5  border-amber-500/20'
            : 'bg-red-500/5 border-red-500/20'
            : 'bg-white/[0.03] border-white/[0.08]'
        }`}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-11 h-11 rounded-full bg-gradient-to-br from-sky-500 to-blue-600 flex items-center justify-center text-white text-sm font-extrabold shrink-0">
                {(activeChild.full_name || 'C').split(' ').pop()[0]?.toUpperCase() || 'C'}
              </div>
              <div>
                <h3 className="text-sm font-bold text-white">{activeChild.full_name || 'Con của bạn'}</h3>
                <p className="text-[11px] text-gray-500 font-mono">{activeChild.student_code}</p>
              </div>
            </div>
            {/* Child switcher nếu nhiều con */}
            {children.length > 1 && (
              <select
                value={activeChild.id}
                onChange={e => setActiveChild(children.find(c => c.id === Number(e.target.value)))}
                className="min-h-[44px] bg-white/10 border border-white/10 rounded-xl px-3 text-xs text-white focus:outline-none [color-scheme:dark]"
              >
                {children.map(c => (
                  <option key={c.id} value={c.id} className="bg-[#1a1d27]">{c.full_name}</option>
                ))}
              </select>
            )}
          </div>

          {/* Today status */}
          {hasTodayRecord ? (() => {
            const st = STATUS[todayRecord.status] || STATUS.ABSENT;
            const StIcon = st.Icon;
            const uni = UNIFORM[todayRecord.uniform_status] || UNIFORM.UNKNOWN;
            return (
              <div className="space-y-2">
                <div className="flex items-center gap-2 flex-wrap">
                  <StIcon className={`w-5 h-5 ${st.text}`} />
                  <span className="text-sm font-bold text-white">Hôm nay: {st.label}</span>
                  <span className={`text-[11px] font-medium inline-flex items-center gap-1 ${uni.cls}`}>
                    {uni.Icon && <uni.Icon className="w-3 h-3 shrink-0" />}
                    <span>{uni.label}</span>
                  </span>
                </div>
                <p className="text-xs text-gray-400 flex items-center gap-1">
                  <Clock className="w-3.5 h-3.5 text-gray-500" />
                  Vào trường lúc&nbsp;
                  <span className="font-bold text-white">
                    {new Date(todayRecord.timestamp).toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' })}
                  </span>
                </p>
              </div>
            );
          })() : (
            <p className="text-xs text-gray-400 flex items-center gap-1.5">
              <Calendar className="w-3.5 h-3.5 text-gray-400" />
              Chưa có dữ liệu điểm danh hôm nay
            </p>
          )}
        </div>
      )}

      {/* Success toast */}
      {submitOk && (
        <div className="flex items-center gap-3 px-4 py-3 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-sm font-semibold">
          <CheckCircle2 className="w-5 h-5 shrink-0" />
          Đã gửi đơn xin nghỉ thành công! Giáo viên sẽ xem xét sớm.
        </div>
      )}
      {submitErr && (
        <div className="flex items-center gap-3 px-4 py-3 rounded-2xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
          <AlertCircle className="w-4 h-4 shrink-0" />
          {submitErr}
        </div>
      )}

      {/* ── Timeline ────────────────────────────────────────────── */}
      <div className="bg-white/[0.03] border border-white/[0.08] rounded-3xl overflow-hidden">
        <div className="px-5 py-4 border-b border-white/[0.06] flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Calendar className="w-4 h-4 text-blue-400" />
            <h4 className="text-sm font-bold text-white">Nhật Ký Điểm Danh</h4>
          </div>
          <span className="text-[11px] text-gray-400 font-medium">{history.length} lần</span>
        </div>

        <div className="px-5 pt-5 pb-4">
          {loading ? (
            <div className="space-y-4 animate-pulse">
              {[1,2,3].map(i => (
                <div key={i} className="flex gap-4">
                  <div className="w-10 h-10 rounded-full bg-white/5 shrink-0" />
                  <div className="flex-1 space-y-2 pt-1">
                    <div className="h-3 w-20 bg-white/5 rounded-full" />
                    <div className="h-2.5 w-32 bg-white/5 rounded-full" />
                    <div className="h-2.5 w-48 bg-white/5 rounded-full" />
                  </div>
                </div>
              ))}
            </div>
          ) : !activeChild ? (
            <div className="py-10 text-center space-y-2">
              <User className="w-8 h-8 text-gray-600 mx-auto" />
              <p className="text-xs text-gray-300">Chưa liên kết thông tin học sinh</p>
              <p className="text-[11px] text-gray-400">Liên hệ nhà trường để được hỗ trợ liên kết tài khoản phụ huynh</p>
            </div>
          ) : history.length === 0 ? (
            <div className="py-10 text-center space-y-2">
              <Calendar className="w-8 h-8 text-gray-600 mx-auto" />
              <p className="text-xs text-gray-300">Chưa có dữ liệu điểm danh</p>
            </div>
          ) : (
            history.map((r, i) => (
              <TimelineRecord
                key={r.id || i}
                record={r}
                isFirst={i === 0}
                isLast={i === history.length - 1}
              />
            ))
          )}
        </div>
      </div>

      {/* ── Floating Action Button — Sticky ở đáy ──────────────── */}
      <div className="fixed bottom-0 left-0 right-0 z-30 px-4 pb-safe pb-6 pointer-events-none">
        {/* Gradient fade để FAB không che content */}
        <div className="absolute inset-x-0 bottom-0 h-28 bg-gradient-to-t from-[#0a0c14] to-transparent pointer-events-none" />
        <div className="relative pointer-events-auto max-w-2xl mx-auto">
          <button
            onClick={() => setShowModal(true)}
            className="w-full min-h-[56px] flex items-center justify-center gap-2.5 rounded-2xl bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-bold text-sm shadow-2xl shadow-blue-600/40 transition-all duration-150 active:scale-[0.97] cursor-pointer"
          >
            <FileText className="w-5 h-5" />
            Nộp Đơn Xin Nghỉ Cho Con
          </button>
        </div>
      </div>

      {/* Leave Modal */}
      <LeaveModal
        isOpen={showModal}
        onClose={() => { setShowModal(false); setSubmitErr(''); }}
        onSubmit={handleSubmitLeave}
        children={children}
        loading={submitting}
      />
    </div>
  );
}
