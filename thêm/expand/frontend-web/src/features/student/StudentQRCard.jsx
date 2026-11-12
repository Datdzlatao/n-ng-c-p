/**
 * StudentQRCard.jsx
 * Thẻ QR điểm danh cá nhân của Học Sinh — Mobile First, Touch-optimised
 *
 * Tiêu chuẩn:
 *  - Touch target tối thiểu 44×44 px cho mọi button
 *  - QR code 240×240 px (to rõ ràng cho máy quét camera)
 *  - Viền trắng tương phản cao cho camera scanner
 *  - Nút "Lưu ảnh QR" dùng canvas export (offline-safe)
 */
import React, { useRef, useState, useEffect, useCallback } from 'react';
import { QRCodeCanvas } from 'qrcode.react';
import {
  Download, RefreshCw, ShieldCheck, User, School,
  Clock, CheckCircle2, XCircle, AlertCircle, Loader2
} from 'lucide-react';
import { attendanceService } from '../../services/attendanceService';

// ── Status badge ───────────────────────────────────────────────────────────────
const STATUS_MAP = {
  ON_TIME: { label: 'Đúng giờ',  cls: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30', Icon: CheckCircle2 },
  LATE:    { label: 'Đi muộn',   cls: 'bg-amber-500/15  text-amber-400  border-amber-500/30',   Icon: AlertCircle },
  ABSENT:  { label: 'Vắng mặt', cls: 'bg-red-500/15    text-red-400    border-red-500/30',     Icon: XCircle },
};
const UNIFORM_MAP = {
  OK:       { label: 'Đúng đồng phục', cls: 'text-emerald-400' },
  VIOLATION:{ label: 'Vi phạm ĐP',     cls: 'text-red-400' },
  UNKNOWN:  { label: 'Chưa xác định',  cls: 'text-gray-400' },
};

function friendlyTime(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  const now = new Date();
  const diffD = Math.floor((now - d) / 86400000);
  const hhmm = d.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' });
  if (diffD === 0) return `Hôm nay ${hhmm}`;
  if (diffD === 1) return `Hôm qua ${hhmm}`;
  return d.toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit' }) + ` ${hhmm}`;
}

// ── QR Canvas ref ──────────────────────────────────────────────────────────────
function useQRDownload(canvasRef, studentCode) {
  const [saving, setSaving] = useState(false);
  const [saved, setSaved]   = useState(false);

  const save = useCallback(async () => {
    setSaving(true);
    try {
      // Tìm canvas trong wrapper
      const canvas = canvasRef.current?.querySelector('canvas');
      if (!canvas) return;

      // Tạo canvas mới có viền trắng + tên học sinh
      const padding = 24;
      const footerH = 48;
      const src = canvas;
      const out = document.createElement('canvas');
      out.width  = src.width  + padding * 2;
      out.height = src.height + padding * 2 + footerH;
      const ctx = out.getContext('2d');

      // Nền trắng
      ctx.fillStyle = '#ffffff';
      ctx.fillRect(0, 0, out.width, out.height);

      // QR
      ctx.drawImage(src, padding, padding);

      // Footer text
      ctx.fillStyle = '#111827';
      ctx.font = 'bold 14px sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText(`Mã HS: ${studentCode}`, out.width / 2, src.height + padding + 22);
      ctx.font = '11px sans-serif';
      ctx.fillStyle = '#6b7280';
      ctx.fillText('EduSAMS — School Attendance Platform', out.width / 2, src.height + padding + 40);

      // Tải về
      const link = document.createElement('a');
      link.download = `qr-${studentCode}.png`;
      link.href = out.toDataURL('image/png');
      link.click();
      setSaved(true);
      setTimeout(() => setSaved(false), 2500);
    } finally {
      setSaving(false);
    }
  }, [canvasRef, studentCode]);

  return { save, saving, saved };
}

// ── Mini Timeline row ──────────────────────────────────────────────────────────
function TimelineRow({ record, isFirst }) {
  const st = STATUS_MAP[record.status] || STATUS_MAP.ABSENT;
  const uni = UNIFORM_MAP[record.uniform_status] || UNIFORM_MAP.UNKNOWN;
  const StIcon = st.Icon;

  return (
    <div className="relative flex gap-4">
      {/* Timeline line */}
      <div className="flex flex-col items-center shrink-0">
        <div className={`w-9 h-9 rounded-full border-2 ${isFirst ? 'border-blue-500 bg-blue-500/20' : 'border-white/10 bg-white/5'} flex items-center justify-center`}>
          <StIcon className={`w-4 h-4 ${isFirst ? 'text-blue-400' : 'text-gray-400'}`} />
        </div>
        {!isFirst && <div className="w-px flex-1 bg-white/5 mt-1" />}
      </div>

      {/* Content */}
      <div className="flex-1 pb-4 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className={`px-2 py-0.5 rounded-full text-[11px] font-bold border ${st.cls}`}>
            {st.label}
          </span>
          <span className={`text-[11px] font-medium ${uni.cls}`}>
            · {uni.label}
          </span>
        </div>
        <p className="text-xs text-gray-300 mt-1 flex items-center gap-1">
          <Clock className="w-3 h-3 shrink-0 text-gray-400" />
          {friendlyTime(record.timestamp)}
          {record.check_type && (
            <span className="ml-2 px-1.5 py-0.5 rounded bg-white/5 text-[10px] text-gray-400 font-mono">
              {record.check_type.replace('_', ' ')}
            </span>
          )}
        </p>
      </div>
    </div>
  );
}

// ── Main Component ─────────────────────────────────────────────────────────────
export function StudentQRCard({ currentUser }) {
  const schoolId   = currentUser?.school_id || currentUser?.schoolId;
  const qrToken    = currentUser?.qr_token  || currentUser?.memberCode || `STU-${currentUser?.id}`;
  const studentCode = currentUser?.student_code || currentUser?.memberCode || currentUser?.user_code || `#${currentUser?.id}`;
  const fullName   = currentUser?.fullName || currentUser?.full_name || currentUser?.username || '';

  const [history, setHistory]   = useState([]);
  const [loading, setLoading]   = useState(false);
  const [studentId, setStudentId] = useState(null);
  const qrWrapRef = useRef(null);
  const { save, saving, saved } = useQRDownload(qrWrapRef, studentCode);

  // Fetch student_id + history
  useEffect(() => {
    if (!schoolId || !currentUser?.id) return;

    // Lấy student_id từ user.id bằng cách gọi API attendance với user_id
    // Ta dùng user_code để tìm student record
    const fetchHistory = async () => {
      setLoading(true);
      try {
        // Thử dùng student_id = user_id (thông thường 1:1)
        const sid = currentUser?.student_id || currentUser?.id;
        setStudentId(sid);
        const rows = await attendanceService.getStudentHistory(schoolId, sid, 20);
        if (Array.isArray(rows)) setHistory(rows);
      } catch {
        setHistory([]);
      } finally {
        setLoading(false);
      }
    };
    fetchHistory();
  }, [schoolId, currentUser?.id]);

  // Chuỗi QR = token hoặc mã học sinh
  const qrValue = qrToken && qrToken !== `STU-${currentUser?.id}`
    ? qrToken
    : `EDUSAMS:${schoolId}:${studentCode}`;

  const todayRecord = history[0];

  return (
    <div className="space-y-5 pb-6">
      {/* ── QR Card ───────────────────────────────────────────── */}
      <div className="bg-white/[0.03] border border-white/[0.08] rounded-3xl overflow-hidden">
        {/* Header gradient strip */}
        <div className="bg-gradient-to-r from-blue-600/30 via-indigo-600/20 to-purple-600/30 px-5 pt-5 pb-6 text-center relative overflow-hidden">
          <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,rgba(99,102,241,0.15),transparent_70%)] pointer-events-none" />
          {/* Avatar + name */}
          <div className="relative flex flex-col items-center gap-2 mb-5">
            <div className="w-14 h-14 rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center text-white text-xl font-extrabold shadow-lg shadow-blue-500/30">
              {fullName.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2) || 'HS'}
            </div>
            <div>
              <h3 className="text-base font-bold text-white">{fullName}</h3>
              <div className="flex items-center justify-center gap-1.5 mt-1">
                <span className="px-2.5 py-0.5 rounded-full bg-blue-500/20 border border-blue-500/30 text-blue-400 text-[11px] font-bold">
                  Học Sinh
                </span>
                <span className="text-[11px] text-gray-300 font-mono font-medium">{studentCode}</span>
              </div>
            </div>
          </div>

          {/* QR Code — white background for camera contrast */}
          <div
            ref={qrWrapRef}
            className="inline-block p-4 bg-white rounded-2xl shadow-2xl shadow-black/40 mx-auto"
            style={{ touchAction: 'none' }}
          >
            <QRCodeCanvas
              value={qrValue}
              size={220}
              level="H"
              includeMargin={false}
              bgColor="#ffffff"
              fgColor="#0f172a"
            />
          </div>

          <p className="mt-3 text-xs text-gray-300">
            Đưa mã này cho camera tại cổng trường để điểm danh
          </p>
        </div>

        {/* Today status strip */}
        {todayRecord && (
          <div className={`px-5 py-3 flex items-center gap-3 border-b border-white/[0.06] ${
            todayRecord.status === 'ON_TIME' ? 'bg-emerald-500/5' :
            todayRecord.status === 'LATE'    ? 'bg-amber-500/5'   : 'bg-red-500/5'
          }`}>
            {(() => { const S = STATUS_MAP[todayRecord.status] || STATUS_MAP.ABSENT; const I = S.Icon; return <I className={`w-5 h-5 ${S.cls.split(' ').find(c=>c.startsWith('text-'))}`} />; })()}
            <div className="flex-1 min-w-0">
              <p className="text-xs font-semibold text-white">
                Hôm nay: {(STATUS_MAP[todayRecord.status] || STATUS_MAP.ABSENT).label}
              </p>
              <p className="text-xs text-gray-300 flex items-center gap-1">
                <Clock className="w-3 h-3 text-gray-400" />
                {friendlyTime(todayRecord.timestamp)}
              </p>
            </div>
            <ShieldCheck className="w-4 h-4 text-gray-500 shrink-0" />
          </div>
        )}

        {/* Actions */}
        <div className="p-4 flex gap-3">
          {/* Lưu ảnh QR — min-h 44px */}
          <button
            onClick={save}
            disabled={saving}
            className="flex-1 min-h-[48px] flex items-center justify-center gap-2 rounded-2xl bg-blue-600 hover:bg-blue-500 disabled:opacity-60 text-white text-sm font-bold shadow-md shadow-blue-500/25 transition-all duration-150 active:scale-95 cursor-pointer"
          >
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : saved ? <CheckCircle2 className="w-4 h-4" /> : <Download className="w-4 h-4" />}
            {saving ? 'Đang lưu...' : saved ? 'Đã lưu!' : 'Lưu ảnh QR'}
          </button>

          {/* Làm mới */}
          <button
            onClick={() => window.location.reload()}
            className="min-w-[48px] min-h-[48px] flex items-center justify-center rounded-2xl bg-white/5 hover:bg-white/10 text-gray-400 hover:text-white transition-all duration-150 active:scale-95 cursor-pointer"
            title="Làm mới"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* ── Attendance History ─────────────────────────────────── */}
      <div className="bg-white/[0.03] border border-white/[0.08] rounded-3xl overflow-hidden">
        <div className="px-5 py-4 border-b border-white/[0.06] flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Clock className="w-4 h-4 text-blue-400" />
            <h4 className="text-sm font-bold text-white">Lịch Sử Điểm Danh</h4>
          </div>
          <span className="text-xs text-gray-300 font-medium">{history.length} lần gần nhất</span>
        </div>

        <div className="px-5 py-4">
          {loading ? (
            <div className="space-y-3">
              {[1,2,3].map(i => (
                <div key={i} className="flex gap-4 animate-pulse">
                  <div className="w-9 h-9 rounded-full bg-white/5 shrink-0" />
                  <div className="flex-1 space-y-2 pt-1">
                    <div className="h-3 w-24 bg-white/5 rounded-full" />
                    <div className="h-2.5 w-32 bg-white/5 rounded-full" />
                  </div>
                </div>
              ))}
            </div>
          ) : history.length === 0 ? (
            <div className="py-8 text-center space-y-2">
              <User className="w-8 h-8 text-gray-600 mx-auto" />
              <p className="text-xs text-gray-300">Chưa có dữ liệu điểm danh</p>
            </div>
          ) : (
            <div className="space-y-0">
              {history.map((r, i) => (
                <TimelineRow key={r.id || i} record={r} isFirst={i === 0} />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
