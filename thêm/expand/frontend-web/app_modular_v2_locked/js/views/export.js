// app/js/views/export.js — Attendance Export (PDF / Word / Excel / Printing)
// ── UI/UX PRO MAX: EXPORT ATTENDANCE (PDF / WORD / CSV) ─────────
let currentExportData = [];
let currentSchoolInfo = null;
let exportFilterDebounceTimer = null;

async function fetchSchoolProfile() {
  if (currentSchoolInfo && currentSchoolInfo.id === schoolId) return currentSchoolInfo;
  try {
    const s = await api('GET', `/api/v1/schools/${schoolId}`);
    currentSchoolInfo = s;
    return s;
  } catch(e) {
    return {
      name: 'TRƯỜNG THPT CHUYÊN STEM',
      school_code: `THPT-STEM-${schoolId}`,
      province_city: 'Tỉnh/Thành phố',
      address: 'Khu Công Nghệ Cao'
    };
  }
}

function formatVNDate(dStr) {
  if (!dStr) return '';
  const parts = dStr.split('-');
  if (parts.length === 3) return `${parts[2]}/${parts[1]}/${parts[0]}`;
  return dStr;
}

function formatVNTime(tStr) {
  if (!tStr) return '';
  if (tStr.includes('T')) {
    const timePart = tStr.split('T')[1];
    return timePart.slice(0, 5);
  }
  if (tStr.includes(' ')) {
    const timePart = tStr.split(' ')[1];
    return timePart.slice(0, 5);
  }
  return tStr.slice(0, 5);
}

function getStatusBadgeText(st) {
  const m = {
    ON_TIME: 'Đúng Giờ',
    LATE: 'Đi Trễ',
    ABSENT: 'Vắng Không Phép',
    EXCUSED: 'Nghỉ Có Phép'
  };
  return m[st] || st || '—';
}

function getUniformBadgeText(uf) {
  const m = {
    OK: 'Chuẩn Phục',
    VIOLATION: 'Sai Phục',
    UNKNOWN: 'Chưa Rõ'
  };
  return m[uf] || uf || '—';
}

async function openExportModal() {
  const today = new Date().toISOString().split('T')[0];
  const dateFromEl = document.getElementById('exportDateFrom');
  const dateToEl   = document.getElementById('exportDateTo');
  const timeFromEl = document.getElementById('exportTimeFrom');
  const timeToEl   = document.getElementById('exportTimeTo');

  if (dateFromEl && !dateFromEl.value) dateFromEl.value = today;
  if (dateToEl && !dateToEl.value) dateToEl.value = today;
  if (timeFromEl && !timeFromEl.value) timeFromEl.value = '06:00';
  if (timeToEl && !timeToEl.value) timeToEl.value = '18:00';

  // Load classes dropdown if needed
  const selClass = document.getElementById('exportClassSelect');
  if (selClass) {
    if (!classesCache || !classesCache.length) {
      try { await loadClasses(); } catch(e) {}
    }
    selClass.innerHTML = '<option value="">Tất cả các lớp</option>' +
      (classesCache || []).map(c => `<option value="${c.id}">${escHtml(c.name)}</option>`).join('');
  }

  // Set school info
  const sch = await fetchSchoolProfile();
  const subEl = document.getElementById('exportSchoolSub');
  if (subEl) {
    subEl.innerText = `${sch.name || 'Trường học'} • Năm học: ${sch.academic_year || '2025-2026'} • Khung giờ linh hoạt & Báo cáo chuẩn văn bản sư phạm`;
  }

  openModal('modalExportAttendance');
  refreshExportPreview();
}

function applyExportPreset(preset) {
  const today = new Date();
  const todayStr = today.toISOString().split('T')[0];
  const dateFromEl = document.getElementById('exportDateFrom');
  const dateToEl   = document.getElementById('exportDateTo');
  const timeFromEl = document.getElementById('exportTimeFrom');
  const timeToEl   = document.getElementById('exportTimeTo');

  // Remove active on all chips
  document.querySelectorAll('.export-preset-chip').forEach(c => c.classList.remove('active'));
  const activeChip = document.getElementById(`chip_${preset}`);
  if (activeChip) activeChip.classList.add('active');

  if (preset === 'today_all') {
    dateFromEl.value = todayStr;
    dateToEl.value = todayStr;
    timeFromEl.value = '00:00';
    timeToEl.value = '23:59';
  } else if (preset === 'morning_rush') {
    dateFromEl.value = todayStr;
    dateToEl.value = todayStr;
    timeFromEl.value = '06:30';
    timeToEl.value = '08:30';
  } else if (preset === 'afternoon_rush') {
    dateFromEl.value = todayStr;
    dateToEl.value = todayStr;
    timeFromEl.value = '11:30';
    timeToEl.value = '17:30';
  } else if (preset === 'yesterday') {
    const y = new Date();
    y.setDate(y.getDate() - 1);
    const yStr = y.toISOString().split('T')[0];
    dateFromEl.value = yStr;
    dateToEl.value = yStr;
    timeFromEl.value = '00:00';
    timeToEl.value = '23:59';
  } else if (preset === 'last7days') {
    const past = new Date();
    past.setDate(past.getDate() - 6);
    dateFromEl.value = past.toISOString().split('T')[0];
    dateToEl.value = todayStr;
    timeFromEl.value = '00:00';
    timeToEl.value = '23:59';
  } else if (preset === 'this_month') {
    const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
    dateFromEl.value = firstDay.toISOString().split('T')[0];
    dateToEl.value = todayStr;
    timeFromEl.value = '00:00';
    timeToEl.value = '23:59';
  }

  refreshExportPreview();
}

