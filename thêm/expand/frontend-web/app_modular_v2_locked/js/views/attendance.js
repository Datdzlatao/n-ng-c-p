// app/js/views/attendance.js — Attendance Logs, Live Feeds & Timeline Lightbox
// ── Attendance (Enhanced In/Out Pairing, Reconciliation & Stranger Alerts) ────────────────────
let currentAttTab = 'all'; // 'all' | 'in' | 'out' | 'recon' | 'strangers'
let attEventsCache = [];
let attReconCache = { stats: {}, records: [] };
let attStrangersCache = [];
let attSearchTimeout = null;

function setTodayDate() {
  const el = document.getElementById('attDate');
  if (el && !el.value) el.value = new Date().toISOString().split('T')[0];
}

function setAttDateOffset(offset) {
  const d = new Date();
  d.setDate(d.getDate() + offset);
  const el = document.getElementById('attDate');
  if (el) {
    el.value = d.toISOString().split('T')[0];
    loadAttendance();
  }
}

function openProofImageModal(imgUrl, title, subtitle, detailsHtml) {
  const modal = document.getElementById('modalProofImage');
  const img = document.getElementById('proofModalImg');
  const titleEl = document.getElementById('proofModalTitle');
  const subEl = document.getElementById('proofModalSubtitle');
  const detEl = document.getElementById('proofModalDetails');
  const dlBtn = document.getElementById('proofModalDownloadBtn');
  if (!modal) return;

  if (titleEl) titleEl.textContent = title || 'Ảnh Chụp Bằng Chứng Camera AI';
  if (subEl) subEl.textContent = subtitle || 'Chi tiết sự kiện nhận diện & kiểm soát nề nếp';
  if (img) {
    img.src = imgUrl || '';
    img.alt = title || 'Ảnh chụp bằng chứng';
  }
  if (dlBtn) dlBtn.href = imgUrl || '#';
  if (detEl) detEl.innerHTML = detailsHtml || '<div style="color:var(--muted);">Không có ghi chú bổ sung.</div>';

  modal.style.display = 'flex';
}

function closeProofImageModal() {
  const modal = document.getElementById('modalProofImage');
  if (modal) modal.style.display = 'none';
}

function openAttendanceProofModal(idx) {
  const r = (attEventsCache || [])[idx];
  if (!r) return;
  const isOut = (r.direction || 'IN').toUpperCase() === 'OUT';
  const rawTs = r.timestamp || '';
  const timeStr = rawTs.replace('T', ' ').split(' ')[1]?.slice(0, 8) || '—';
  const dateStr = rawTs.replace('T', ' ').split(' ')[0] || r.date_only || '';
  const violationLabel = r.violation_details || (r.status === 'LATE' ? 'Đi học muộn giờ quy định' : (r.uniform_status === 'VIOLATION' ? 'Vi phạm trang phục đồng phục' : 'Nhận diện nề nếp bình thường'));

  const detailsHtml = `
    <div style="display:grid;grid-template-columns:120px 1fr;gap:6px 14px;line-height:1.6;font-size:0.84rem;">
      <span style="color:var(--muted);">Học sinh:</span><strong>${escHtml(r.full_name)} (${escHtml(r.student_code)})</strong>
      <span style="color:var(--muted);">Lớp học:</span><span>${escHtml(r.class_name || '—')}</span>
      <span style="color:var(--muted);">Sự kiện:</span><span>${isOut ? '🔵 Lượt ra về' : '🟢 Lượt đến trường'} lúc <strong>${escHtml(timeStr)}</strong> (${escHtml(dateStr)})</span>
      <span style="color:var(--muted);">Trạm camera:</span><span>${escHtml(r.camera_name || 'Cổng trường')} · ${escHtml(r.camera_location || 'Camera AI')}</span>
      <span style="color:var(--muted);">Hình thức:</span><span><span class="chip chip-blue" style="font-size:0.72rem;">${escHtml(r.check_type || 'FACE_AI')}</span></span>
      <span style="color:var(--muted);">Tình trạng:</span><span>${statusChip(r.status)} · ${!isOut ? uniformChip(r.uniform_status) : ''}</span>
      <span style="color:var(--muted);">Chi tiết nề nếp:</span><span style="color:var(--orange);font-weight:600;">${escHtml(violationLabel)}</span>
      <span style="color:var(--muted);">Điểm trừ nề nếp:</span><span style="color:${(r.points_deducted||0)>0?'var(--red)':'var(--green)'};font-weight:700;">${(r.points_deducted||0)>0?`-${r.points_deducted} điểm`:'0 điểm'}</span>
    </div>
  `;

  openProofImageModal(
    r.proof_image_url,
    `Ảnh Chụp Camera AI - ${r.full_name}`,
    `${r.student_code} | ${timeStr} | ${r.camera_name || 'Cổng trường'}`,
    detailsHtml
  );
}

