'use client';

import React, { useState } from 'react';
import { 
  X, 
  Plus, 
  Trash2, 
  Scale, 
  TrendingUp, 
  Stethoscope, 
  Package, 
  Sprout, 
  Cpu, 
  Droplet,
  Calendar,
  CheckCircle2,
  AlertCircle,
  Scissors,
  ShieldCheck,
  Activity
} from 'lucide-react';
import { Line } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

interface ModalWrapperProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  icon?: string | React.ReactNode;
  children: React.ReactNode;
}

function ModalWrapper({ isOpen, onClose, title, icon, children }: ModalWrapperProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-150">
      <div className="bg-fb-card w-full max-w-lg rounded-2xl shadow-2xl border border-fb-divider overflow-hidden flex flex-col max-h-[92vh]">
        {/* Modal Header */}
        <div className="p-4 border-b border-fb-divider flex items-center justify-between bg-fb-bg/40">
          <h3 className="font-bold text-base text-fb-text flex items-center gap-2">
            {typeof icon === 'string' ? <span className="text-xl">{icon}</span> : icon}
            <span>{title}</span>
          </h3>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-full hover:bg-fb-hover flex items-center justify-center text-fb-muted hover:text-fb-text transition cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-4 overflow-y-auto flex-1">{children}</div>
      </div>
    </div>
  );
}

// ==========================================
// 1. Modal Thêm Khu Vực / Chuồng
// ==========================================
export function ModalAddPen({
  isOpen,
  onClose,
  onAdd,
}: {
  isOpen: boolean;
  onClose: () => void;
  onAdd: (type: string, id: string, name: string) => Promise<void>;
}) {
  const [type, setType] = useState('livestock');
  const [id, setId] = useState('');
  const [name, setName] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!id || !name) return alert('Vui lòng điền đủ mã và tên khu vực');
    await onAdd(type, id, name);
    setId('');
    setName('');
    onClose();
  };

  return (
    <ModalWrapper isOpen={isOpen} onClose={onClose} title="Thêm Khu Vực / Vườn Trồng Mới" icon="🏡">
      <form onSubmit={handleSubmit} className="space-y-3.5">
        <div>
          <label className="block text-xs font-semibold text-fb-muted mb-1">Loại Phân Hệ Quản Lý</label>
          <select
            value={type}
            onChange={(e) => setType(e.target.value)}
            className="w-full bg-fb-bg text-sm rounded-xl px-3 py-2 border border-fb-divider focus:ring-2 focus:ring-emerald-500 font-medium"
          >
            <option value="livestock">🐖 Chuồng Trại Chăn Nuôi</option>
            <option value="cultivation">🌿 Vườn Canh Tác / Nhà Màng Trồng Trọt</option>
          </select>
        </div>

        <div>
          <label className="block text-xs font-semibold text-fb-muted mb-1">Mã Khu Vực (ID)</label>
          <input
            type="text"
            placeholder={type === 'livestock' ? 'VD: CHUONG_03, PEN_A03' : 'VD: VUON_02, PEN_B02'}
            value={id}
            onChange={(e) => setId(e.target.value)}
            className="w-full bg-fb-bg text-sm rounded-xl px-3 py-2 border border-fb-divider focus:ring-2 focus:ring-emerald-500"
          />
        </div>

        <div>
          <label className="block text-xs font-semibold text-fb-muted mb-1">Tên Khu Vực / Mô Tả</label>
          <input
            type="text"
            placeholder={type === 'livestock' ? 'VD: Chuồng Heo Thịt Khu A3' : 'VD: Khu Nhà Màng Dưa Lưới B2'}
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full bg-fb-bg text-sm rounded-xl px-3 py-2 border border-fb-divider focus:ring-2 focus:ring-emerald-500"
          />
        </div>

        <div className="flex gap-2 pt-2 border-t border-fb-divider">
          <button
            type="button"
            onClick={onClose}
            className="flex-1 py-2 rounded-xl border border-fb-divider text-xs font-semibold hover:bg-fb-hover cursor-pointer"
          >
            Hủy
          </button>
          <button
            type="submit"
            className="flex-1 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold shadow cursor-pointer"
          >
            Lưu Khu Vực
          </button>
        </div>
      </form>
    </ModalWrapper>
  );
}

