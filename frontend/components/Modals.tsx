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
  Droplet 
} from 'lucide-react';
import { Line } from 'react-chartjs-2';

interface ModalWrapperProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  icon?: string;
  children: React.ReactNode;
}

function ModalWrapper({ isOpen, onClose, title, icon, children }: ModalWrapperProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-150">
      <div className="bg-fb-card w-full max-w-lg rounded-2xl shadow-fb-popover border border-fb-divider overflow-hidden flex flex-col max-h-[90vh]">
        {/* Modal Header */}
        <div className="p-4 border-b border-fb-divider flex items-center justify-between bg-fb-bg/30">
          <h3 className="font-bold text-base text-fb-text flex items-center gap-2">
            {icon && <span>{icon}</span>}
            <span>{title}</span>
          </h3>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-full hover:bg-fb-hover flex items-center justify-center text-fb-muted hover:text-fb-text transition"
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

// 1. Modal Thêm Khu Vực / Chuồng
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
    <ModalWrapper isOpen={isOpen} onClose={onClose} title="Thêm Khu Vực / Chuồng Mới" icon="🏡">
      <form onSubmit={handleSubmit} className="space-y-3">
        <div>
          <label className="block text-xs font-semibold text-fb-muted mb-1">Loại khu vực</label>
          <select
            value={type}
            onChange={(e) => setType(e.target.value)}
            className="w-full bg-fb-bg text-sm rounded-xl px-3 py-2 border border-fb-divider focus:ring-2 focus:ring-emerald-500"
          >
            <option value="livestock">🐖 Chuồng Trại Chăn Nuôi</option>
            <option value="cultivation">🌿 Vườn Trồng Trọt</option>
          </select>
        </div>

        <div>
          <label className="block text-xs font-semibold text-fb-muted mb-1">Mã khu vực</label>
          <input
            type="text"
            placeholder="VD: CHUONG_03, VUON_02"
            value={id}
            onChange={(e) => setId(e.target.value)}
            className="w-full bg-fb-bg text-sm rounded-xl px-3 py-2 border border-fb-divider focus:ring-2 focus:ring-emerald-500"
          />
        </div>

        <div>
          <label className="block text-xs font-semibold text-fb-muted mb-1">Tên khu vực</label>
          <input
            type="text"
            placeholder="VD: Chuồng Heo Thịt Khu A3"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full bg-fb-bg text-sm rounded-xl px-3 py-2 border border-fb-divider focus:ring-2 focus:ring-emerald-500"
          />
        </div>

        <div className="flex gap-2 pt-2 border-t border-fb-divider">
          <button
            type="button"
            onClick={onClose}
            className="flex-1 py-2 rounded-xl border border-fb-divider text-xs font-semibold hover:bg-fb-hover"
          >
            Hủy
          </button>
          <button
            type="submit"
            className="flex-1 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold shadow"
          >
            Lưu Khu Vực
          </button>
        </div>
      </form>
    </ModalWrapper>
  );
}

// 2. Modal Thêm Thiết Bị IoT
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
    <ModalWrapper isOpen={isOpen} onClose={onClose} title="Thêm Thiết Bị IoT" icon="🎮">
      <form onSubmit={handleSubmit} className="space-y-3">
        <div>
          <label className="block text-xs font-semibold text-fb-muted mb-1">Mã thiết bị</label>
          <input
            type="text"
            placeholder="VD: QUAT_02, PHUN_01"
            value={id}
            onChange={(e) => setId(e.target.value)}
            className="w-full bg-fb-bg text-sm rounded-xl px-3 py-2 border border-fb-divider focus:ring-2 focus:ring-emerald-500"
          />
        </div>

        <div>
          <label className="block text-xs font-semibold text-fb-muted mb-1">Tên thiết bị</label>
          <input
            type="text"
            placeholder="VD: Quạt Thông Gió Công Suất Lớn"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full bg-fb-bg text-sm rounded-xl px-3 py-2 border border-fb-divider focus:ring-2 focus:ring-emerald-500"
          />
        </div>

        <div>
          <label className="block text-xs font-semibold text-fb-muted mb-1">Chân GPIO (Pin)</label>
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
            className="flex-1 py-2 rounded-xl border border-fb-divider text-xs font-semibold hover:bg-fb-hover"
          >
            Hủy
          </button>
          <button
            type="submit"
            className="flex-1 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold shadow"
          >
            Lưu Thiết Bị
          </button>
        </div>
      </form>
    </ModalWrapper>
  );
}

