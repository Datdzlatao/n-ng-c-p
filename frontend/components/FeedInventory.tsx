'use client';

import React, { useState } from 'react';
import { 
  Package, 
  Search, 
  Plus, 
  Minus 
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
}

export default function FeedInventory({
  items,
  onOpenImport,
  onOpenExport,
}: FeedInventoryProps) {
  const [searchTerm, setSearchTerm] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('All');

  // Lọc danh mục vật tư
  const filtered = items.filter((item) => {
    const matchName = item.name.toLowerCase().includes(searchTerm.toLowerCase());
    const matchCat = categoryFilter === 'All' || item.category === categoryFilter;
    return matchName && matchCat;
  });

  return (
    <div className="bg-fb-card rounded-2xl shadow-fb-card border border-fb-divider p-4 mb-4">
      {/* Tiêu đề & Nút xuất nhập */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between pb-3 border-b border-fb-divider gap-2">
        <div className="flex items-center gap-2.5">
          <div className="w-10 h-10 rounded-full bg-orange-100 flex items-center justify-center text-orange-600 font-bold shadow-inner">
            <Package className="w-5 h-5" />
          </div>
          <div>
            <h4 className="font-bold text-sm text-fb-text">
              Kho Vật Tư & Thức Ăn Nông Trại
            </h4>
            <p className="text-xs text-fb-muted">
              Đang quản lý {items.length} mặt hàng thức ăn và phân bón
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 w-full sm:w-auto">
          <button
            onClick={onOpenImport}
            className="flex-1 sm:flex-none flex items-center justify-center gap-1.5 px-3.5 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl font-bold text-xs transition shadow cursor-pointer"
          >
            <Plus className="w-4 h-4" />
            <span>Nhập Kho</span>
          </button>

          <button
            onClick={onOpenExport}
            className="flex-1 sm:flex-none flex items-center justify-center gap-1.5 px-3.5 py-1.5 bg-orange-500 hover:bg-orange-600 text-white rounded-xl font-bold text-xs transition shadow cursor-pointer"
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
            placeholder="Tìm tên hàng (Ví dụ: Cám con cò, Phân Ure...)"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full bg-fb-bg text-sm rounded-xl pl-9 pr-3 py-2 border border-fb-divider focus:outline-none focus:ring-2 focus:ring-emerald-500 transition"
          />
        </div>

        <div className="relative sm:w-48">
          <select
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            className="w-full bg-fb-bg text-sm rounded-xl px-3 py-2 border border-fb-divider focus:outline-none focus:ring-2 focus:ring-emerald-500 transition cursor-pointer font-medium"
            aria-label="Lọc theo phân loại vật tư"
          >
            <option value="All">Tất cả phân loại</option>
            <option value="Feed">🥩 Thức ăn chăn nuôi</option>
            <option value="Fertilizer">🌱 Phân bón & Dinh dưỡng</option>
            <option value="Other">🛠️ Vật tư khác</option>
          </select>
        </div>
      </div>

      {/* Danh sách vật tư */}
      <div className="max-h-72 overflow-y-auto space-y-2 pr-1">
        {filtered.length === 0 ? (
          <div className="text-center py-6 text-fb-muted text-sm">
            Không tìm thấy vật tư nào phù hợp.
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
                <div className="flex items-center gap-2.5">
                  <div
                    className={`w-8 h-8 rounded-lg flex items-center justify-center text-xs font-bold ${
                      item.category === 'Feed'
                        ? 'bg-amber-100 text-amber-700'
                        : item.category === 'Fertilizer'
                        ? 'bg-green-100 text-green-700'
                        : 'bg-slate-200 text-slate-700'
                    }`}
                  >
                    {item.category === 'Feed' ? '🥩' : item.category === 'Fertilizer' ? '🌱' : '🛠️'}
                  </div>

                  <div>
                    <span className="font-bold text-sm text-fb-text block">{item.name}</span>
                    <span className="text-[11px] text-fb-muted">
                      {item.category === 'Feed' 
                        ? 'Thức ăn chăn nuôi' 
                        : item.category === 'Fertilizer' 
                        ? 'Phân bón & Dinh dưỡng' 
                        : 'Vật tư chuồng trại'}
                    </span>
                  </div>
                </div>

                <div className="text-right">
                  <div className="flex items-center gap-1.5 justify-end">
                    <span
                      className={`font-extrabold text-sm ${
                        isOutOfStock
                          ? 'text-red-600'
                          : isLowStock
                          ? 'text-orange-600'
                          : 'text-emerald-700'
                      }`}
                    >
                      {item.quantity} {item.unit}
                    </span>

                    {isOutOfStock && (
                      <span className="text-[10px] bg-red-100 text-red-700 font-bold px-1.5 py-0.5 rounded-full">
                        Hết Hàng
                      </span>
                    )}

                    {isLowStock && (
                      <span className="text-[10px] bg-orange-100 text-orange-700 font-bold px-1.5 py-0.5 rounded-full">
                        Sắp Hết
                      </span>
                    )}
                  </div>

                  {/* Thanh biểu thị mức tồn kho */}
                  <div className="w-24 bg-slate-200 h-1.5 rounded-full mt-1.5 overflow-hidden ml-auto">
                    <div
                      className={`h-full transition-all ${
                        isOutOfStock
                          ? 'bg-red-500'
                          : isLowStock
                          ? 'bg-orange-500'
                          : 'bg-emerald-500'
                      }`}
                      style={{ width: `${Math.min(100, (item.quantity / 50) * 100)}%` }}
                    />
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
