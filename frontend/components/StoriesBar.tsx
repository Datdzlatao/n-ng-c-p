'use client';

import React from 'react';
import { Plus, Home, AlertCircle, Thermometer, Droplets } from 'lucide-react';

interface PenStory {
  id: string;
  name: string;
  type: string;
  temp?: number;
  hum?: number;
  hasAlert?: boolean;
}

interface StoriesBarProps {
  pens: PenStory[];
  currentPenId: string;
  onSelectPen: (penId: string) => void;
  onOpenAddPenModal: () => void;
}

export default function StoriesBar({
  pens,
  currentPenId,
  onSelectPen,
  onOpenAddPenModal,
}: StoriesBarProps) {
  return (
    <div className="w-full overflow-x-auto pb-2 scrollbar-none">
      <div className="flex gap-2.5 min-w-max">
        {/* Create Pen Story Card */}
        <div
          onClick={onOpenAddPenModal}
          className="relative w-28 sm:w-32 h-44 sm:h-48 rounded-2xl bg-fb-card shadow-fb-card border border-fb-divider overflow-hidden cursor-pointer group hover:shadow-md transition flex flex-col justify-between"
        >
          <div className="h-3/4 bg-gradient-to-b from-emerald-100 to-green-50 flex items-center justify-center group-hover:scale-105 transition duration-300">
            <div className="w-10 h-10 rounded-full bg-emerald-600 text-white flex items-center justify-center shadow-lg">
              <Plus className="w-6 h-6" />
            </div>
          </div>
          <div className="p-2 text-center bg-fb-card relative">
            <span className="text-xs font-bold text-fb-text block truncate">Thêm Chuồng</span>
            <span className="text-[10px] text-fb-muted">Khu vực mới</span>
          </div>
        </div>

        {/* Pens Story Cards */}
        {pens.map((pen) => {
          const isSelected = pen.id === currentPenId;
          const hasAlert = pen.hasAlert;

          return (
            <div
              key={pen.id}
              onClick={() => onSelectPen(pen.id)}
              className={`relative w-28 sm:w-32 h-44 sm:h-48 rounded-2xl shadow-fb-card border overflow-hidden cursor-pointer group transition duration-200 select-none ${
                isSelected
                  ? 'ring-2 ring-emerald-500 border-emerald-400'
                  : 'border-fb-divider hover:shadow-md'
              }`}
            >
              {/* Background with stylized farm gradient */}
              <div
                className={`absolute inset-0 bg-gradient-to-b ${
                  hasAlert
                    ? 'from-red-600 via-rose-800 to-slate-900'
                    : isSelected
                    ? 'from-emerald-700 via-teal-800 to-slate-900'
                    : 'from-slate-700 via-slate-800 to-slate-950'
                } group-hover:scale-105 transition duration-300`}
              >
                {/* Decorative Pattern */}
                <div className="absolute inset-0 opacity-20 bg-[radial-gradient(#fff_1px,transparent_1px)] [background-size:12px_12px]" />
              </div>

              {/* Story Header: Avatar with Ring */}
              <div className="absolute top-2.5 left-2.5 z-10">
                <div
                  className={`w-9 h-9 rounded-full p-0.5 flex items-center justify-center shadow ${
                    hasAlert
                      ? 'bg-red-500 alert-pulse'
                      : isSelected
                      ? 'bg-emerald-400'
                      : 'bg-white/70'
                  }`}
                >
                  <div className="w-full h-full rounded-full bg-slate-900 text-white flex items-center justify-center font-bold text-xs">
                    {pen.type === 'cultivation' ? '🌿' : '🐖'}
                  </div>
                </div>
              </div>

              {/* Story Content / Badges */}
              <div className="absolute inset-x-0 bottom-0 p-2.5 z-10 bg-gradient-to-t from-black/90 via-black/50 to-transparent">
                {hasAlert && (
                  <span className="inline-flex items-center gap-1 text-[10px] font-bold text-red-300 bg-red-950/80 px-1.5 py-0.5 rounded-full mb-1 border border-red-500/50">
                    <AlertCircle className="w-3 h-3 text-red-400" /> Cảnh Báo
                  </span>
                )}

                <p className="text-xs font-bold text-white truncate drop-shadow-sm">{pen.name}</p>

                {/* Metrics snippet */}
                <div className="flex items-center gap-2 mt-1 text-[10px] text-slate-300">
                  <span className="flex items-center gap-0.5">
                    <Thermometer className="w-2.5 h-2.5 text-orange-400" />
                    {pen.temp !== undefined ? `${pen.temp}°C` : '--'}
                  </span>
                  <span className="flex items-center gap-0.5">
                    <Droplets className="w-2.5 h-2.5 text-blue-400" />
                    {pen.hum !== undefined ? `${pen.hum}%` : '--'}
                  </span>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