function openStrangerProofModal(idx) {
  const r = (attStrangersCache || [])[idx];
  if (!r) return;
  const isOut = (r.direction || 'IN').toUpperCase() === 'OUT';
  const rawTs = r.timestamp || r.created_at || '';
  const timeStr = rawTs.replace('T', ' ').split(' ')[1]?.slice(0, 8) || '—';
  const dateStr = rawTs.replace('T', ' ').split(' ')[0] || r.date_only || '';

  const detailsHtml = `
    <div style="display:grid;grid-template-columns:130px 1fr;gap:8px 14px;line-height:1.6;font-size:0.84rem;">
      <span style="color:var(--muted);">Cảnh báo:</span><strong style="color:#f43f5e;">${escHtml(r.title || 'Phát hiện người lạ / Không rõ danh tính')}</strong>
      <span style="color:var(--muted);">Thời gian phát hiện:</span><span><strong>${escHtml(timeStr)}</strong> (${escHtml(dateStr)})</span>
      <span style="color:var(--muted);">Khu vực cổng:</span><span>${isOut ? '🔵 Cổng ra về' : '🟢 Cổng đến trường'}</span>
      <span style="color:var(--muted);">Trạm camera:</span><span>${escHtml(r.camera_name || 'Cổng trường')} · ${escHtml(r.camera_location || 'Camera AI')}</span>
      <span style="color:var(--muted);">Mô tả chi tiết:</span><span>${escHtml(r.description || 'Khuôn mặt chưa được đăng ký trong CSDL học sinh/giáo viên của nhà trường.')}</span>
      <span style="color:var(--muted);">Trạng thái:</span><span><span class="chip chip-orange" style="font-size:0.72rem;">Đang giám sát an ninh</span></span>
    </div>
  `;

  openProofImageModal(
    r.proof_image_url,
    '🚨 Ảnh Chụp Đối Tượng Người Lạ (Camera AI)',
    `${timeStr} (${dateStr}) | Trạm: ${r.camera_name || 'Cổng trường'}`,
    detailsHtml
  );
}

function openReconLogProofModal(idx) {
  const student = window.currentReconStudent;
  if (!student || !student.all_logs) return;
  const l = student.all_logs[idx];
  if (!l) return;
  const isIn = (l.direction || 'IN').toUpperCase() === 'IN';
  const timeStr = escHtml(l.time || l.timestamp?.slice(11,19) || '');
  const violationText = l.violation_details || (l.status === 'LATE' ? 'Đi học muộn' : (l.uniform_status === 'VIOLATION' ? 'Sai đồng phục' : ''));

  const detailsHtml = `
    <div style="display:grid;grid-template-columns:120px 1fr;gap:6px 12px;line-height:1.5;font-size:0.84rem;">
      <span style="color:var(--muted);">Học sinh:</span><strong>${escHtml(student.full_name)} (${escHtml(student.student_code)})</strong>
      <span style="color:var(--muted);">Lớp:</span><span>${escHtml(student.class_name)}</span>
      <span style="color:var(--muted);">Lượt quét:</span><span>${isIn ? '🟢 Lượt đến trường' : '🔵 Lượt ra về'} lúc <strong>${timeStr}</strong></span>
      <span style="color:var(--muted);">Trạm quét:</span><span>${escHtml(l.camera_name || 'Cổng trường')}</span>
      <span style="color:var(--muted);">Tình trạng:</span><span>${statusChip(l.status)} · ${!isIn ? '' : uniformChip(l.uniform_status)}</span>
      ${violationText ? `<span style="color:var(--muted);">Ghi chú vi phạm:</span><span style="color:var(--orange);font-weight:600;">${escHtml(violationText)}</span>` : ''}
    </div>
  `;

  openProofImageModal(
    l.proof_image_url,
    `Ảnh Chụp Camera - ${student.full_name}`,
    `${student.student_code} | ${timeStr} | ${l.camera_name || 'Cổng trường'}`,
    detailsHtml
  );
}

function switchAttTab(tab) {
  currentAttTab = tab;
  ['all', 'in', 'out', 'recon', 'strangers'].forEach(t => {
    const btn = document.getElementById(`attTabBtn-${t}`);
    if (btn) {
      if (t === tab) {
        btn.className = 'btn btn-sm btn-primary att-tab-btn';
      } else {
        btn.className = 'btn btn-sm btn-outline att-tab-btn';
        if (t === 'recon') {
          btn.style.borderColor = 'rgba(245,158,11,0.4)';
          btn.style.color = 'var(--orange)';
        } else if (t === 'strangers') {
          btn.style.borderColor = 'rgba(239,68,68,0.4)';
          btn.style.color = '#f43f5e';
        }
      }
    }
  });

  const eventsWrap = document.getElementById('attEventsTableWrap');
  const reconWrap = document.getElementById('attReconTableWrap');
  const strangersWrap = document.getElementById('attStrangersTableWrap');

  if (eventsWrap) eventsWrap.style.display = 'none';
  if (reconWrap) reconWrap.style.display = 'none';
  if (strangersWrap) strangersWrap.style.display = 'none';

  if (tab === 'recon') {
    if (reconWrap) reconWrap.style.display = 'block';
    renderAttendanceReconTable();
  } else if (tab === 'strangers') {
    if (strangersWrap) strangersWrap.style.display = 'block';
    renderAttendanceStrangersTable();
  } else {
    if (eventsWrap) eventsWrap.style.display = 'block';
    renderAttendanceEventsTable();
  }
  renderAttendanceStatsStrip();
}