// 3. Modal Thêm Vật Nuôi
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
    <ModalWrapper isOpen={isOpen} onClose={onClose} title="Nhập Hồ Sơ Vật Nuôi" icon="🐖">
      <form onSubmit={handleSubmit} className="space-y-3">
        <div>
          <label className="block text-xs font-semibold text-fb-muted mb-1">Mã cá thể</label>
          <input
            type="text"
            placeholder="VD: HEO_105, GA_02"
            value={id}
            onChange={(e) => setId(e.target.value)}
            className="w-full bg-fb-bg text-sm rounded-xl px-3 py-2 border border-fb-divider focus:ring-2 focus:ring-emerald-500"
          />
        </div>

        <div>
          <label className="block text-xs font-semibold text-fb-muted mb-1">Loài</label>
          <select
            value={species}
            onChange={(e) => setSpecies(e.target.value)}
            className="w-full bg-fb-bg text-sm rounded-xl px-3 py-2 border border-fb-divider focus:ring-2 focus:ring-emerald-500"
          >
            <option value="Heo">Heo (Lợn)</option>
            <option value="Gà">Gà</option>
            <option value="Bò">Bò</option>
          </select>
        </div>

        <div className="grid grid-cols-2 gap-2">
          <div>
            <label className="block text-xs font-semibold text-fb-muted mb-1">Cân nặng hiện tại (kg)</label>
            <input
              type="number"
              step="0.1"
              value={weight}
              onChange={(e) => setWeight(Number(e.target.value))}
              className="w-full bg-fb-bg text-sm rounded-xl px-3 py-2 border border-fb-divider focus:ring-2 focus:ring-emerald-500"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-fb-muted mb-1">Mục tiêu xuất chuồng (kg)</label>
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
            className="flex-1 py-2 rounded-xl border border-fb-divider text-xs font-semibold hover:bg-fb-hover"
          >
            Hủy
          </button>
          <button
            type="submit"
            className="flex-1 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold shadow"
          >
            Lưu Hồ Sơ
          </button>
        </div>
      </form>
    </ModalWrapper>
  );
}

