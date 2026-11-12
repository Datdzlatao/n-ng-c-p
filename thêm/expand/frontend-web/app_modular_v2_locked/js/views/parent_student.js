// app/js/views/parent_student.js — Student & Parent Self-Service Views
// ── My Attendance (Student & Parent) ─────────────
async function loadMyAttendance() {
  const tbl = document.getElementById('myAttBody');
  const sel = document.getElementById('myAttStudentSelect');
  tbl.innerHTML = '<tr><td colspan="6" style="text-align:center;padding:24px;color:var(--muted);">Đang tải...</td></tr>';
  
  let studentId = null;
  const btnAdd = document.getElementById('btnParentAddChild');
  if (btnAdd) btnAdd.style.display = currentUser?.role === 'PARENT' ? 'inline-flex' : 'none';

  if (currentUser?.role === 'PARENT') {
    const children = currentUser?.children || [];
    if (children.length > 0) {
      sel.style.display = 'inline-block';
      const curVal = sel.value;
      sel.innerHTML = children.map(c => `<option value="${c.id}" ${c.id == curVal ? 'selected' : ''}>Con: ${escHtml(c.full_name)} (${escHtml(c.class_name||'Chưa xếp lớp')})</option>`).join('');
      studentId = parseInt(sel.value) || children[0].id;
    } else {
      sel.style.display = 'none';
      tbl.innerHTML = `<tr><td colspan="6" style="text-align:center;padding:36px 16px;">
        <div style="max-width:460px;margin:0 auto;background:rgba(59,130,246,0.06);border:1.5px dashed var(--blue);border-radius:12px;padding:24px;">
          <div style="font-size:2.4rem;margin-bottom:8px;">👨‍👩‍👧</div>
          <div style="font-weight:800;font-size:1.05rem;margin-bottom:6px;color:var(--text);">Chưa Có Học Sinh Liên Kết</div>
          <div style="font-size:0.83rem;color:var(--muted);margin-bottom:18px;line-height:1.5;">
            Tài khoản phụ huynh của bạn chưa liên kết với học sinh nào. Hãy nhập Mã Học Sinh của con để bắt đầu theo dõi điểm danh, nề nếp và gửi đơn xin phép trực tuyến!
          </div>
          <button class="btn btn-primary" onclick="openLinkChildModal()" style="background:var(--blue);font-weight:700;padding:8px 18px;display:inline-flex;align-items:center;gap:6px;">
            <span>🔗 Liên Kết Con Em Ngay</span>
          </button>
        </div>
      </td></tr>`;
      return;
    }
  } else if (currentUser?.role === 'STUDENT') {
    sel.style.display = 'none';
    studentId = currentUser?.student_profile?.id;
    if (!studentId) {
      try {
        const meRes = await api('GET', '/api/v1/auth/me');
        currentUser = meRes.user;
        studentId = currentUser?.student_profile?.id;
      } catch(e) {}
    }
  } else {
    const stuList = window.currentStudentsList || [];
    if (stuList.length > 0) {
      studentId = stuList[0].id;
    }
  }

  if (!studentId) {
    tbl.innerHTML = emptyRow('Không tìm thấy thông tin học sinh.', 6);
    return;
  }

  try {
    const rows = await api('GET', `/api/v1/s/${schoolId}/attendance/student/${studentId}`);
    if (!rows.length) {
      tbl.innerHTML = emptyRow('Chưa có lịch sử điểm danh nào.', 6);
      return;
    }
    tbl.innerHTML = rows.map(r => {
      const timeStr = r.timestamp ? r.timestamp.slice(0,16).replace('T',' ') : r.date_only;
      const pts = (r.points_deducted || 0) > 0 ? `<span style="color:var(--red);font-weight:700;">-${r.points_deducted}</span>` : '<span style="color:var(--muted)">0</span>';
      const disputeStatus = r.is_disputed ? '<span class="chip chip-orange">Đang khiếu nại</span>' : '<span style="color:var(--muted)">Bình thường</span>';
      const canDispute = !r.is_disputed && (r.status === 'LATE' || r.status === 'ABSENT' || r.uniform_status === 'VIOLATION');
      return `
        <tr>
          <td><code style="color:var(--blue);font-weight:600;">${escHtml(timeStr)}</code></td>
          <td>${statusChip(r.status)}</td>
          <td>${uniformChip(r.uniform_status)}</td>
          <td>${pts}</td>
          <td>${disputeStatus}</td>
          <td>
            ${canDispute ? `<button class="btn btn-sm btn-outline" style="padding:4px 8px;font-size:0.75rem;color:var(--orange);border-color:var(--orange);" onclick="openCreateDisputeModal(${r.id}, ${studentId})">⚖️ Khiếu nại</button>` : '—'}
          </td>
        </tr>
      `;
    }).join('');
  } catch(e) {
    tbl.innerHTML = errorRow(e, 6);
  }
}