function debounceAttendanceSearch(term) {
  clearTimeout(attSearchTimeout);
  attSearchTimeout = setTimeout(() => {
    if (currentAttTab === 'recon') {
      loadAttendance();
    } else if (currentAttTab === 'strangers') {
      renderAttendanceStrangersTable();
    } else {
      renderAttendanceEventsTable();
    }
  }, 250);
}

async function populateAttendanceClasses() {
  const select = document.getElementById('attClassFilter');
  if (!select) return;
  if (!classesCache || !classesCache.length) {
    try { await loadClasses(); } catch(e) {}
  }
  const curVal = select.value;
  select.innerHTML = '<option value="">Tất cả các lớp</option>' + 
    (classesCache || []).map(c => `<option value="${c.id}">${escHtml(c.name)}</option>`).join('');
  if (curVal) select.value = curVal;
}

async function loadAttendance() {
  setTodayDate();
  await populateAttendanceClasses();

  const date = document.getElementById('attDate')?.value || new Date().toISOString().split('T')[0];
  const classId = document.getElementById('attClassFilter')?.value || '';
  const search = document.getElementById('attSearchInput')?.value || '';

  const tblEvents = document.getElementById('attBody');
  const tblRecon = document.getElementById('attReconBody');
  const tblStrangers = document.getElementById('attStrangersBody');
  if (tblEvents) tblEvents.innerHTML = '<tr><td colspan="8" style="text-align:center;padding:24px;color:var(--muted);">Đang tải dữ liệu sự kiện...</td></tr>';
  if (tblRecon) tblRecon.innerHTML = '<tr><td colspan="7" style="text-align:center;padding:24px;color:var(--muted);">Đang đối chiếu dữ liệu vào - ra...</td></tr>';
  if (tblStrangers) tblStrangers.innerHTML = '<tr><td colspan="6" style="text-align:center;padding:24px;color:var(--muted);">Đang tải danh sách cảnh báo người lạ...</td></tr>';

  try {
    let eventsUrl = `/api/v1/s/${schoolId}/attendance?date=${date}&limit=50000`;
    if (classId) eventsUrl += `&class_id=${classId}`;

    let reconUrl = `/api/v1/s/${schoolId}/attendance/reconciliation?date=${date}`;
    if (classId) reconUrl += `&class_id=${classId}`;
    if (search.trim()) reconUrl += `&search=${encodeURIComponent(search.trim())}`;

    let strangersUrl = `/api/v1/s/${schoolId}/attendance/security-alerts?date=${date}&limit=5000`;

    const [events, reconRes, strangersRes, todaySummary] = await Promise.all([
      api('GET', eventsUrl),
      api('GET', reconUrl),
      api('GET', strangersUrl).catch(() => []),
      api('GET', `/api/v1/s/${schoolId}/attendance/today?date=${date}`).catch(() => ({}))
    ]);

    attEventsCache = events || [];
    attReconCache = reconRes || { stats: {}, records: [] };
    attStrangersCache = strangersRes || [];

    // Update Tab Badges
    const badgeAll = document.getElementById('attBadgeAll');
    const badgeIn = document.getElementById('attBadgeIn');
    const badgeOut = document.getElementById('attBadgeOut');
    const badgeRecon = document.getElementById('attBadgeRecon');
    const badgeStrangers = document.getElementById('attBadgeStrangers');

    const inCount = attEventsCache.filter(r => (r.direction || 'IN').toUpperCase() === 'IN').length;
    const outCount = attEventsCache.filter(r => (r.direction || 'IN').toUpperCase() === 'OUT').length;
    const reconAnomalies = (attReconCache.records || []).filter(r => r.is_anomaly).length;

    if (badgeAll) badgeAll.textContent = attEventsCache.length;
    if (badgeIn) badgeIn.textContent = inCount;
    if (badgeOut) badgeOut.textContent = outCount;
    if (badgeRecon) badgeRecon.textContent = reconAnomalies > 0 ? `${reconAnomalies} cảnh báo` : (attReconCache.records || []).length;
    if (badgeStrangers) badgeStrangers.textContent = attStrangersCache.length;

    const btnAbsent = document.getElementById('btnMarkAbsent');
    if (btnAbsent) {
      btnAbsent.style.display = ['TEACHER','HEADMASTER','ADMIN','PLATFORM_ADMIN','INSPECTOR'].includes(currentUser?.role) ? 'inline-block' : 'none';
    }

    renderAttendanceStatsStrip(todaySummary);

    if (currentAttTab === 'recon') {
      renderAttendanceReconTable();
    } else if (currentAttTab === 'strangers') {
      renderAttendanceStrangersTable();
    } else {
      renderAttendanceEventsTable();
    }
  } catch(e) {
    if (tblEvents) tblEvents.innerHTML = errorRow(e, 8);
    if (tblRecon) tblRecon.innerHTML = errorRow(e, 7);
    if (tblStrangers) tblStrangers.innerHTML = errorRow(e, 6);
  }
}