// 4. Modal Hồ Sơ Sức Khỏe & Thú Y
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
    <ModalWrapper isOpen={isOpen} onClose={onClose} title={`Hồ Sơ Sức Khỏe: ${animalId}`} icon="🏥">
      <div className="space-y-4">
        {/* Input New Log */}
        <form onSubmit={handleSubmit} className="p-3 bg-red-50 border border-red-200 rounded-xl space-y-2">
          <span className="text-xs font-bold text-red-800 block">Thêm Ghi Chép Mới:</span>
          
          <div className="grid grid-cols-2 gap-2">
            <select
              value={type}
              onChange={(e) => setType(e.target.value)}
              className="bg-white text-xs rounded-lg px-2.5 py-1.5 border border-red-300 focus:outline-none"
            >
              <option value="Vaccine">💉 Tiêm Vắc-xin</option>
              <option value="Treatment">💊 Điều trị / Thuốc</option>
              <option value="Sick">🚑 Phát hiện bệnh</option>
            </select>

            <input
              type="text"
              placeholder="Tên thuốc / bệnh (VD: Tụ huyết trùng)"
              value={action}
              onChange={(e) => setAction(e.target.value)}
              className="bg-white text-xs rounded-lg px-2.5 py-1.5 border border-red-300 focus:outline-none"
            />
          </div>

          <input
            type="text"
            placeholder="Ghi chú chi tiết (VD: Sốt cao, đã cách ly tiêm liều 1...)"
            value={note}
            onChange={(e) => setNote(e.target.value)}
            className="w-full bg-white text-xs rounded-lg px-2.5 py-1.5 border border-red-300 focus:outline-none"
          />

          <button
            type="submit"
            className="w-full py-1.5 bg-red-600 hover:bg-red-700 text-white rounded-lg text-xs font-bold transition shadow"
          >
            Lưu Ghi Chép Thú Y
          </button>
        </form>

        {/* Existing Logs List */}
        <div className="max-h-56 overflow-y-auto space-y-2">
          {logs.length === 0 ? (
            <p className="text-center py-4 text-xs text-fb-muted">Chưa có lịch sử bệnh án nào.</p>
          ) : (
            logs.map((l) => (
              <div
                key={l.id}
                className="p-2.5 rounded-xl border border-fb-divider bg-fb-bg/50 flex items-center justify-between text-xs"
              >
                <div>
                  <div className="flex items-center gap-1.5">
                    <span className="font-bold text-red-700">[{l.type}]</span>
                    <span className="font-semibold text-fb-text">{l.action || l.note}</span>
                  </div>
                  {l.note && l.action && <p className="text-slate-600 mt-0.5">{l.note}</p>}
                  <span className="text-[10px] text-slate-400 block mt-0.5">
                    {l.created_at ? new Date(l.created_at).toLocaleString('vi-VN') : 'Gần đây'}
                  </span>
                </div>

                <button
                  onClick={() => onDeleteLog(l.id)}
                  className="p-1 text-slate-400 hover:text-red-600 transition"
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

// 5. Modal Theo Dõi Cân Nặng (Weight Tracking Chart)
export function ModalWeightTracking({
  isOpen,
  onClose,
  animalId,
  logs,
  onSaveWeight,
}: {
  isOpen: boolean;
  onClose: () => void;
  animalId: string;
  logs: Array<{ created_at?: string; weight: number }>;
  onSaveWeight: (weight: number) => Promise<void>;
}) {
  const [newWeight, setNewWeight] = useState('');

  const chartData = {
    labels: logs.length > 0 ? logs.map(l => l.created_at ? new Date(l.created_at).toLocaleDateString('vi-VN') : '--') : ['Lần 1', 'Lần 2'],
    datasets: [
      {
        label: 'Cân nặng (kg)',
        data: logs.length > 0 ? logs.map(l => l.weight) : [20, 25],
        borderColor: '#16A34A',
        backgroundColor: 'rgba(22, 163, 74, 0.1)',
        tension: 0.35,
        fill: true,
        pointRadius: 4,
        pointBackgroundColor: '#16A34A',
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
    <ModalWrapper isOpen={isOpen} onClose={onClose} title={`Tăng Trưởng: ${animalId}`} icon="📈">
      <div className="space-y-4">
        {/* Chart */}
        <div className="h-56 bg-fb-bg rounded-xl p-2 border border-fb-divider">
          <Line
            data={chartData}
            options={{
              responsive: true,
              maintainAspectRatio: false,
              plugins: { legend: { display: false } },
            }}
          />
        </div>

        {/* Update Form */}
        <form onSubmit={handleSubmit} className="p-3 bg-emerald-50 border border-emerald-200 rounded-xl space-y-2">
          <label className="block text-xs font-bold text-emerald-900">
            ⚖️ Cập nhật số cân mới (kg):
          </label>
          <div className="flex gap-2">
            <input
              type="number"
              step="0.1"
              placeholder="VD: 32.5"
              value={newWeight}
              onChange={(e) => setNewWeight(e.target.value)}
              className="flex-1 bg-white text-sm rounded-lg px-3 py-2 border border-emerald-300 focus:outline-none"
            />
            <button
              type="submit"
              className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs rounded-lg shadow"
            >
              Cập Nhật
            </button>
          </div>
        </form>
      </div>
    </ModalWrapper>
  );
}

// 6. Modal Nhập Kho
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
    <ModalWrapper isOpen={isOpen} onClose={onClose} title="📥 Nhập Kho Vật Tư & Cám" icon="📦">
      <form onSubmit={handleSubmit} className="space-y-3">
        <div>
          <label className="block text-xs font-semibold text-fb-muted mb-1">Loại hàng hóa</label>
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="w-full bg-fb-bg text-sm rounded-xl px-3 py-2 border border-fb-divider"
          >
            <option value="Feed">🥩 Thức ăn chăn nuôi (Cám, ngô...)</option>
            <option value="Fertilizer">🌱 Phân bón / Thuốc bảo vệ</option>
            <option value="Other">🛠️ Dụng cụ nông trại khác</option>
          </select>
        </div>

        <div>
          <label className="block text-xs font-semibold text-fb-muted mb-1">Tên hàng hóa</label>
          <input
            type="text"
            placeholder="VD: Cám Cò Pro Max, Phân NPK..."
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full bg-fb-bg text-sm rounded-xl px-3 py-2 border border-fb-divider"
          />
        </div>

        <div className="grid grid-cols-2 gap-2">
          <div>
            <label className="block text-xs font-semibold text-fb-muted mb-1">Số lượng</label>
            <input
              type="number"
              step="0.5"
              placeholder="VD: 50"
              value={qty}
              onChange={(e) => setQty(e.target.value)}
              className="w-full bg-fb-bg text-sm rounded-xl px-3 py-2 border border-fb-divider"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-fb-muted mb-1">Đơn vị tính</label>
            <input
              type="text"
              placeholder="kg, bao, lít..."
              value={unit}
              onChange={(e) => setUnit(e.target.value)}
              className="w-full bg-fb-bg text-sm rounded-xl px-3 py-2 border border-fb-divider"
            />
          </div>
        </div>

        <div>
          <label className="block text-xs font-semibold text-fb-muted mb-1">Giá nhập (VNĐ)</label>
          <input
            type="number"
            placeholder="VD: 350000"
            value={price}
            onChange={(e) => setPrice(e.target.value)}
            className="w-full bg-fb-bg text-sm rounded-xl px-3 py-2 border border-fb-divider"
          />
        </div>

        <div className="flex gap-2 pt-2 border-t border-fb-divider">
          <button
            type="button"
            onClick={onClose}
            className="flex-1 py-2 rounded-xl border border-fb-divider text-xs font-semibold hover:bg-fb-hover"
          >
            Hủy
          </button>
          <button
            type="submit"
            className="flex-1 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold shadow"
          >
            Lưu Vào Kho
          </button>
        </div>
      </form>
    </ModalWrapper>
  );
}

// 7. Modal Xuất Kho (Cho Ăn)
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

  const selectedItem = inventoryItems.find((i) => String(i.id) === String(activeItemId));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeItemId || !qty) return alert('Vui lòng chọn hàng và nhập số lượng xuất');
    await onExport(activeItemId, parseFloat(qty), activePenId, note);
    setQty('');
    setNote('');
    onClose();
  };

  return (
    <ModalWrapper isOpen={isOpen} onClose={onClose} title="📤 Xuất Dùng Vật Tư / Cho Ăn" icon="🥩">
      <form onSubmit={handleSubmit} className="space-y-3">
        <div>
          <label className="block text-xs font-semibold text-fb-muted mb-1">Mặt hàng cần xuất</label>
          <select
            value={activeItemId}
            onChange={(e) => setSelectedItemId(e.target.value)}
            className="w-full bg-fb-bg text-sm rounded-xl px-3 py-2 border border-fb-divider"
          >
            {inventoryItems.map((item) => (
              <option key={String(item.id)} value={String(item.id)}>
                {item.name} (Còn {item.quantity} {item.unit})
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-xs font-semibold text-fb-muted mb-1">Số lượng xuất dùng</label>
          <input
            type="number"
            step="0.5"
            placeholder="VD: 15"
            value={qty}
            onChange={(e) => setQty(e.target.value)}
            className="w-full bg-fb-bg text-sm rounded-xl px-3 py-2 border border-fb-divider"
          />
        </div>

        <div>
          <label className="block text-xs font-semibold text-fb-muted mb-1">Xuất cho chuồng / khu vực nào?</label>
          <select
            value={penId}
            onChange={(e) => setPenId(e.target.value)}
            className="w-full bg-fb-bg text-sm rounded-xl px-3 py-2 border border-fb-divider"
          >
            {pens.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name} ({p.id})
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-xs font-semibold text-fb-muted mb-1">Ghi chú mục đích</label>
          <input
            type="text"
            placeholder="VD: Cho ăn bữa sáng, bón thúc dưa lưới..."
            value={note}
            onChange={(e) => setNote(e.target.value)}
            className="w-full bg-fb-bg text-sm rounded-xl px-3 py-2 border border-fb-divider"
          />
        </div>

        <div className="flex gap-2 pt-2 border-t border-fb-divider">
          <button
            type="button"
            onClick={onClose}
            className="flex-1 py-2 rounded-xl border border-fb-divider text-xs font-semibold hover:bg-fb-hover"
          >
            Hủy
          </button>
          <button
            type="submit"
            className="flex-1 py-2 rounded-xl bg-orange-500 hover:bg-orange-600 text-white text-xs font-semibold shadow"
          >
            Xác Nhận Xuất
          </button>
        </div>
      </form>
    </ModalWrapper>
  );
}

// 8. Modal Thêm Cây Trồng
export function ModalAddCrop({
  isOpen,
  onClose,
  onAdd,
}: {
  isOpen: boolean;
  onClose: () => void;
  onAdd: (name: string, qty: number, date: string) => Promise<void>;
}) {
  const [name, setName] = useState('');
  const [qty, setQty] = useState('');
  const [date, setDate] = useState(new Date().toISOString().split('T')[0]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name || !qty) return alert('Vui lòng điền đủ tên cây và số lượng gốc');
    await onAdd(name, parseInt(qty), date);
    setName('');
    setQty('');
    onClose();
  };

  return (
    <ModalWrapper isOpen={isOpen} onClose={onClose} title="🌱 Thêm Cây Trồng Mới" icon="🌿">
      <form onSubmit={handleSubmit} className="space-y-3">
        <div>
          <label className="block text-xs font-semibold text-fb-muted mb-1">Tên cây trồng</label>
          <input
            type="text"
            placeholder="VD: Dưa Lưới Nhật Bản, Cà Chua Bi..."
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full bg-fb-bg text-sm rounded-xl px-3 py-2 border border-fb-divider"
          />
        </div>

        <div>
          <label className="block text-xs font-semibold text-fb-muted mb-1">Số lượng gốc</label>
          <input
            type="number"
            placeholder="VD: 120"
            value={qty}
            onChange={(e) => setQty(e.target.value)}
            className="w-full bg-fb-bg text-sm rounded-xl px-3 py-2 border border-fb-divider"
          />
        </div>

        <div>
          <label className="block text-xs font-semibold text-fb-muted mb-1">Ngày gieo trồng</label>
          <input
            type="date"
            value={date}
            onChange={(e) => setDate(e.target.value)}
            className="w-full bg-fb-bg text-sm rounded-xl px-3 py-2 border border-fb-divider"
          />
        </div>

        <div className="flex gap-2 pt-2 border-t border-fb-divider">
          <button
            type="button"
            onClick={onClose}
            className="flex-1 py-2 rounded-xl border border-fb-divider text-xs font-semibold hover:bg-fb-hover"
          >
            Hủy
          </button>
          <button
            type="submit"
            className="flex-1 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold shadow"
          >
            Gieo Trồng
          </button>
        </div>
      </form>
    </ModalWrapper>
  );
}

// 9. Modal Tăng Trưởng Cây
export function ModalCropTracking({
  isOpen,
  onClose,
  cropId,
  logs,
  onSaveGrowth,
}: {
  isOpen: boolean;
  onClose: () => void;
  cropId: string;
  logs: Array<{ created_at?: string; height_or_size: number }>;
  onSaveGrowth: (size: number) => Promise<void>;
}) {
  const [size, setSize] = useState('');

  const chartData = {
    labels: logs.length > 0 ? logs.map(l => l.created_at ? new Date(l.created_at).toLocaleDateString('vi-VN') : '--') : ['Lần 1', 'Lần 2'],
    datasets: [
      {
        label: 'Chiều cao / kích thước (cm)',
        data: logs.length > 0 ? logs.map(l => l.height_or_size) : [10, 25],
        borderColor: '#10B981',
        backgroundColor: 'rgba(16, 185, 129, 0.1)',
        tension: 0.35,
        fill: true,
      },
    ],
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!size) return alert('Vui lòng nhập kích thước mới');
    await onSaveGrowth(parseFloat(size));
    setSize('');
  };

  return (
    <ModalWrapper isOpen={isOpen} onClose={onClose} title={`Tăng Trưởng Cây: ${cropId}`} icon="📏">
      <div className="space-y-4">
        <div className="h-56 bg-fb-bg rounded-xl p-2 border border-fb-divider">
          <Line data={chartData} options={{ responsive: true, maintainAspectRatio: false }} />
        </div>

        <form onSubmit={handleSubmit} className="p-3 bg-emerald-50 border border-emerald-200 rounded-xl space-y-2">
          <label className="block text-xs font-bold text-emerald-900">
            📏 Cập nhật chiều cao mới (cm):
          </label>
          <div className="flex gap-2">
            <input
              type="number"
              step="0.5"
              placeholder="VD: 45"
              value={size}
              onChange={(e) => setSize(e.target.value)}
              className="flex-1 bg-white text-sm rounded-lg px-3 py-2 border border-emerald-300 focus:outline-none"
            />
            <button
              type="submit"
              className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs rounded-lg shadow"
            >
              Lưu
            </button>
          </div>
        </form>
      </div>
    </ModalWrapper>
  );
}

// 10. Modal Chăm Sóc Cây
export function ModalCropCare({
  isOpen,
  onClose,
  cropId,
  logs,
  onAddCare,
}: {
  isOpen: boolean;
  onClose: () => void;
  cropId: string;
  logs: Array<{ id: string; type: string; note: string; created_at?: string }>;
  onAddCare: (type: string, note: string) => Promise<void>;
}) {
  const [type, setType] = useState('Water');
  const [note, setNote] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await onAddCare(type, note);
    setNote('');
  };

  return (
    <ModalWrapper isOpen={isOpen} onClose={onClose} title={`Nhật Ký Chăm Sóc Cây: ${cropId}`} icon="💦">
      <div className="space-y-4">
        <form onSubmit={handleSubmit} className="p-3 bg-teal-50 border border-teal-200 rounded-xl space-y-2">
          <div className="grid grid-cols-2 gap-2">
            <select
              value={type}
              onChange={(e) => setType(e.target.value)}
              className="bg-white text-xs rounded-lg px-2.5 py-1.5 border border-teal-300"
            >
              <option value="Water">💧 Tưới Nước</option>
              <option value="Fertilizer">🧪 Bón Phân</option>
              <option value="Pesticide">⚠️ Phun Thuốc</option>
              <option value="Prune">✂️ Tỉa Cành</option>
            </select>

            <input
              type="text"
              placeholder="Ghi chú (VD: Phân NPK pha loãng)"
              value={note}
              onChange={(e) => setNote(e.target.value)}
              className="bg-white text-xs rounded-lg px-2.5 py-1.5 border border-teal-300"
            />
          </div>

          <button
            type="submit"
            className="w-full py-1.5 bg-teal-600 hover:bg-teal-700 text-white rounded-lg text-xs font-bold transition shadow"
          >
            Ghi Nhật Ký
          </button>
        </form>

        <div className="max-h-56 overflow-y-auto space-y-2">
          {logs.map((l) => (
            <div key={l.id} className="p-2 rounded-xl bg-fb-bg/50 border border-fb-divider text-xs flex justify-between">
              <div>
                <span className="font-bold text-teal-700">[{l.type}]</span>
                <span className="ml-2 text-fb-text">{l.note}</span>
              </div>
              <span className="text-[10px] text-slate-400">
                {l.created_at ? new Date(l.created_at).toLocaleDateString('vi-VN') : ''}
              </span>
            </div>
          ))}
        </div>
      </div>
    </ModalWrapper>
  );
}
