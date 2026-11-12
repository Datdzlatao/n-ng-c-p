// app/js/views/verify.js — Pending FaceID Biometric Approvals
// ── Pending Verify & FaceID Verification ──────────
async function loadPendingVerify() {
  const tbl = document.getElementById('verifyBody');
  tbl.innerHTML = '<tr><td colspan="7" style="text-align:center;padding:24px;color:var(--muted)">Đang tải...</td></tr>';
  try {
    const rows = await api('GET', `/api/v1/auth/verify/pending-list?school_id=${schoolId}`);
    if (!rows.length) { tbl.innerHTML = emptyRow('Không có hồ sơ nào đang chờ duyệt.', 7); return; }
    tbl.innerHTML = rows.map(u => {
      const isJoinReq = u.verification_method === 'JOIN_REQUEST';
      const isFaceScan = u.verification_method === 'FACE_SCAN';
      return `
      <tr>
        <td><strong>${escHtml(u.full_name)}</strong></td>
        <td><code>${escHtml(u.username)}</code></td>
        <td><span class="chip chip-blue">${escHtml(u.role)}</span></td>
        <td>${escHtml(u.phone||u.email||'—')}</td>
        <td>${isFaceScan ? '<span class="chip chip-purple" style="font-weight:700;">📸 FaceID 3D</span>' : (isJoinReq ? '<span class="chip chip-blue" style="font-weight:700;">📥 Gia Nhập</span>' : escHtml(u.verification_method || 'ID_CARD'))}</td>
        <td>
          ${isFaceScan
            ? `<div style="display:flex;align-items:center;gap:6px;">
                 <img src="${u.verification_doc_url || '/assets/icons/default_avatar.png'}" style="width:34px;height:34px;border-radius:6px;object-fit:cover;border:1px solid var(--purple);" onerror="this.src='/assets/icons/default_avatar.png'">
                 <button class="btn btn-outline btn-sm" style="padding:2px 8px;font-size:0.7rem;color:var(--purple);border-color:var(--purple);" onclick="viewBiometricDetails(${u.id}, ${JSON.stringify(u.full_name)})">👁️ Xem Mẫu Mặt</button>
               </div>`
            : (isJoinReq
                ? `<span style="font-size:0.78rem;color:var(--muted);">Đơn xin vào trường</span>`
                : (u.verification_doc_url ? `<a href="${u.verification_doc_url}" target="_blank" style="color:var(--blue);font-size:0.78rem;font-weight:700;">🔍 Xem Ảnh</a>` : '—'))
          }
        </td>
        <td>
          <div style="display:flex;gap:4px;flex-wrap:wrap;">
            <button class="btn btn-success" style="padding:4px 8px;font-size:0.72rem;" onclick="approveVerify(${u.id},'VERIFIED')">✓ ${isJoinReq ? 'Chấp Thuận' : 'Tích Xanh'}</button>
            <button class="btn btn-danger"  style="padding:4px 7px;font-size:0.72rem;" onclick="approveVerify(${u.id},'REJECTED')" title="Từ chối">✕</button>
            ${!isJoinReq ? `<button class="btn btn-outline btn-sm" style="padding:3px 6px;font-size:0.7rem;border-color:var(--purple);color:var(--purple);" onclick="scanFaceForPendingUser(${u.id}, '${u.full_name}', '${u.student_code||u.username}')" title="Quét FaceID trực tiếp">📸 Quét</button>` : ''}
          </div>
        </td>
      </tr>`;
    }).join('');
  } catch(e) { tbl.innerHTML = errorRow(e, 7); }
}

async function approveVerify(userId, status) {
  try {
    const res = await api('POST', '/api/v1/auth/verify/approve', { user_id: userId, status });
    toast(status==='VERIFIED'?'✅ Đã Phê Duyệt':'❌ Đã Từ Chối', res.message, 'success');
    loadPendingVerify();
    if (typeof loadJoinRequests === 'function') loadJoinRequests();
    loadStats().then(updateBadges);
  } catch(e) { toast('Lỗi', e.detail||'', 'error'); }
}

