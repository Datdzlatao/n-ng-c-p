'use client';

import React, { useState, useMemo } from 'react';
import { 
  Plus, 
  Trash2, 
  TrendingUp, 
  Stethoscope, 
  Sprout, 
  Calendar, 
  CheckCircle2, 
  AlertCircle,
  Droplet,
  Truck,
  LayoutGrid,
  Table as TableIcon,
  Search,
  Filter,
  Scissors
} from 'lucide-react';

export interface Animal {
  id: string;
  species: string;
  weight: number;
  target_weight: number;
  feeding_status?: string;
  status?: string;
}

export interface Crop {
  id: string;
  name: string;
  quantity: number;
  planted_at?: string;
  planting_date?: string;
  plant_date?: string;
  expected_harvest?: string;
  harvest_date?: string;
  status?: string;
  stage?: string;
}

interface FeedLivestockCropsProps {
  currentMode: 'livestock' | 'cultivation';
  animals: Animal[];
  crops: Crop[];
  penName: string;
  onOpenAddModal: () => void;
  onOpenTracking: (animalId: string) => void;
  onOpenHealth: (animalId: string) => void;
  onDeleteAnimal: (animalId: string) => void;
  onExportAnimal?: (animal: Animal) => void;
  onOpenCropTracking: (cropId: string) => void;
  onOpenCropCare: (cropId: string) => void;
  onDeleteCrop: (cropId: string) => void;
  onExportCrop?: (crop: Crop) => void;
}

