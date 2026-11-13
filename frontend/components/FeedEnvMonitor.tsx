'use client';

import React from 'react';
import { 
  Activity, 
  Thermometer, 
  Droplets, 
  Wind, 
  RotateCw, 
  TrendingUp, 
  MessageSquare 
} from 'lucide-react';
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
import { Line } from 'react-chartjs-2';

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

interface FeedEnvMonitorProps {
  penName: string;
  penId: string;
  currentMode: 'livestock' | 'cultivation';
  temp: number;
  hum: number;
  smell: number;
  historyLogs?: Array<{ time: string; temp: number; hum: number; smell: number }>;
  onRefresh: () => void;
  onOpenChat: () => void;
}

export default function FeedEnvMonitor({
  penName,
  penId,
  currentMode,
  temp,
  hum,
  smell,
  historyLogs = [],
  onRefresh,
  onOpenChat,
}: FeedEnvMonitorProps) {
  const isLivestock = currentMode === 'livestock';

  // Kiểm tra ngưỡng cảnh báo an toàn
  const isTempHot = temp >= (isLivestock ? 35 : 40);
  const isHumHigh = hum >= (isLivestock ? 90 : 95);
  const isSmellBad = isLivestock ? smell >= 400 : smell <= 30;

  // Dữ liệu hiển thị biểu đồ
  const defaultLabels = historyLogs.length > 0 
    ? historyLogs.map(l => l.time) 
    : ['10:00', '11:00', '12:00', '13:00', '14:00', '15:00'];
  
  const tempData = historyLogs.length > 0 ? historyLogs.map(l => l.temp) : [27.5, 28.2, 29.1, 31.0, 30.5, temp || 29.8];
  const humData = historyLogs.length > 0 ? historyLogs.map(l => l.hum) : [72, 70, 68, 65, 69, hum || 70];

  const chartData = {
    labels: defaultLabels,
    datasets: [
      {
        label: 'Nhiệt độ (°C)',
        data: tempData,
        borderColor: '#15803D',
        backgroundColor: 'rgba(21, 128, 61, 0.1)',
        borderWidth: 2.5,
        tension: 0.35,
        fill: true,
        pointRadius: 4,
        pointBackgroundColor: '#15803D',
      },
      {
        label: 'Độ ẩm (%)',
        data: humData,
        borderColor: '#0284C7',
        backgroundColor: 'rgba(2, 132, 199, 0.05)',
        borderWidth: 2,
        tension: 0.35,
        fill: true,
        pointRadius: 3,
        pointBackgroundColor: '#0284C7',
      },
    ],
  };

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top' as const,
        labels: { boxWidth: 12, font: { size: 11, weight: 'bold' as const } },
      },
      tooltip: {
        backgroundColor: '#0F172A',
        padding: 10,
        titleFont: { size: 12 },
        bodyFont: { size: 11 },
      },
    },
    scales: {
      y: {
        grid: { color: '#E2E8F0' },
        ticks: { font: { size: 10 } },
      },
      x: {
        grid: { display: false },
        ticks: { font: { size: 10 } },
      },
    },
  };

  return (
    <div className="bg-fb-card rounded-2xl shadow-fb-card border border-fb-divider p-4 mb-4">
      {/* Tiêu đề trạm đo */}
      <div className="flex items-center justify-between pb-3 border-b border-fb-divider">
        <div className="flex items-center gap-2.5">
          <div className="w-10 h-10 rounded-full bg-emerald-100 flex items-center justify-center text-emerald-700 font-bold shadow-inner">
            <Activity className="w-5 h-5 animate-pulse" />
          </div>
          <div>
            <h4 className="font-bold text-sm text-fb-text">
              Trạm Cảm Biến Khí Hậu • {penName}
            </h4>
            <p className="text-xs text-fb-muted flex items-center gap-1.5">
              <span>Mã khu vực: <strong>{penId}</strong></span>
              <span>•</span>
              <span className="flex items-center gap-1 text-emerald-700 font-bold">
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-ping inline-block" />
                Thời gian thực
              </span>
            </p>
          </div>
        </div>

        <button
          onClick={onRefresh}
          title="Lấy dữ liệu cảm biến mới nhất"
          className="p-1.5 rounded-full hover:bg-fb-hover text-fb-muted hover:text-emerald-700 transition cursor-pointer"
          aria-label="Làm mới dữ liệu cảm biến"
        >
          <RotateCw className="w-4 h-4" />
        </button>
      </div>

      {/* 3 Đồng hồ thông số chính */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 my-4">
        {/* Thẻ nhiệt độ */}
        <div
          className={`p-3.5 rounded-2xl border transition ${
            isTempHot
              ? 'bg-red-50 border-red-300 text-red-900'
              : 'bg-gradient-to-br from-orange-50 to-amber-50/60 border-orange-200 text-slate-800'
          }`}
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-700 flex items-center gap-1">
              <Thermometer className="w-3.5 h-3.5 text-orange-600" />
              Nhiệt Độ
            </span>
            <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
              isTempHot ? 'bg-red-200 text-red-800' : 'bg-emerald-100 text-emerald-800'
            }`}>
              {isTempHot ? 'Nóng Quá Mức' : 'Thích Hợp'}
            </span>
          </div>

          <div className="mt-2 flex items-baseline gap-1">
            <span className="text-3xl font-extrabold tracking-tight">
              {temp !== undefined ? temp : '--'}
            </span>
            <span className="text-sm font-semibold text-slate-500">°C</span>
          </div>

          <div className="w-full bg-slate-200 h-1.5 rounded-full mt-3 overflow-hidden">
            <div
              className={`h-full transition-all duration-500 ${isTempHot ? 'bg-red-500' : 'bg-orange-500'}`}
              style={{ width: `${Math.min(100, (temp / 45) * 100)}%` }}
            />
          </div>
        </div>

        {/* Thẻ độ ẩm */}
        <div
          className={`p-3.5 rounded-2xl border transition ${
            isHumHigh
              ? 'bg-blue-100 border-blue-400 text-blue-900'
              : 'bg-gradient-to-br from-blue-50 to-cyan-50/60 border-blue-200 text-slate-800'
          }`}
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-700 flex items-center gap-1">
              <Droplets className="w-3.5 h-3.5 text-blue-600" />
              Độ Ẩm Không Khí
            </span>
            <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
              isHumHigh ? 'bg-blue-200 text-blue-800' : 'bg-emerald-100 text-emerald-800'
            }`}>
              {isHumHigh ? 'Ẩm Ướt Cao' : 'Bình Thường'}
            </span>
          </div>

          <div className="mt-2 flex items-baseline gap-1">
            <span className="text-3xl font-extrabold tracking-tight">
              {hum !== undefined ? hum : '--'}
            </span>
            <span className="text-sm font-semibold text-slate-500">%</span>
          </div>

          <div className="w-full bg-slate-200 h-1.5 rounded-full mt-3 overflow-hidden">
            <div
              className={`h-full transition-all duration-500 ${isHumHigh ? 'bg-blue-600' : 'bg-blue-500'}`}
              style={{ width: `${Math.min(100, hum)}%` }}
            />
          </div>
        </div>

        {/* Thẻ mùi chuồng / độ ẩm đất */}
        <div
          className={`p-3.5 rounded-2xl border transition ${
            isSmellBad
              ? 'bg-rose-50 border-rose-300 text-rose-900'
              : 'bg-gradient-to-br from-emerald-50 to-teal-50/60 border-emerald-200 text-slate-800'
          }`}
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-700 flex items-center gap-1">
              <Wind className="w-3.5 h-3.5 text-emerald-700" />
              {isLivestock ? 'Nồng Độ Khí Chuồng' : 'Độ Ẩm Của Đất'}
            </span>
            <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
              isSmellBad ? 'bg-rose-200 text-rose-800' : 'bg-emerald-100 text-emerald-800'
            }`}>
              {isSmellBad ? (isLivestock ? 'Mùi Nồng' : 'Đất Khô') : 'An Toàn'}
            </span>
          </div>

          <div className="mt-2 flex items-baseline gap-1">
            <span className="text-3xl font-extrabold tracking-tight">
              {smell !== undefined ? smell : '--'}
            </span>
            <span className="text-sm font-semibold text-slate-500">
              {isLivestock ? 'ppm' : '%'}
            </span>
          </div>

          <div className="w-full bg-slate-200 h-1.5 rounded-full mt-3 overflow-hidden">
            <div
              className={`h-full transition-all duration-500 ${isSmellBad ? 'bg-rose-500' : 'bg-emerald-600'}`}
              style={{ width: `${Math.min(100, isLivestock ? (smell / 600) * 100 : smell)}%` }}
            />
          </div>
        </div>
      </div>

      {/* Biểu đồ theo dõi diễn biến */}
      <div className="bg-fb-bg rounded-xl p-3 border border-fb-divider h-64 mt-2">
        <Line data={chartData} options={chartOptions} />
      </div>

      {/* Chân thẻ */}
      <div className="flex items-center justify-between pt-3 mt-3 border-t border-fb-divider text-xs text-fb-muted">
        <div className="flex gap-4">
          <button className="flex items-center gap-1.5 hover:text-emerald-700 transition font-medium cursor-pointer">
            <TrendingUp className="w-4 h-4" />
            <span>Chỉ số duy trì ổn định</span>
          </button>
          <button onClick={onOpenChat} className="flex items-center gap-1.5 text-emerald-700 font-bold hover:underline cursor-pointer">
            <MessageSquare className="w-4 h-4" />
            <span>Nhờ trợ lý phân tích biểu đồ này</span>
          </button>
        </div>
        <span className="text-[11px]">Dữ liệu tự động đo đạc từ trạm cảm biến</span>
      </div>
    </div>
  );
}
