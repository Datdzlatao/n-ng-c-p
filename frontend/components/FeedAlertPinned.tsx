'use client';

import React from 'react';
import { AlertTriangle, Fan, BellOff, ShieldAlert, Sparkles, Droplets } from 'lucide-react';

interface FeedAlertPinnedProps {
  penName: string;
  penId: string;
  issues: string[];
  temp?: number;
  smell?: number;
  currentMode?: 'livestock' | 'cultivation';
  onActivateFan: () => void;
  onDismiss: () => void;
  onAskAI: () => void;
}

export default function FeedAlertPinned({
  penName,
  penId,
  issues,
  temp,
  smell,
  currentMode = 'livestock',
  onActivateFan,
  onDismiss,
  onAskAI,
}: FeedAlertPinnedProps) {
  if (!issues || issues.length === 0) return null;

  const isLivestock = currentMode === 'livestock';

  return (
    <div className="bg-gradient-to-r from-red-600 via-rose-600 to-orange-600 rounded-2xl shadow-lg p-0.5 alert-pulse mb-4">
      <div className="bg-fb-card rounded-[14px] p-4 text-fb-text">
        {/* Tiêu đề thông báo cảnh báo */}
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-red-100 flex items-center justify-center text-red-600 font-bold shadow-inner shrink-0">
              <ShieldAlert className="w-6 h-6 animate-pulse" />
            </div>
            <div>
              <div className="flex items-center gap-1.5 flex-wrap">
                <span className="font-bold text-sm text-red-600 uppercase tracking-wider">
                  ⚠️ Báo Động Môi Trường Khẩn Cấp
                </span>
                <span className="text-xs bg-red-100 text-red-700 px-2 py-0.5 rounded-full font-bold">
                  {isLivestock ? 'Khí Hậu Chuồng Nuôi' : 'Vi Khí Hậu Vườn Trồng'}
                </span>
              </div>
              <p className="text-xs text-fb-muted mt-0.5">
                Tại <strong className="text-fb-text">{penName}</strong> ({penId}) • Vừa phát hiện
              </p>
            </div>
          </div>

          <button
            onClick={onDismiss}
            title="Tạm ẩn cảnh báo này"
            className="text-fb-muted hover:text-fb-text p-1 text-xs rounded hover:bg-fb-hover cursor-pointer"
            aria-label="Tạm ẩn cảnh báo"
          >
            <BellOff className="w-4 h-4" />
          </button>
        </div>

        {/* Nội dung chi tiết chỉ số vượt ngưỡng */}
        <div className="mt-3 bg-red-50 border border-red-200 rounded-xl p-3 text-sm">
          <p className="font-semibold text-red-800 text-xs sm:text-sm">
            Hệ thống cảm biến tự động ghi nhận chỉ số vi khí hậu vượt ngưỡng an toàn:
          </p>
          <div className="flex flex-wrap gap-2 mt-2">
            {issues.map((issue, i) => (
              <span
                key={i}
                className="inline-flex items-center gap-1 bg-white border border-red-300 text-red-700 font-bold px-2.5 py-1 rounded-lg text-xs shadow-sm"
              >
                <AlertTriangle className="w-3.5 h-3.5 text-red-500" />
                {issue}
              </span>
            ))}
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mt-2.5 pt-2 border-t border-red-200/60 text-xs text-red-700">
            <div>
              Nhiệt độ hiện tại: <strong className="text-red-900 font-bold">{temp ?? '--'}°C</strong>{' '}
              <span className="text-red-600">(Ngưỡng: dưới {isLivestock ? '35' : '40'}°C)</span>
            </div>
            <div>
              {isLivestock ? (
                <>
                  Nồng độ khí chuồng: <strong className="text-red-900 font-bold">{smell ?? '--'} ppm</strong>{' '}
                  <span className="text-red-600">(Ngưỡng: dưới 400 ppm)</span>
                </>
              ) : (
                <>
                  Độ ẩm của đất: <strong className="text-red-900 font-bold">{smell ?? '--'}%</strong>{' '}
                  <span className="text-red-600">(Ngưỡng: trên 30%)</span>
                </>
              )}
            </div>
          </div>
        </div>

        {/* Nút hành động nhanh */}
        <div className="mt-3 flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-fb-divider">
          <div className="flex gap-2">
            <button
              onClick={onActivateFan}
              className="flex items-center gap-1.5 px-3.5 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl font-bold text-xs transition shadow cursor-pointer"
            >
              {isLivestock ? (
                <>
                  <Fan className="w-4 h-4 animate-spin" />
                  <span>Bật Quạt Hút Mùi Ngay</span>
                </>
              ) : (
                <>
                  <Droplets className="w-4 h-4 animate-pulse" />
                  <span>Bật Bơm Tưới / Phun Sương Ngay</span>
                </>
              )}
            </button>

            <button
              onClick={onAskAI}
              className="flex items-center gap-1.5 px-3.5 py-1.5 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 border border-indigo-200 rounded-xl font-bold text-xs transition cursor-pointer"
            >
              <Sparkles className="w-3.5 h-3.5 text-indigo-600" />
              <span>Hỏi Trợ Lý AI</span>
            </button>
          </div>

          <span className="text-[11px] text-fb-muted">Khuyến nghị xử lý khẩn cấp</span>
        </div>
      </div>
    </div>
  );
}
