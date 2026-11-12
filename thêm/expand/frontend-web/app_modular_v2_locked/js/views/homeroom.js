// app/js/views/homeroom.js — Homeroom Teacher (GVCN) Roll-Call & Roster
// ── Homeroom (GVCN) ──────────────────────────────────
let currentHomeroomClassId = null;
let currentHomeroomData = null;
let currentHomeroomRoster = [];
let currentHomeroomFilter = 'ALL';
let currentHomeroomSearchQuery = '';

async function loadHomeroomView(targetClassId = null) {
  const container = document.getElementById('view-homeroom');
  if (!container) return;

  const hrRosterBody = document.getElementById('hrRosterBody');
  hrRosterBody.innerHTML = '<tr><td colspan="7" style="text-align:center;padding:32px;color:var(--muted);">Đang tải bảng sĩ số lớp...</td></tr>';

  try {
    let classMeta = null;

    if (targetClassId) {
      currentHomeroomClassId = parseInt(targetClassId);
      // Lấy danh sách lớp để nạp thông tin lớp được chọn
      const allClasses = await api('GET', `/api/v1/s/${schoolId}/classes`);
      const found = allClasses.find(c => c.id === currentHomeroomClassId);
      if (found) {
        classMeta = {
          has_class: true,
          class: {
            id: found.id,
            name: found.name,
            grade_level: found.grade_level,
            academic_year: found.academic_year || '2025-2026',
            teacher_name: found.teacher_name || 'Chưa phân công',
            invite_code: found.invite_code || '—'
          }
        };
      }
    } else {
      // Mặc định gọi my-homeroom của GVCN
      const res = await api('GET', `/api/v1/s/${schoolId}/classes/my-homeroom`);
      if (res && res.has_class) {
        classMeta = res;
        currentHomeroomClassId = res.class.id;
      } else {
        classMeta = res;
      }
    }

    // Nếu giáo viên chưa được gán lớp hoặc Admin/Ban Giám Hiệu đang xem
    if (!classMeta || !classMeta.has_class) {
      if (['HEADMASTER', 'ADMIN', 'PLATFORM_ADMIN'].includes(currentUser?.role)) {
        const allClasses = await api('GET', `/api/v1/s/${schoolId}/classes`);
        if (allClasses && allClasses.length > 0) {
          setupHomeroomClassSelector(allClasses, allClasses[0].id);
          return loadHomeroomView(allClasses[0].id);
        }
      }
      renderNoHomeroomState();
      return;
    }

    currentHomeroomData = classMeta;

    // Thiết lập dropdown chọn lớp cho Admin/Hiệu Trưởng
    if (['HEADMASTER', 'ADMIN', 'PLATFORM_ADMIN'].includes(currentUser?.role)) {
      const allClasses = await api('GET', `/api/v1/s/${schoolId}/classes`);
      setupHomeroomClassSelector(allClasses, currentHomeroomClassId);
    } else {
      const selWrap = document.getElementById('hrClassSelectorWrap');
      if (selWrap) selWrap.style.display = 'none';
    }

    // Cập nhật thông tin Hero Banner
    document.getElementById('hrClassName').textContent = `Lớp ${classMeta.class.name}`;
    document.getElementById('hrBadgeGrade').textContent = `Khối ${classMeta.class.grade_level}`;
    document.getElementById('hrBadgeYear').textContent = classMeta.class.academic_year || '2025-2026';
    document.getElementById('hrTeacherName').textContent = classMeta.class.teacher_name || '—';
    document.getElementById('hrInviteCode').textContent = classMeta.class.invite_code || '—';

    const now = new Date();
    const dayNames = ['Chủ Nhật', 'Thứ Hai', 'Thứ Ba', 'Thứ Tư', 'Thứ Năm', 'Thứ Sáu', 'Thứ Bảy'];
    const dateStr = `${dayNames[now.getDay()]}, ${String(now.getDate()).padStart(2,'0')}/${String(now.getMonth()+1).padStart(2,'0')}/${now.getFullYear()}`;
    const hrDateDisplay = document.getElementById('hrDateDisplay');
    if (hrDateDisplay) hrDateDisplay.textContent = dateStr;

    // Tải danh sách sĩ số hôm nay từ API
    const roster = await api('GET', `/api/v1/s/${schoolId}/classes/${currentHomeroomClassId}/roster-today`);
    currentHomeroomRoster = roster || [];

    // Cập nhật các thẻ KPI
    recalculateHomeroomStats();

    // Hiển thị bảng danh sách
    renderHomeroomRosterTable();

  } catch(e) {
    console.error("loadHomeroomView error:", e);
    hrRosterBody.innerHTML = `<tr><td colspan="7" style="text-align:center;padding:32px;color:var(--rose);">Lỗi khi tải dữ liệu: ${escHtml(e.detail || e.message || 'Không thể kết nối')}</td></tr>`;
  }
}