// ==========================================
// 2. Modal Thêm Thiết Bị IoT
// ==========================================
export function ModalAddDevice({
  isOpen,
  onClose,
  onAdd,
}: {
  isOpen: boolean;
  onClose: () => void;
  onAdd: (id: string, name: string, pin: number) => Promise<void>;
}) {
  const [id, setId] = useState('');
  const [name, setName] = useState('');
  const [pin, setPin] = useState(5);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!id || !name) return alert('Vui lòng điền đủ thông tin thiết bị');
    await onAdd(id, name, Number(pin));
    setId('');
    setName('');
    onClose();
  };

  return (
    <ModalWrapper isOpen={isOpen} onClose={onClose} title="Thêm Thiết Bị Nông Trại" icon="🎮">
      <form onSubmit={handleSubmit} className="space-y-3.5">
        <div>
          <label className="block text-xs font-semibold text-fb-muted mb-1">Mã Thiết Bị (ID)</label>
          <input
            type="text"
            placeholder="VD: QUAT_02, BOM_01, PHUN_02"
            value={id}
            onChange={(e) => setId(e.target.value)}
            className="w-full bg-fb-bg text-sm rounded-xl px-3 py-2 border border-fb-divider focus:ring-2 focus:ring-emerald-500"
          />
        </div>

        <div>
          <label className="block text-xs font-semibold text-fb-muted mb-1">Tên Thiết Bị</label>
          <input
            type="text"
            placeholder="VD: Quạt Thông Gió, Máy Bơm Tưới Tự Động..."
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full bg-fb-bg text-sm rounded-xl px-3 py-2 border border-fb-divider focus:ring-2 focus:ring-emerald-500"
          />
        </div>

        <div>
          <label className="block text-xs font-semibold text-fb-muted mb-1">Chân GPIO Điều Khiển (Pin Relay)</label>
          <input
            type="number"
            value={pin}
            onChange={(e) => setPin(Number(e.target.value))}
            className="w-full bg-fb-bg text-sm rounded-xl px-3 py-2 border border-fb-divider focus:ring-2 focus:ring-emerald-500"
          />
        </div>

        <div className="flex gap-2 pt-2 border-t border-fb-divider">
          <button
            type="button"
            onClick={onClose}
            className="flex-1 py-2 rounded-xl border border-fb-divider text-xs font-semibold hover:bg-fb-hover cursor-pointer"
          >
            Hủy
          </button>
          <button
            type="submit"
            className="flex-1 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold shadow cursor-pointer"
          >
            Lưu Thiết Bị
          </button>
        </div>
      </form>
    </ModalWrapper>
  );
}

// ==========================================
// 3. Modal Thêm Vật Nuôi (Chăn Nuôi)
// ==========================================
export function ModalAddAnimal({
  isOpen,
  onClose,
  onAdd,
}: {
  isOpen: boolean;
  onClose: () => void;
  onAdd: (id: string, species: string, weight: number, targetWeight: number) => Promise<void>;
}) {
  const [id, setId] = useState('');
  const [species, setSpecies] = useState('Heo');
  const [weight, setWeight] = useState(25);
  const [target, setTarget] = useState(100);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!id) return alert('Vui lòng nhập mã con vật');
    await onAdd(id, species, Number(weight), Number(target));
    setId('');
    onClose();
  };

  return (
    <ModalWrapper isOpen={isOpen} onClose={onClose} title="Nhập Hồ Sơ Vật Nuôi Mới" icon="🐖">
      <form onSubmit={handleSubmit} className="space-y-3.5">
        <div>
          <label className="block text-xs font-semibold text-fb-muted mb-1">Mã Thẻ / Số Tai Định Danh</label>
          <input
            type="text"
            placeholder="VD: HEO_105, GA_02, BO_03"
            value={id}
            onChange={(e) => setId(e.target.value)}
            className="w-full bg-fb-bg text-sm rounded-xl px-3 py-2 border border-fb-divider focus:ring-2 focus:ring-emerald-500"
          />
        </div>

        <div>
          <label className="block text-xs font-semibold text-fb-muted mb-1">Loài Vật Nuôi</label>
          <select
            value={species}
            onChange={(e) => setSpecies(e.target.value)}
            className="w-full bg-fb-bg text-sm rounded-xl px-3 py-2 border border-fb-divider focus:ring-2 focus:ring-emerald-500 font-medium"
          >
            <option value="Heo">🐷 Heo (Lợn)</option>
            <option value="Gà">🐔 Gà</option>
            <option value="Bò">🐮 Bò</option>
            <option value="Dê">🐐 Dê</option>
            <option value="Vịt">🦆 Vịt</option>
          </select>
        </div>

        <div className="grid grid-cols-2 gap-2.5">
          <div>
            <label className="block text-xs font-semibold text-fb-muted mb-1">Cân Nặng Hiện Tại (kg)</label>
            <input
              type="number"
              step="0.1"
              value={weight}
              onChange={(e) => setWeight(Number(e.target.value))}
              className="w-full bg-fb-bg text-sm rounded-xl px-3 py-2 border border-fb-divider focus:ring-2 focus:ring-emerald-500"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-fb-muted mb-1">Mục Tiêu Xuất Chuồng (kg)</label>
            <input
              type="number"
              step="0.1"
              value={target}
              onChange={(e) => setTarget(Number(e.target.value))}
              className="w-full bg-fb-bg text-sm rounded-xl px-3 py-2 border border-fb-divider focus:ring-2 focus:ring-emerald-500"
            />
          </div>
        </div>

        <div className="flex gap-2 pt-2 border-t border-fb-divider">
          <button
            type="button"
            onClick={onClose}
            className="flex-1 py-2 rounded-xl border border-fb-divider text-xs font-semibold hover:bg-fb-hover cursor-pointer"
          >
            Hủy
          </button>
          <button
            type="submit"
            className="flex-1 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold shadow cursor-pointer"
          >
            Lưu Hồ Sơ
          </button>
        </div>
      </form>
    </ModalWrapper>
  );
}