function onExportFilterChange() {
  if (exportFilterDebounceTimer) clearTimeout(exportFilterDebounceTimer);
  exportFilterDebounceTimer = setTimeout(() => {
    refreshExportPreview();
  }, 250);
}

async function refreshExportPreview() {
  const dateFrom = document.getElementById('exportDateFrom')?.value || '';
  const dateTo   = document.getElementById('exportDateTo')?.value || '';
  const timeFrom = document.getElementById('exportTimeFrom')?.value || '';
  const timeTo   = document.getElementById('exportTimeTo')?.value || '';
  const classId  = document.getElementById('exportClassSelect')?.value || '';
  const status   = document.getElementById('exportStatusSelect')?.value || '';
  const uniform  = document.getElementById('exportUniformSelect')?.value || '';
  const timeMode = document.getElementById('exportTimeMode')?.value || 'daily';

  const previewBody = document.getElementById('exportPreviewBody');
  const countEl     = document.getElementById('exportPreviewCount');
  const rangeSumEl  = document.getElementById('exportRangeSummary');
  const startHelp   = document.getElementById('exportStartHelper');
  const endHelp     = document.getElementById('exportEndHelper');

  if (startHelp) startHelp.innerText = `Định dạng: ${timeFrom || '00:00'} ngày ${formatVNDate(dateFrom) || '—'}`;
  if (endHelp) endHelp.innerText = `Định dạng: ${timeTo || '23:59'} ngày ${formatVNDate(dateTo) || '—'}`;
  if (rangeSumEl) {
    rangeSumEl.innerText = `Từ ${timeFrom} (${formatVNDate(dateFrom)}) đến ${timeTo} (${formatVNDate(dateTo)})`;
  }

  if (previewBody) {
    previewBody.innerHTML = '<tr><td colspan="7" style="text-align:center;padding:16px;color:var(--muted);"><span class="cam-pulse-dot" style="display:inline-block;margin-right:6px;"></span>Đang tra cứu dữ liệu...</td></tr>';
  }

  try {
    let url = `/api/v1/s/${schoolId}/attendance?limit=5000`;
    if (dateFrom) url += `&date_from=${dateFrom}`;
    if (dateTo)   url += `&date_to=${dateTo}`;
    if (timeFrom) url += `&time_from=${timeFrom}`;
    if (timeTo)   url += `&time_to=${timeTo}`;
    if (timeMode) url += `&time_mode=${timeMode}`;
    if (classId)  url += `&class_id=${classId}`;
    if (status)   url += `&status=${status}`;
    if (uniform)  url += `&uniform_status=${uniform}`;

    const rows = await api('GET', url);
    currentExportData = rows || [];

    // Calculate live KPI stats
    const total = currentExportData.length;
    const countOnTime = currentExportData.filter(r => r.status === 'ON_TIME').length;
    const countLate   = currentExportData.filter(r => r.status === 'LATE').length;
    const countAbsent = currentExportData.filter(r => r.status === 'ABSENT' || r.status === 'EXCUSED').length;
    const countUniform = currentExportData.filter(r => r.uniform_status === 'VIOLATION').length;
    const pctOnTime   = total > 0 ? Math.round((countOnTime / total) * 100) : 0;

    const elTotal = document.getElementById('expStatTotal');
    const elOnTime = document.getElementById('expStatOnTime');
    const elLate = document.getElementById('expStatLate');
    const elAbsent = document.getElementById('expStatAbsent');
    const elUniform = document.getElementById('expStatUniform');

    if (elTotal) elTotal.innerText = total;
    if (elOnTime) elOnTime.innerText = `${countOnTime} (${pctOnTime}%)`;
    if (elLate) elLate.innerText = countLate;
    if (elAbsent) elAbsent.innerText = countAbsent;
    if (elUniform) elUniform.innerText = countUniform;

    if (countEl) countEl.innerText = `Xem trước dữ liệu (${total} bản ghi)`;

    if (!currentExportData.length) {
      if (previewBody) {
        previewBody.innerHTML = '<tr><td colspan="7" style="text-align:center;padding:24px;color:var(--muted);">📭 Không có bản ghi nào phù hợp với bộ lọc thời gian đã chọn.</td></tr>';
      }
      return;
    }

    // Render preview table (top 8 rows)
    const previewRows = currentExportData.slice(0, 8);
    let html = previewRows.map(r => {
      const timeStr = r.timestamp ? formatVNTime(r.timestamp) + ' ' + formatVNDate(r.date_only || r.timestamp.slice(0,10)) : (r.date_only || '—');
      const pts = (r.points_deducted || 0) > 0 ? `<span style="color:var(--red);font-weight:700;">-${r.points_deducted}</span>` : '<span style="color:var(--muted)">0</span>';
      return `
        <tr>
          <td><code style="color:var(--blue);font-weight:600;">${escHtml(timeStr)}</code></td>
          <td><b>${escHtml(r.student_code || '—')}</b></td>
          <td>${escHtml(r.full_name || 'Học sinh')}</td>
          <td><span class="chip chip-blue" style="font-size:0.72rem;">${escHtml(r.class_name || 'Chưa xếp')}</span></td>
          <td>${statusChip(r.status)}</td>
          <td>${uniformChip(r.uniform_status)}</td>
          <td>${pts}</td>
        </tr>
      `;
    }).join('');

    if (total > 8) {
      html += `<tr><td colspan="7" style="text-align:center;padding:8px;font-size:0.75rem;color:var(--muted);background:rgba(255,255,255,0.02);">... và còn ${total - 8} bản ghi khác sẽ được xuất đầy đủ ra tệp.</td></tr>`;
    }

    if (previewBody) previewBody.innerHTML = html;
  } catch(e) {
    if (previewBody) {
      previewBody.innerHTML = `<tr><td colspan="7" style="text-align:center;padding:16px;color:var(--red);">⚠️ Lỗi tải dữ liệu xem trước: ${escHtml(e.message || 'Không kết nối được')}</td></tr>`;
    }
  }
}