function setupHomeroomClassSelector(classes, activeClassId) {
  const selWrap = document.getElementById('hrClassSelectorWrap');
  const sel = document.getElementById('hrClassSelect');
  if (!selWrap || !sel) return;

  selWrap.style.display = 'inline-block';
  sel.innerHTML = classes.map(c => `
    <option value="${c.id}" ${c.id === activeClassId ? 'selected' : ''}>Lớp ${escHtml(c.name)} (Khối ${c.grade_level})</option>
  `).join('');
}

function onHomeroomClassSelect(classId) {
  if (!classId) return;
  loadHomeroomView(parseInt(classId));
}

function renderNoHomeroomState() {
  document.getElementById('hrClassName').textContent = 'Chưa Được Phân Công Lớp';
  document.getElementById('hrTeacherName').textContent = currentUser?.full_name || '—';
  document.getElementById('hrInviteCode').textContent = '—';
  document.getElementById('hrRateVal').textContent = '0%';
  document.getElementById('hrKpiTotal').textContent = '0';
  document.getElementById('hrKpiOnTime').textContent = '0';
  document.getElementById('hrKpiLate').textContent = '0';
  document.getElementById('hrKpiExcused').textContent = '0';
  document.getElementById('hrKpiAbsent').textContent = '0';
  document.getElementById('hrKpiViolations').textContent = '0';
  document.getElementById('hrRosterBody').innerHTML = `
    <tr>
      <td colspan="7" style="text-align:center;padding:48px;color:var(--muted);">
        <div style="font-size:2.2rem;margin-bottom:10px;">👨‍🏫</div>
        <div style="font-size:1.05rem;font-weight:700;color:#f8fafc;margin-bottom:6px;">Tài khoản Giáo viên (Chưa được bổ nhiệm làm GVCN)</div>
        <div style="font-size:0.85rem;color:var(--muted);max-width:460px;margin:0 auto;line-height:1.5;">
          Bạn đang hoạt động với vai trò Giáo Viên. Nếu được Ban Giám Hiệu bổ nhiệm làm Giáo viên chủ nhiệm (GVCN), bảng tổng hợp sĩ số, điểm danh tiết 1 và xét duyệt đơn nghỉ phép của lớp chủ nhiệm sẽ hiển thị tại đây.
        </div>
      </td>
    </tr>
  `;
}