function renderAttendanceStatsStrip(todaySummary) {
  const statsEl = document.getElementById('attStats');
  if (!statsEl) return;

  if (currentAttTab === 'recon') {
    const s = attReconCache.stats || {};
    statsEl.innerHTML = [
      { label:'Tổng Học Sinh', val: s.total_students ?? 0, color:'var(--text)', icon:'👥' },
      { label:'Đang Ở Trường', val: s.in_campus ?? 0, color:'var(--green)', icon:'🟢' },
      { label:'Đã Ra Về',      val: s.departed ?? 0,  color:'var(--blue)', icon:'🔵' },
      { label:'Ra Về Sớm',     val: s.early_exit ?? 0, color:'var(--orange)', icon:'⚠️' },
      { label:'Vắng / Phép',   val: (s.absent ?? 0) + (s.excused ?? 0), color:'var(--red)', icon:'✕' },
      { label:'Bất Thường',    val: s.anomaly ?? 0, color:'#f43f5e', icon:'🚨' },
    ].map(item => `
      <div class="stat-card" style="min-width:130px;">
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:2px;">
          <span style="font-size:0.75rem;color:var(--muted);font-weight:600;">${item.label}</span>
          <span style="font-size:0.85rem;">${item.icon}</span>
        </div>
        <div class="stat-num" style="color:${item.color};font-size:1.4rem;">${item.val}</div>
      </div>
    `).join('');
  } else if (currentAttTab === 'strangers') {
    const totalStrangers = attStrangersCache.length;
    const inStrangers = attStrangersCache.filter(s => (s.direction || 'IN').toUpperCase() === 'IN').length;
    const outStrangers = attStrangersCache.filter(s => (s.direction || 'IN').toUpperCase() === 'OUT').length;
    const hasPhoto = attStrangersCache.filter(s => !!s.proof_image_url).length;

    statsEl.innerHTML = [
      { label:'Tổng Người Lạ Phát Hiện', val: totalStrangers, color:'#f43f5e', icon:'🚨' },
      { label:'Phát Hiện Tại Cổng Vào', val: inStrangers, color:'var(--green)', icon:'🟢' },
      { label:'Phát Hiện Tại Cổng Ra', val: outStrangers, color:'var(--blue)', icon:'🔵' },
      { label:'Đã Lưu Ảnh Bằng Chứng', val: hasPhoto, color:'var(--purple)', icon:'📷' },
    ].map(item => `
      <div class="stat-card" style="min-width:140px;">
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:2px;">
          <span style="font-size:0.75rem;color:var(--muted);font-weight:600;">${item.label}</span>
          <span style="font-size:0.85rem;">${item.icon}</span>
        </div>
        <div class="stat-num" style="color:${item.color};font-size:1.4rem;">${item.val}</div>
      </div>
    `).join('');
  } else {
    const classId = document.getElementById('attClassFilter')?.value || '';
    const total = (!classId && todaySummary?.total_scans !== undefined) ? Math.max(attEventsCache.length, todaySummary.total_scans) : attEventsCache.length;
    const inCount = (!classId && todaySummary?.total_in !== undefined) ? todaySummary.total_in : attEventsCache.filter(r => (r.direction || 'IN').toUpperCase() === 'IN').length;
    const outCount = (!classId && todaySummary?.total_out !== undefined) ? todaySummary.total_out : attEventsCache.filter(r => (r.direction || 'IN').toUpperCase() === 'OUT').length;
    const onTime = attEventsCache.filter(r => r.status === 'ON_TIME').length;
    const late = attEventsCache.filter(r => r.status === 'LATE').length;
    const uniformViolations = attEventsCache.filter(r => r.uniform_status === 'VIOLATION').length;
    const strangerCount = (!classId && todaySummary?.total_strangers !== undefined) ? Math.max(attStrangersCache.length, todaySummary.total_strangers) : attStrangersCache.length;

    statsEl.innerHTML = [
      { label:'Tổng Lượt Quét', val: total, color:'var(--text)', icon:'📊' },
      { label:'Lượt Đến Trường', val: inCount, color:'var(--green)', icon:'🟢' },
      { label:'Lượt Ra Về', val: outCount, color:'var(--blue)', icon:'🔵' },
      { label:'Đúng Giờ', val: onTime, color:'var(--green)', icon:'✓' },
      { label:'Đi Trễ', val: late, color:'var(--orange)', icon:'⏰' },
      { label:'Lỗi Đồng Phục', val: uniformViolations, color:'var(--red)', icon:'👕' },
      { label:'Cảnh Báo Người Lạ', val: strangerCount, color: strangerCount > 0 ? '#f43f5e' : 'var(--muted)', icon:'🚨' },
    ].map(item => `
      <div class="stat-card" style="min-width:125px;">
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:2px;">
          <span style="font-size:0.75rem;color:var(--muted);font-weight:600;">${item.label}</span>
          <span style="font-size:0.85rem;">${item.icon}</span>
        </div>
        <div class="stat-num" style="color:${item.color};font-size:1.4rem;">${item.val}</div>
      </div>
    `).join('');
  }
}

