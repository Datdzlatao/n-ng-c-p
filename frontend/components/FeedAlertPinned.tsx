'use client';

import React from 'react';
import { AlertTriangle, Fan, BellOff, ShieldAlert, Sparkles } from 'lucide-react';

interface FeedAlertPinnedProps {
  penName: string;
  penId: string;
  issues: string[];
  temp?: number;
  smell?: number;
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
  onActivateFan,
  onDismiss,
  onAskAI,
}: FeedAlertPinnedProps) {
  if (!issues || issues.length === 0) return null;

  return (
    <div className="bg-gradient-to-r from-red-600 via-rose-600 to-orange-600 rounded-2xl shadow-lg p-0.5 alert-pulse mb-4">
      <div className="bg-fb-card rounded-[14px] p-4 text-fb-text">
        {/* Tiêu đề thông báo cảnh báo */}
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-red-100 flex items-center justify-center text-red-600 font-bold shadow-inner">
              <ShieldAlert className="w-6 h-6 animate-pulse" />
            </div>
            <div>
              <div className="flex items-center gap-1.5">
                <span className="font-bold text-sm text-red-600 uppercase tracking-wider">
                  ⚠️ Báo Động Môi Trường Khẩn Cấp
                </span>
                <span className="text-xs bg-red-100 text-red-700 px-2 py-0.5 rounded-full font-bold">
                  Khí Hậu Chuồng
                </span>
              </div>
              <p className="text-xs text-fb-muted">
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
          <p className="font-semibold text-red-800">
            Hệ thống cảm biến tự động ghi nhận chỉ số vượt ngưỡng an toàn:
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

          <div className="grid grid-cols-2 gap-2 mt-2.5 pt-2 border-t border-red-200/60 text-xs text-red-700">
            <div>Nhiệt độ hiện tại: <strong className="text-red-900">{temp ?? '--'}°C</strong> (Ngưỡng an toàn: dưới 35°C)</div>
            <div>Nồng độ khí chuồng: <strong className="text-red-900">{smell ?? '--'} ppm</strong> (Ngưỡng an toàn: dưới 400)</div>
          </div>
        </div>

        {/* Nút hành động nhanh */}
        <div className="mt-3 flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-fb-divider">
          <div className="flex gap-2">
            <button
              onClick={onActivateFan}
              className="flex items-center gap-1.5 px-3.5 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg font-bold text-xs transition shadow cursor-pointer"
            >
              <Fan className="w-4 h-4 animate-spin" />
              Bật Quạt Hút Mùi Ngay
            </button>

            <button
              onClick={onAskAI}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 border border-indigo-200 rounded-lg font-bold text-xs transition cursor-pointer"
            >
              <Sparkles className="w-4 h-4 text-indigo-500" />
              Hỏi Trợ Lý Ảo
            </button>
          </div>

          <span className="text-[11px] text-fb-muted italic">
            * Hệ thống tự động theo dõi và cập nhật liên tục
          </span>
        </div>
      </div>
    </div>
  );
}