// ==========================================
// 4. Modal Thêm Cây Trồng (Trồng Trọt) - Đồng nhất với ModalAddAnimal
// ==========================================
export function ModalAddCrop({
  isOpen,
  onClose,
  onAdd,
}: {
  isOpen: boolean;
  onClose: () => void;
  onAdd: (name: string, qty: number, date: string, expectedHarvest?: string) => Promise<void>;
}) {
  const [name, setName] = useState('');
  const [qty, setQty] = useState('');
  const [date, setDate] = useState(new Date().toISOString().split('T')[0]);
  const [expectedHarvest, setExpectedHarvest] = useState(() => {
    const d = new Date();
    d.setDate(d.getDate() + 65);
    return d.toISOString().split('T')[0];
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name || !qty) return alert('Vui lòng điền đủ tên giống cây và số lượng gốc');
    await onAdd(name, parseInt(qty), date, expectedHarvest);
    setName('');
    setQty('');
    onClose();
  };

  return (
    <ModalWrapper isOpen={isOpen} onClose={onClose} title="Gieo Trồng Vụ Mùa Mới" icon="🌿">
      <form onSubmit={handleSubmit} className="space-y-3.5">
        <div>
          <label className="block text-xs font-semibold text-fb-muted mb-1">Tên Giống Cây Trồng</label>
          <input
            type="text"
            placeholder="VD: Dưa Lưới Fuji F1, Cà Chua Bi Hà Lan, Lúa ST25..."
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full bg-fb-bg text-sm rounded-xl px-3 py-2 border border-fb-divider focus:ring-2 focus:ring-emerald-500"
          />
        </div>

        <div>
          <label className="block text-xs font-semibold text-fb-muted mb-1">Quy Mô Số Lượng (Gốc / Luống / Khay)</label>
          <input
            type="number"
            placeholder="VD: 500"
            value={qty}
            onChange={(e) => setQty(e.target.value)}
            className="w-full bg-fb-bg text-sm rounded-xl px-3 py-2 border border-fb-divider focus:ring-2 focus:ring-emerald-500"
          />
        </div>

        <div className="grid grid-cols-2 gap-2.5">
          <div>
            <label className="block text-xs font-semibold text-fb-muted mb-1">Ngày Gieo Trồng</label>
            <input
              type="date"
              value={date}
              onChange={(e) => setDate(e.target.value)}
              className="w-full bg-fb-bg text-sm rounded-xl px-3 py-2 border border-fb-divider focus:ring-2 focus:ring-emerald-500"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-fb-muted mb-1">Dự Kiến Thu Hoạch</label>
            <input
              type="date"
              value={expectedHarvest}
              onChange={(e) => setExpectedHarvest(e.target.value)}
              className="w-full bg-fb-bg text-sm rounded-xl px-3 py-2 border border-fb-divider focus:ring-2 focus:ring-emerald-500"
            />
          </div>
        </div>

        <div className="flex gap-2 pt-2 border-t border-fb-divider">
          <button
            type="button"
            onClick={onClose}
            className="flex-1 py-2 rounded-xl border border-fb-divider text-xs font-semibold hover:bg-fb-hover cursor-pointer"
          >
            Hủy
          </button>
          <button
            type="submit"
            className="flex-1 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold shadow cursor-pointer"
          >
            Lưu Vụ Mùa
          </button>
        </div>
      </form>
    </ModalWrapper>
  );
}

