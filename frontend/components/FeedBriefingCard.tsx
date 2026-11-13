'use client';

import React, { useState } from 'react';
import { 
  Bot, 
  Sparkles, 
  ThumbsUp, 
  MessageSquare, 
  Share2, 
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
  currentMode?: 'livestock' | 'cultivation';
}

export default function FeedBriefingCard({
  onOpenChat,
  pendingTasksCount = 2,
  lowStockCount = 1,
  sickAnimalsCount = 1,
  briefingText,
  onTriggerBriefing,
  isLoading = false,
  currentMode = 'livestock',
}: FeedBriefingCardProps) {
  const [liked, setLiked] = useState(false);
  const [likeCount, setLikeCount] = useState(12);

  const isLivestock = currentMode === 'livestock';

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
      {/* Tác giả bản tin / Trợ lý thông minh */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="relative">
            <div className="w-10 h-10 rounded-2xl bg-gradient-to-tr from-emerald-600 via-teal-600 to-green-500 flex items-center justify-center text-white shadow">
              <Bot className="w-5 h-5" />
            </div>
            <span className="absolute -bottom-0.5 -right-0.5 w-3 h-3 bg-emerald-500 rounded-full ring-2 ring-white" />
          </div>

          <div>
            <div className="flex items-center gap-1.5">
              <h4 className="font-bold text-sm text-fb-text hover:underline cursor-pointer">
                Trợ Lý Nông Trại Thông Minh
              </h4>
              <span className="w-4 h-4 rounded-full bg-emerald-600 text-white flex items-center justify-center text-[9px] font-bold">
                ✓
              </span>
            </div>
            <p className="text-xs text-fb-muted flex items-center gap-1">
              Bản tin sáng tự động • 07:00 Hôm nay • {isLivestock ? '🐖 Khu Chăn Nuôi' : '🌿 Khu Trồng Trọt'}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {onTriggerBriefing && (
            <button
              onClick={onTriggerBriefing}
              disabled={isLoading}
              title="Tổng hợp lại toàn bộ dữ liệu nông trại và tạo bản tin mới"
              className="text-xs flex items-center gap-1 px-2.5 py-1.5 bg-emerald-50 hover:bg-emerald-100 text-emerald-800 font-bold rounded-xl border border-emerald-200 transition disabled:opacity-50 cursor-pointer"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
              <span className="hidden sm:inline">{isLoading ? 'Đang tạo...' : 'Làm Mới'}</span>
            </button>
          )}

          <span className="text-xs font-bold px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-800 border border-emerald-200">
            Bản Tin Mỗi Ngày
          </span>
        </div>
      </div>

      {/* Nội dung bản tin */}
      <div className="mt-3 text-sm text-fb-text space-y-2">
        {briefingText ? (
          <div className="bg-slate-50 border border-slate-200 rounded-xl p-3 text-xs md:text-sm text-slate-800 leading-relaxed whitespace-pre-line font-medium">
            {briefingText}
          </div>
        ) : (
          <p className="leading-relaxed text-xs sm:text-sm text-fb-text">
            Kính chào bà con! ☀️ Hôm nay thời tiết dự kiến ấm áp, khô ráo. Dưới đây là tổng hợp nhanh các đầu việc cần lưu ý trong ngày từ hệ thống phân tích tự động:
          </p>
        )}

        {/* Lưới điểm tin nhanh */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 pt-1 pb-1">
          <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200 flex items-center gap-2">
            <span className="text-xl">📋</span>
            <div>
              <div className="text-xs text-fb-muted">Công việc trong ngày</div>
              <div className="font-bold text-sm text-fb-text">{pendingTasksCount} nhiệm vụ</div>
            </div>
          </div>

          <div className="p-2.5 rounded-xl bg-orange-50 border border-orange-200 flex items-center gap-2">
            <span className="text-xl">⚠️</span>
            <div>
              <div className="text-xs text-orange-700">Kho sắp hết</div>
              <div className="font-bold text-sm text-orange-800">{lowStockCount} mặt hàng</div>
            </div>
          </div>

          <div className="p-2.5 rounded-xl bg-rose-50 border border-rose-200 flex items-center gap-2">
            <span className="text-xl">{isLivestock ? '🩺' : '🌿'}</span>
            <div>
              <div className="text-xs text-rose-700">
                {isLivestock ? 'Vật nuôi cần chú ý' : 'Cây trồng cần tưới/chăm'}
              </div>
              <div className="font-bold text-sm text-rose-800">
                {sickAnimalsCount} {isLivestock ? 'cá thể' : 'vụ/luống'}
              </div>
            </div>
          </div>
        </div>

        <p className="text-xs text-fb-muted italic pt-1">
          {isLivestock
            ? '💡 Lưu ý quan trọng: Nên kiểm tra chuồng cách ly lúc 09:30 và bổ sung thức ăn vào kho trước 15:00 chiều.'
            : '💡 Lưu ý quan trọng: Nên kiểm tra độ ẩm đất nhà màng lúc 08:30 và bổ sung phân bón dinh dưỡng trước 15:00 chiều.'}
        </p>
      </div>

      {/* Lượt tương tác */}
      <div className="flex items-center justify-between text-xs text-fb-muted pt-3 pb-2 border-b border-fb-divider mt-2">
        <div className="flex items-center gap-1.5">
          <span className="flex items-center justify-center w-4 h-4 rounded-full bg-emerald-600 text-white text-[10px]">
            👍
          </span>
          <span className="flex items-center justify-center w-4 h-4 rounded-full bg-red-500 text-white text-[10px]">
            ❤️
          </span>
          <span>{likeCount} thành viên đã xem</span>
        </div>
        <span>3 câu hỏi tư vấn</span>
      </div>

      {/* Các nút tương tác */}
      <div className="grid grid-cols-3 gap-1 pt-1 mt-1 text-xs font-semibold text-fb-muted">
        <button
          onClick={handleLike}
          className={`flex items-center justify-center gap-1.5 py-2 rounded-xl transition cursor-pointer ${
            liked ? 'text-emerald-700 font-bold bg-emerald-50' : 'hover:bg-fb-hover text-fb-muted'
          }`}
        >
          <ThumbsUp className={`w-4 h-4 ${liked ? 'fill-emerald-600 text-emerald-600' : ''}`} />
          <span>Hữu ích ({likeCount})</span>
        </button>

        <button
          onClick={onOpenChat}
          className="flex items-center justify-center gap-1.5 py-2 rounded-xl hover:bg-fb-hover text-fb-muted transition cursor-pointer"
        >
          <MessageSquare className="w-4 h-4 text-emerald-600" />
          <span>Hỏi chi tiết</span>
        </button>

        <button
          onClick={() => alert('Đã sao chép liên kết bản tin!')}
          className="flex items-center justify-center gap-1.5 py-2 rounded-xl hover:bg-fb-hover text-fb-muted transition cursor-pointer"
        >
          <Share2 className="w-4 h-4" />
          <span>Chia sẻ</span>
        </button>
      </div>
    </div>
  );
}