function renderAttendanceEventsTable() {
  const tbl = document.getElementById('attBody');
  if (!tbl) return;

  const searchTerm = (document.getElementById('attSearchInput')?.value || '').toLowerCase().trim();

  let rows = attEventsCache || [];
  if (currentAttTab === 'in') {
    rows = rows.filter(r => (r.direction || 'IN').toUpperCase() === 'IN');
  } else if (currentAttTab === 'out') {
    rows = rows.filter(r => (r.direction || 'IN').toUpperCase() === 'OUT');
  }

  if (searchTerm) {
    rows = rows.filter(r => 
      (r.full_name || '').toLowerCase().includes(searchTerm) || 
      (r.student_code || '').toLowerCase().includes(searchTerm)
    );
  }

  if (!rows.length) {
    tbl.innerHTML = emptyRow('Không tìm thấy dữ liệu lượt điểm danh nào phù hợp.', 8);
    return;
  }

  tbl.innerHTML = rows.map((r, idx) => {
    const isOut = (r.direction || 'IN').toUpperCase() === 'OUT';
    const rawTs = r.timestamp || '';
    const timeStr = rawTs.replace('T', ' ').split(' ')[1]?.slice(0, 8) || '—';
    const dateStr = rawTs.replace('T', ' ').split(' ')[0] || r.date_only || '';

    return `
      <tr style="transition:background 0.2s;">
        <td style="font-family:var(--font-mono);font-size:0.82rem;">
          <div style="font-weight:700;color:var(--text);">${escHtml(timeStr)}</div>
          <div style="font-size:0.72rem;color:var(--muted);">${escHtml(dateStr)}</div>
        </td>
        <td>
          ${isOut 
            ? `<span class="chip chip-blue" style="font-weight:700;font-size:0.7rem;display:inline-flex;align-items:center;gap:4px;">
                 <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>
                 RA VỀ
               </span>`
            : `<span class="chip chip-green" style="font-weight:700;font-size:0.7rem;display:inline-flex;align-items:center;gap:4px;">
                 <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="19" y1="12" x2="5" y2="12"/><polyline points="12 19 5 12 12 5"/></svg>
                 ĐẾN TRƯỜNG
               </span>`
          }
        </td>
        <td>
          <div style="display:flex;align-items:center;gap:8px;">
            <div style="width:36px;height:36px;border-radius:8px;background:rgba(56,189,248,0.1);border:1px solid var(--border);display:flex;align-items:center;justify-content:center;overflow:hidden;flex-shrink:0;">
              ${r.proof_image_url 
                ? `<img src="${escHtml(r.proof_image_url)}" style="width:100%;height:100%;object-fit:cover;cursor:pointer;" onclick="openAttendanceProofModal(${idx})" title="Ảnh camera AI chụp trực tiếp (Bấm để phóng to)" onerror="this.src='${escHtml(r.face_photo_url || '')}'">`
                : (r.face_photo_url 
                    ? `<img src="${escHtml(r.face_photo_url)}" style="width:100%;height:100%;object-fit:cover;" onerror="this.outerHTML='<span style=\\'font-size:0.8rem;\\'>👤</span>'">` 
                    : `<span style="font-size:0.8rem;">👤</span>`)}
            </div>
            <div>
              <div style="font-weight:700;font-size:0.88rem;color:var(--text);">${escHtml(r.full_name)}</div>
              <div style="font-size:0.72rem;color:var(--muted);font-family:var(--font-mono);">${escHtml(r.student_code)}</div>
              ${r.violation_details ? `<div style="color:var(--orange);font-size:0.7rem;margin-top:2px;">⚠️ ${escHtml(r.violation_details)}</div>` : ''}
            </div>
          </div>
        </td>
        <td>
          <span class="chip chip-muted" style="font-size:0.75rem;font-weight:600;">${escHtml(r.class_name || '—')}</span>
        </td>
        <td style="font-size:0.8rem;">
          <div style="color:var(--text);font-weight:600;">${escHtml(r.camera_name || 'Cổng trường')}</div>
          <div style="color:var(--muted);font-size:0.72rem;">${escHtml(r.camera_location || 'Camera AI')}</div>
        </td>
        <td>
          <div style="display:flex;flex-direction:column;gap:3px;align-items:flex-start;">
            ${statusChip(r.status)}
            ${!isOut ? uniformChip(r.uniform_status) : ''}
          </div>
        </td>
        <td>
          <span style="color:${(r.points_deducted||0)>0?'var(--red)':'var(--muted)'};font-weight:700;font-family:var(--font-mono);">
            ${(r.points_deducted||0)>0?`-${r.points_deducted}`:'0'}
          </span>
        </td>
        <td>
          <div style="display:flex;align-items:center;gap:6px;">
            ${r.proof_image_url ? `
              <button class="btn btn-xs btn-outline" onclick="openAttendanceProofModal(${idx})" style="padding:3px 8px;font-size:0.72rem;display:inline-flex;align-items:center;gap:4px;border-radius:6px;border-color:rgba(56,189,248,0.3);color:var(--blue);font-weight:600;" title="Xem ảnh chụp camera trực tiếp lúc điểm danh">
                📷 Ảnh Camera
              </button>
            ` : '<span style="color:var(--muted);font-size:0.75rem;">—</span>'}
          </div>
        </td>
      </tr>
    `;
  }).join('');
}