async function executeExportPDF() {
  if (!currentExportData || !currentExportData.length) {
    toast('Chưa Có Dữ Liệu', 'Không có bản ghi điểm danh nào trong khoảng thời gian đã chọn để xuất PDF.', 'warning');
    return;
  }

  const sch = await fetchSchoolProfile();
  const dateFrom = document.getElementById('exportDateFrom')?.value || '';
  const dateTo   = document.getElementById('exportDateTo')?.value || '';
  const timeFrom = document.getElementById('exportTimeFrom')?.value || '00:00';
  const timeTo   = document.getElementById('exportTimeTo')?.value || '23:59';
  const selClass = document.getElementById('exportClassSelect');
  const className = selClass && selClass.value ? selClass.options[selClass.selectedIndex].text : 'Tất cả các lớp';
  const selStatus = document.getElementById('exportStatusSelect');
  const statusName = selStatus && selStatus.value ? selStatus.options[selStatus.selectedIndex].text : 'Tất cả trạng thái';
  const selUniform = document.getElementById('exportUniformSelect');
  const uniformName = selUniform && selUniform.value ? selUniform.options[selUniform.selectedIndex].text : 'Tất cả nề nếp';

  // Stats
  const total = currentExportData.length;
  const countOnTime = currentExportData.filter(r => r.status === 'ON_TIME').length;
  const countLate   = currentExportData.filter(r => r.status === 'LATE').length;
  const countAbsent = currentExportData.filter(r => r.status === 'ABSENT').length;
  const countExcused = currentExportData.filter(r => r.status === 'EXCUSED').length;
  const countUniform = currentExportData.filter(r => r.uniform_status === 'VIOLATION').length;
  const pctOnTime   = total > 0 ? Math.round((countOnTime / total) * 100) : 0;

  const now = new Date();
  const todayVN = `ngày ${now.getDate()} tháng ${now.getMonth() + 1} năm ${now.getFullYear()}`;
  const reporterName = currentUser?.full_name || currentUser?.username || 'Cán bộ phụ trách';
  const reporterRole = currentUser?.role === 'HEADMASTER' ? 'Ban Giám Hiệu' : (currentUser?.role === 'INSPECTOR' ? 'Ban Giám Thị' : 'Giáo Viên');

  // Build Table Rows
  const rowsHtml = currentExportData.map((r, idx) => {
    const timeStr = r.timestamp ? (formatVNTime(r.timestamp) + ' ' + formatVNDate(r.date_only || r.timestamp.slice(0, 10))) : (r.date_only || '—');
    const methodStr = r.check_type === 'FACE_AI' ? 'FaceID AI' : (r.check_type === 'QR_SCAN' ? 'Mã QR' : 'Thủ công');
    const stStr = getStatusBadgeText(r.status);
    const ufStr = getUniformBadgeText(r.uniform_status);
    const ptsStr = (r.points_deducted || 0) > 0 ? `-${r.points_deducted}đ` : '—';
    const noteStr = r.violation_details ? `${escHtml(r.violation_details)} (${ptsStr})` : (r.status === 'LATE' ? `Đi trễ (${ptsStr})` : (r.uniform_status === 'VIOLATION' ? `Sai phục (${ptsStr})` : '—'));

    const stBg = r.status === 'ON_TIME' ? '#ecfdf5' : (r.status === 'LATE' ? '#fffbeb' : (r.status === 'ABSENT' ? '#fef2f2' : '#eff6ff'));
    const stColor = r.status === 'ON_TIME' ? '#065f46' : (r.status === 'LATE' ? '#92400e' : (r.status === 'ABSENT' ? '#991b1b' : '#1e40af'));

    return `
      <tr>
        <td style="text-align:center;">${idx + 1}</td>
        <td style="font-weight:bold;text-align:center;">${escHtml(r.student_code || '—')}</td>
        <td><b>${escHtml(r.full_name || 'Học sinh')}</b></td>
        <td style="text-align:center;">${escHtml(r.class_name || '—')}</td>
        <td style="text-align:center;">${escHtml(timeStr)}</td>
        <td style="text-align:center;">${escHtml(methodStr)}</td>
        <td style="text-align:center;background:${stBg};color:${stColor};font-weight:bold;">${escHtml(stStr)}</td>
        <td style="text-align:center;">${escHtml(ufStr)}</td>
        <td style="text-align:center;color:#b91c1c;">${escHtml(noteStr)}</td>
      </tr>
    `;
  }).join('');

  const docHtml = `
<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="utf-8">
  <title>BÁO CÁO ĐIỂM DANH - ${escHtml(sch.name || 'STEM')}</title>
  <style>
    @page {
      size: A4 portrait;
      margin: 12mm 10mm 12mm 10mm;
    }
    body {
      font-family: "Times New Roman", Times, serif;
      color: #000;
      background: #fff;
      margin: 0;
      padding: 0;
      font-size: 11pt;
      line-height: 1.35;
      -webkit-print-color-adjust: exact !important;
      print-color-adjust: exact !important;
    }
    .print-actions {
      position: fixed;
      top: 12px;
      right: 12px;
      z-index: 9999;
      display: flex;
      gap: 10px;
      background: rgba(255,255,255,0.95);
      padding: 8px 14px;
      border: 1px solid #ccc;
      border-radius: 8px;
      box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    .btn-p {
      padding: 8px 16px;
      font-size: 13px;
      font-weight: bold;
      border-radius: 6px;
      border: none;
      cursor: pointer;
    }
    .btn-p-blue { background: #2563eb; color: #fff; }
    .btn-p-gray { background: #f3f4f6; color: #374151; border: 1px solid #d1d5db; }
    @media print {
      .print-actions { display: none !important; }
    }
    .header-table {
      width: 100%;
      border-collapse: collapse;
      margin-bottom: 12px;
    }
    .header-table td {
      vertical-align: top;
      border: none;
      padding: 0;
    }
    .org-title { font-size: 10pt; text-transform: uppercase; }
    .school-title { font-size: 10.5pt; font-weight: bold; text-transform: uppercase; }
    .nation-title { font-size: 10.5pt; font-weight: bold; text-transform: uppercase; text-align: center; }
    .motto { font-size: 10.5pt; font-weight: bold; text-align: center; }
    .divider-line { width: 140px; height: 1px; background: #000; margin: 3px auto 0 auto; }
    .doc-number { font-size: 9.5pt; margin-top: 4px; font-style: italic; }

    .report-title-box {
      text-align: center;
      margin: 14px 0 10px 0;
    }
    .report-main-title {
      font-size: 15pt;
      font-weight: bold;
      text-transform: uppercase;
      margin: 0;
      color: #111;
    }
    .report-time {
      font-size: 10.5pt;
      font-style: italic;
      margin-top: 4px;
    }
    .report-filter-meta {
      font-size: 9.5pt;
      color: #333;
      margin-top: 3px;
    }

    /* KPI Summary Box */
    .kpi-table {
      width: 100%;
      border-collapse: collapse;
      margin: 10px 0 14px 0;
    }
    .kpi-table th, .kpi-table td {
      border: 1px solid #444;
      padding: 5px 8px;
      text-align: center;
      font-size: 9.5pt;
    }
    .kpi-table th {
      background: #f8fafc;
      font-weight: bold;
    }
    .kpi-num {
      font-size: 11pt;
      font-weight: bold;
    }

    /* Main Table */
    .data-table {
      width: 100%;
      border-collapse: collapse;
      margin-top: 6px;
    }
    .data-table th, .data-table td {
      border: 1px solid #333;
      padding: 5px 6px;
      font-size: 9.5pt;
    }
    .data-table th {
      background: #f1f5f9;
      font-weight: bold;
      text-align: center;
    }

    /* Signatures */
    .sig-table {
      width: 100%;
      margin-top: 20px;
      page-break-inside: avoid;
      border-collapse: collapse;
    }
    .sig-table td {
      border: none;
      vertical-align: top;
      text-align: center;
      width: 33.33%;
      padding: 0 8px;
    }
    .sig-date {
      font-size: 9.5pt;
      font-style: italic;
      margin-bottom: 4px;
    }
    .sig-role {
      font-size: 10pt;
      font-weight: bold;
      text-transform: uppercase;
    }
    .sig-sub {
      font-size: 9pt;
      font-style: italic;
      color: #444;
    }
    .sig-spacer {
      height: 60px;
    }
    .sig-name {
      font-size: 10pt;
      font-weight: bold;
    }
  </style>
</head>
<body>
  <div class="print-actions">
    <button class="btn-p btn-p-blue" onclick="window.print()">🖨️ In Báo Cáo / Lưu PDF</button>
    <button class="btn-p btn-p-gray" onclick="window.close()">✕ Đóng</button>
  </div>

  <table class="header-table">
    <tr>
      <td style="width: 45%;">
        <div class="org-title">SỞ GIÁO DỤC VÀ ĐÀO TẠO ${escHtml(sch.province_city || 'VIỆT NAM').toUpperCase()}</div>
        <div class="school-title">${escHtml(sch.name || 'TRƯỜNG THPT CHUYÊN STEM')}</div>
        <div class="doc-number">Mã trường: ${escHtml(sch.school_code || `SCH-${sch.id}`)} | Số: ......../BC-ĐD</div>
      </td>
      <td style="width: 55%; text-align: center;">
        <div class="nation-title">CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM</div>
        <div class="motto">Độc lập - Tự do - Hạnh phúc</div>
        <div class="divider-line"></div>
        <div style="font-size: 9.5pt; font-style: italic; margin-top: 6px;">${escHtml(sch.province_city || 'Địa phương')}, ${todayVN}</div>
      </td>
    </tr>
  </table>

  <div class="report-title-box">
    <h1 class="report-main-title">BÁO CÁO TỔNG HỢP ĐIỂM DANH & CHUYÊN CẦN HỌC SINH</h1>
    <div class="report-time">Khung thời gian: Từ <b>${timeFrom}</b> ngày <b>${formatVNDate(dateFrom)}</b> đến <b>${timeTo}</b> ngày <b>${formatVNDate(dateTo)}</b></div>
    <div class="report-filter-meta">Áp dụng: Lớp: <b>${escHtml(className)}</b> | Trạng thái: <b>${escHtml(statusName)}</b> | Đồng phục: <b>${escHtml(uniformName)}</b></div>
  </div>

  <!-- KPI SUMMARY TABLE -->
  <table class="kpi-table">
    <thead>
      <tr>
        <th>Tổng Lượt Quét</th>
        <th>Đúng Giờ (Tỷ lệ %)</th>
        <th>Đi Trễ</th>
        <th>Vắng Không Phép</th>
        <th>Nghỉ Có Phép</th>
        <th>Vi Phạm Đồng Phục</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td><span class="kpi-num">${total}</span></td>
        <td><span class="kpi-num" style="color:#047857;">${countOnTime} (${pctOnTime}%)</span></td>
        <td><span class="kpi-num" style="color:#b45309;">${countLate}</span></td>
        <td><span class="kpi-num" style="color:#b91c1c;">${countAbsent}</span></td>
        <td><span class="kpi-num" style="color:#1d4ed8;">${countExcused}</span></td>
        <td><span class="kpi-num" style="color:#be123c;">${countUniform}</span></td>
      </tr>
    </tbody>
  </table>

  <!-- DETAIL TABLE -->
  <table class="data-table">
    <thead>
      <tr>
        <th style="width:32px;">STT</th>
        <th style="width:75px;">Mã HS</th>
        <th>Họ Và Tên</th>
        <th style="width:55px;">Lớp</th>
        <th style="width:110px;">Thời Gian Quét</th>
        <th style="width:70px;">Hình Thức</th>
        <th style="width:80px;">Trạng Thái</th>
        <th style="width:75px;">Đồng Phục</th>
        <th style="width:95px;">Ghi Chú / Trừ Điểm</th>
      </tr>
    </thead>
    <tbody>
      ${rowsHtml}
    </tbody>
  </table>

  <!-- SIGNATURES -->
  <table class="sig-table">
    <tr>
      <td>
        <div class="sig-role">NGƯỜI LẬP BÁO CÁO</div>
        <div class="sig-sub">(Ký và ghi rõ họ tên)</div>
        <div class="sig-spacer"></div>
        <div class="sig-name">${escHtml(reporterName)}</div>
        <div style="font-size:8pt;color:#666;">(${reporterRole})</div>
      </td>
      <td>
        <div class="sig-role">GIÁO VIÊN / GIÁM THỊ</div>
        <div class="sig-sub">(Ký và ghi rõ họ tên)</div>
        <div class="sig-spacer"></div>
        <div class="sig-name">...................................................</div>
      </td>
      <td>
        <div class="sig-date">${escHtml(sch.province_city || 'Địa phương')}, ${todayVN}</div>
        <div class="sig-role">HIỆU TRƯỞNG / BGH DUYỆT</div>
        <div class="sig-sub">(Ký tên và đóng dấu)</div>
        <div class="sig-spacer"></div>
        <div class="sig-name">...................................................</div>
      </td>
    </tr>
  </table>

  <script>
    window.onload = function() {
      setTimeout(function() {
        window.print();
      }, 500);
    };
  <\/script>
</body>
</html>
  `;

  const printWin = window.open('', '_blank', 'width=1050,height=900');
  if (!printWin) {
    toast('Thông Báo', 'Trình duyệt đang chặn cửa sổ in (Pop-up). Vui lòng cho phép trình duyệt mở tab mới để xuất PDF.', 'warning');
    return;
  }
  printWin.document.open();
  printWin.document.write(docHtml);
  printWin.document.close();
  toast('Đang Mở Bản In PDF', 'Hộp thoại in đã được khởi chạy. Bạn hãy chọn "Lưu dưới dạng PDF" (Save as PDF).', 'success');
}