export default function FeedLivestockCrops({
  currentMode,
  animals,
  crops,
  penName,
  onOpenAddModal,
  onOpenTracking,
  onOpenHealth,
  onDeleteAnimal,
  onExportAnimal,
  onOpenCropTracking,
  onOpenCropCare,
  onDeleteCrop,
  onExportCrop,
}: FeedLivestockCropsProps) {
  const isLivestock = currentMode === 'livestock';

  // Shared UI controls across both Livestock & Cultivation
  const [viewMode, setViewMode] = useState<'table' | 'cards'>('table');
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<'all' | 'ready' | 'attention' | 'healthy'>('all');

  // Helper: Icon for Species
  const getSpeciesIcon = (species: string) => {
    const s = (species || '').toLowerCase();
    if (s.includes('gà') || s.includes('ga') || s.includes('chicken')) return '🐔';
    if (s.includes('bò') || s.includes('bo') || s.includes('cow')) return '🐮';
    if (s.includes('dê') || s.includes('goat')) return '🐐';
    if (s.includes('vịt') || s.includes('duck')) return '🦆';
    return '🐷';
  };

  // Helper: Icon for Crops
  const getCropIcon = (name: string) => {
    const n = (name || '').toLowerCase();
    if (n.includes('dưa') || n.includes('melon')) return '🍈';
    if (n.includes('cà chua') || n.includes('tomato')) return '🍅';
    if (n.includes('lúa') || n.includes('rice')) return '🌾';
    if (n.includes('bắp') || n.includes('ngô') || n.includes('corn')) return '🌽';
    if (n.includes('dâu') || n.includes('berry')) return '🍓';
    if (n.includes('rau') || n.includes('xà lách') || n.includes('cải')) return '🥬';
    if (n.includes('nấm') || n.includes('mushroom')) return '🍄';
    return '🌿';
  };

  // Helper: Calculate Crop Harvest Progress (%)
  const getCropProgress = (crop: Crop) => {
    const pDateStr = crop.plant_date || crop.planting_date || crop.planted_at;
    const hDateStr = crop.harvest_date || crop.expected_harvest;
    
    // Explicit status check
    const status = (crop.status || '').toLowerCase();
    if (status.includes('ripen') || status.includes('ready') || status.includes('harvest')) return 100;

    if (pDateStr) {
      const pDate = new Date(pDateStr).getTime();
      const now = Date.now();
      if (hDateStr) {
        const hDate = new Date(hDateStr).getTime();
        const total = Math.max(1, hDate - pDate);
        const elapsed = Math.max(0, now - pDate);
        return Math.min(100, Math.max(5, Math.round((elapsed / total) * 100)));
      } else {
        // Assume default standard crop cycle 60 days if no harvest date given
        const daysPassed = Math.max(1, (now - pDate) / (1000 * 60 * 60 * 24));
        return Math.min(100, Math.round((daysPassed / 60) * 100));
      }
    }
    return 65;
  };

  // Helper: Format Date String
  const formatDate = (dateStr?: string) => {
    if (!dateStr) return 'Mới trồng';
    try {
      const d = new Date(dateStr);
      if (isNaN(d.getTime())) return dateStr;
      return d.toLocaleDateString('vi-VN');
    } catch {
      return dateStr;
    }
  };

  // 1. Process & Filter Animals (Livestock)
  const processedAnimals = useMemo(() => {
    return animals.map((a) => {
      const pct = a.target_weight ? Math.min(100, Math.round((a.weight / a.target_weight) * 100)) : 50;
      const isSick = a.feeding_status === 'Anorexic' || a.status === 'Sick' || a.status === 'Attention';
      const isSkinny = a.target_weight && a.weight < a.target_weight * 0.8;
      const isReady = pct >= 100;

      let filterCategory: 'ready' | 'attention' | 'healthy' = 'healthy';
      if (isReady) filterCategory = 'ready';
      else if (isSick || isSkinny) filterCategory = 'attention';

      return {
        ...a,
        pct,
        isSick,
        isSkinny,
        isReady,
        filterCategory,
      };
    }).filter((a) => {
      const matchSearch = 
        a.id.toLowerCase().includes(searchQuery.toLowerCase()) || 
        a.species.toLowerCase().includes(searchQuery.toLowerCase());
      const matchStatus = statusFilter === 'all' || a.filterCategory === statusFilter;
      return matchSearch && matchStatus;
    });
  }, [animals, searchQuery, statusFilter]);

  // 2. Process & Filter Crops (Cultivation)
  const processedCrops = useMemo(() => {
    return crops.map((c) => {
      const pct = getCropProgress(c);
      const statusLower = (c.status || '').toLowerCase();
      const isSick = statusLower.includes('sick') || statusLower.includes('pest') || statusLower.includes('bệnh');
      const isAttention = statusLower.includes('care') || statusLower.includes('dry') || statusLower.includes('khô');
      const isReady = pct >= 100 || statusLower.includes('ripen') || statusLower.includes('ready') || statusLower.includes('thu hoạch');

      let filterCategory: 'ready' | 'attention' | 'healthy' = 'healthy';
      if (isReady) filterCategory = 'ready';
      else if (isSick || isAttention) filterCategory = 'attention';

      return {
        ...c,
        pct,
        isSick,
        isAttention,
        isReady,
        filterCategory,
      };
    }).filter((c) => {
      const matchSearch = 
        String(c.id).toLowerCase().includes(searchQuery.toLowerCase()) || 
        c.name.toLowerCase().includes(searchQuery.toLowerCase());
      const matchStatus = statusFilter === 'all' || c.filterCategory === statusFilter;
      return matchSearch && matchStatus;
    });
  }, [crops, searchQuery, statusFilter]);

  const totalCount = isLivestock ? animals.length : crops.length;
  const readyCount = isLivestock 
    ? animals.filter((a) => a.target_weight && a.weight >= a.target_weight).length
    : crops.filter((c) => getCropProgress(c) >= 100).length;

  return (
    <div className="bg-fb-card rounded-2xl shadow-fb-card border border-fb-divider p-4 mb-4">
      {/* 1. Header Chung: Tiêu đề, Thống kê, Nút thêm & Chuyển chế độ xem */}
      <div className="flex flex-col md:flex-row md:items-center justify-between pb-3.5 border-b border-fb-divider gap-3">
        <div className="flex items-center gap-3">
          <div className="w-11 h-11 rounded-2xl bg-gradient-to-tr from-emerald-100 to-green-100 flex items-center justify-center text-2xl shadow-inner border border-emerald-200 shrink-0">
            {isLivestock ? '🐖' : '🌿'}
          </div>
          <div>
            <h4 className="font-bold text-base text-fb-text flex items-center gap-2">
              <span>{isLivestock ? 'Danh Mục Đàn Vật Nuôi' : 'Danh Sách Cây Trồng & Mùa Vụ'}</span>
              <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-800 font-bold border border-emerald-200">
                {penName}
              </span>
            </h4>
            <p className="text-xs text-fb-muted mt-0.5 flex items-center gap-2">
              <span>{isLivestock ? `Tổng số: ${totalCount} cá thể` : `Tổng số: ${totalCount} vụ canh tác`}</span>
              <span>•</span>
              <span className="text-emerald-700 font-semibold">
                {readyCount > 0 
                  ? `🎉 ${readyCount} ${isLivestock ? 'đạt chuẩn xuất chuồng' : 'sẵn sàng thu hoạch'}`
                  : `${isLivestock ? 'Đang nuôi dưỡng tích cực' : 'Đang trong vụ sinh trưởng'}`}
              </span>
            </p>
          </div>
        </div>

        {/* Nút thao tác nhanh trên Header */}
        <div className="flex items-center gap-2 self-end md:self-auto">
          {/* Bộ chuyển chế độ hiển thị Bảng / Thẻ */}
          <div className="flex items-center bg-fb-bg rounded-xl p-1 border border-fb-divider shadow-inner">
            <button
              onClick={() => setViewMode('table')}
              title="Xem dạng Bảng dữ liệu chi tiết"
              className={`p-1.5 rounded-lg text-xs font-bold transition flex items-center gap-1 cursor-pointer ${
                viewMode === 'table'
                  ? 'bg-white text-emerald-700 shadow-sm border border-fb-divider'
                  : 'text-fb-muted hover:text-fb-text'
              }`}
            >
              <TableIcon className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Bảng</span>
            </button>
            <button
              onClick={() => setViewMode('cards')}
              title="Xem dạng Lưới Thẻ trực quan"
              className={`p-1.5 rounded-lg text-xs font-bold transition flex items-center gap-1 cursor-pointer ${
                viewMode === 'cards'
                  ? 'bg-white text-emerald-700 shadow-sm border border-fb-divider'
                  : 'text-fb-muted hover:text-fb-text'
              }`}
            >
              <LayoutGrid className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Thẻ</span>
            </button>
          </div>

          {/* Nút thêm mới */}
          <button
            onClick={onOpenAddModal}
            className="flex items-center gap-1.5 px-3.5 py-2 bg-emerald-600 hover:bg-emerald-700 active:scale-95 text-white rounded-xl font-bold text-xs transition shadow cursor-pointer"
          >
            <Plus className="w-4 h-4" />
            <span>{isLivestock ? 'Thêm Con Vật' : 'Thêm Cây Trồng'}</span>
          </button>
        </div>
      </div>

      {/* 2. Thanh Công Cụ Chung: Tìm kiếm & Lọc trạng thái */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-2.5 my-3 pt-1">
        <div className="relative flex-1">
          <Search className="w-4 h-4 text-fb-muted absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder={
              isLivestock
                ? 'Tìm mã thẻ hoặc loài (VD: HEO_01, Bò, Gà...)'
                : 'Tìm mã hoặc tên giống cây (VD: Dưa lưới, Cà chua...)'
            }
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-fb-bg text-xs rounded-xl pl-9 pr-3 py-2 border border-fb-divider focus:outline-none focus:ring-2 focus:ring-emerald-500 transition"
          />
        </div>

        {/* Lọc theo trạng thái */}
        <div className="flex items-center gap-1 overflow-x-auto pb-1 sm:pb-0 scrollbar-none">
          <button
            onClick={() => setStatusFilter('all')}
            className={`px-2.5 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition cursor-pointer ${
              statusFilter === 'all'
                ? 'bg-emerald-100 text-emerald-900 font-bold border border-emerald-300'
                : 'text-fb-muted hover:bg-fb-hover'
            }`}
          >
            Tất cả ({totalCount})
          </button>
          <button
            onClick={() => setStatusFilter('ready')}
            className={`px-2.5 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition cursor-pointer flex items-center gap-1 ${
              statusFilter === 'ready'
                ? 'bg-emerald-600 text-white font-bold shadow-sm'
                : 'text-fb-muted hover:bg-fb-hover'
            }`}
          >
            <CheckCircle2 className="w-3 h-3" />
            <span>{isLivestock ? 'Đạt Chuẩn Xuất' : 'Sẵn Sàng Thu Hoạch'}</span>
          </button>
          <button
            onClick={() => setStatusFilter('attention')}
            className={`px-2.5 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition cursor-pointer flex items-center gap-1 ${
              statusFilter === 'attention'
                ? 'bg-amber-100 text-amber-900 font-bold border border-amber-300'
                : 'text-fb-muted hover:bg-fb-hover'
            }`}
          >
            <AlertCircle className="w-3 h-3" />
            <span>Cần Chú Ý</span>
          </button>
          <button
            onClick={() => setStatusFilter('healthy')}
            className={`px-2.5 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition cursor-pointer ${
              statusFilter === 'healthy'
                ? 'bg-emerald-50 text-emerald-800 font-bold border border-emerald-200'
                : 'text-fb-muted hover:bg-fb-hover'
            }`}
          >
            {isLivestock ? 'Khỏe Mạnh' : 'Sinh Trưởng Tốt'}
          </button>
        </div>
      </div>

      {/* 3. Khối Danh Sách Hiển Thị: Dạng Bảng hoặc Dạng Thẻ Đồng Bộ */}
      <div className="mt-2">
        {/* === A. EMPTY STATE CHUNG === */}
        {((isLivestock && processedAnimals.length === 0) || (!isLivestock && processedCrops.length === 0)) ? (
          <div className="text-center py-10 px-4 text-fb-muted text-sm border-2 border-dashed border-fb-divider rounded-2xl bg-fb-bg/30">
            <span className="text-4xl block mb-2">{isLivestock ? '🐖' : '🌿'}</span>
            <h5 className="font-bold text-fb-text text-sm">
              {searchQuery || statusFilter !== 'all'
                ? 'Không tìm thấy kết quả phù hợp'
                : isLivestock
                ? 'Chưa có vật nuôi nào trong chuồng này'
                : 'Chưa có cây trồng nào trong vườn này'}
            </h5>
            <p className="text-xs text-fb-muted mt-1 max-w-sm mx-auto">
              {searchQuery || statusFilter !== 'all'
                ? 'Thử thay đổi từ khóa tìm kiếm hoặc bỏ bộ lọc trạng thái để xem đầy đủ.'
                : isLivestock
                ? 'Bấm nút "+ Thêm Con Vật" phía trên để bắt đầu theo dõi tăng trọng và sức khỏe đàn nuôi!'
                : 'Bấm nút "+ Thêm Cây Trồng" phía trên để bắt đầu theo dõi sinh trưởng và lịch tưới bón!'}
            </p>
            {!(searchQuery || statusFilter !== 'all') && (
              <button
                onClick={onOpenAddModal}
                className="mt-3.5 inline-flex items-center gap-1.5 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl font-bold text-xs transition shadow cursor-pointer"
              >
                <Plus className="w-4 h-4" />
                <span>{isLivestock ? 'Thêm Con Vật Mới' : 'Gieo Trồng Vụ Mới'}</span>
              </button>
            )}
          </div>
        ) : viewMode === 'table' ? (
          /* === B. GIAO DIỆN DẠNG BẢNG (TABLE VIEW) ĐỒNG NHẤT 100% === */
          <div className="overflow-x-auto rounded-xl border border-fb-divider">
            <table className="w-full text-left text-sm border-collapse">
              <thead>
                <tr className="border-b border-fb-divider text-[11px] font-bold text-fb-muted uppercase bg-fb-bg/70 tracking-wider">
                  <th className="py-3 px-3.5">Mã Định Danh</th>
                  <th className="py-3 px-3">Phân Loại / Loài</th>
                  <th className="py-3 px-3">{isLivestock ? 'Cân Nặng / Mục Tiêu' : 'Tiến Độ Vụ Mùa'}</th>
                  <th className="py-3 px-3">Trạng Thái Thể Trạng</th>
                  <th className="py-3 px-3.5 text-right">Thao Tác</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-fb-divider">
                {isLivestock
                  ? processedAnimals.map((a) => (
                      <tr key={a.id} className="hover:bg-fb-hover/50 transition">
                        {/* Cột 1: Mã thẻ & Icon */}
                        <td className="py-3 px-3.5 font-bold text-fb-text">
                          <div className="flex items-center gap-2.5">
                            <span className="w-8 h-8 rounded-xl bg-slate-100 flex items-center justify-center text-sm shadow-inner shrink-0">
                              {getSpeciesIcon(a.species)}
                            </span>
                            <div>
                              <span className="font-bold text-fb-text block">{a.id}</span>
                              <span className="text-[10px] text-fb-muted">Mã theo dõi</span>
                            </div>
                          </div>
                        </td>

                        {/* Cột 2: Loài */}
                        <td className="py-3 px-3">
                          <span className="font-semibold text-fb-text text-xs">{a.species}</span>
                        </td>

                        {/* Cột 3: Cân nặng & Tiến độ xuất chuồng */}
                        <td className="py-3 px-3">
                          <div className="flex items-baseline gap-1 text-xs">
                            <strong className="text-fb-text font-bold">{a.weight} kg</strong>
                            <span className="text-fb-muted">/ {a.target_weight} kg</span>
                            <span className="text-[10px] text-emerald-700 font-bold ml-1">({a.pct}%)</span>
                          </div>
                          <div className="w-32 bg-slate-200 h-1.5 rounded-full mt-1.5 overflow-hidden">
                            <div
                              className={`h-full rounded-full transition-all duration-300 ${
                                a.pct >= 100 ? 'bg-emerald-600' : 'bg-emerald-500'
                              }`}
                              style={{ width: `${Math.min(100, a.pct)}%` }}
                            />
                          </div>
                        </td>

                        {/* Cột 4: Huy hiệu trạng thái */}
                        <td className="py-3 px-3">
                          {a.isReady ? (
                            <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2.5 py-1 rounded-full bg-emerald-600 text-white shadow-sm animate-pulse">
                              <CheckCircle2 className="w-3 h-3" /> Đạt Chuẩn Xuất Chuồng
                            </span>
                          ) : a.isSick ? (
                            <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2.5 py-1 rounded-full bg-red-100 text-red-700">
                              <AlertCircle className="w-3 h-3 text-red-500" /> Biếng Ăn / Cần Chú Ý
                            </span>
                          ) : a.isSkinny ? (
                            <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2.5 py-1 rounded-full bg-amber-100 text-amber-800">
                              <AlertCircle className="w-3 h-3 text-amber-500" /> Còi Cọc
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2.5 py-1 rounded-full bg-emerald-100 text-emerald-800">
                              <CheckCircle2 className="w-3 h-3 text-emerald-600" /> Khỏe Mạnh
                            </span>
                          )}
                        </td>

                        {/* Cột 5: Cụm nút thao tác */}
                        <td className="py-3 px-3.5 text-right">
                          <div className="flex items-center justify-end gap-1.5">
                            {onExportAnimal && (
                              <button
                                onClick={() => onExportAnimal(a)}
                                title="Bán hoặc xuất chuồng cá thể này"
                                className={`flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-bold transition shadow-sm cursor-pointer ${
                                  a.isReady
                                    ? 'bg-emerald-600 hover:bg-emerald-700 text-white'
                                    : 'bg-emerald-50 hover:bg-emerald-100 text-emerald-800 border border-emerald-300'
                                }`}
                              >
                                <Truck className="w-3.5 h-3.5" />
                                <span>Xuất Chuồng</span>
                              </button>
                            )}

                            <button
                              onClick={() => onOpenTracking(a.id)}
                              title="Xem biểu đồ tăng trọng theo thời gian"
                              className="p-1.5 rounded-lg bg-blue-50 text-blue-600 hover:bg-blue-100 transition border border-blue-200 cursor-pointer"
                              aria-label="Xem biểu đồ tăng trọng"
                            >
                              <TrendingUp className="w-4 h-4" />
                            </button>

                            <button
                              onClick={() => onOpenHealth(a.id)}
                              title="Xem sổ theo dõi tiêm phòng và y tế"
                              className="p-1.5 rounded-lg bg-rose-50 text-rose-600 hover:bg-rose-100 transition border border-rose-200 cursor-pointer"
                              aria-label="Xem sổ y tế"
                            >
                              <Stethoscope className="w-4 h-4" />
                            </button>

                            <button
                              onClick={() => onDeleteAnimal(a.id)}
                              title="Xóa hồ sơ cá thể này"
                              className="p-1.5 rounded-lg text-slate-400 hover:text-red-600 hover:bg-red-50 transition cursor-pointer"
                              aria-label="Xóa hồ sơ cá thể"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))
                  : processedCrops.map((c) => (
                      <tr key={c.id} className="hover:bg-fb-hover/50 transition">
                        {/* Cột 1: Mã vụ & Icon Cây */}
                        <td className="py-3 px-3.5 font-bold text-fb-text">
                          <div className="flex items-center gap-2.5">
                            <span className="w-8 h-8 rounded-xl bg-slate-100 flex items-center justify-center text-sm shadow-inner shrink-0">
                              {getCropIcon(c.name)}
                            </span>
                            <div>
                              <span className="font-bold text-fb-text block">{c.id}</span>
                              <span className="text-[10px] text-fb-muted">Mã vụ mùa</span>
                            </div>
                          </div>
                        </td>

                        {/* Cột 2: Tên giống cây & Quy mô */}
                        <td className="py-3 px-3">
                          <div className="font-semibold text-fb-text text-xs">{c.name}</div>
                          <span className="text-[10px] text-fb-muted">Quy mô: {c.quantity} gốc/luống</span>
                        </td>

                        {/* Cột 3: Tiến độ sinh trưởng & Ngày gieo trồng */}
                        <td className="py-3 px-3">
                          <div className="flex items-baseline gap-1 text-xs">
                            <strong className="text-fb-text font-bold">
                              {formatDate(c.plant_date || c.planting_date || c.planted_at)}
                            </strong>
                            <span className="text-[10px] text-emerald-700 font-bold ml-1">({c.pct}%)</span>
                          </div>
                          <div className="w-32 bg-slate-200 h-1.5 rounded-full mt-1.5 overflow-hidden">
                            <div
                              className={`h-full rounded-full transition-all duration-300 ${
                                c.pct >= 100 ? 'bg-emerald-600' : 'bg-emerald-500'
                              }`}
                              style={{ width: `${Math.min(100, c.pct)}%` }}
                            />
                          </div>
                        </td>

                        {/* Cột 4: Huy hiệu trạng thái */}
                        <td className="py-3 px-3">
                          {c.isReady ? (
                            <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2.5 py-1 rounded-full bg-emerald-600 text-white shadow-sm animate-pulse">
                              <CheckCircle2 className="w-3 h-3" /> Sẵn Sàng Thu Hoạch
                            </span>
                          ) : c.isSick ? (
                            <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2.5 py-1 rounded-full bg-red-100 text-red-700">
                              <AlertCircle className="w-3 h-3 text-red-500" /> Sâu Bệnh / Cần Chú Ý
                            </span>
                          ) : c.isAttention ? (
                            <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2.5 py-1 rounded-full bg-amber-100 text-amber-800">
                              <AlertCircle className="w-3 h-3 text-amber-500" /> Chậm Lớn / Cần Tưới
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2.5 py-1 rounded-full bg-emerald-100 text-emerald-800">
                              <CheckCircle2 className="w-3 h-3 text-emerald-600" /> Sinh Trưởng Tốt
                            </span>
                          )}
                        </td>

                        {/* Cột 5: Cụm nút thao tác */}
                        <td className="py-3 px-3.5 text-right">
                          <div className="flex items-center justify-end gap-1.5">
                            {onExportCrop ? (
                              <button
                                onClick={() => onExportCrop(c)}
                                title="Thu hoạch hoặc xuất bán vụ mùa này"
                                className={`flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-bold transition shadow-sm cursor-pointer ${
                                  c.isReady
                                    ? 'bg-emerald-600 hover:bg-emerald-700 text-white'
                                    : 'bg-emerald-50 hover:bg-emerald-100 text-emerald-800 border border-emerald-300'
                                }`}
                              >
                                <Scissors className="w-3.5 h-3.5" />
                                <span>Thu Hoạch</span>
                              </button>
                            ) : null}

                            <button
                              onClick={() => onOpenCropTracking(c.id)}
                              title="Xem biểu đồ chiều cao sinh trưởng theo thời gian"
                              className="p-1.5 rounded-lg bg-blue-50 text-blue-600 hover:bg-blue-100 transition border border-blue-200 cursor-pointer"
                              aria-label="Xem biểu đồ sinh trưởng cây"
                            >
                              <TrendingUp className="w-4 h-4" />
                            </button>

                            <button
                              onClick={() => onOpenCropCare(c.id)}
                              title="Xem nhật ký chăm sóc, tưới tiêu và bón phân"
                              className="p-1.5 rounded-lg bg-teal-50 text-teal-700 hover:bg-teal-100 transition border border-teal-200 cursor-pointer"
                              aria-label="Xem nhật ký chăm sóc cây"
                            >
                              <Droplet className="w-4 h-4" />
                            </button>

                            <button
                              onClick={() => onDeleteCrop(c.id)}
                              title="Xóa thông tin vụ mùa này"
                              className="p-1.5 rounded-lg text-slate-400 hover:text-red-600 hover:bg-red-50 transition cursor-pointer"
                              aria-label="Xóa vụ mùa"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
              </tbody>
            </table>
          </div>
        ) : (
          /* === C. GIAO DIỆN DẠNG THẺ (CARDS VIEW) ĐỒNG NHẤT 100% === */
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-2 gap-3.5">
            {isLivestock
              ? processedAnimals.map((a) => (
                  <div
                    key={a.id}
                    className="p-4 rounded-2xl border border-fb-divider bg-fb-bg/30 hover:bg-white hover:shadow-md transition flex flex-col justify-between"
                  >
                    <div>
                      {/* Card Header */}
                      <div className="flex items-start justify-between">
                        <div className="flex items-center gap-2.5">
                          <span className="w-9 h-9 rounded-xl bg-slate-100 flex items-center justify-center text-lg shadow-inner">
                            {getSpeciesIcon(a.species)}
                          </span>
                          <div>
                            <h5 className="font-bold text-sm text-fb-text flex items-center gap-1.5">
                              {a.id}
                              <span className="text-[11px] font-semibold text-fb-muted">({a.species})</span>
                            </h5>
                            <p className="text-[11px] text-fb-muted">Mã định danh chuồng nuôi</p>
                          </div>
                        </div>

                        <button
                          onClick={() => onDeleteAnimal(a.id)}
                          title="Xóa thông tin cá thể này"
                          className="text-slate-400 hover:text-red-600 p-1 rounded-lg hover:bg-red-50 transition cursor-pointer"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>

                      {/* Card Progress Metric */}
                      <div className="mt-3.5 bg-white p-3 rounded-xl border border-fb-divider">
                        <div className="flex items-center justify-between text-xs">
                          <span className="text-fb-muted font-medium">Tiến độ xuất chuồng:</span>
                          <span className="font-bold text-fb-text">
                            {a.weight} kg <span className="text-fb-muted font-normal">/ {a.target_weight} kg</span>
                          </span>
                        </div>
                        <div className="w-full bg-slate-200 h-2 rounded-full mt-2 overflow-hidden">
                          <div
                            className={`h-full rounded-full transition-all duration-300 ${
                              a.pct >= 100 ? 'bg-emerald-600' : 'bg-emerald-500'
                            }`}
                            style={{ width: `${Math.min(100, a.pct)}%` }}
                          />
                        </div>
                        <div className="flex justify-between items-center text-[10px] text-fb-muted mt-1.5">
                          <span>{a.pct}% mục tiêu</span>
                          <span>{Math.max(0, a.target_weight - a.weight)} kg còn lại</span>
                        </div>
                      </div>

                      {/* Card Status Badge */}
                      <div className="mt-2.5">
                        {a.isReady ? (
                          <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2.5 py-0.5 rounded-full bg-emerald-600 text-white shadow-sm animate-pulse">
                            <CheckCircle2 className="w-3 h-3" /> Đạt Chuẩn Xuất Chuồng
                          </span>
                        ) : a.isSick ? (
                          <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2.5 py-0.5 rounded-full bg-red-100 text-red-700">
                            <AlertCircle className="w-3 h-3 text-red-500" /> Biếng Ăn / Cần Chú Ý
                          </span>
                        ) : a.isSkinny ? (
                          <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2.5 py-0.5 rounded-full bg-amber-100 text-amber-800">
                            <AlertCircle className="w-3 h-3 text-amber-500" /> Còi Cọc
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2.5 py-0.5 rounded-full bg-emerald-100 text-emerald-800">
                            <CheckCircle2 className="w-3 h-3 text-emerald-600" /> Khỏe Mạnh
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Card Actions Footer */}
                    <div className="flex items-center gap-2 mt-4 pt-3 border-t border-fb-divider">
                      {onExportAnimal && (
                        <button
                          onClick={() => onExportAnimal(a)}
                          className={`flex-1 py-1.5 px-2 rounded-xl text-xs font-bold transition flex items-center justify-center gap-1 shadow-sm cursor-pointer ${
                            a.isReady
                              ? 'bg-emerald-600 hover:bg-emerald-700 text-white'
                              : 'bg-emerald-50 hover:bg-emerald-100 text-emerald-800 border border-emerald-300'
                          }`}
                        >
                          <Truck className="w-3.5 h-3.5" />
                          <span>Xuất Chuồng</span>
                        </button>
                      )}

                      <button
                        onClick={() => onOpenTracking(a.id)}
                        className="py-1.5 px-2.5 rounded-xl bg-blue-50 hover:bg-blue-100 text-blue-700 text-xs font-bold transition border border-blue-200 flex items-center gap-1 cursor-pointer"
                        title="Xem biểu đồ tăng trọng"
                      >
                        <TrendingUp className="w-3.5 h-3.5" />
                        <span>Tăng Trọng</span>
                      </button>

                      <button
                        onClick={() => onOpenHealth(a.id)}
                        className="py-1.5 px-2.5 rounded-xl bg-rose-50 hover:bg-rose-100 text-rose-700 text-xs font-bold transition border border-rose-200 flex items-center gap-1 cursor-pointer"
                        title="Xem sổ y tế"
                      >
                        <Stethoscope className="w-3.5 h-3.5" />
                        <span>Sổ Y Tế</span>
                      </button>
                    </div>
                  </div>
                ))
              : processedCrops.map((c) => (
                  <div
                    key={c.id}
                    className="p-4 rounded-2xl border border-fb-divider bg-fb-bg/30 hover:bg-white hover:shadow-md transition flex flex-col justify-between"
                  >
                    <div>
                      {/* Card Header */}
                      <div className="flex items-start justify-between">
                        <div className="flex items-center gap-2.5">
                          <span className="w-9 h-9 rounded-xl bg-slate-100 flex items-center justify-center text-lg shadow-inner">
                            {getCropIcon(c.name)}
                          </span>
                          <div>
                            <h5 className="font-bold text-sm text-fb-text flex items-center gap-1.5">
                              {c.name}
                            </h5>
                            <p className="text-[11px] text-fb-muted">Mã: {c.id} • Quy mô: {c.quantity} gốc/luống</p>
                          </div>
                        </div>

                        <button
                          onClick={() => onDeleteCrop(c.id)}
                          title="Xóa thông tin vụ mùa này"
                          className="text-slate-400 hover:text-red-600 p-1 rounded-lg hover:bg-red-50 transition cursor-pointer"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>

                      {/* Card Progress Metric */}
                      <div className="mt-3.5 bg-white p-3 rounded-xl border border-fb-divider">
                        <div className="flex items-center justify-between text-xs">
                          <span className="text-fb-muted font-medium flex items-center gap-1">
                            <Calendar className="w-3.5 h-3.5 text-slate-400" />
                            Gieo trồng:
                          </span>
                          <span className="font-bold text-fb-text">
                            {formatDate(c.plant_date || c.planting_date || c.planted_at)}
                          </span>
                        </div>
                        <div className="w-full bg-slate-200 h-2 rounded-full mt-2 overflow-hidden">
                          <div
                            className={`h-full rounded-full transition-all duration-300 ${
                              c.pct >= 100 ? 'bg-emerald-600' : 'bg-emerald-500'
                            }`}
                            style={{ width: `${Math.min(100, c.pct)}%` }}
                          />
                        </div>
                        <div className="flex justify-between items-center text-[10px] text-fb-muted mt-1.5">
                          <span>{c.pct}% chu kỳ sinh trưởng</span>
                          <span>{c.isReady ? 'Sẵn sàng thu hoạch' : 'Đang phát triển'}</span>
                        </div>
                      </div>

                      {/* Card Status Badge */}
                      <div className="mt-2.5">
                        {c.isReady ? (
                          <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2.5 py-0.5 rounded-full bg-emerald-600 text-white shadow-sm animate-pulse">
                            <CheckCircle2 className="w-3 h-3" /> Sẵn Sàng Thu Hoạch
                          </span>
                        ) : c.isSick ? (
                          <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2.5 py-0.5 rounded-full bg-red-100 text-red-700">
                            <AlertCircle className="w-3 h-3 text-red-500" /> Sâu Bệnh / Cần Chú Ý
                          </span>
                        ) : c.isAttention ? (
                          <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2.5 py-0.5 rounded-full bg-amber-100 text-amber-800">
                            <AlertCircle className="w-3 h-3 text-amber-500" /> Chậm Lớn / Cần Tưới
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2.5 py-0.5 rounded-full bg-emerald-100 text-emerald-800">
                            <CheckCircle2 className="w-3 h-3 text-emerald-600" /> Sinh Trưởng Tốt
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Card Actions Footer */}
                    <div className="flex items-center gap-2 mt-4 pt-3 border-t border-fb-divider">
                      {onExportCrop && (
                        <button
                          onClick={() => onExportCrop(c)}
                          className={`flex-1 py-1.5 px-2 rounded-xl text-xs font-bold transition flex items-center justify-center gap-1 shadow-sm cursor-pointer ${
                            c.isReady
                              ? 'bg-emerald-600 hover:bg-emerald-700 text-white'
                              : 'bg-emerald-50 hover:bg-emerald-100 text-emerald-800 border border-emerald-300'
                          }`}
                        >
                          <Scissors className="w-3.5 h-3.5" />
                          <span>Thu Hoạch</span>
                        </button>
                      )}

                      <button
                        onClick={() => onOpenCropTracking(c.id)}
                        className="py-1.5 px-2.5 rounded-xl bg-blue-50 hover:bg-blue-100 text-blue-700 text-xs font-bold transition border border-blue-200 flex items-center gap-1 cursor-pointer"
                        title="Xem biểu đồ sinh trưởng cây"
                      >
                        <TrendingUp className="w-3.5 h-3.5" />
                        <span>Sinh Trưởng</span>
                      </button>

                      <button
                        onClick={() => onOpenCropCare(c.id)}
                        className="py-1.5 px-2.5 rounded-xl bg-teal-50 hover:bg-teal-100 text-teal-700 text-xs font-bold transition border border-teal-200 flex items-center gap-1 cursor-pointer"
                        title="Xem nhật ký chăm sóc và tưới"
                      >
                        <Droplet className="w-3.5 h-3.5" />
                        <span>Chăm Sóc</span>
                      </button>
                    </div>
                  </div>
                ))}
          </div>
        )}
      </div>
    </div>
  );
}