function renderAttendanceStrangersTable() {
  const tbl = document.getElementById('attStrangersBody');
  if (!tbl) return;

  const searchTerm = (document.getElementById('attSearchInput')?.value || '').toLowerCase().trim();

  let rows = attStrangersCache || [];
  if (searchTerm) {
    rows = rows.filter(r => 
      (r.title || '').toLowerCase().includes(searchTerm) || 
      (r.description || '').toLowerCase().includes(searchTerm) ||
      (r.camera_name || '').toLowerCase().includes(searchTerm)
    );
  }

  if (!rows.length) {
    tbl.innerHTML = emptyRow('Không có cảnh báo người lạ nào được ghi nhận trong ngày này.', 6);
    return;
  }

  tbl.innerHTML = rows.map((r, idx) => {
    const isOut = (r.direction || 'IN').toUpperCase() === 'OUT';
    const rawTs = r.timestamp || r.created_at || '';
    const timeStr = rawTs.replace('T', ' ').split(' ')[1]?.slice(0, 8) || '—';
    const dateStr = rawTs.replace('T', ' ').split(' ')[0] || r.date_only || '';

    return `
      <tr style="transition:background 0.2s;background:rgba(239,68,68,0.03);">
        <td style="font-family:var(--font-mono);font-size:0.82rem;">
          <div style="font-weight:700;color:var(--text);">${escHtml(timeStr)}</div>
          <div style="font-size:0.72rem;color:var(--muted);">${escHtml(dateStr)}</div>
        </td>
        <td>
          ${isOut 
            ? `<span class="chip chip-blue" style="font-weight:700;font-size:0.7rem;display:inline-flex;align-items:center;gap:4px;">
                 <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>
                 CỔNG RA
               </span>`
            : `<span class="chip chip-green" style="font-weight:700;font-size:0.7rem;display:inline-flex;align-items:center;gap:4px;">
                 <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="19" y1="12" x2="5" y2="12"/><polyline points="12 19 5 12 12 5"/></svg>
                 CỔNG VÀO
               </span>`
          }
        </td>
        <td style="font-size:0.8rem;">
          <div style="color:var(--text);font-weight:600;">${escHtml(r.camera_name || 'Cổng trường')}</div>
          <div style="color:var(--muted);font-size:0.72rem;">${escHtml(r.camera_location || 'Camera AI')}</div>
        </td>
        <td>
          <div style="font-weight:700;font-size:0.85rem;color:#f43f5e;display:flex;align-items:center;gap:6px;">
            <span>🚨</span>
            <span>${escHtml(r.title || 'Phát hiện người lạ tại cổng')}</span>
          </div>
          <div style="font-size:0.75rem;color:var(--muted);margin-top:2px;">
            ${escHtml(r.description || 'Không khớp dữ liệu khuôn mặt đã đăng ký.')}
          </div>
        </td>
        <td>
          <span class="chip chip-red" style="font-weight:700;font-size:0.72rem;display:inline-flex;align-items:center;gap:4px;">
            ⚠️ CẢNH BÁO
          </span>
        </td>
        <td>
          <div style="display:flex;align-items:center;gap:6px;">
            ${r.proof_image_url ? `
              <button class="btn btn-xs btn-outline" onclick="openStrangerProofModal(${idx})" style="padding:3px 10px;font-size:0.74rem;display:inline-flex;align-items:center;gap:4px;border-radius:6px;border-color:rgba(239,68,68,0.45);color:#f43f5e;font-weight:600;" title="Xem ảnh chụp đối tượng người lạ">
                📷 Xem ảnh camera
              </button>
            ` : '<span style="color:var(--muted);font-size:0.75rem;">Không có ảnh</span>'}
          </div>
        </td>
      </tr>
    `;
  }).join('');
}