function recalculateHomeroomStats() {
  const total = currentHomeroomRoster.length;
  const onTime = currentHomeroomRoster.filter(s => s.status === 'ON_TIME').length;
  const late = currentHomeroomRoster.filter(s => s.status === 'LATE').length;
  const excused = currentHomeroomRoster.filter(s => s.status === 'EXCUSED').length;
  const absent = currentHomeroomRoster.filter(s => s.status === 'ABSENT' || s.status === 'NOT_CHECKED_IN').length;
  const violations = currentHomeroomRoster.filter(s => s.uniform_status === 'VIOLATION').length;

  const present = onTime + late;
  const rate = total > 0 ? ((present / total) * 100).toFixed(1) : '0';

  document.getElementById('hrRateVal').textContent = `${rate}%`;
  document.getElementById('hrKpiTotal').textContent = total;
  document.getElementById('hrKpiOnTime').textContent = onTime;
  document.getElementById('hrKpiOnTimePct').textContent = total > 0 ? `${Math.round((onTime / total) * 100)}%` : '0%';
  document.getElementById('hrKpiLate').textContent = late;
  document.getElementById('hrKpiLatePct').textContent = total > 0 ? `${Math.round((late / total) * 100)}%` : '0%';
  document.getElementById('hrKpiExcused').textContent = excused;
  document.getElementById('hrKpiExcusedPct').textContent = total > 0 ? `${Math.round((excused / total) * 100)}%` : '0%';
  document.getElementById('hrKpiAbsent').textContent = absent;
  document.getElementById('hrKpiAbsentPct').textContent = total > 0 ? `${Math.round((absent / total) * 100)}%` : '0%';
  document.getElementById('hrKpiViolations').textContent = violations;

  document.getElementById('hrBtnAbsentCount').textContent = absent;
  document.getElementById('hrPendingLeaves').textContent = currentHomeroomData?.counts?.pending_leaves || 0;
  document.getElementById('hrPendingDisputes').textContent = currentHomeroomData?.counts?.pending_disputes || 0;

  document.getElementById('hrTabAllCnt').textContent = total;
  document.getElementById('hrTabPresentCnt').textContent = present;
  document.getElementById('hrTabAbsentCnt').textContent = absent;
  document.getElementById('hrTabLateCnt').textContent = late;
  document.getElementById('hrTabExcusedCnt').textContent = excused;
  document.getElementById('hrTabViolationsCnt').textContent = violations;
}

