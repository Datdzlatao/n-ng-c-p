'use client';

import React, { useState, useEffect } from 'react';
import { 
  Package, 
  Search, 
  Plus, 
  Minus,
  AlertCircle
} from 'lucide-react';

interface InventoryItem {
  id: string;
  name: string;
  category: string;
  quantity: number;
  unit: string;
  price?: number;
}

interface FeedInventoryProps {
  items: InventoryItem[];
  onOpenImport: () => void;
  onOpenExport: () => void;
  currentMode?: 'livestock' | 'cultivation';
}

export default function FeedInventory({
  items,
  onOpenImport,
  onOpenExport,
  currentMode = 'livestock',
}: FeedInventoryProps) {
  const [searchTerm, setSearchTerm] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('All');

  const isLivestock = currentMode === 'livestock';

  // Lọc danh mục vật tư
  const filtered = items.filter((item) => {
    const matchName = item.name.toLowerCase().includes(searchTerm.toLowerCase());
    const matchCat = categoryFilter === 'All' || item.category === categoryFilter;
    return matchName && matchCat;
  });

  return (
    <div className="bg-fb-card rounded-2xl shadow-fb-card border border-fb-divider p-4 mb-4">
      {/* Tiêu đề & Nút xuất nhập */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between pb-3.5 border-b border-fb-divider gap-2">
        <div className="flex items-center gap-2.5">
          <div className="w-10 h-10 rounded-2xl bg-gradient-to-tr from-amber-100 to-orange-100 flex items-center justify-center text-orange-600 font-bold shadow-inner border border-amber-200">
            <Package className="w-5 h-5" />
          </div>
          <div>
            <h4 className="font-bold text-sm text-fb-text">
              Kho Vật Tư Nông Trại
            </h4>
            <p className="text-xs text-fb-muted">
              Đang quản lý {items.length} mặt hàng thức ăn, phân bón & vật tư
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 w-full sm:w-auto">
          <button
            onClick={onOpenImport}
            className="flex-1 sm:flex-none flex items-center justify-center gap-1.5 px-3.5 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl font-bold text-xs transition shadow cursor-pointer"
          >
            <Plus className="w-4 h-4" />
            <span>Nhập Kho</span>
          </button>

          <button
            onClick={onOpenExport}
            className="flex-1 sm:flex-none flex items-center justify-center gap-1.5 px-3.5 py-2 bg-orange-500 hover:bg-orange-600 text-white rounded-xl font-bold text-xs transition shadow cursor-pointer"
          >
            <Minus className="w-4 h-4" />
            <span>Xuất Dùng</span>
          </button>
        </div>
      </div>

      {/* Thanh tìm kiếm & bộ lọc */}
      <div className="flex flex-col sm:flex-row gap-2 my-3">
        <div className="relative flex-1">
          <Search className="w-4 h-4 text-fb-muted absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder={
              isLivestock
                ? 'Tìm tên hàng (Ví dụ: Cám con cò, thức ăn đậm đặc...)'
                : 'Tìm tên hàng (Ví dụ: Phân NPK, Đạm vi sinh...)'
            }
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full bg-fb-bg text-xs rounded-xl pl-9 pr-3 py-2 border border-fb-divider focus:outline-none focus:ring-2 focus:ring-emerald-500 transition"
          />
        </div>

        {/* Quick Filter Category Chips */}
        <div className="flex items-center gap-1 overflow-x-auto pb-1 sm:pb-0 scrollbar-none">
          <button
            onClick={() => setCategoryFilter('All')}
            className={`px-2.5 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition cursor-pointer ${
              categoryFilter === 'All'
                ? 'bg-emerald-100 text-emerald-900 font-bold border border-emerald-300'
                : 'text-fb-muted hover:bg-fb-hover'
            }`}
          >
            Tất cả
          </button>
          <button
            onClick={() => setCategoryFilter('Feed')}
            className={`px-2.5 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition cursor-pointer flex items-center gap-1 ${
              categoryFilter === 'Feed'
                ? 'bg-emerald-600 text-white font-bold shadow-sm'
                : 'text-fb-muted hover:bg-fb-hover'
            }`}
          >
            <span>🥩</span>
            <span>Thức Ăn</span>
          </button>
          <button
            onClick={() => setCategoryFilter('Fertilizer')}
            className={`px-2.5 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition cursor-pointer flex items-center gap-1 ${
              categoryFilter === 'Fertilizer'
                ? 'bg-emerald-600 text-white font-bold shadow-sm'
                : 'text-fb-muted hover:bg-fb-hover'
            }`}
          >
            <span>🌱</span>
            <span>Phân Bón</span>
          </button>
          <button
            onClick={() => setCategoryFilter('Other')}
            className={`px-2.5 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition cursor-pointer flex items-center gap-1 ${
              categoryFilter === 'Other'
                ? 'bg-emerald-600 text-white font-bold shadow-sm'
                : 'text-fb-muted hover:bg-fb-hover'
            }`}
          >
            <span>🛠️</span>
            <span>Khác</span>
          </button>
        </div>
      </div>

      {/* Danh sách vật tư */}
      <div className="max-h-72 overflow-y-auto space-y-2 pr-1">
        {filtered.length === 0 ? (
          <div className="text-center py-6 text-fb-muted text-xs border border-dashed border-fb-divider rounded-xl">
            Không tìm thấy vật tư nào phù hợp với tìm kiếm.
          </div>
        ) : (
          filtered.map((item) => {
            const isOutOfStock = item.quantity <= 0;
            const isLowStock = item.quantity > 0 && item.quantity <= 5;

            return (
              <div
                key={item.id}
                className="flex items-center justify-between p-3 rounded-xl bg-fb-bg/40 border border-fb-divider hover:bg-white hover:shadow-sm transition"
              >
                <div className="flex items-center gap-2.5 min-w-0">
                  <span className="w-8 h-8 rounded-lg bg-white flex items-center justify-center text-sm shadow-sm border border-fb-divider shrink-0">
                    {item.category === 'Feed' ? '🥩' : item.category === 'Fertilizer' ? '🌱' : '🛠️'}
                  </span>
                  <div className="min-w-0">
                    <span className="font-bold text-xs text-fb-text block truncate">{item.name}</span>
                    <span className="text-[10px] text-fb-muted block">
                      Phân loại: {item.category === 'Feed' ? 'Thức ăn chăn nuôi' : item.category === 'Fertilizer' ? 'Phân bón & Dinh dưỡng' : 'Dụng cụ'}
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <div className="text-right">
                    <div className="font-extrabold text-sm text-fb-text">
                      {item.quantity}{' '}
                      <span className="text-xs font-normal text-fb-muted">{item.unit}</span>
                    </div>
                    {isOutOfStock ? (
                      <span className="text-[10px] text-red-600 font-bold flex items-center gap-0.5 justify-end">
                        <AlertCircle className="w-3 h-3" /> Hết hàng
                      </span>
                    ) : isLowStock ? (
                      <span className="text-[10px] text-amber-600 font-bold flex items-center gap-0.5 justify-end">
                        <AlertCircle className="w-3 h-3" /> Sắp hết
                      </span>
                    ) : (
                      <span className="text-[10px] text-emerald-600 font-bold">Còn hàng</span>
                    )}
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
