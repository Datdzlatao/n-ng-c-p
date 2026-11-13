'use client';

import React from 'react';
import { 
  Cpu, 
  Plus, 
  Power, 
  Activity, 
  Wind, 
  Droplet, 
  SunMedium,
  Check
} from 'lucide-react';

interface Device {
  id: string;
  name: string;
  is_active: boolean;
  pin?: number;
}

interface ActivityEvent {
  id: string;
  type: string;
  title: string;
  desc: string;
  time: string;
}

interface RightSidebarProps {
  devices: Device[];
  penName: string;
  currentMode?: 'livestock' | 'cultivation';
  onToggleDevice: (id: string, currentStatus: boolean) => void;
  onOpenAddDeviceModal: () => void;
  recentActivities?: ActivityEvent[];
}

export default function RightSidebar({
  devices,
  penName,
  currentMode = 'livestock',
  onToggleDevice,
  onOpenAddDeviceModal,
  recentActivities = [],
}: RightSidebarProps) {
  const isLivestock = currentMode === 'livestock';
  const currentPenLabel = penName || (isLivestock ? 'Chuồng nuôi đang chọn' : 'Vườn trồng đang chọn');

  return (
    <aside className="w-64 lg:w-72 shrink-0 hidden xl:block space-y-4">
      {/* Khối điều khiển thiết bị điện */}
      <div className="bg-fb-card rounded-2xl p-4 shadow-fb-card border border-fb-divider">
        <div className="flex items-center justify-between pb-2 border-b border-fb-divider mb-3">
          <div className="flex items-center gap-1.5">
            <Cpu className="w-4 h-4 text-emerald-600" />
            <h4 className="font-bold text-sm text-fb-text">
              {isLivestock ? 'Thiết Bị Chuồng Trại' : 'Thiết Bị Vườn Trồng'}
            </h4>
          </div>

          <button
            onClick={onOpenAddDeviceModal}
            className="text-[11px] font-bold text-emerald-700 hover:text-emerald-800 flex items-center gap-0.5 hover:underline cursor-pointer"
          >
            <Plus className="w-3.5 h-3.5" />
            Thêm Mới
          </button>
        </div>

        <p className="text-[11px] text-fb-muted mb-3 truncate">
          Điều khiển thiết bị tại: <strong className="text-fb-text">{currentPenLabel}</strong>
        </p>

        {devices.length === 0 ? (
          <div className="text-center py-6 px-2 text-fb-muted text-xs border border-dashed border-fb-divider rounded-xl">
            {isLivestock
              ? 'Chưa có thiết bị nào. Hãy thêm quạt hút mùi hoặc đèn sưởi ấm!'
              : 'Chưa có thiết bị nào. Hãy thêm máy bơm tưới hoặc quạt thông gió!'}
          </div>
        ) : (
          <div className="space-y-2.5">
            {devices.map((d) => {
              const nameLower = d.name.toLowerCase();
              const isFan = nameLower.includes('quạt') || nameLower.includes('fan');
              const isWater = 
                nameLower.includes('phun') || 
                nameLower.includes('bơm') || 
                nameLower.includes('tưới') || 
                nameLower.includes('pump') || 
                nameLower.includes('water');
              const isLamp = 
                nameLower.includes('đèn') || 
                nameLower.includes('sưởi') || 
                nameLower.includes('quang hợp') || 
                nameLower.includes('light') || 
                nameLower.includes('heat');

              return (
                <div
                  key={d.id}
                  className={`flex items-center justify-between p-2.5 rounded-xl border transition ${
                    d.is_active
                      ? 'bg-emerald-50/80 border-emerald-300'
                      : 'bg-fb-bg/60 border-fb-divider'
                  }`}
                >
                  <div className="flex items-center gap-2.5 min-w-0">
                    <div
                      className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 ${
                        d.is_active ? 'bg-emerald-600 text-white shadow-sm' : 'bg-slate-200 text-slate-500'
                      }`}
                    >
                      {isFan ? (
                        <Wind className={`w-4 h-4 ${d.is_active ? 'animate-spin' : ''}`} />
                      ) : isWater ? (
                        <Droplet className="w-4 h-4" />
                      ) : isLamp ? (
                        <SunMedium className="w-4 h-4" />
                      ) : (
                        <Power className="w-4 h-4" />
                      )}
                    </div>

                    <div className="min-w-0">
                      <span className="font-bold text-xs text-fb-text block truncate">
                        {d.name}
                      </span>
                      <span className="text-[10px] text-fb-muted block">
                        Cổng điều khiển: {d.pin ?? '--'}
                      </span>
                    </div>
                  </div>

                  {/* Nút công tắc bật tắt */}
                  <button
                    onClick={() => onToggleDevice(d.id, d.is_active)}
                    className={`w-11 h-6 flex items-center rounded-full p-1 transition-colors duration-200 focus:outline-none cursor-pointer ${
                      d.is_active ? 'bg-emerald-600' : 'bg-slate-300'
                    }`}
                    title={d.is_active ? 'Đang bật (Bấm để tắt)' : 'Đang tắt (Bấm để bật)'}
                    aria-label={`Bật tắt ${d.name}`}
                  >
                    <div
                      className={`bg-white w-4 h-4 rounded-full shadow transform transition-transform duration-200 flex items-center justify-center ${
                        d.is_active ? 'translate-x-5' : 'translate-x-0'
                      }`}
                    >
                      {d.is_active && <Check className="w-2.5 h-2.5 text-emerald-600" />}
                    </div>
                  </button>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Nhật ký hoạt động gần đây */}
      <div className="bg-fb-card rounded-2xl p-4 shadow-fb-card border border-fb-divider">
        <div className="flex items-center gap-1.5 pb-2 border-b border-fb-divider mb-3">
          <Activity className="w-4 h-4 text-emerald-600" />
          <h4 className="font-bold text-sm text-fb-text">Nhật Ký Nông Trại</h4>
        </div>

        <div className="space-y-3">
          {recentActivities.length === 0 ? (
            <>
              <div className="flex items-start gap-2 text-xs">
                <span className="w-2 h-2 rounded-full bg-emerald-500 mt-1.5 shrink-0" />
                <div>
                  <p className="font-semibold text-fb-text">
                    {isLivestock ? 'Khí hậu chuồng nuôi ổn định' : 'Vi khí hậu nhà màng ổn định'}
                  </p>
                  <p className="text-[11px] text-fb-muted">Nhiệt độ 28.5°C, Độ ẩm 72%</p>
                  <span className="text-[10px] text-slate-400">1 phút trước</span>
                </div>
              </div>

              <div className="flex items-start gap-2 text-xs">
                <span className="w-2 h-2 rounded-full bg-blue-500 mt-1.5 shrink-0" />
                <div>
                  <p className="font-semibold text-fb-text">
                    {isLivestock ? 'Cho đàn ăn theo lịch' : 'Tưới nước nhỏ giọt định kỳ'}
                  </p>
                  <p className="text-[11px] text-fb-muted">
                    {isLivestock ? 'Đã xuất 15kg cám theo tiêu chuẩn' : 'Hệ thống tưới tự động 15 phút'}
                  </p>
                  <span className="text-[10px] text-slate-400">25 phút trước</span>
                </div>
              </div>

              <div className="flex items-start gap-2 text-xs">
                <span className="w-2 h-2 rounded-full bg-orange-500 mt-1.5 shrink-0" />
                <div>
                  <p className="font-semibold text-fb-text">
                    {isLivestock ? 'Kiểm tra nồng độ khí chuồng' : 'Kiểm tra độ ẩm của đất'}
                  </p>
                  <p className="text-[11px] text-fb-muted">
                    {isLivestock ? 'Chỉ số an toàn: 180 ppm' : 'Độ ẩm đất lý tưởng: 68%'}
                  </p>
                  <span className="text-[10px] text-slate-400">40 phút trước</span>
                </div>
              </div>
            </>
          ) : (
            recentActivities.map((act) => (
              <div key={act.id} className="flex items-start gap-2 text-xs">
                <span className="w-2 h-2 rounded-full bg-emerald-500 mt-1.5 shrink-0" />
                <div>
                  <p className="font-semibold text-fb-text">{act.title}</p>
                  <p className="text-[11px] text-fb-muted">{act.desc}</p>
                  <span className="text-[10px] text-slate-400">{act.time}</span>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </aside>
  );
}