// ── My Leaves (Student & Parent) ─────────────────
async function loadMyLeaves() {
  const tbl = document.getElementById('myLeavesBody');
  tbl.innerHTML = '<tr><td colspan="6" style="text-align:center;padding:24px;color:var(--muted);">Đang tải danh sách đơn xin phép...</td></tr>';
  try {
    const rows = await api('GET', `/api/v1/s/${schoolId}/leaves`);
    if (!rows.length) {
      tbl.innerHTML = emptyRow('Bạn chưa gửi đơn xin nghỉ phép nào.', 6);
      return;
    }
    tbl.innerHTML = rows.map(l => `
      <tr>
        <td><strong>${escHtml(l.student_name || 'Học sinh')}</strong><br><small style="color:var(--muted);">${escHtml(l.class_name || '—')}</small></td>
        <td><code>${escHtml(l.start_date)}</code></td>
        <td><code>${escHtml(l.end_date)}</code></td>
        <td>${escHtml(l.reason)}</td>
        <td>${leaveChip(l.status)}</td>
        <td style="font-size:0.8rem;color:var(--muted);">${escHtml(l.created_at?.slice(0,10) || '—')}</td>
      </tr>
    `).join('');
  } catch(e) {
    tbl.innerHTML = errorRow(e, 6);
  }
}

// ── My Disputes (Student & Parent) ───────────────
async function loadMyDisputes() {
  const tbl = document.getElementById('myDisputesBody');
  tbl.innerHTML = '<tr><td colspan="6" style="text-align:center;padding:24px;color:var(--muted);">Đang tải danh sách khiếu nại...</td></tr>';
  try {
    const rows = await api('GET', `/api/v1/s/${schoolId}/disputes`);
    if (!rows.length) {
      tbl.innerHTML = emptyRow('Bạn chưa có khiếu nại nề nếp nào.', 6);
      return;
    }
    tbl.innerHTML = rows.map(d => `
      <tr>
        <td><strong>${escHtml(d.student_name || 'Học sinh')}</strong><br><small style="color:var(--muted);">${escHtml(d.class_name || '—')}</small></td>
        <td>${escHtml(d.reason)}</td>
        <td><span class="chip ${d.level==='LEVEL_1_TEACHER'?'chip-blue':'chip-purple'}">${d.level==='LEVEL_1_TEACHER'?'Cấp 1 (GVCN)':'Cấp 2 (Giám Thị)'}</span></td>
        <td>${disputeChip(d.status)}</td>
        <td style="font-size:0.8rem;color:var(--muted);">${escHtml(d.created_at?.slice(0,10) || '—')}</td>
        <td style="font-size:0.85rem;">${escHtml(d.resolution_note || 'Chưa có phản hồi')}</td>
      </tr>
    `).join('');
  } catch(e) {
    tbl.innerHTML = errorRow(e, 6);
  }
}

// ── Modals & Actions for Student & Parent ─────────
function openCreateLeaveModal() {
  const grpChild = document.getElementById('grpLeaveChildSelect');
  const selChild = document.getElementById('leaveStudentId');
  if (currentUser?.role === 'PARENT') {
    const children = currentUser.children || [];
    if (!children.length) {
      toast('Chưa Liên Kết Con Em', 'Vui lòng liên kết tài khoản với con em trước khi tạo đơn xin phép.', 'warning');
      openLinkChildModal();
      return;
    }
    grpChild.style.display = 'block';
    selChild.innerHTML = children.map(ch =>
      `<option value="${ch.id}">${escHtml(ch.full_name)} (${escHtml(ch.class_name || 'Chưa xếp lớp')})</option>`
    ).join('');
  } else {
    grpChild.style.display = 'none';
  }
  const today = new Date().toISOString().split('T')[0];
  const startEl = document.getElementById('leaveStartDate');
  const endEl = document.getElementById('leaveEndDate');
  if (startEl && !startEl.value) startEl.value = today;
  if (endEl && !endEl.value) endEl.value = today;
  openModal('modalCreateLeave');
}