function renderAttendanceReconTable() {
  const tbl = document.getElementById('attReconBody');
  if (!tbl) return;

  const records = attReconCache.records || [];
  if (!records.length) {
    tbl.innerHTML = emptyRow('Không có dữ liệu đối chiếu học sinh cho bộ lọc này.', 7);
    return;
  }

  tbl.innerHTML = records.map(r => {
    let presenceChip = '';
    switch(r.presence_status) {
      case 'IN_CAMPUS':
        presenceChip = '<span class="chip chip-green" style="font-weight:700;font-size:0.72rem;">🟢 Đang Ở Trường</span>';
        break;
      case 'DEPARTED':
        presenceChip = '<span class="chip chip-blue" style="font-weight:700;font-size:0.72rem;">🔵 Đã Ra Về</span>';
        break;
      case 'EARLY_EXIT':
        presenceChip = '<span class="chip chip-orange" style="font-weight:700;font-size:0.72rem;">⚠️ Ra Về Sớm</span>';
        break;
      case 'OUT_WITHOUT_IN':
        presenceChip = '<span class="chip chip-red" style="font-weight:700;font-size:0.72rem;">🚨 Ra Chưa Có Giờ Đến</span>';
        break;
      case 'EXCUSED':
        presenceChip = '<span class="chip chip-blue" style="font-size:0.72rem;">📝 Nghỉ Có Phép</span>';
        break;
      case 'ABSENT':
      default:
        presenceChip = '<span class="chip chip-red" style="font-size:0.72rem;">✕ Vắng Mặt</span>';
        break;
    }

    return `
      <tr style="${r.is_anomaly ? 'background:rgba(245,158,11,0.05);' : ''}">
        <td>
          <div style="display:flex;align-items:center;gap:8px;">
            <div style="width:34px;height:34px;border-radius:8px;background:rgba(56,189,248,0.1);border:1px solid var(--border);display:flex;align-items:center;justify-content:center;overflow:hidden;flex-shrink:0;">
              ${r.face_photo_url 
                ? `<img src="${escHtml(r.face_photo_url)}" style="width:100%;height:100%;object-fit:cover;" onerror="this.outerHTML='<span style=\\'font-size:0.8rem;\\'>👤</span>'">`
                : `<span style="font-size:0.8rem;">👤</span>`}
            </div>
            <div>
              <div style="font-weight:700;font-size:0.88rem;color:var(--text);">${escHtml(r.full_name)}</div>
              <div style="font-size:0.72rem;color:var(--muted);font-family:var(--font-mono);">${escHtml(r.student_code)}</div>
            </div>
          </div>
        </td>
        <td>
          <span class="chip chip-muted" style="font-size:0.75rem;font-weight:600;">${escHtml(r.class_name)}</span>
        </td>
        <td>
          ${r.first_in ? `
            <div style="font-family:var(--font-mono);font-weight:700;color:var(--green);font-size:0.82rem;">
              ${escHtml(r.first_in.time)}
            </div>
            <div style="font-size:0.7rem;color:var(--muted);">${escHtml(r.first_in.camera_name)}</div>
            ${r.first_in.status === 'LATE' ? `<span class="chip chip-orange" style="font-size:0.65rem;padding:1px 4px;margin-top:2px;">Đi trễ</span>` : ''}
          ` : `<span style="color:var(--muted);font-size:0.78rem;">— Chưa có giờ đến —</span>`}
        </td>
        <td>
          ${r.last_out ? `
            <div style="font-family:var(--font-mono);font-weight:700;color:var(--blue);font-size:0.82rem;">
              ${escHtml(r.last_out.time)}
            </div>
            <div style="font-size:0.7rem;color:var(--muted);">${escHtml(r.last_out.camera_name)}</div>
          ` : `<span style="color:var(--muted);font-size:0.78rem;">— Chưa có giờ về —</span>`}
        </td>
        <td>
          <div style="font-family:var(--font-mono);font-size:0.82rem;font-weight:700;color:var(--text);">
            ${escHtml(r.duration_formatted)}
          </div>
          <div style="font-size:0.7rem;color:var(--muted);">
            ${r.total_in_count} lượt đến · ${r.total_out_count} lượt về
          </div>
        </td>
        <td>
          ${presenceChip}
          ${r.is_anomaly ? `<div style="font-size:0.7rem;color:var(--orange);margin-top:2px;">⚠️ ${escHtml(r.anomaly_note)}</div>` : ''}
        </td>
        <td>
          <button class="btn btn-xs btn-outline" onclick="openAttTimelineModal(${r.student_id})" 
                  style="font-size:0.72rem;padding:4px 8px;border-radius:6px;display:inline-flex;align-items:center;gap:4px;" title="Xem toàn bộ các lượt quét của học sinh">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
            Chi Tiết
          </button>
        </td>
      </tr>
    `;
  }).join('');
}

