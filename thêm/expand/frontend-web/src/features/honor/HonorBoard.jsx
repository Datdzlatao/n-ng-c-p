/**
 * src/features/honor/HonorBoard.jsx
 * Bảng Vinh Danh Học Đường & Hệ Thống Chuỗi Lửa Chuyên Cần (Streak Flames)
 */
import React, { useState, useEffect } from 'react';
import {
  Award, Flame, Trophy, Crown, Sparkles, TrendingUp,
  Users, ShieldCheck, Star, ChevronRight, Loader2, ArrowUpRight
} from 'lucide-react';
import { honorService } from '../../services/honorService';
import { FlameStreakBadge, getFlameTierFromDays } from '../../components/common/FlameStreakBadge';

function getInitials(name = '') {
  return name.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2) || '?';
}

export function HonorBoard({ currentUser }) {
  const schoolId = currentUser?.school_id || currentUser?.schoolId;
  const [loading, setLoading] = useState(true);
  const [honorData, setHonorData] = useState(null);
  const [activeTab, setActiveTab] = useState('streaks'); // 'streaks' | 'points' | 'classes'

  const fetchHonorData = async () => {
    if (!schoolId) return;
    setLoading(true);
    try {
      const res = await honorService.getHonorBoard(schoolId);
      if (res?.status === 'success' && res.data) {
        setHonorData(res.data);
      }
    } catch (err) {
      console.error('Failed to load honor board:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHonorData();
  }, [schoolId]);

  if (loading) {
    return (
      <div className="py-20 text-center space-y-3">
        <Loader2 className="w-8 h-8 animate-spin text-amber-400 mx-auto" />
        <p className="text-sm text-gray-400">Đang đồng bộ dữ liệu Bảng Vinh Danh &amp; Chuỗi Lửa...</p>
      </div>
    );
  }

  const myStreak = honorData?.my_streak;
  const streakLeaders = honorData?.streak_leaders || [];
  const pointsLeaders = honorData?.points_leaders || [];
  const classRankings = honorData?.class_rankings || [];

  // Top 3 Podium
  const top1 = streakLeaders[0];
  const top2 = streakLeaders[1];
  const top3 = streakLeaders[2];

  // Tính tiến trình nâng cấp ngọn lửa
  const curDays = myStreak?.current_streak || 0;
  const flameTier = getFlameTierFromDays(curDays);
  let nextTarget = 3;
  let targetName = 'Lửa Xanh Lá (3 ngày)';
  if (curDays >= 30) {
    nextTarget = 30;
    targetName = 'Đã đạt Cấp Tối Thượng 🟣';
  } else if (curDays >= 14) {
    nextTarget = 30;
    targetName = 'Lửa Tím Tối Thượng (30 ngày)';
  } else if (curDays >= 7) {
    nextTarget = 14;
    targetName = 'Lửa Đỏ Rực (14 ngày)';
  } else if (curDays >= 3) {
    nextTarget = 7;
    targetName = 'Lửa Cam Nhiệt Huyết (7 ngày)';
  }
  const progressPercent = Math.min(100, Math.round((curDays / nextTarget) * 100));

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      {/* ── 1. MY STREAK SHOWCASE BANNER (Dành cho Học Sinh) ── */}
      {myStreak && (
        <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-[#1b1528] via-[#161826] to-[#121929] border border-white/[0.09] p-5 sm:p-7 shadow-2xl">
          {/* Radial ambient glow */}
          <div className="absolute top-0 right-1/4 w-72 h-72 bg-amber-500/10 rounded-full blur-3xl pointer-events-none" />

          <div className="relative flex flex-col md:flex-row items-center justify-between gap-6">
            <div className="flex items-center gap-5 w-full md:w-auto">
              {/* Giant Flame Avatar */}
              <div className="relative flex items-center justify-center shrink-0">
                <div className="w-16 h-16 sm:w-20 sm:h-20 rounded-2xl bg-gradient-to-br from-white/5 to-white/10 border border-white/15 flex items-center justify-center shadow-inner">
                  <Flame className="w-10 h-10 sm:w-12 sm:h-12 text-amber-400 fill-amber-400 drop-shadow-[0_0_12px_rgba(245,158,11,0.8)] animate-pulse" />
                </div>
                <span className="absolute -bottom-2 -right-1 text-xs">
                  {myStreak.flame?.badge_icon || '🔥'}
                </span>
              </div>

              {/* Text info */}
              <div className="space-y-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-xs text-gray-400 font-medium">Chuỗi Lửa Của Bạn</span>
                  <span className={`px-2 py-0.5 rounded-full text-[10px] font-extrabold border ${flameTier.cls}`}>
                    {myStreak.flame?.tier_name || 'Khởi Động'}
                  </span>
                </div>
                <h3 className="text-xl sm:text-2xl font-black text-white flex items-center gap-2">
                  <span>{curDays} Ngày Đúng Giờ Liên Tiếp</span>
                </h3>
                <p className="text-xs text-gray-300">
                  {myStreak.full_name} · Lớp {myStreak.class_name} · Điểm nề nếp: <strong className="text-emerald-400">{myStreak.current_points}đ</strong>
                </p>
              </div>
            </div>

            {/* Progress to Next Flame Tier */}
            <div className="w-full md:w-72 bg-black/30 border border-white/[0.08] rounded-2xl p-4 space-y-2 shrink-0">
              <div className="flex items-center justify-between text-xs">
                <span className="text-gray-400 text-[11px]">Mục tiêu tiếp theo:</span>
                <span className="font-bold text-amber-300 text-[11px]">{targetName}</span>
              </div>
              <div className="w-full h-2 bg-white/10 rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-amber-500 to-rose-500 rounded-full transition-all duration-500 shadow-[0_0_8px_rgba(245,158,11,0.5)]"
                  style={{ width: `${progressPercent}%` }}
                />
              </div>
              <p className="text-[11px] text-gray-400 text-right">
                {curDays >= 30
                  ? '🌟 Bạn đã chạm đỉnh bảng vàng vinh quang!'
                  : `Còn ${nextTarget - curDays} ngày nữa để thăng cấp ngọn lửa`}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* ── 2. PODIUM TOP 3 SHOWCASE ── */}
      {streakLeaders.length >= 3 && (
        <div className="pt-4 pb-2">
          <div className="text-center space-y-1 mb-6">
            <span className="px-3 py-1 rounded-full text-[11px] font-extrabold bg-amber-500/10 border border-amber-500/20 text-amber-400 inline-flex items-center gap-1.5">
              <Crown className="w-3.5 h-3.5" /> Bục Vinh Danh Toàn Trường
            </span>
            <h2 className="text-xl sm:text-2xl font-black text-white">Top Chiến Thần Chuỗi Lửa</h2>
          </div>

          <div className="grid grid-cols-3 gap-2 sm:gap-4 items-end max-w-lg mx-auto">
            {/* Top 2: Bạc */}
            {top2 && (
              <div className="bg-white/[0.03] border border-white/[0.08] rounded-2xl p-3 sm:p-4 text-center space-y-2 h-44 sm:h-52 flex flex-col justify-end">
                <div className="w-10 h-10 sm:w-12 sm:h-12 rounded-full bg-gradient-to-br from-slate-300 to-gray-500 flex items-center justify-center mx-auto text-white font-black text-xs sm:text-sm shadow-lg shadow-gray-500/30">
                  {getInitials(top2.full_name)}
                </div>
                <div>
                  <span className="text-[10px] font-bold text-gray-400">🥈 HẠNG 2</span>
                  <h4 className="text-xs sm:text-sm font-bold text-white truncate">{top2.full_name}</h4>
                  <p className="text-[10px] text-gray-400">Lớp {top2.class_name}</p>
                </div>
                <div className="pt-1">
                  <FlameStreakBadge streak={top2.streak} size="sm" />
                </div>
              </div>
            )}

            {/* Top 1: Vàng (Cao nhất) */}
            {top1 && (
              <div className="relative bg-gradient-to-b from-amber-500/15 via-white/[0.04] to-white/[0.02] border border-amber-500/30 rounded-2xl p-3 sm:p-4 text-center space-y-2 h-52 sm:h-64 flex flex-col justify-end shadow-xl shadow-amber-500/10">
                <Crown className="w-6 h-6 sm:w-7 sm:h-7 text-amber-400 mx-auto -mt-3 animate-bounce" />
                <div className="w-12 h-12 sm:w-14 sm:h-14 rounded-full bg-gradient-to-br from-amber-400 to-yellow-600 flex items-center justify-center mx-auto text-slate-950 font-black text-sm sm:text-base shadow-xl shadow-amber-500/40">
                  {getInitials(top1.full_name)}
                </div>
                <div>
                  <span className="text-[11px] font-extrabold text-amber-400">👑 QUÁN QUÂN</span>
                  <h4 className="text-xs sm:text-base font-extrabold text-white truncate">{top1.full_name}</h4>
                  <p className="text-[10px] sm:text-xs text-gray-300">Lớp {top1.class_name}</p>
                </div>
                <div className="pt-1">
                  <FlameStreakBadge streak={top1.streak} size="md" />
                </div>
              </div>
            )}

            {/* Top 3: Đồng */}
            {top3 && (
              <div className="bg-white/[0.03] border border-white/[0.08] rounded-2xl p-3 sm:p-4 text-center space-y-2 h-40 sm:h-48 flex flex-col justify-end">
                <div className="w-10 h-10 sm:w-12 sm:h-12 rounded-full bg-gradient-to-br from-amber-700 to-yellow-900 flex items-center justify-center mx-auto text-white font-black text-xs sm:text-sm shadow-lg shadow-amber-900/30">
                  {getInitials(top3.full_name)}
                </div>
                <div>
                  <span className="text-[10px] font-bold text-amber-600">🥉 HẠNG 3</span>
                  <h4 className="text-xs sm:text-sm font-bold text-white truncate">{top3.full_name}</h4>
                  <p className="text-[10px] text-gray-400">Lớp {top3.class_name}</p>
                </div>
                <div className="pt-1">
                  <FlameStreakBadge streak={top3.streak} size="sm" />
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── 3. TABS LEADERBOARDS ── */}
      <div className="space-y-4 pt-2">
        <div className="flex border-b border-white/[0.08] gap-2 sm:gap-4 overflow-x-auto pb-1 scrollbar-none">
          <button
            onClick={() => setActiveTab('streaks')}
            className={`flex items-center gap-2 px-4 py-2 text-xs sm:text-sm font-semibold border-b-2 transition-all cursor-pointer whitespace-nowrap ${
              activeTab === 'streaks'
                ? 'border-amber-500 text-amber-400'
                : 'border-transparent text-gray-400 hover:text-gray-200'
            }`}
          >
            <Flame className="w-4 h-4" />
            <span>Chuỗi Lửa Chuyên Cần</span>
          </button>

          <button
            onClick={() => setActiveTab('points')}
            className={`flex items-center gap-2 px-4 py-2 text-xs sm:text-sm font-semibold border-b-2 transition-all cursor-pointer whitespace-nowrap ${
              activeTab === 'points'
                ? 'border-emerald-500 text-emerald-400'
                : 'border-transparent text-gray-400 hover:text-gray-200'
            }`}
          >
            <Star className="w-4 h-4" />
            <span>Gương Mẫu 100 Điểm</span>
          </button>

          <button
            onClick={() => setActiveTab('classes')}
            className={`flex items-center gap-2 px-4 py-2 text-xs sm:text-sm font-semibold border-b-2 transition-all cursor-pointer whitespace-nowrap ${
              activeTab === 'classes'
                ? 'border-blue-500 text-blue-400'
                : 'border-transparent text-gray-400 hover:text-gray-200'
            }`}
          >
            <Award className="w-4 h-4" />
            <span>Thi Đua Tập Thể Lớp</span>
          </button>
        </div>

        {/* Tab 1: Streaks Leaderboard */}
        {activeTab === 'streaks' && (
          <div className="space-y-4">
            {/* Rule Explainer & Flame Progression Card */}
            <div className="bg-gradient-to-r from-amber-500/10 via-rose-500/10 to-indigo-500/10 border border-amber-500/20 rounded-2xl p-4 sm:p-5 space-y-3">
              <div className="flex items-start gap-3">
                <div className="p-2 rounded-xl bg-amber-500/20 text-amber-400 shrink-0 mt-0.5">
                  <ShieldCheck className="w-5 h-5" />
                </div>
                <div className="space-y-1 text-xs">
                  <h4 className="text-white font-bold text-sm flex items-center gap-1.5">
                    <span>Quy Tắc Chuỗi Lửa: Yêu Cầu 1 Ngày Học Trọn Vẹn Hợp Lệ</span>
                    <Sparkles className="w-3.5 h-3.5 text-amber-400" />
                  </h4>
                  <p className="text-gray-300 leading-relaxed">
                    Ngọn lửa chỉ được thắp thêm khi bạn hoàn thành <strong>nguyên cả 1 ngày trọn vẹn hợp lệ</strong>: Đến trường đúng giờ (ON_TIME), tác phong đồng phục chuẩn chỉ (OK) và tham dự đầy đủ mọi tiết học.
                  </p>
                  <p className="text-rose-300 font-medium">
                    ⚠️ Nếu trong ngày có bất kỳ vi phạm nào (đi muộn, sai đồng phục, vắng tiết không phép), ngọn lửa ngày đó sẽ bị dập tắt và chuỗi sẽ tính lại từ đầu.
                  </p>
                </div>
              </div>
            </div>

            <div className="bg-white/[0.02] border border-white/[0.07] rounded-2xl overflow-hidden divide-y divide-white/[0.05]">
              {streakLeaders.map((s, idx) => (
              <div
                key={s.student_id || idx}
                className="p-3.5 sm:p-4 flex items-center justify-between gap-3 hover:bg-white/[0.02] transition"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <span className={`w-6 text-center font-extrabold text-sm ${
                    idx === 0 ? 'text-amber-400' : idx === 1 ? 'text-slate-300' : idx === 2 ? 'text-amber-600' : 'text-gray-500'
                  }`}>
                    #{idx + 1}
                  </span>
                  <div className="w-9 h-9 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white font-bold text-xs shrink-0">
                    {getInitials(s.full_name)}
                  </div>
                  <div className="min-w-0">
                    <h4 className="text-xs sm:text-sm font-bold text-white truncate">{s.full_name}</h4>
                    <p className="text-[11px] text-gray-400">
                      Mã: <span className="font-mono text-gray-300">{s.student_code}</span> · Lớp {s.class_name}
                    </p>
                  </div>
                </div>

                <div className="shrink-0 flex items-center gap-2">
                  <FlameStreakBadge streak={s.streak} size="sm" />
                </div>
              </div>
            ))}

            {streakLeaders.length === 0 && (
              <p className="text-center text-xs text-gray-400 py-8">Chưa có dữ liệu chuỗi ngày.</p>
            )}
          </div>
        </div>
      )}

        {/* Tab 2: Points Leaderboard */}
        {activeTab === 'points' && (
          <div className="bg-white/[0.02] border border-white/[0.07] rounded-2xl overflow-hidden divide-y divide-white/[0.05]">
            {pointsLeaders.map((s, idx) => (
              <div
                key={s.student_id || idx}
                className="p-3.5 sm:p-4 flex items-center justify-between gap-3 hover:bg-white/[0.02] transition"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <span className="w-6 text-center font-extrabold text-sm text-gray-400">
                    #{idx + 1}
                  </span>
                  <div className="w-9 h-9 rounded-full bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center text-white font-bold text-xs shrink-0">
                    {getInitials(s.full_name)}
                  </div>
                  <div className="min-w-0">
                    <h4 className="text-xs sm:text-sm font-bold text-white truncate">{s.full_name}</h4>
                    <p className="text-[11px] text-gray-400">
                      Mã: <span className="font-mono text-gray-300">{s.student_code}</span> · Lớp {s.class_name}
                    </p>
                  </div>
                </div>

                <span className="px-3 py-1 rounded-full text-xs font-extrabold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                  ⭐ {s.current_points} Điểm
                </span>
              </div>
            ))}
          </div>
        )}

        {/* Tab 3: Class Rankings */}
        {activeTab === 'classes' && (
          <div className="bg-white/[0.02] border border-white/[0.07] rounded-2xl overflow-hidden divide-y divide-white/[0.05]">
            {classRankings.map((c) => (
              <div
                key={c.class_id}
                className="p-3.5 sm:p-4 flex items-center justify-between gap-3 hover:bg-white/[0.02] transition"
              >
                <div className="flex items-center gap-3.5 min-w-0">
                  <span className={`w-7 text-center font-black text-sm sm:text-base ${
                    c.rank === 1 ? 'text-amber-400' : c.rank === 2 ? 'text-slate-300' : c.rank === 3 ? 'text-amber-600' : 'text-gray-500'
                  }`}>
                    {c.rank === 1 ? '🥇' : c.rank === 2 ? '🥈' : c.rank === 3 ? '🥉' : `#${c.rank}`}
                  </span>
                  <div>
                    <h4 className="text-sm sm:text-base font-bold text-white flex items-center gap-2">
                      <span>Lớp {c.class_name}</span>
                      <span className="text-[10px] font-normal px-2 py-0.5 rounded-full bg-white/5 text-gray-400">
                        Khối {c.grade_level}
                      </span>
                    </h4>
                    <p className="text-xs text-gray-400 mt-0.5">
                      GVCN: <strong className="text-gray-200">{c.teacher_name}</strong> · Sĩ số: {c.student_count} HS
                    </p>
                  </div>
                </div>

                <div className="text-right shrink-0">
                  <div className="text-base sm:text-lg font-black text-amber-400">
                    {c.score} <span className="text-xs text-gray-400 font-normal">điểm</span>
                  </div>
                  <span className="text-[10px] text-emerald-400 font-medium">Thi đua tuần</span>
                </div>
              </div>
            ))}

            {classRankings.length === 0 && (
              <p className="text-center text-xs text-gray-400 py-8">Chưa có dữ liệu thi đua lớp.</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
