'use client';

import React from 'react';
import { 
  User, 
  Layers, 
  Activity, 
  Package, 
  Cpu, 
  Plus, 
  Sparkles, 
  ChevronRight, 
  ShieldCheck,
  AlertTriangle
} from 'lucide-react';

interface LeftSidebarProps {
  userEmail: string;
  currentMode: 'livestock' | 'cultivation';
  onModeChange: (mode: 'livestock' | 'cultivation') => void;
  pens: Array<{ id: string; name: string; type: string; hasAlert?: boolean }>;
  currentPenId: string;
  onSelectPen: (penId: string) => void;
  onOpenAddPenModal: () => void;
}

export default function LeftSidebar({
  userEmail,
  currentMode,
  onModeChange,
  pens,
  currentPenId,
  onSelectPen,
  onOpenAddPenModal,
}: LeftSidebarProps) {
  return (
    <aside className="w-64 lg:w-72 shrink-0 hidden md:block space-y-4">
      {/* User Mini Profile Card */}
      <div className="bg-fb-card rounded-2xl p-3.5 shadow-fb-card border border-fb-divider flex items-center gap-3">
        <div className="w-10 h-10 rounded-full bg-gradient-to-tr from-emerald-600 to-teal-500 text-white font-bold flex items-center justify-center text-sm shadow">
          {userEmail ? userEmail.charAt(0).toUpperCase() : 'N'}
        </div>
        <div className="min-w-0 flex-1">
          <h4 className="font-bold text-sm text-fb-text truncate">Nông Dân Thông Minh</h4>
          <p className="text-xs text-fb-muted truncate">{userEmail || 'Chủ trang trại'}</p>
        </div>
      </div>

      {/* Farm Mode Switcher */}
      <div className="bg-fb-card rounded-2xl p-2 shadow-fb-card border border-fb-divider">
        <div className="text-[11px] font-bold text-fb-muted px-2 py-1 uppercase tracking-wider">
          Chế Độ Trang Trại
        </div>
        <div className="grid grid-cols-2 gap-1 mt-1">
          <button
            onClick={() => onModeChange('livestock')}
            className={`py-2 px-2.5 rounded-xl font-semibold text-xs flex items-center justify-center gap-1.5 transition ${
              currentMode === 'livestock'
                ? 'bg-emerald-100 text-emerald-800 shadow-sm'
                : 'text-fb-muted hover:bg-fb-hover'
            }`}
          >
            <span>🐖</span>
            <span>Chăn Nuôi</span>
          </button>

          <button
            onClick={() => onModeChange('cultivation')}
            className={`py-2 px-2.5 rounded-xl font-semibold text-xs flex items-center justify-center gap-1.5 transition ${
              currentMode === 'cultivation'
                ? 'bg-emerald-100 text-emerald-800 shadow-sm'
                : 'text-fb-muted hover:bg-fb-hover'
            }`}
          >
            <span>🌿</span>
            <span>Trồng Trọt</span>
          </button>
        </div>
      </div>

      {/* Pens List Section */}
      <div className="bg-fb-card rounded-2xl p-3.5 shadow-fb-card border border-fb-divider">
        <div className="flex items-center justify-between pb-2 border-b border-fb-divider mb-2">
          <span className="text-xs font-bold text-fb-text flex items-center gap-1.5">
            <Layers className="w-4 h-4 text-emerald-600" />
            {currentMode === 'livestock' ? 'Danh Sách Chuồng' : 'Danh Sách Vườn'}
          </span>

          <button
            onClick={onOpenAddPenModal}
            className="text-[11px] font-bold text-emerald-600 hover:text-emerald-700 flex items-center gap-0.5 hover:underline"
          >
            <Plus className="w-3.5 h-3.5" />
            Thêm
          </button>
        </div>

        <div className="space-y-1 max-h-56 overflow-y-auto pr-1">
          {pens.map((pen) => {
            const isSelected = pen.id === currentPenId;
            const hasAlert = pen.hasAlert;

            return (
              <div
                key={pen.id}
                onClick={() => onSelectPen(pen.id)}
                className={`flex items-center justify-between p-2 rounded-xl text-xs font-medium cursor-pointer transition ${
                  isSelected
                    ? 'bg-emerald-50 text-emerald-900 font-bold border border-emerald-200'
                    : 'text-fb-text hover:bg-fb-hover'
                }`}
              >
                <div className="flex items-center gap-2 truncate">
                  <span
                    className={`w-2 h-2 rounded-full shrink-0 ${
                      hasAlert ? 'bg-red-500 animate-ping' : isSelected ? 'bg-emerald-500' : 'bg-slate-300'
                    }`}
                  />
                  <span className="truncate">{pen.name}</span>
                </div>

                <div className="flex items-center gap-1">
                  {hasAlert && (
                    <AlertTriangle className="w-3.5 h-3.5 text-red-500 shrink-0" />
                  )}
                  <ChevronRight className="w-3.5 h-3.5 text-slate-400" />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* System Status info */}
      <div className="bg-gradient-to-br from-emerald-50 to-teal-50 border border-emerald-200 rounded-2xl p-3 text-xs text-emerald-900 shadow-sm">
        <div className="flex items-center gap-1.5 font-bold mb-1">
          <ShieldCheck className="w-4 h-4 text-emerald-600" />
          <span>The Watcher 24/7 Hoạt Động</span>
        </div>
        <p className="text-[11px] text-emerald-700 leading-relaxed">
          Tự động rà soát cảm biến vi khí hậu & mùi chuồng mỗi 15 giây qua Supabase Realtime.
        </p>
      </div>
    </aside>
  );
}