function openAttTimelineModal(studentId) {
  const student = (attReconCache.records || []).find(r => r.student_id === studentId);
  if (!student) return;
  window.currentReconStudent = student;

  const modal = document.getElementById('attTimelineModal');
  const nameEl = document.getElementById('attModalStudentName');
  const subEl = document.getElementById('attModalStudentSub');
  const contentEl = document.getElementById('attModalTimelineContent');

  const presenceTextMap = {
    IN_CAMPUS: '🟢 Đang Ở Trường',
    DEPARTED: '🔵 Đã Ra Về',
    EARLY_EXIT: '⚠️ Ra Về Sớm',
    OUT_WITHOUT_IN: '🚨 Ra Chưa Có Giờ Đến',
    ABSENT: '✕ Vắng Mặt',
    EXCUSED: '📝 Nghỉ Có Phép'
  };

  if (nameEl) nameEl.textContent = student.full_name;
  if (subEl) subEl.textContent = `Mã HS: ${student.student_code} | Lớp: ${student.class_name} | Trạng thái: ${presenceTextMap[student.presence_status] || student.presence_status}`;

  const logs = student.all_logs || [];
  if (!logs.length) {
    contentEl.innerHTML = '<div style="text-align:center;padding:24px;color:var(--muted);">Không có lượt điểm danh nào trong ngày được chọn.</div>';
  } else {
    contentEl.innerHTML = `
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:14px;background:rgba(255,255,255,0.03);padding:10px 14px;border-radius:10px;border:1px solid var(--border);">
        <div style="font-size:0.8rem;color:var(--muted);">Tổng thời gian ở trường: <strong style="color:var(--text);font-family:var(--font-mono);">${escHtml(student.duration_formatted)}</strong></div>
        <div style="font-size:0.8rem;color:var(--muted);">Tổng lượt quét ghi nhận: <strong style="color:var(--blue);">${logs.length}</strong></div>
      </div>
      <div style="position:relative;padding-left:24px;margin-left:8px;border-left:2px dashed rgba(56,189,248,0.3);">
        ${logs.map((l, idx) => {
          const isIn = (l.direction || 'IN').toUpperCase() === 'IN';
          const timeStr = escHtml(l.time || l.timestamp?.slice(11,19) || '');
          const violationText = l.violation_details || (l.status === 'LATE' ? 'Đi học muộn' : (l.uniform_status === 'VIOLATION' ? 'Sai đồng phục' : ''));

          return `
            <div style="position:relative;margin-bottom:18px;">
              <div style="position:absolute;left:-31px;top:2px;width:14px;height:14px;border-radius:50%;background:${isIn ? 'var(--green)' : 'var(--blue)'};box-shadow:0 0 8px ${isIn ? 'rgba(16,185,129,0.6)' : 'rgba(59,130,246,0.6)'};"></div>
              <div style="background:rgba(17,24,39,0.6);border:1px solid var(--border);border-radius:10px;padding:10px 14px;">
                <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:4px;">
                  <span class="chip ${isIn ? 'chip-green' : 'chip-blue'}" style="font-size:0.7rem;font-weight:700;">
                    ${isIn ? '🟢 LƯỢT ĐẾN TRƯỜNG' : '🔵 LƯỢT RA VỀ'}
                  </span>
                  <span style="font-family:var(--font-mono);font-size:0.85rem;font-weight:700;color:var(--text);">
                    ${timeStr}
                  </span>
                </div>
                <div style="font-size:0.78rem;color:var(--muted);display:flex;align-items:center;gap:6px;flex-wrap:wrap;">
                  <span>📍 Trạm: <strong style="color:var(--text);">${escHtml(l.camera_name || 'Cổng trường')}</strong></span>
                  <span>·</span>
                  <span>Nề nếp: ${statusChip(l.status)}</span>
                </div>
                ${violationText ? `<div style="font-size:0.72rem;color:var(--orange);margin-top:4px;">⚠️ ${escHtml(violationText)}</div>` : ''}
                ${l.proof_image_url ? `
                  <div style="margin-top:8px;">
                    <button class="btn btn-xs btn-outline" onclick="openReconLogProofModal(${idx})" style="padding:2px 8px;font-size:0.7rem;display:inline-flex;align-items:center;gap:4px;color:var(--blue);border-color:rgba(56,189,248,0.3);">
                      📷 Xem ảnh camera
                    </button>
                  </div>
                ` : ''}
              </div>
            </div>
          `;
        }).join('')}
      </div>
    `;
  }

  if (modal) {
    modal.style.display = 'flex';
  }
}

function closeAttTimelineModal() {
  const modal = document.getElementById('attTimelineModal');
  if (modal) modal.style.display = 'none';
}

function statusChip(s) {
  const m = { ON_TIME:'<span class="chip chip-green">✓ Đúng Giờ</span>', LATE:'<span class="chip chip-orange">⏰ Trễ</span>', ABSENT:'<span class="chip chip-red">✕ Vắng</span>', EXCUSED:'<span class="chip chip-blue">📝 Phép</span>' };
  return m[s] || `<span class="chip chip-muted">${escHtml(s)}</span>`;
}
function uniformChip(s) {
  const m = { OK:'<span class="chip chip-green">✓ Đúng Phục</span>', VIOLATION:'<span class="chip chip-red">✕ Sai Phục</span>', UNKNOWN:'<span class="chip chip-muted">?</span>' };
  return m[s] || '<span class="chip chip-muted">—</span>';
}



export {
  closeAttTimelineModal, closeProofImageModal, debounceAttendanceSearch, loadAttendance, openAttTimelineModal, openAttendanceProofModal, openProofImageModal, openReconLogProofModal, openStrangerProofModal, populateAttendanceClasses, renderAttendanceEventsTable, renderAttendanceReconTable, renderAttendanceStatsStrip, renderAttendanceStrangersTable, setAttDateOffset, setTodayDate, statusChip, switchAttTab, uniformChip
};