// ==========================================
// 5. Modal Theo Dõi Cân Nặng (Chăn Nuôi)
// ==========================================
export function ModalWeightTracking({
  isOpen,
  onClose,
  animalId,
  logs,
  onSaveWeight,
  onDeleteWeight,
}: {
  isOpen: boolean;
  onClose: () => void;
  animalId: string;
  logs: Array<{ id?: string | number; created_at?: string; weight: number }>;
  onSaveWeight: (weight: number) => Promise<void>;
  onDeleteWeight?: (logId: string) => Promise<void>;
}) {
  const [newWeight, setNewWeight] = useState('');

  // Sorted chronological logs
  const sortedLogs = [...logs].sort((a, b) => {
    const da = a.created_at ? new Date(a.created_at).getTime() : 0;
    const db = b.created_at ? new Date(b.created_at).getTime() : 0;
    return da - db;
  });

  const latestWeight = sortedLogs.length > 0 ? sortedLogs[sortedLogs.length - 1].weight : '--';

  const chartData = {
    labels: sortedLogs.length > 0 
      ? sortedLogs.map(l => l.created_at ? new Date(l.created_at).toLocaleDateString('vi-VN') : '--') 
      : ['Lần 1', 'Lần 2'],
    datasets: [
      {
        label: 'Cân nặng (kg)',
        data: sortedLogs.length > 0 ? sortedLogs.map(l => l.weight) : [20, 25],
        borderColor: '#10B981',
        backgroundColor: 'rgba(16, 185, 129, 0.12)',
        tension: 0.35,
        fill: true,
        pointRadius: 4,
        pointBackgroundColor: '#10B981',
      },
    ],
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newWeight) return alert('Vui lòng nhập cân nặng mới');
    await onSaveWeight(parseFloat(newWeight));
    setNewWeight('');
  };

  return (
    <ModalWrapper isOpen={isOpen} onClose={onClose} title={`Biểu Đồ Tăng Trọng: ${animalId}`} icon="📈">
      <div className="space-y-3.5">
        {/* Top Summary Cards */}
        <div className="grid grid-cols-2 gap-2.5">
          <div className="p-3 bg-emerald-50 rounded-xl border border-emerald-200">
            <span className="text-[11px] font-semibold text-emerald-800 block">Cân Nặng Mới Nhất</span>
            <div className="flex items-baseline gap-1 mt-0.5">
              <strong className="text-xl font-extrabold text-emerald-950">{latestWeight}</strong>
              <span className="text-xs text-emerald-800">kg</span>
            </div>
          </div>

          <div className="p-3 bg-blue-50 rounded-xl border border-blue-200">
            <span className="text-[11px] font-semibold text-blue-800 block">Tổng Lần Ghi Nhận</span>
            <div className="flex items-baseline gap-1 mt-0.5">
              <strong className="text-xl font-extrabold text-blue-950">{logs.length}</strong>
              <span className="text-xs text-blue-800">lần cân</span>
            </div>
          </div>
        </div>

        {/* Biểu đồ Chart */}
        <div className="h-52 bg-fb-bg rounded-xl p-2.5 border border-fb-divider">
          <Line
            data={chartData}
            options={{
              responsive: true,
              maintainAspectRatio: false,
              plugins: { legend: { display: false } },
            }}
          />
        </div>

        {/* Form Cập nhật số cân mới */}
        <form onSubmit={handleSubmit} className="p-3 bg-emerald-50/60 border border-emerald-200 rounded-xl space-y-2">
          <label className="block text-xs font-bold text-emerald-900">
            ⚖️ Cập Nhật Số Cân Mới (kg):
          </label>
          <div className="flex gap-2">
            <input
              type="number"
              step="0.1"
              placeholder="VD: 32.5"
              value={newWeight}
              onChange={(e) => setNewWeight(e.target.value)}
              className="flex-1 bg-white text-sm rounded-lg px-3 py-2 border border-emerald-300 focus:outline-none focus:ring-2 focus:ring-emerald-500"
            />
            <button
              type="submit"
              className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs rounded-lg shadow cursor-pointer"
            >
              Lưu Số Cân
            </button>
          </div>
        </form>

        {/* Lịch sử các lần cân */}
        <div className="max-h-40 overflow-y-auto space-y-1.5 pr-1">
          <span className="text-xs font-bold text-fb-muted block mb-1">Lịch sử cân đo:</span>
          {sortedLogs.length === 0 ? (
            <p className="text-center py-3 text-xs text-fb-muted">Chưa có mốc cân đo nào.</p>
          ) : (
            sortedLogs.slice().reverse().map((l, i) => (
              <div
                key={l.id || i}
                className="p-2 rounded-xl border border-fb-divider bg-fb-bg/40 flex items-center justify-between text-xs"
              >
                <div className="flex items-center gap-2">
                  <Scale className="w-3.5 h-3.5 text-emerald-600" />
                  <span className="font-bold text-fb-text">{l.weight} kg</span>
                  <span className="text-[11px] text-fb-muted">
                    {l.created_at ? new Date(l.created_at).toLocaleString('vi-VN') : 'Gần đây'}
                  </span>
                </div>
                {onDeleteWeight && l.id && (
                  <button
                    onClick={() => onDeleteWeight(String(l.id))}
                    className="p-1 text-slate-400 hover:text-red-600 transition"
                    title="Xóa mốc cân này"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>
            ))
          )}
        </div>
      </div>
    </ModalWrapper>
  );
}

// ==========================================
// 6. Modal Theo Dõi Sinh Trưởng Cây (Trồng Trọt) - Đồng nhất với ModalWeightTracking
// ==========================================
export function ModalCropTracking({
  isOpen,
  onClose,
  cropId,
  logs,
  onSaveGrowth,
  onDeleteGrowth,
}: {
  isOpen: boolean;
  onClose: () => void;
  cropId: string;
  logs: Array<{ id?: string | number; created_at?: string; height_or_size?: number; size?: number }>;
  onSaveGrowth: (size: number) => Promise<void>;
  onDeleteGrowth?: (logId: string) => Promise<void>;
}) {
  const [size, setSize] = useState('');

  // Sorted chronological logs
  const sortedLogs = [...logs].sort((a, b) => {
    const da = a.created_at ? new Date(a.created_at).getTime() : 0;
    const db = b.created_at ? new Date(b.created_at).getTime() : 0;
    return da - db;
  });

  const getLogVal = (l: any) => l.height_or_size ?? l.size ?? 0;
  const latestSize = sortedLogs.length > 0 ? getLogVal(sortedLogs[sortedLogs.length - 1]) : '--';

  const chartData = {
    labels: sortedLogs.length > 0 
      ? sortedLogs.map(l => l.created_at ? new Date(l.created_at).toLocaleDateString('vi-VN') : '--') 
      : ['Lần 1', 'Lần 2'],
    datasets: [
      {
        label: 'Chiều cao / Kích thước (cm)',
        data: sortedLogs.length > 0 ? sortedLogs.map(l => getLogVal(l)) : [15, 28],
        borderColor: '#10B981',
        backgroundColor: 'rgba(16, 185, 129, 0.12)',
        tension: 0.35,
        fill: true,
        pointRadius: 4,
        pointBackgroundColor: '#10B981',
      },
    ],
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!size) return alert('Vui lòng nhập chiều cao mới của cây');
    await onSaveGrowth(parseFloat(size));
    setSize('');
  };

  return (
    <ModalWrapper isOpen={isOpen} onClose={onClose} title={`Biểu Đồ Sinh Trưởng: ${cropId}`} icon="📏">
      <div className="space-y-3.5">
        {/* Top Summary Cards */}
        <div className="grid grid-cols-2 gap-2.5">
          <div className="p-3 bg-emerald-50 rounded-xl border border-emerald-200">
            <span className="text-[11px] font-semibold text-emerald-800 block">Kích Thước Mới Nhất</span>
            <div className="flex items-baseline gap-1 mt-0.5">
              <strong className="text-xl font-extrabold text-emerald-950">{latestSize}</strong>
              <span className="text-xs text-emerald-800">cm</span>
            </div>
          </div>

          <div className="p-3 bg-blue-50 rounded-xl border border-blue-200">
            <span className="text-[11px] font-semibold text-blue-800 block">Tổng Lần Ghi Nhận</span>
            <div className="flex items-baseline gap-1 mt-0.5">
              <strong className="text-xl font-extrabold text-blue-950">{logs.length}</strong>
              <span className="text-xs text-blue-800">lần đo</span>
            </div>
          </div>
        </div>

        {/* Biểu đồ Chart */}
        <div className="h-52 bg-fb-bg rounded-xl p-2.5 border border-fb-divider">
          <Line
            data={chartData}
            options={{
              responsive: true,
              maintainAspectRatio: false,
              plugins: { legend: { display: false } },
            }}
          />
        </div>

        {/* Form Cập nhật kích thước mới */}
        <form onSubmit={handleSubmit} className="p-3 bg-emerald-50/60 border border-emerald-200 rounded-xl space-y-2">
          <label className="block text-xs font-bold text-emerald-900">
            📏 Cập Nhật Chiều Cao / Kích Thước Mới (cm):
          </label>
          <div className="flex gap-2">
            <input
              type="number"
              step="0.5"
              placeholder="VD: 45"
              value={size}
              onChange={(e) => setSize(e.target.value)}
              className="flex-1 bg-white text-sm rounded-lg px-3 py-2 border border-emerald-300 focus:outline-none focus:ring-2 focus:ring-emerald-500"
            />
            <button
              type="submit"
              className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs rounded-lg shadow cursor-pointer"
            >
              Lưu Chiều Cao
            </button>
          </div>
        </form>

        {/* Lịch sử các lần đo */}
        <div className="max-h-40 overflow-y-auto space-y-1.5 pr-1">
          <span className="text-xs font-bold text-fb-muted block mb-1">Lịch sử đo đạc sinh trưởng:</span>
          {sortedLogs.length === 0 ? (
            <p className="text-center py-3 text-xs text-fb-muted">Chưa có mốc đo chiều cao nào.</p>
          ) : (
            sortedLogs.slice().reverse().map((l, i) => (
              <div
                key={l.id || i}
                className="p-2 rounded-xl border border-fb-divider bg-fb-bg/40 flex items-center justify-between text-xs"
              >
                <div className="flex items-center gap-2">
                  <Sprout className="w-3.5 h-3.5 text-emerald-600" />
                  <span className="font-bold text-fb-text">{getLogVal(l)} cm</span>
                  <span className="text-[11px] text-fb-muted">
                    {l.created_at ? new Date(l.created_at).toLocaleString('vi-VN') : 'Gần đây'}
                  </span>
                </div>
                {onDeleteGrowth && l.id && (
                  <button
                    onClick={() => onDeleteGrowth(String(l.id))}
                    className="p-1 text-slate-400 hover:text-red-600 transition"
                    title="Xóa mốc đo này"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>
            ))
          )}
        </div>
      </div>
    </ModalWrapper>
  );
}

// ==========================================
// 7. Modal Sức Khỏe & Thú Y (Chăn Nuôi)
// ==========================================
export function ModalHealth({
  isOpen,
  onClose,
  animalId,
  logs,
  onAddLog,
  onDeleteLog,
}: {
  isOpen: boolean;
  onClose: () => void;
  animalId: string;
  logs: Array<{ id: string; type: string; action?: string; note?: string; created_at?: string }>;
  onAddLog: (type: string, action: string, note: string) => Promise<void>;
  onDeleteLog: (logId: string) => Promise<void>;
}) {
  const [type, setType] = useState('Vaccine');
  const [action, setAction] = useState('');
  const [note, setNote] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!action) return alert('Vui lòng nhập tên thuốc hoặc triệu chứng bệnh');
    await onAddLog(type, action, note);
    setAction('');
    setNote('');
  };

  return (
    <ModalWrapper isOpen={isOpen} onClose={onClose} title={`Sổ Y Tế & Thú Y: ${animalId}`} icon="🏥">
      <div className="space-y-3.5">
        {/* Form ghi chép mới */}
        <form onSubmit={handleSubmit} className="p-3 bg-rose-50 border border-rose-200 rounded-xl space-y-2">
          <span className="text-xs font-bold text-rose-900 block">Thêm Ghi Chép Thú Y Mới:</span>
          
          <div className="grid grid-cols-2 gap-2">
            <select
              value={type}
              onChange={(e) => setType(e.target.value)}
              className="bg-white text-xs rounded-lg px-2.5 py-1.5 border border-rose-300 focus:outline-none font-semibold text-rose-900"
            >
              <option value="Vaccine">💉 Tiêm Vắc-xin</option>
              <option value="Treatment">💊 Điều trị / Thuốc</option>
              <option value="Sick">🚑 Phát hiện bệnh</option>
              <option value="Checkup">🩺 Khám sức khỏe</option>
            </select>

            <input
              type="text"
              placeholder="Tên thuốc / bệnh (VD: Tai xanh)"
              value={action}
              onChange={(e) => setAction(e.target.value)}
              className="bg-white text-xs rounded-lg px-2.5 py-1.5 border border-rose-300 focus:outline-none"
            />
          </div>

          <input
            type="text"
            placeholder="Ghi chú chi tiết (VD: Sốt nhẹ, đã tiêm hạ sốt liều 1...)"
            value={note}
            onChange={(e) => setNote(e.target.value)}
            className="w-full bg-white text-xs rounded-lg px-2.5 py-1.5 border border-rose-300 focus:outline-none"
          />

          <button
            type="submit"
            className="w-full py-2 bg-rose-600 hover:bg-rose-700 text-white rounded-lg text-xs font-bold transition shadow cursor-pointer"
          >
            Lưu Ghi Chép Thú Y
          </button>
        </form>

        {/* Danh sách lịch sử y tế */}
        <div className="max-h-56 overflow-y-auto space-y-2 pr-1">
          <span className="text-xs font-bold text-fb-muted block mb-1">Nhật ký điều trị & vắc-xin:</span>
          {logs.length === 0 ? (
            <p className="text-center py-4 text-xs text-fb-muted">Chưa có lịch sử bệnh án nào.</p>
          ) : (
            logs.map((l) => (
              <div
                key={l.id}
                className="p-2.5 rounded-xl border border-fb-divider bg-fb-bg/40 flex items-center justify-between text-xs"
              >
                <div>
                  <div className="flex items-center gap-1.5">
                    <span className="font-bold text-rose-700 bg-rose-100 px-1.5 py-0.5 rounded text-[10px]">
                      {l.type === 'Vaccine' ? '💉 Vắc-xin' : l.type === 'Treatment' ? '💊 Điều trị' : '🚑 Triệu chứng'}
                    </span>
                    <span className="font-semibold text-fb-text">{l.action || l.note}</span>
                  </div>
                  {l.note && l.action && <p className="text-slate-600 mt-0.5 text-[11px]">{l.note}</p>}
                  <span className="text-[10px] text-slate-400 block mt-0.5">
                    {l.created_at ? new Date(l.created_at).toLocaleString('vi-VN') : 'Gần đây'}
                  </span>
                </div>

                <button
                  onClick={() => onDeleteLog(l.id)}
                  className="p-1 text-slate-400 hover:text-red-600 transition cursor-pointer"
                  title="Xóa ghi chép này"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))
          )}
        </div>
      </div>
    </ModalWrapper>
  );
}

