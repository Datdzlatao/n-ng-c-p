'use client';

import React from 'react';
import { 
  Cpu, 
  Plus, 
  Power, 
  Activity, 
  CheckCircle, 
  Clock, 
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
  onToggleDevice: (id: string, currentStatus: boolean) => void;
  onOpenAddDeviceModal: () => void;
  recentActivities?: ActivityEvent[];
}

export default function RightSidebar({
  devices,
  penName,
  onToggleDevice,
  onOpenAddDeviceModal,
  recentActivities = [],
}: RightSidebarProps) {
  return (
    <aside className="w-64 lg:w-72 shrink-0 hidden xl:block space-y-4">
      {/* IoT Devices Control Card */}
      <div className="bg-fb-card rounded-2xl p-4 shadow-fb-card border border-fb-divider">
        <div className="flex items-center justify-between pb-2 border-b border-fb-divider mb-3">
          <div className="flex items-center gap-1.5">
            <Cpu className="w-4 h-4 text-emerald-600" />
            <h4 className="font-bold text-sm text-fb-text">Thiết Bị Chuồng</h4>
          </div>

          <button
            onClick={onOpenAddDeviceModal}
            className="text-[11px] font-bold text-emerald-600 hover:text-emerald-700 flex items-center gap-0.5 hover:underline"
          >
            <Plus className="w-3.5 h-3.5" />
            Thêm
          </button>
        </div>

        <p className="text-[11px] text-fb-muted mb-3">
          Điều khiển thiết bị IoT tại: <strong>{penName}</strong>
        </p>

        {devices.length === 0 ? (
          <div className="text-center py-6 text-fb-muted text-xs border border-dashed border-fb-divider rounded-xl">
            Chưa có thiết bị nào. Hãy thêm quạt hút hoặc đèn sưởi!
          </div>
        ) : (
          <div className="space-y-2.5">
            {devices.map((d) => {
              const isFan = d.name.toLowerCase().includes('quạt');
              const isWater = d.name.toLowerCase().includes('phun') || d.name.toLowerCase().includes('bơm');
              const isLamp = d.name.toLowerCase().includes('đèn') || d.name.toLowerCase().includes('sưởi');

              return (
                <div
                  key={d.id}
                  className={`flex items-center justify-between p-2.5 rounded-xl border transition ${
                    d.is_active
                      ? 'bg-emerald-50/70 border-emerald-300'
                      : 'bg-fb-bg/50 border-fb-divider'
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
                        GPIO Pin: {d.pin ?? '--'}
                      </span>
                    </div>
                  </div>

                  {/* iOS Style Toggle Switch */}
                  <button
                    onClick={() => onToggleDevice(d.id, d.is_active)}
                    className={`w-11 h-6 flex items-center rounded-full p-1 transition-colors duration-200 focus:outline-none ${
                      d.is_active ? 'bg-emerald-600' : 'bg-slate-300'
                    }`}
                  >
                    <div
                      className={`bg-white w-4 h-4 rounded-full shadow-md transform transition-transform duration-200 flex items-center justify-center ${
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

      {/* Live Activity Feed Widget */}
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
                  <p className="font-semibold text-fb-text">Ghi nhận vi khí hậu ổn định</p>
                  <p className="text-[11px] text-fb-muted">Nhiệt độ 28.5°C, Độ ẩm 72%</p>
                  <span className="text-[10px] text-slate-400">1 phút trước</span>
                </div>
              </div>

              <div className="flex items-start gap-2 text-xs">
                <span className="w-2 h-2 rounded-full bg-blue-500 mt-1.5 shrink-0" />
                <div>
                  <p className="font-semibold text-fb-text">Cho ăn buổi sáng</p>
                  <p className="text-[11px] text-fb-muted">Đã xuất 15kg cám cò chuồng A1</p>
                  <span className="text-[10px] text-slate-400">25 phút trước</span>
                </div>
              </div>

              <div className="flex items-start gap-2 text-xs">
                <span className="w-2 h-2 rounded-full bg-orange-500 mt-1.5 shrink-0" />
                <div>
                  <p className="font-semibold text-fb-text">The Watcher kiểm tra mùi</p>
                  <p className="text-[11px] text-fb-muted">Chỉ số NH3 an toàn: 180 ppm</p>
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