function renderHomeroomRosterTable() {
  const tbl = document.getElementById('hrRosterBody');
  if (!tbl) return;

  const q = currentHomeroomSearchQuery.trim().toLowerCase();
  let list = currentHomeroomRoster;

  // Lọc theo bộ lọc Tab
  if (currentHomeroomFilter === 'PRESENT') {
    list = list.filter(s => s.status === 'ON_TIME' || s.status === 'LATE');
  } else if (currentHomeroomFilter === 'ABSENT') {
    list = list.filter(s => s.status === 'ABSENT' || s.status === 'NOT_CHECKED_IN');
  } else if (currentHomeroomFilter === 'LATE') {
    list = list.filter(s => s.status === 'LATE');
  } else if (currentHomeroomFilter === 'EXCUSED') {
    list = list.filter(s => s.status === 'EXCUSED');
  } else if (currentHomeroomFilter === 'VIOLATION') {
    list = list.filter(s => s.uniform_status === 'VIOLATION');
  }

  // Lọc theo từ khóa tìm kiếm
  if (q) {
    list = list.filter(s =>
      (s.full_name && s.full_name.toLowerCase().includes(q)) ||
      (s.student_code && s.student_code.toLowerCase().includes(q))
    );
  }

  if (list.length === 0) {
    tbl.innerHTML = `<tr><td colspan="7" style="text-align:center;padding:32px;color:var(--muted);">Không tìm thấy học sinh nào phù hợp với bộ lọc.</td></tr>`;
    return;
  }

  tbl.innerHTML = list.map((s, idx) => {
    const avatarSrc = s.face_photo_url ? s.face_photo_url : '/assets/icons/default_avatar.png';
    const ekycBadge = s.face_approved === 1
      ? `<span class="chip chip-green" style="font-size:0.65rem;padding:1px 6px;">✓ Tích Xanh</span>`
      : `<span class="chip chip-amber" style="font-size:0.65rem;padding:1px 6px;">Chưa eKYC</span>`;

    // Quét cổng
    let gateHtml = '—';
    if (s.time) {
      const methodLabel = s.checkin_method === 'FACE_AI' ? '📸 AI Cổng' : (s.checkin_method === 'QR_SCAN' ? '📱 Mã QR' : '👩‍🏫 GVCN');
      gateHtml = `
        <div style="font-weight:700;font-size:0.86rem;color:#f8fafc;">${escHtml(s.time)}</div>
        <div style="font-size:0.7rem;color:var(--muted);margin-top:2px;">${methodLabel}</div>
        ${s.proof_image_url ? `<a href="${escHtml(s.proof_image_url)}" target="_blank" style="font-size:0.7rem;color:var(--blue);text-decoration:underline;display:inline-block;margin-top:2px;">📷 Xem ảnh</a>` : ''}
      `;
    } else if (s.has_approved_leave) {
      gateHtml = `<span class="chip chip-purple" style="font-size:0.72rem;">📝 Nghỉ có phép</span>`;
    } else {
      gateHtml = `<span style="color:var(--muted);font-size:0.78rem;">Chưa quét cổng</span>`;
    }

    // 4 nút điểm danh 1-chạm
    const isOntime = s.status === 'ON_TIME';
    const isLate = s.status === 'LATE';
    const isExcused = s.status === 'EXCUSED';
    const isAbsent = s.status === 'ABSENT' || s.status === 'NOT_CHECKED_IN';

    const rollCallButtons = `
      <div class="rollcall-btn-group">
        <button class="btn-rc ${isOntime ? 'active-ontime' : ''}" onclick="quickRollCall(${s.student_id}, 'ON_TIME')" title="Đúng giờ">🟢 Đúng Giờ</button>
        <button class="btn-rc ${isLate ? 'active-late' : ''}" onclick="quickRollCall(${s.student_id}, 'LATE')" title="Đi trễ">🟡 Đi Trễ</button>
        <button class="btn-rc ${isExcused ? 'active-excused' : ''}" onclick="quickRollCall(${s.student_id}, 'EXCUSED')" title="Có phép">🔵 Có Phép</button>
        <button class="btn-rc ${isAbsent ? 'active-absent' : ''}" onclick="quickRollCall(${s.student_id}, 'ABSENT')" title="Vắng">🔴 Vắng</button>
      </div>
    `;

    // Đồng phục
    const uniformBadge = s.uniform_status === 'VIOLATION'
      ? `<span class="chip chip-red" style="font-weight:700;">⚠️ Vi phạm</span>`
      : `<span class="chip chip-green">✓ Chuẩn</span>`;

    // Ghi chú / Đơn phép
    let noteHtml = '<span style="color:var(--muted);">—</span>';
    if (s.has_approved_leave) {
      noteHtml = `<span style="color:#c084fc;font-size:0.76rem;font-weight:600;">Đơn đã duyệt: ${escHtml(s.leave_reason || 'Nghỉ phép')}</span>`;
    } else if (s.leave_pending) {
      noteHtml = `<span style="color:#fbbf24;font-size:0.76rem;">⏳ Có đơn chờ duyệt</span>`;
    }

    // Phụ huynh & Liên hệ
    const parentPhone = s.parent_phone ? escHtml(s.parent_phone) : '';
    const contactHtml = parentPhone ? `
      <div style="display:flex;align-items:center;gap:6px;">
        <a href="tel:${parentPhone}" class="btn btn-outline btn-sm" style="padding:2px 8px;font-size:0.72rem;text-decoration:none;" title="Gọi phụ huynh">📞 ${parentPhone}</a>
        <button class="btn btn-danger btn-sm" style="padding:2px 7px;font-size:0.7rem;" onclick="notifySingleStudentParent(${s.student_id}, '${escHtml(s.full_name)}', '${parentPhone}')" title="Gửi thông báo riêng">✉️</button>
      </div>
    ` : `<span style="color:var(--muted);font-size:0.75rem;">Chưa có SĐT</span>`;

    return `
      <tr>
        <td style="color:var(--muted);font-size:0.8rem;text-align:center;">${idx + 1}</td>
        <td>
          <div style="display:flex;align-items:center;gap:10px;">
            <img src="${avatarSrc}" style="width:38px;height:38px;border-radius:10px;object-fit:cover;border:1px solid rgba(255,255,255,0.12);" onerror="this.src='/assets/icons/default_avatar.png'">
            <div>
              <div style="font-weight:700;color:#f8fafc;font-size:0.88rem;">${escHtml(s.full_name)}</div>
              <div style="display:flex;align-items:center;gap:6px;margin-top:2px;">
                <code style="font-size:0.72rem;color:var(--blue);">${escHtml(s.student_code)}</code>
                ${ekycBadge}
              </div>
            </div>
          </div>
        </td>
        <td>${gateHtml}</td>
        <td>${rollCallButtons}</td>
        <td>${uniformBadge}</td>
        <td>${noteHtml}</td>
        <td>${contactHtml}</td>
      </tr>
    `;
  }).join('');
}

