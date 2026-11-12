/**
 * src/components/common/FlameStreakBadge.jsx
 * Hiệu ứng Huy Hiệu Chuỗi Lửa Chuyên Cần (Streak Flame) đa cấp độ màu sắc
 */
import React from 'react';
import { Flame, Sparkles } from 'lucide-react';

export const FLAME_TIERS = {
  PURPLE: {
    label: 'Lửa Tím Tối Thượng',
    cls: 'text-purple-300 bg-purple-950/50 border-purple-500/50 shadow-[0_0_20px_rgba(168,85,247,0.45)]',
    flameCls: 'text-purple-400 fill-purple-400 drop-shadow-[0_0_8px_rgba(168,85,247,0.8)]',
    dot: 'bg-purple-400',
    min: 30,
  },
  RED: {
    label: 'Lửa Đỏ Rực',
    cls: 'text-rose-300 bg-rose-950/40 border-rose-500/50 shadow-[0_0_16px_rgba(244,63,94,0.4)]',
    flameCls: 'text-rose-400 fill-rose-400 drop-shadow-[0_0_6px_rgba(244,63,94,0.8)]',
    dot: 'bg-rose-400',
    min: 14,
  },
  ORANGE: {
    label: 'Lửa Cam Nhiệt Huyết',
    cls: 'text-amber-300 bg-amber-950/40 border-amber-500/50 shadow-[0_0_14px_rgba(245,158,11,0.35)]',
    flameCls: 'text-amber-400 fill-amber-400 drop-shadow-[0_0_5px_rgba(245,158,11,0.7)]',
    dot: 'bg-amber-400',
    min: 7,
  },
  GREEN: {
    label: 'Lửa Xanh Lá',
    cls: 'text-emerald-300 bg-emerald-950/40 border-emerald-500/40 shadow-[0_0_12px_rgba(16,185,129,0.3)]',
    flameCls: 'text-emerald-400 fill-emerald-400 drop-shadow-[0_0_5px_rgba(16,185,129,0.7)]',
    dot: 'bg-emerald-400',
    min: 3,
  },
  BLUE: {
    label: 'Lửa Mầm',
    cls: 'text-sky-300 bg-sky-950/30 border-sky-500/30 shadow-[0_0_8px_rgba(14,165,233,0.2)]',
    flameCls: 'text-sky-400 fill-sky-400',
    dot: 'bg-sky-400',
    min: 1,
  },
  NONE: {
    label: 'Chưa Có Lửa',
    cls: 'text-gray-400 bg-white/5 border-white/10',
    flameCls: 'text-gray-500',
    dot: 'bg-gray-500',
    min: 0,
  }
};

export function getFlameTierFromDays(days = 0) {
  if (days >= 30) return FLAME_TIERS.PURPLE;
  if (days >= 14) return FLAME_TIERS.RED;
  if (days >= 7)  return FLAME_TIERS.ORANGE;
  if (days >= 3)  return FLAME_TIERS.GREEN;
  if (days >= 1)  return FLAME_TIERS.BLUE;
  return FLAME_TIERS.NONE;
}

export function FlameStreakBadge({ streak = 0, size = 'md', showLabel = true, className = '' }) {
  const tier = getFlameTierFromDays(streak);

  const sizeStyles = {
    sm: 'px-2 py-0.5 text-[11px] gap-1',
    md: 'px-3 py-1 text-xs gap-1.5',
    lg: 'px-4 py-1.5 text-sm gap-2 font-bold',
  };

  const iconSizes = {
    sm: 'w-3.5 h-3.5',
    md: 'w-4 h-4',
    lg: 'w-5 h-5',
  };

  return (
    <div
      className={`inline-flex items-center rounded-full border transition-all duration-300 ${tier.cls} ${sizeStyles[size] || sizeStyles.md} ${className}`}
      title={`${tier.label}: Chuỗi ${streak} ngày đúng giờ liên tiếp`}
    >
      {/* Animated Flame Icon */}
      <div className="relative flex items-center justify-center">
        <Flame
          className={`${iconSizes[size] || iconSizes.md} ${tier.flameCls} ${
            streak >= 3 ? 'animate-[bounce_2s_infinite]' : ''
          }`}
        />
        {streak >= 14 && (
          <Sparkles className="w-2.5 h-2.5 absolute -top-1 -right-1 text-amber-300 animate-spin" />
        )}
      </div>

      {/* Streak Counter */}
      <span className="font-extrabold tracking-tight">
        {streak} {showLabel ? (streak === 1 ? 'ngày' : 'ngày liên tục') : 'd'}
      </span>
    </div>
  );
}
