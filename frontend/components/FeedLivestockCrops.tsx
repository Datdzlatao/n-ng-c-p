'use client';

import React from 'react';
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
  Truck
} from 'lucide-react';

interface Animal {
  id: string;
  species: string;
  weight: number;
  target_weight: number;
  feeding_status?: string;
  status?: string;
}

interface Crop {
  id: string;
  name: string;
  quantity: number;
  planted_at?: string;
  planting_date?: string;
  plant_date?: string;
  expected_harvest?: string;
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
}: FeedLivestockCropsProps) {
  const isLivestock = currentMode === 'livestock';

  return (
    <div className="bg-fb-card rounded-2xl shadow-fb-card border border-fb-divider p-4 mb-4">
      {/* Tiêu đề & Nút thêm */}
      <div className="flex items-center justify-between pb-3 border-b border-fb-divider">
        <div className="flex items-center gap-2.5">
          <div className="w-10 h-10 rounded-full bg-emerald-100 flex items-center justify-center text-emerald-800 text-xl shadow-inner">
            {isLivestock ? '🐖' : '🌿'}
          </div>
          <div>
            <h4 className="font-bold text-sm text-fb-text">
              {isLivestock ? 'Danh Mục Đàn Vật Nuôi' : 'Danh Sách Cây Trồng'} • {penName}
            </h4>
            <p className="text-xs text-fb-muted">
              {isLivestock
                ? `Tổng số: ${animals.length} cá thể đang theo dõi`
                : `Tổng số: ${crops.length} luống / vụ mùa canh tác`}
            </p>
          </div>
        </div>

        <button
          onClick={onOpenAddModal}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl font-bold text-xs transition shadow cursor-pointer"
        >
          <Plus className="w-4 h-4" />
          <span>{isLivestock ? 'Thêm Con Vật' : 'Thêm Cây Trồng'}</span>
        </button>
      </div>

      {/* Nội dung danh sách */}
      <div className="mt-4">
        {isLivestock ? (
          animals.length === 0 ? (
            <div className="text-center py-8 text-fb-muted text-sm border-2 border-dashed border-fb-divider rounded-xl">
              <span className="text-3xl block mb-2">🐖</span>
              Chưa có vật nuôi nào trong chuồng này. Hãy bấm "+ Thêm Con Vật" để bắt đầu theo dõi!
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-fb-divider text-xs text-fb-muted uppercase bg-fb-bg/50">
                    <th className="py-2.5 px-3 rounded-l-lg">Mã Thẻ</th>
                    <th className="py-2.5 px-3">Loài</th>
                    <th className="py-2.5 px-3">Cân Nặng / Mục Tiêu</th>
                    <th className="py-2.5 px-3">Thể Trạng</th>
                    <th className="py-2.5 px-3 text-right rounded-r-lg">Thao Tác</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-fb-divider">
                  {animals.map((a) => {
                    const pct = a.target_weight ? Math.min(100, (a.weight / a.target_weight) * 100) : 50;
                    const isSick = a.feeding_status === 'Anorexic' || a.status === 'Sick';
                    const isSkinny = a.target_weight && a.weight < a.target_weight * 0.8;

                    return (
                      <tr key={a.id} className="hover:bg-fb-hover/50 transition">
                        {/* Mã định danh con vật */}
                        <td className="py-3 px-3 font-bold text-fb-text flex items-center gap-2">
                          <span className="w-7 h-7 rounded-full bg-slate-100 flex items-center justify-center text-xs">
                            {a.species === 'Gà' ? '🐔' : a.species === 'Bò' ? '🐮' : '🐷'}
                          </span>
                          <span>{a.id}</span>
                        </td>

                        {/* Loài */}
                        <td className="py-3 px-3 text-fb-muted font-medium">{a.species}</td>

                        {/* Cân nặng hiện tại và tiến độ xuất chuồng */}
                        <td className="py-3 px-3">
                          <div className="flex items-baseline gap-1 text-xs">
                            <strong className="text-fb-text">{a.weight} kg</strong>
                            <span className="text-fb-muted">/ {a.target_weight} kg</span>
                          </div>
                          <div className="w-28 bg-slate-200 h-1.5 rounded-full mt-1.5 overflow-hidden">
                            <div
                              className="h-full bg-emerald-600 rounded-full transition-all"
                              style={{ width: `${pct}%` }}
                            />
                          </div>
                        </td>

                        {/* Huy hiệu thể trạng */}
                        <td className="py-3 px-3">
                          {pct >= 100 ? (
                            <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2.5 py-0.5 rounded-full bg-emerald-600 text-white shadow-sm animate-pulse">
                              <CheckCircle2 className="w-3 h-3" /> Đạt Chuẩn Xuất Chuồng
                            </span>
                          ) : isSick ? (
                            <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2.5 py-0.5 rounded-full bg-red-100 text-red-700">
                              <AlertCircle className="w-3 h-3 text-red-500" /> Biếng Ăn / Cần Chú Ý
                            </span>
                          ) : isSkinny ? (
                            <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2.5 py-0.5 rounded-full bg-amber-100 text-amber-700">
                              <AlertCircle className="w-3 h-3 text-amber-500" /> Còi Cọc
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2.5 py-0.5 rounded-full bg-emerald-100 text-emerald-800">
                              <CheckCircle2 className="w-3 h-3 text-emerald-600" /> Khỏe Mạnh
                            </span>
                          )}
                        </td>

                        {/* Các nút thao tác */}
                        <td className="py-3 px-3 text-right">
                          <div className="flex items-center justify-end gap-1.5">
                            {onExportAnimal && (
                              <button
                                onClick={() => onExportAnimal(a)}
                                title="Bán hoặc xuất chuồng cá thể này"
                                className={`flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-bold transition shadow-sm cursor-pointer ${
                                  pct >= 100
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
                              className="p-1.5 rounded-lg bg-red-50 text-red-600 hover:bg-red-100 transition border border-red-200 cursor-pointer"
                              aria-label="Xem sổ y tế"
                            >
                              <Stethoscope className="w-4 h-4" />
                            </button>

                            <button
                              onClick={() => onDeleteAnimal(a.id)}
                              title="Xóa thông tin cá thể này"
                              className="p-1.5 rounded-lg text-slate-400 hover:text-red-600 hover:bg-red-50 transition cursor-pointer"
                              aria-label="Xóa hồ sơ cá thể"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )
        ) : (
          /* Giao diện xem cây trồng */
          crops.length === 0 ? (
            <div className="text-center py-8 text-fb-muted text-sm border-2 border-dashed border-fb-divider rounded-xl">
              <span className="text-3xl block mb-2">🌿</span>
              Chưa có cây trồng nào trong vườn này. Hãy bấm "+ Thêm Cây Trồng" để bắt đầu!
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {crops.map((c) => (
                <div
                  key={c.id}
                  className="p-3.5 rounded-xl border border-fb-divider bg-fb-bg/40 hover:bg-white hover:shadow-sm transition"
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <h5 className="font-bold text-sm text-fb-text flex items-center gap-1.5">
                        <Sprout className="w-4 h-4 text-emerald-600" />
                        {c.name}
                      </h5>
                      <p className="text-xs text-fb-muted mt-0.5">
                        Quy mô: <strong>{c.quantity} gốc / luống</strong>
                      </p>
                    </div>

                    <button
                      onClick={() => onDeleteCrop(c.id)}
                      title="Xóa thông tin vụ mùa này"
                      className="text-slate-400 hover:text-red-600 p-1 rounded cursor-pointer"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>

                  <div className="flex items-center gap-1.5 text-xs text-slate-500 mt-2">
                    <Calendar className="w-3.5 h-3.5 text-slate-400" />
                    <span>Ngày gieo trồng: {c.planting_date || c.planted_at || 'Mới trồng'}</span>
                  </div>

                  <div className="flex gap-2 mt-3 pt-2.5 border-t border-fb-divider">
                    <button
                      onClick={() => onOpenCropTracking(c.id)}
                      className="flex-1 py-1.5 px-2 bg-emerald-50 hover:bg-emerald-100 text-emerald-800 text-xs font-bold rounded-lg transition border border-emerald-200 flex items-center justify-center gap-1 cursor-pointer"
                    >
                      <TrendingUp className="w-3.5 h-3.5" />
                      Sinh Trưởng
                    </button>

                    <button
                      onClick={() => onOpenCropCare(c.id)}
                      className="flex-1 py-1.5 px-2 bg-blue-50 hover:bg-blue-100 text-blue-700 text-xs font-bold rounded-lg transition border border-blue-200 flex items-center justify-center gap-1 cursor-pointer"
                    >
                      <Droplet className="w-3.5 h-3.5" />
                      Chăm Sóc & Tưới
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )
        )}
      </div>
    </div>
  );
}