// ==========================================
// 8. Modal Chăm Sóc Cây (Trồng Trọt) - Đồng nhất với ModalHealth
// ==========================================
export function ModalCropCare({
  isOpen,
  onClose,
  cropId,
  logs,
  onAddCare,
  onDeleteCare,
}: {
  isOpen: boolean;
  onClose: () => void;
  cropId: string;
  logs: Array<{ id: string; type: string; note: string; action?: string; created_at?: string }>;
  onAddCare: (type: string, note: string, action?: string) => Promise<void>;
  onDeleteCare?: (logId: string) => Promise<void>;
}) {
  const [type, setType] = useState('Water');
  const [action, setAction] = useState('');
  const [note, setNote] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await onAddCare(type, note, action);
    setAction('');
    setNote('');
  };

  return (
    <ModalWrapper isOpen={isOpen} onClose={onClose} title={`Sổ Nhật Ký Canh Tác: ${cropId}`} icon="💦">
      <div className="space-y-3.5">
        {/* Form ghi chép mới */}
        <form onSubmit={handleSubmit} className="p-3 bg-teal-50 border border-teal-200 rounded-xl space-y-2">
          <span className="text-xs font-bold text-teal-900 block">Thêm Ghi Chép Chăm Sóc Mới:</span>

          <div className="grid grid-cols-2 gap-2">
            <select
              value={type}
              onChange={(e) => setType(e.target.value)}
              className="bg-white text-xs rounded-lg px-2.5 py-1.5 border border-teal-300 focus:outline-none font-semibold text-teal-900"
            >
              <option value="Water">💧 Tưới Nước</option>
              <option value="Fertilizer">🧪 Bón Phân NPK</option>
              <option value="Pesticide">⚠️ Phun Thuốc BVTV</option>
              <option value="Prune">✂️ Tỉa Cành / Chồi</option>
              <option value="Inspect">🔍 Kiểm Tra Sâu Bệnh</option>
            </select>

            <input
              type="text"
              placeholder="Tên phân / thuốc (VD: NPK 20-20-15)"
              value={action}
              onChange={(e) => setAction(e.target.value)}
              className="bg-white text-xs rounded-lg px-2.5 py-1.5 border border-teal-300 focus:outline-none"
            />
          </div>

          <input
            type="text"
            placeholder="Ghi chú chi tiết (VD: Tưới đẫm buổi sáng, pha loãng tỉ lệ 1:1000...)"
            value={note}
            onChange={(e) => setNote(e.target.value)}
            className="w-full bg-white text-xs rounded-lg px-2.5 py-1.5 border border-teal-300 focus:outline-none"
          />

          <button
            type="submit"
            className="w-full py-2 bg-teal-600 hover:bg-teal-700 text-white rounded-lg text-xs font-bold transition shadow cursor-pointer"
          >
            Lưu Ghi Chép Canh Tác
          </button>
        </form>

        {/* Danh sách lịch sử chăm sóc */}
        <div className="max-h-56 overflow-y-auto space-y-2 pr-1">
          <span className="text-xs font-bold text-fb-muted block mb-1">Nhật ký tưới bón & bảo vệ cây:</span>
          {logs.length === 0 ? (
            <p className="text-center py-4 text-xs text-fb-muted">Chưa có lịch sử chăm sóc nào.</p>
          ) : (
            logs.map((l) => (
              <div
                key={l.id}
                className="p-2.5 rounded-xl border border-fb-divider bg-fb-bg/40 flex items-center justify-between text-xs"
              >
                <div>
                  <div className="flex items-center gap-1.5">
                    <span className="font-bold text-teal-800 bg-teal-100 px-1.5 py-0.5 rounded text-[10px]">
                      {l.type === 'Water' ? '💧 Tưới' : l.type === 'Fertilizer' ? '🧪 Phân bón' : l.type === 'Pesticide' ? '⚠️ Thuốc' : '✂️ Kỹ thuật'}
                    </span>
                    <span className="font-semibold text-fb-text">{l.action || l.note}</span>
                  </div>
                  {l.note && l.action && <p className="text-slate-600 mt-0.5 text-[11px]">{l.note}</p>}
                  <span className="text-[10px] text-slate-400 block mt-0.5">
                    {l.created_at ? new Date(l.created_at).toLocaleString('vi-VN') : 'Gần đây'}
                  </span>
                </div>

                {onDeleteCare && (
                  <button
                    onClick={() => onDeleteCare(l.id)}
                    className="p-1 text-slate-400 hover:text-red-600 transition cursor-pointer"
                    title="Xóa ghi chép này"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                )}
              </div>
            ))
          )}
        </div>
      </div>
    </ModalWrapper>
  );
}