async function executeExportWord() {
  if (!currentExportData || !currentExportData.length) {
    toast('Chưa Có Dữ Liệu', 'Không có bản ghi điểm danh nào để xuất file Word.', 'warning');
    return;
  }

  const sch = await fetchSchoolProfile();
  const dateFrom = document.getElementById('exportDateFrom')?.value || '';
  const dateTo   = document.getElementById('exportDateTo')?.value || '';
  const timeFrom = document.getElementById('exportTimeFrom')?.value || '00:00';
  const timeTo   = document.getElementById('exportTimeTo')?.value || '23:59';
  const selClass = document.getElementById('exportClassSelect');
  const className = selClass && selClass.value ? selClass.options[selClass.selectedIndex].text : 'Tất cả các lớp';
  const selStatus = document.getElementById('exportStatusSelect');
  const statusName = selStatus && selStatus.value ? selStatus.options[selStatus.selectedIndex].text : 'Tất cả trạng thái';
  const selUniform = document.getElementById('exportUniformSelect');
  const uniformName = selUniform && selUniform.value ? selUniform.options[selUniform.selectedIndex].text : 'Tất cả nề nếp';

  const total = currentExportData.length;
  const countOnTime = currentExportData.filter(r => r.status === 'ON_TIME').length;
  const countLate   = currentExportData.filter(r => r.status === 'LATE').length;
  const countAbsent = currentExportData.filter(r => r.status === 'ABSENT').length;
  const countExcused = currentExportData.filter(r => r.status === 'EXCUSED').length;
  const countUniform = currentExportData.filter(r => r.uniform_status === 'VIOLATION').length;
  const pctOnTime   = total > 0 ? Math.round((countOnTime / total) * 100) : 0;

  const now = new Date();
  const todayVN = `ngày ${now.getDate()} tháng ${now.getMonth() + 1} năm ${now.getFullYear()}`;
  const reporterName = currentUser?.full_name || currentUser?.username || 'Cán bộ phụ trách';
  const reporterRole = currentUser?.role === 'HEADMASTER' ? 'Ban Giám Hiệu' : (currentUser?.role === 'INSPECTOR' ? 'Ban Giám Thị' : 'Giáo Viên');

  const rowsHtml = currentExportData.map((r, idx) => {
    const timeStr = r.timestamp ? (formatVNTime(r.timestamp) + ' ' + formatVNDate(r.date_only || r.timestamp.slice(0, 10))) : (r.date_only || '—');
    const methodStr = r.check_type === 'FACE_AI' ? 'FaceID AI' : (r.check_type === 'QR_SCAN' ? 'Mã QR' : 'Thủ công');
    const stStr = getStatusBadgeText(r.status);
    const ufStr = getUniformBadgeText(r.uniform_status);
    const ptsStr = (r.points_deducted || 0) > 0 ? `-${r.points_deducted}đ` : '0';
    const noteStr = r.violation_details ? `${escHtml(r.violation_details)} (${ptsStr})` : (r.status === 'LATE' ? `Đi trễ (${ptsStr})` : (r.uniform_status === 'VIOLATION' ? `Sai phục (${ptsStr})` : '—'));

    return `
      <tr>
        <td style="border:1px solid #000;text-align:center;padding:5px;">${idx + 1}</td>
        <td style="border:1px solid #000;text-align:center;font-weight:bold;padding:5px;">${escHtml(r.student_code || '—')}</td>
        <td style="border:1px solid #000;padding:5px;"><b>${escHtml(r.full_name || 'Học sinh')}</b></td>
        <td style="border:1px solid #000;text-align:center;padding:5px;">${escHtml(r.class_name || '—')}</td>
        <td style="border:1px solid #000;text-align:center;padding:5px;">${escHtml(timeStr)}</td>
        <td style="border:1px solid #000;text-align:center;padding:5px;">${escHtml(methodStr)}</td>
        <td style="border:1px solid #000;text-align:center;font-weight:bold;padding:5px;">${escHtml(stStr)}</td>
        <td style="border:1px solid #000;text-align:center;padding:5px;">${escHtml(ufStr)}</td>
        <td style="border:1px solid #000;text-align:center;padding:5px;color:#b91c1c;">${escHtml(noteStr)}</td>
      </tr>
    `;
  }).join('');

  const wordContent = `
<html xmlns:o="urn:schemas-microsoft-com:office:office"
      xmlns:w="urn:schemas-microsoft-com:office:word"
      xmlns="http://www.w3.org/TR/REC-html40">
<head>
  <meta charset="utf-8">
  <!--[if gte mso 9]>
  <xml>
    <w:WordDocument>
      <w:View>Print</w:View>
      <w:Zoom>100</w:Zoom>
      <w:DoNotOptimizeForBrowser/>
    </w:WordDocument>
  </xml>
  <![endif]-->
  <style>
    @page Section1 {
      size: 595.3pt 841.9pt;
      margin: 1.5cm 1.5cm 1.5cm 1.5cm;
      mso-header-margin: 35.4pt;
      mso-footer-margin: 35.4pt;
      mso-paper-source: 0;
    }
    div.Section1 { page: Section1; }
    body {
      font-family: "Times New Roman", Times, serif;
      font-size: 11pt;
      line-height: 1.35;
      color: #000;
    }
    table { border-collapse: collapse; width: 100%; }
    th { background-color: #f1f5f9; font-weight: bold; border: 1px solid #000; padding: 6px; text-align: center; }
    td { border: 1px solid #000; padding: 5px; }
  </style>
</head>
<body>
  <div class="Section1">
    <table style="border:none;margin-bottom:15px;">
      <tr>
        <td style="border:none;width:45%;vertical-align:top;">
          <div style="font-size:10pt;text-transform:uppercase;">SỞ GIÁO DỤC VÀ ĐÀO TẠO ${escHtml(sch.province_city || 'VIỆT NAM').toUpperCase()}</div>
          <div style="font-size:11pt;font-weight:bold;text-transform:uppercase;">${escHtml(sch.name || 'TRƯỜNG THPT CHUYÊN STEM')}</div>
          <div style="font-size:9.5pt;font-style:italic;">Mã trường: ${escHtml(sch.school_code || `SCH-${sch.id}`)} | Số: ......../BC-ĐD</div>
        </td>
        <td style="border:none;width:55%;text-align:center;vertical-align:top;">
          <div style="font-size:11pt;font-weight:bold;text-transform:uppercase;">CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM</div>
          <div style="font-size:11pt;font-weight:bold;">Độc lập - Tự do - Hạnh phúc</div>
          <div style="margin:2px auto;width:120px;border-bottom:1px solid #000;"></div>
          <div style="font-size:9.5pt;font-style:italic;margin-top:6px;">${escHtml(sch.province_city || 'Địa phương')}, ${todayVN}</div>
        </td>
      </tr>
    </table>

    <div style="text-align:center;margin:15px 0 10px 0;">
      <div style="font-size:15pt;font-weight:bold;text-transform:uppercase;">BÁO CÁO TỔNG HỢP ĐIỂM DANH & CHUYÊN CẦN HỌC SINH</div>
      <div style="font-size:10.5pt;font-style:italic;margin-top:4px;">Khung thời gian: Từ <b>${timeFrom}</b> ngày <b>${formatVNDate(dateFrom)}</b> đến <b>${timeTo}</b> ngày <b>${formatVNDate(dateTo)}</b></div>
      <div style="font-size:9.5pt;margin-top:3px;">Áp dụng: Lớp: <b>${escHtml(className)}</b> | Trạng thái: <b>${escHtml(statusName)}</b> | Đồng phục: <b>${escHtml(uniformName)}</b></div>
    </div>

    <!-- KPI TABLE -->
    <table style="margin:10px 0 15px 0;">
      <thead>
        <tr>
          <th>Tổng Lượt Quét</th>
          <th>Đúng Giờ (Tỷ lệ %)</th>
          <th>Đi Trễ</th>
          <th>Vắng Không Phép</th>
          <th>Nghỉ Có Phép</th>
          <th>Vi Phạm Đồng Phục</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td style="text-align:center;font-weight:bold;">${total}</td>
          <td style="text-align:center;font-weight:bold;color:#047857;">${countOnTime} (${pctOnTime}%)</td>
          <td style="text-align:center;font-weight:bold;color:#b45309;">${countLate}</td>
          <td style="text-align:center;font-weight:bold;color:#b91c1c;">${countAbsent}</td>
          <td style="text-align:center;font-weight:bold;color:#1d4ed8;">${countExcused}</td>
          <td style="text-align:center;font-weight:bold;color:#be123c;">${countUniform}</td>
        </tr>
      </tbody>
    </table>

    <!-- DETAIL TABLE -->
    <table>
      <thead>
        <tr>
          <th style="width:30px;">STT</th>
          <th style="width:75px;">Mã HS</th>
          <th>Họ Và Tên</th>
          <th style="width:55px;">Lớp</th>
          <th style="width:110px;">Thời Gian Quét</th>
          <th style="width:70px;">Hình Thức</th>
          <th style="width:80px;">Trạng Thái</th>
          <th style="width:75px;">Đồng Phục</th>
          <th style="width:95px;">Ghi Chú</th>
        </tr>
      </thead>
      <tbody>
        ${rowsHtml}
      </tbody>
    </table>

    <!-- SIGNATURES -->
    <table style="border:none;margin-top:25px;">
      <tr>
        <td style="border:none;width:33.33%;text-align:center;vertical-align:top;">
          <div style="font-weight:bold;text-transform:uppercase;">NGƯỜI LẬP BÁO CÁO</div>
          <div style="font-style:italic;font-size:9pt;">(Ký và ghi rõ họ tên)</div>
          <div style="height:60px;"></div>
          <div style="font-weight:bold;">${escHtml(reporterName)}</div>
          <div style="font-size:8pt;color:#666;">(${reporterRole})</div>
        </td>
        <td style="border:none;width:33.33%;text-align:center;vertical-align:top;">
          <div style="font-weight:bold;text-transform:uppercase;">GIÁO VIÊN / GIÁM THỊ</div>
          <div style="font-style:italic;font-size:9pt;">(Ký và ghi rõ họ tên)</div>
          <div style="height:60px;"></div>
          <div style="font-weight:bold;">...................................................</div>
        </td>
        <td style="border:none;width:33.33%;text-align:center;vertical-align:top;">
          <div style="font-style:italic;font-size:9.5pt;margin-bottom:3px;">${escHtml(sch.province_city || 'Địa phương')}, ${todayVN}</div>
          <div style="font-weight:bold;text-transform:uppercase;">HIỆU TRƯỞNG / BGH DUYỆT</div>
          <div style="font-style:italic;font-size:9pt;">(Ký tên và đóng dấu)</div>
          <div style="height:60px;"></div>
          <div style="font-weight:bold;">...................................................</div>
        </td>
      </tr>
    </table>
  </div>
</body>
</html>
  `;

  const blob = new Blob(['\ufeff' + wordContent], { type: 'application/msword;charset=utf-8' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  const cleanSchool = (sch.school_code || 'STEM').replace(/[^a-zA-Z0-9_-]/g, '_');
  a.download = `Bao_cao_diem_danh_${cleanSchool}_${dateFrom || 'start'}_${dateTo || 'end'}.doc`;
  a.click();
  toast('✅ Thành Công', 'Đã tải xuống tệp Word (.DOC) báo cáo điểm danh.', 'success');
}

async function exportAttendanceFilteredCSV() {
  const dateFrom = document.getElementById('exportDateFrom')?.value || '';
  const dateTo   = document.getElementById('exportDateTo')?.value || '';
  const timeFrom = document.getElementById('exportTimeFrom')?.value || '';
  const timeTo   = document.getElementById('exportTimeTo')?.value || '';
  const classId  = document.getElementById('exportClassSelect')?.value || '';
  const status   = document.getElementById('exportStatusSelect')?.value || '';
  const uniform  = document.getElementById('exportUniformSelect')?.value || '';
  const timeMode = document.getElementById('exportTimeMode')?.value || 'daily';

  const token = localStorage.getItem(AUTH_KEY);
  const apiBase = (typeof STEM_CONFIG !== 'undefined' && STEM_CONFIG.API_BASE) ? STEM_CONFIG.API_BASE : '';

  let url = `${apiBase}/api/v1/s/${schoolId}/attendance/export-csv?`;
  const params = [];
  if (dateFrom) params.push(`date_from=${encodeURIComponent(dateFrom)}`);
  if (dateTo)   params.push(`date_to=${encodeURIComponent(dateTo)}`);
  if (timeFrom) params.push(`time_from=${encodeURIComponent(timeFrom)}`);
  if (timeTo)   params.push(`time_to=${encodeURIComponent(timeTo)}`);
  if (timeMode) params.push(`time_mode=${encodeURIComponent(timeMode)}`);
  if (classId)  params.push(`class_id=${encodeURIComponent(classId)}`);
  if (status)   params.push(`status=${encodeURIComponent(status)}`);
  if (uniform)  params.push(`uniform_status=${encodeURIComponent(uniform)}`);
  url += params.join('&');

  try {
    const res = await fetch(url, { headers: { Authorization: `Bearer ${token}` } });
    if (!res.ok) throw new Error('Không thể xuất báo cáo CSV');
    const blob = await res.blob();
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `diem_danh_${dateFrom || 'start'}_${dateTo || 'end'}.csv`;
    a.click();
    toast('✅ Thành Công', 'Đã tải xuống tệp CSV điểm danh.', 'success');
  } catch(e) {
    toast('Lỗi', e.message || 'Lỗi khi xuất CSV', 'error');
  }
}

async function exportAttendanceCSV() {
  // Backward compatible quick caller
  openExportModal();
}

async function confirmMarkAbsentToday() {
  if (!confirm('Bạn có chắc chắn muốn chốt vắng hôm nay cho các học sinh chưa điểm danh?\n- Học sinh có đơn phép hợp lệ sẽ được ghi nhận là CÓ PHÉP (EXCUSED).\n- Học sinh không phép sẽ ghi nhận VẮNG (ABSENT) và bị trừ điểm nề nếp.')) return;
  try {
    const res = await api('POST', `/api/v1/s/${schoolId}/attendance/mark-absent-today`);
    toast('✅ Đã Chốt Vắng', res.message || 'Đã chốt danh sách vắng hôm nay.', 'success');
    loadAttendance();
  } catch(e) {
    toast('Lỗi', e.detail || 'Không thể chốt vắng hôm nay.', 'error');
  }
}



export {
  applyExportPreset, confirmMarkAbsentToday, executeExportPDF, executeExportWord, exportAttendanceCSV, exportAttendanceFilteredCSV, fetchSchoolProfile, formatVNDate, formatVNTime, getStatusBadgeText, getUniformBadgeText, onExportFilterChange, openExportModal, refreshExportPreview
};