async function openDirectFaceScanModal() {
  openModal('modalDirectFaceScan');
  const sel = document.getElementById('dfsStudentSelect');
  sel.innerHTML = '<option value="">Đang tải danh sách học sinh...</option>';
  try {
    const students = await api('GET', `/api/v1/s/${schoolId}/students`);
    if (!students || students.length === 0) {
      sel.innerHTML = '<option value="">Chưa có học sinh nào. Hãy thêm học sinh trước.</option>';
      return;
    }
    sel.innerHTML = students.map(s => `
      <option value="${s.id}" data-code="${s.student_code}" data-name="${s.full_name}">
        ${s.student_code} — ${s.full_name} (${s.class_name || 'Chưa phân lớp'})
      </option>
    `).join('');
  } catch(e) {
    sel.innerHTML = '<option value="">Lỗi tải danh sách học sinh</option>';
  }
}

function triggerDirectFaceScan() {
  const sel = document.getElementById('dfsStudentSelect');
  const opt = sel.selectedOptions[0];
  if (!opt || !opt.value) {
    toast('Chưa chọn học sinh', 'Vui lòng chọn một học sinh trong danh sách', 'error');
    return;
  }
  const studentId = parseInt(opt.value);
  const studentCode = opt.getAttribute('data-code');
  const studentName = opt.getAttribute('data-name');
  closeModal('modalDirectFaceScan');

  if (typeof BiometricScanner !== 'undefined') {
    BiometricScanner.start({
      schoolId: schoolId,
      studentId: studentId,
      studentCode: studentCode,
      studentName: studentName,
      verifyAccount: true,
      onComplete: () => {
        toast('✅ Xác Minh FaceID Thành Công', `Đã cấp Tích Xanh & nạp mẫu mặt cho ${studentName}`, 'success');
        loadPendingVerify();
        loadStudents();
      }
    });
  }
}

function scanFaceForPendingUser(userId, name, code) {
  if (typeof BiometricScanner !== 'undefined') {
    BiometricScanner.start({
      schoolId: schoolId,
      studentId: userId,
      studentCode: code || `HS${schoolId}-${userId}`,
      studentName: name,
      verifyAccount: true,
      onComplete: () => {
        toast('✅ Đã Nạp FaceID & Xác Minh', `Đã cấp Tích Xanh chính chủ cho ${name}`, 'success');
        loadPendingVerify();
        loadStats().then(updateBadges);
      }
    });
  }
}

async function viewBiometricDetails(userIdOrStudentId, name = '') {
  openModal('modalFaceSamplesViewer');
  document.getElementById('fsvTitle').innerText = `Mẫu Mặt FaceID: ${name || 'Học Sinh'}`;
  const grid = document.getElementById('fsvGrid');
  const countEl = document.getElementById('fsvCount');
  grid.innerHTML = '<div style="text-align:center;color:var(--muted);padding:24px;grid-column:1/-1;">Đang tải mẫu ảnh sinh trắc học...</div>';
  countEl.innerText = '';

  try {
    const samples = await api('GET', `/api/v1/s/${schoolId}/students/${userIdOrStudentId}/samples`);
    if (!samples || samples.length === 0) {
      grid.innerHTML = `
        <div style="text-align:center;color:var(--muted);padding:24px;grid-column:1/-1;">
          <div style="font-size:2rem;margin-bottom:6px;">📭</div>
          Chưa có mẫu quét chi tiết nào được lưu trữ cho học sinh này.<br>
          <span style="font-size:0.75rem;color:var(--muted);">Ảnh đại diện chính diện vẫn được dùng để nhận diện.</span>
        </div>`;
      return;
    }
    countEl.innerText = `Đã thu thập ${samples.length} góc quét sinh trắc học bảo mật AES-256`;
    grid.innerHTML = samples.map(s => `
      <div style="background:var(--card);border:1px solid var(--border);border-radius:8px;padding:8px;text-align:center;">
        <img src="${s.image_url}" style="width:100%;height:100px;object-fit:cover;border-radius:6px;margin-bottom:6px;" alt="${s.angle_type}">
        <div style="font-size:0.75rem;font-weight:700;color:var(--blue);">${s.angle_type}</div>
        <div style="font-size:0.68rem;color:var(--muted);">Góc: ${s.yaw_angle ? s.yaw_angle.toFixed(1) : 0}°</div>
      </div>
    `).join('');
  } catch(e) {
    grid.innerHTML = `<div style="text-align:center;color:var(--red);padding:24px;grid-column:1/-1;">⚠️ Không tải được mẫu mặt: ${e.detail||e.message||e}</div>`;
  }
}



export {
  approveVerify, loadPendingVerify, openDirectFaceScanModal, scanFaceForPendingUser, triggerDirectFaceScan, viewBiometricDetails
};