// ==========================================
// 9. Modal Nhập Kho Vật Tư
// ==========================================
export function ModalImport({
  isOpen,
  onClose,
  onImport,
}: {
  isOpen: boolean;
  onClose: () => void;
  onImport: (category: string, name: string, qty: number, unit: string, price: number) => Promise<void>;
}) {
  const [category, setCategory] = useState('Feed');
  const [name, setName] = useState('');
  const [qty, setQty] = useState('');
  const [unit, setUnit] = useState('kg');
  const [price, setPrice] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name || !qty) return alert('Vui lòng điền đủ tên hàng và số lượng');
    await onImport(category, name, parseFloat(qty), unit, parseFloat(price) || 0);
    setName('');
    setQty('');
    setPrice('');
    onClose();
  };

  return (
    <ModalWrapper isOpen={isOpen} onClose={onClose} title="📥 Nhập Kho Vật Tư Nông Trại" icon="📦">
      <form onSubmit={handleSubmit} className="space-y-3.5">
        <div>
          <label className="block text-xs font-semibold text-fb-muted mb-1">Phân Loại Hàng Hóa</label>
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="w-full bg-fb-bg text-sm rounded-xl px-3 py-2 border border-fb-divider font-medium"
          >
            <option value="Feed">🥩 Thức ăn chăn nuôi (Cám, ngô, thức ăn đậm đặc...)</option>
            <option value="Fertilizer">🌱 Phân bón & Dinh dưỡng (NPK, vi sinh, đạm...)</option>
            <option value="Other">🛠️ Dụng cụ & Vật tư nông trại khác</option>
          </select>
        </div>

        <div>
          <label className="block text-xs font-semibold text-fb-muted mb-1">Tên Hàng Hóa</label>
          <input
            type="text"
            placeholder="VD: Cám Cò Đậm Đặc, Phân NPK Đầu Trâu..."
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full bg-fb-bg text-sm rounded-xl px-3 py-2 border border-fb-divider focus:ring-2 focus:ring-emerald-500"
          />
        </div>

        <div className="grid grid-cols-2 gap-2.5">
          <div>
            <label className="block text-xs font-semibold text-fb-muted mb-1">Số Lượng Nhập</label>
            <input
              type="number"
              step="0.5"
              placeholder="VD: 50"
              value={qty}
              onChange={(e) => setQty(e.target.value)}
              className="w-full bg-fb-bg text-sm rounded-xl px-3 py-2 border border-fb-divider focus:ring-2 focus:ring-emerald-500"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-fb-muted mb-1">Đơn Vị Tính</label>
            <input
              type="text"
              placeholder="kg, bao, lít, chai..."
              value={unit}
              onChange={(e) => setUnit(e.target.value)}
              className="w-full bg-fb-bg text-sm rounded-xl px-3 py-2 border border-fb-divider focus:ring-2 focus:ring-emerald-500"
            />
          </div>
        </div>

        <div>
          <label className="block text-xs font-semibold text-fb-muted mb-1">Đơn Giá Nhập (VNĐ)</label>
          <input
            type="number"
            placeholder="VD: 350000"
            value={price}
            onChange={(e) => setPrice(e.target.value)}
            className="w-full bg-fb-bg text-sm rounded-xl px-3 py-2 border border-fb-divider focus:ring-2 focus:ring-emerald-500"
          />
        </div>

        <div className="flex gap-2 pt-2 border-t border-fb-divider">
          <button
            type="button"
            onClick={onClose}
            className="flex-1 py-2 rounded-xl border border-fb-divider text-xs font-semibold hover:bg-fb-hover cursor-pointer"
          >
            Hủy
          </button>
          <button
            type="submit"
            className="flex-1 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold shadow cursor-pointer"
          >
            Lưu Vào Kho
          </button>
        </div>
      </form>
    </ModalWrapper>
  );
}

