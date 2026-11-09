'use client';

import React, { useState } from 'react';
import { 
  Bot, 
  CheckCircle, 
  Sparkles, 
  ThumbsUp, 
  MessageSquare, 
  Share2, 
  Calendar, 
  AlertCircle,
  RefreshCw
} from 'lucide-react';

interface FeedBriefingCardProps {
  onOpenChat: () => void;
  pendingTasksCount?: number;
  lowStockCount?: number;
  sickAnimalsCount?: number;
  briefingText?: string;
  onTriggerBriefing?: () => void;
  isLoading?: boolean;
}

export default function FeedBriefingCard({
  onOpenChat,
  pendingTasksCount = 2,
  lowStockCount = 1,
  sickAnimalsCount = 1,
  briefingText,
  onTriggerBriefing,
  isLoading = false,
}: FeedBriefingCardProps) {
  const [liked, setLiked] = useState(false);
  const [likeCount, setLikeCount] = useState(12);

  const handleLike = () => {
    if (liked) {
      setLiked(false);
      setLikeCount(likeCount - 1);
    } else {
      setLiked(true);
      setLikeCount(likeCount + 1);
    }
  };

  return (
    <div className="bg-fb-card rounded-2xl shadow-fb-card border border-fb-divider p-4 mb-4">
      {/* Post Author / Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="relative">
            <div className="w-10 h-10 rounded-full bg-gradient-to-tr from-indigo-600 via-purple-600 to-pink-500 flex items-center justify-center text-white shadow">
              <Bot className="w-5 h-5" />
            </div>
            <span className="absolute bottom-0 right-0 w-3 h-3 bg-emerald-500 rounded-full ring-2 ring-white" />
          </div>

          <div>
            <div className="flex items-center gap-1.5">
              <h4 className="font-bold text-sm text-fb-text hover:underline cursor-pointer">
                Trợ Lý Nông Trại Thông Minh (Gemini AI)
              </h4>
              <span className="w-4 h-4 rounded-full bg-fb-blue text-white flex items-center justify-center text-[9px] font-bold">
                ✓
              </span>
            </div>
            <p className="text-xs text-fb-muted flex items-center gap-1">
              Bản tin buổi sáng tự động • 07:00 Hôm nay • 🌾 Toàn Trang Trại
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {onTriggerBriefing && (
            <button
              onClick={onTriggerBriefing}
              disabled={isLoading}
              title="Quét lại toàn trang trại và yêu cầu Gemini viết bản tin mới"
              className="text-xs flex items-center gap-1 px-2.5 py-1 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 font-semibold rounded-lg border border-indigo-200 transition disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
              <span>{isLoading ? 'Đang tạo...' : 'Làm Mới Bản Tin'}</span>
            </button>
          )}

          <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-indigo-50 text-indigo-700 border border-indigo-200">
            Daily Briefing
          </span>
        </div>
      </div>

      {/* Post Text Content */}
      <div className="mt-3 text-sm text-fb-text space-y-2">
        {briefingText ? (
          <div className="bg-slate-50 border border-slate-200 rounded-xl p-3 text-xs md:text-sm text-slate-800 leading-relaxed whitespace-pre-line font-medium">
            {briefingText}
          </div>
        ) : (
          <p className="leading-relaxed">
            Chào buổi sáng bà con! ☀️ Hôm nay thời tiết có xu hướng nóng vào buổi trưa. Dưới đây là các điểm mấu chốt hệ thống đã tự động rà soát qua giao thức FastMCP:
          </p>
        )}

        {/* Highlight Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 pt-1 pb-1">
          <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200 flex items-center gap-2">
            <span className="text-xl">📋</span>
            <div>
              <div className="text-xs text-fb-muted">Công việc hôm nay</div>
              <div className="font-bold text-sm text-fb-text">{pendingTasksCount} nhiệm vụ</div>
            </div>
          </div>

          <div className="p-2.5 rounded-xl bg-orange-50 border border-orange-200 flex items-center gap-2">
            <span className="text-xl">⚠️</span>
            <div>
              <div className="text-xs text-orange-700">Kho sắp cạn</div>
              <div className="font-bold text-sm text-orange-800">{lowStockCount} mặt hàng</div>
            </div>
          </div>

          <div className="p-2.5 rounded-xl bg-rose-50 border border-rose-200 flex items-center gap-2">
            <span className="text-xl">🩺</span>
            <div>
              <div className="text-xs text-rose-700">Vật nuôi cần chú ý</div>
              <div className="font-bold text-sm text-rose-800">{sickAnimalsCount} cá thể</div>
            </div>
          </div>
        </div>

        <p className="text-xs text-fb-muted italic pt-1">
          💡 Khuyến nghị ưu tiên: Kiểm tra chuồng cách ly lúc 09:30 và bổ sung thêm cám cò vào kho trước 15:00 chiều.
        </p>
      </div>

      {/* Reaction Counts Bar */}
      <div className="flex items-center justify-between text-xs text-fb-muted pt-3 pb-2 border-b border-fb-divider mt-2">
        <div className="flex items-center gap-1.5">
          <span className="flex items-center justify-center w-4 h-4 rounded-full bg-fb-blue text-white text-[10px]">
            👍
          </span>
          <span className="flex items-center justify-center w-4 h-4 rounded-full bg-red-500 text-white text-[10px]">
            ❤️
          </span>
          <span>{likeCount} nông dân đã xem</span>
        </div>
        <span>3 câu hỏi với AI</span>
      </div>

      {/* Post Action Buttons (Like / Comment / Share) */}
      <div className="grid grid-cols-3 gap-1 pt-1 mt-1 text-xs font-semibold text-fb-muted">
        <button
          onClick={handleLike}
          className={`py-1.5 rounded-lg flex items-center justify-center gap-2 hover:bg-fb-hover transition ${
            liked ? 'text-fb-blue font-bold' : ''
          }`}
        >
          <ThumbsUp className="w-4 h-4" />
          <span>Thích</span>
        </button>

        <button
          onClick={onOpenChat}
          className="py-1.5 rounded-lg flex items-center justify-center gap-2 hover:bg-fb-hover transition text-indigo-600 font-bold"
        >
          <MessageSquare className="w-4 h-4" />
          <span>Hỏi Chi Tiết AI</span>
        </button>

        <button
          onClick={() => alert('Đã sao chép nội dung bản tin vào khay nhớ tạm!')}
          className="py-1.5 rounded-lg flex items-center justify-center gap-2 hover:bg-fb-hover transition"
        >
          <Share2 className="w-4 h-4" />
          <span>Chia Sẻ</span>
        </button>
      </div>
    </div>
  );
}