async function submitCreateLeave() {
  let studentId = null;
  if (currentUser?.role === 'STUDENT') {
    studentId = currentUser.student_profile?.id;
  } else if (currentUser?.role === 'PARENT') {
    studentId = parseInt(document.getElementById('leaveStudentId').value);
  } else {
    studentId = (window.currentStudentsList || [])[0]?.id;
  }
  const startDate = document.getElementById('leaveStartDate').value;
  const endDate = document.getElementById('leaveEndDate').value;
  const reason = document.getElementById('leaveReason').value.trim();

  if (!studentId) { toast('Lỗi', 'Không xác định được học sinh.', 'error'); return; }
  if (!startDate || !endDate) { toast('Thiếu Thông Tin', 'Vui lòng chọn đầy đủ ngày bắt đầu và kết thúc.', 'warning'); return; }
  if (startDate > endDate) { toast('Sai Khoảng Thời Gian', 'Ngày bắt đầu không thể sau ngày kết thúc.', 'warning'); return; }
  if (!reason) { toast('Thiếu Lý Do', 'Vui lòng nhập lý do xin nghỉ phép.', 'warning'); return; }

  try {
    const res = await api('POST', `/api/v1/s/${schoolId}/leaves`, {
      student_id: studentId,
      start_date: startDate,
      end_date: endDate,
      reason: reason
    });
    toast('✅ Đã Gửi Đơn', res.message || 'Đơn xin phép đã được gửi đến GVCN.', 'success');
    closeModal('modalCreateLeave');
    document.getElementById('leaveReason').value = '';
    loadMyLeaves();
  } catch(e) {
    toast('Lỗi', e.detail || 'Không thể gửi đơn xin nghỉ phép.', 'error');
  }
}

async function openCreateDisputeModal(attLogId = null, studentId = null) {
  const grpChild = document.getElementById('grpDisputeChildSelect');
  const selChild = document.getElementById('disputeStudentId');
  if (currentUser?.role === 'PARENT') {
    const children = currentUser.children || [];
    if (!children.length) {
      toast('Chưa Liên Kết Con Em', 'Vui lòng liên kết tài khoản với con em trước khi gửi khiếu nại.', 'warning');
      openLinkChildModal();
      return;
    }
    grpChild.style.display = 'block';
    selChild.innerHTML = children.map(ch =>
      `<option value="${ch.id}" ${ch.id === studentId ? 'selected' : ''}>${escHtml(ch.full_name)} (${escHtml(ch.class_name || 'Chưa xếp lớp')})</option>`
    ).join('');
  } else {
    grpChild.style.display = 'none';
  }

  const effectiveStudentId = studentId || (currentUser?.role === 'STUDENT' ? currentUser?.student_profile?.id : (currentUser?.children?.[0]?.id));
  const selAtt = document.getElementById('disputeAttendanceLogId');
  selAtt.innerHTML = '<option value="">-- Khiếu nại nề nếp chung / Không gắn bản ghi cụ thể --</option>';
  if (effectiveStudentId) {
    try {
      const logs = await api('GET', `/api/v1/s/${schoolId}/attendance/student/${effectiveStudentId}`);
      logs.slice(0, 10).forEach(l => {
        const timeStr = l.timestamp ? l.timestamp.slice(0, 16).replace('T', ' ') : l.date_only;
        const opt = document.createElement('option');
        opt.value = l.id;
        opt.text = `${timeStr} - ${l.status === 'LATE' ? 'Đi trễ' : l.status} - Đồng phục: ${l.uniform_status}`;
        if (attLogId && l.id === attLogId) opt.selected = true;
        selAtt.appendChild(opt);
      });
    } catch(e) {}
  }
  openModal('modalCreateDispute');
}

async function submitCreateDispute() {
  let studentId = null;
  if (currentUser?.role === 'STUDENT') {
    studentId = currentUser.student_profile?.id;
  } else if (currentUser?.role === 'PARENT') {
    studentId = parseInt(document.getElementById('disputeStudentId').value);
  } else {
    studentId = (window.currentStudentsList || [])[0]?.id;
  }
  const attLogVal = document.getElementById('disputeAttendanceLogId').value;
  const attLogId = attLogVal ? parseInt(attLogVal) : null;
  const reason = document.getElementById('disputeReason').value.trim();

  if (!studentId) { toast('Lỗi', 'Không xác định được học sinh.', 'error'); return; }
  if (!reason) { toast('Thiếu Lý Do', 'Vui lòng nhập lý do khiếu nại để GVCN đối chiếu.', 'warning'); return; }

  try {
    const res = await api('POST', `/api/v1/s/${schoolId}/disputes`, {
      attendance_log_id: attLogId,
      student_id: studentId,
      reason: reason
    });
    toast('✅ Đã Gửi Khiếu Nại', res.message || 'Khiếu nại đã được gửi tới GVCN.', 'success');
    closeModal('modalCreateDispute');
    document.getElementById('disputeReason').value = '';
    loadMyDisputes();
    loadMyAttendance();
  } catch(e) {
    toast('Lỗi', e.detail || 'Không thể gửi khiếu nại.', 'error');
  }
}



export {
  loadMyAttendance, loadMyDisputes, loadMyLeaves, openCreateDisputeModal, openCreateLeaveModal, submitCreateDispute, submitCreateLeave
};