// ==========================================
// 10. Modal Xuất Kho Dùng
// ==========================================
export function ModalExport({
  isOpen,
  onClose,
  inventoryItems,
  pens,
  onExport,
}: {
  isOpen: boolean;
  onClose: () => void;
  inventoryItems: Array<{ id: string | number; name: string; quantity: number; unit: string; category: string }>;
  pens: Array<{ id: string; name: string }>;
  onExport: (itemId: string, qty: number, penId: string, note: string) => Promise<void>;
}) {
  const [selectedItemId, setSelectedItemId] = useState('');
  const [qty, setQty] = useState('');
  const [penId, setPenId] = useState('');
  const [note, setNote] = useState('');

  const activeItemId = selectedItemId || (inventoryItems.length > 0 ? String(inventoryItems[0].id) : '');
  const activePenId = penId || (pens.length > 0 ? pens[0].id : '');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeItemId || !qty) return alert('Vui lòng chọn hàng và nhập số lượng xuất');
    await onExport(activeItemId, parseFloat(qty), activePenId, note);
    setQty('');
    setNote('');
    onClose();
  };

  return (
    <ModalWrapper isOpen={isOpen} onClose={onClose} title="📤 Xuất Kho Vật Tư / Cho Ăn / Bón Cây" icon="🥩">
      <form onSubmit={handleSubmit} className="space-y-3.5">
        <div>
          <label className="block text-xs font-semibold text-fb-muted mb-1">Mặt Hàng Cần Xuất</label>
          <select
            value={activeItemId}
            onChange={(e) => setSelectedItemId(e.target.value)}
            className="w-full bg-fb-bg text-sm rounded-xl px-3 py-2 border border-fb-divider font-medium"
          >
            {inventoryItems.map((item) => (
              <option key={String(item.id)} value={String(item.id)}>
                {item.name} (Tồn kho: {item.quantity} {item.unit})
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-xs font-semibold text-fb-muted mb-1">Số Lượng Xuất Dùng</label>
          <input
            type="number"
            step="0.5"
            placeholder="VD: 15"
            value={qty}
            onChange={(e) => setQty(e.target.value)}
            className="w-full bg-fb-bg text-sm rounded-xl px-3 py-2 border border-fb-divider focus:ring-2 focus:ring-emerald-500"
          />
        </div>

        <div>
          <label className="block text-xs font-semibold text-fb-muted mb-1">Xuất Cho Chuồng / Vườn Nào?</label>
          <select
            value={penId}
            onChange={(e) => setPenId(e.target.value)}
            className="w-full bg-fb-bg text-sm rounded-xl px-3 py-2 border border-fb-divider font-medium"
          >
            {pens.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name} ({p.id})
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-xs font-semibold text-fb-muted mb-1">Ghi Chú Mục Đích Xuất Dùng</label>
          <input
            type="text"
            placeholder="VD: Cho heo ăn sáng, bón thúc dưa lưới..."
            value={note}
            onChange={(e) => setNote(e.target.value)}
            className="w-full bg-fb-bg text-sm rounded-xl px-3 py-2 border border-fb-divider focus:ring-2 focus:ring-emerald-500"
          />
        </div>

        <div className="flex gap-2 pt-2 border-t border-fb-divider">
          <button
            type="button"
            onClick={onClose}
            className="flex-1 py-2 rounded-xl border border-fb-divider text-xs font-semibold hover:bg-fb-hover cursor-pointer"
          >
            Hủy
          </button>
          <button
            type="submit"
            className="flex-1 py-2 rounded-xl bg-orange-500 hover:bg-orange-600 text-white text-xs font-semibold shadow cursor-pointer"
          >
            Xác Nhận Xuất Dùng
          </button>
        </div>
      </form>
    </ModalWrapper>
  );
}