function filterHomeroomRoster(filterKey, btnEl) {
  currentHomeroomFilter = filterKey;
  document.querySelectorAll('#hrFilterTabs .hr-tab-btn').forEach(b => {
    b.classList.remove('btn-primary', 'active');
    b.classList.add('btn-outline');
  });
  if (btnEl) {
    btnEl.classList.remove('btn-outline');
    btnEl.classList.add('btn-primary', 'active');
  }
  renderHomeroomRosterTable();
}

function onHomeroomSearch(q) {
  currentHomeroomSearchQuery = q || '';
  renderHomeroomRosterTable();
}

async function quickRollCall(studentId, newStatus) {
  if (!currentHomeroomClassId) return;
  const target = currentHomeroomRoster.find(s => s.student_id === studentId);
  if (!target) return;

  const oldStatus = target.status;
  target.status = newStatus;
  target.checkin_method = 'MANUAL';

  // Cập nhật UI lạc quan ngay lập tức
  renderHomeroomRosterTable();
  recalculateHomeroomStats();

  try {
    const res = await api('POST', `/api/v1/s/${schoolId}/classes/${currentHomeroomClassId}/roll-call`, {
      items: [
        { student_id: studentId, status: newStatus }
      ]
    });
    const statusLabels = { ON_TIME: 'Đúng Giờ', LATE: 'Đi Trễ', EXCUSED: 'Có Phép', ABSENT: 'Vắng Mặt' };
    toast('✅ Đã Cập Nhật', `${target.full_name}: ${statusLabels[newStatus] || newStatus}`, 'success');
  } catch(e) {
    target.status = oldStatus;
    renderHomeroomRosterTable();
    recalculateHomeroomStats();
    toast('Lỗi Cập Nhật', e.detail || 'Không thể lưu trạng thái', 'error');
  }
}

async function promptNotifyAbsentParents() {
  if (!currentHomeroomClassId) return;
  const unexcusedList = currentHomeroomRoster.filter(s => (s.status === 'ABSENT' || s.status === 'NOT_CHECKED_IN') && !s.has_approved_leave);

  if (unexcusedList.length === 0) {
    toast('Sĩ Số Đầy Đủ', 'Tất cả học sinh hôm nay đã có mặt hoặc có phép!', 'info');
    return;
  }

  const previewNames = unexcusedList.slice(0, 3).map(s => s.full_name).join(', ') + (unexcusedList.length > 3 ? ` và ${unexcusedList.length - 3} học sinh khác` : '');
  const confirmed = confirm(`Xác nhận gửi thông báo vắng học sáng nay tới phụ huynh của ${unexcusedList.length} học sinh?\n(${previewNames})`);
  if (!confirmed) return;

  try {
    const res = await api('POST', `/api/v1/s/${schoolId}/classes/${currentHomeroomClassId}/notify-absent-parents`);
    toast('📢 Đã Gửi Cảnh Báo', res.message || `Đã thông báo tới ${res.notified_count} phụ huynh.`, 'success');
  } catch(e) {
    toast('Lỗi Gửi Cảnh Báo', e.detail || 'Không thể gửi cảnh báo', 'error');
  }
}

async function notifySingleStudentParent(studentId, studentName, phone) {
  if (!phone) {
    toast('Thiếu SĐT', 'Học sinh này chưa có số điện thoại phụ huynh', 'error');
    return;
  }
  const ok = confirm(`Gửi thông báo điểm danh / vắng mặt tới phụ huynh của em ${studentName} (${phone})?`);
  if (!ok) return;
  toast('📢 Đã Gửi Tin Nhắn', `Đã gửi cảnh báo tới phụ huynh em ${studentName} (${phone})`, 'success');
}

function printHomeroomRoster() {
  window.print();
}



export {
  filterHomeroomRoster, loadHomeroomView, notifySingleStudentParent, onHomeroomClassSelect, onHomeroomSearch, printHomeroomRoster, promptNotifyAbsentParents, quickRollCall, recalculateHomeroomStats, renderHomeroomRosterTable, renderNoHomeroomState, setupHomeroomClassSelector
};
