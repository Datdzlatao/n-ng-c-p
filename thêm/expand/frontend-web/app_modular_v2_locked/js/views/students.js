// app/js/views/students.js — Student Directory, ID Cards & Face Approvals
// ── Students ─────────────────────────────────────
// ── Students & Apple FaceID Scanner ────────────────
let faceidStream = null;
let currentFacePoseIndex = 0;
let capturedFacePoses = { front: null, left: null, right: null, tilt: null };
let activeFaceEnrollStudent = null;

const FACE_STEPS = [
  { id: 'front', label: '🎯 Bước 1/4: Nhìn thẳng vào Camera', pct: '25%' },
  { id: 'left',  label: '🎯 Bước 2/4: Nghiêng nhẹ mặt sang Trái', pct: '50%' },
  { id: 'right', label: '🎯 Bước 3/4: Nghiêng nhẹ mặt sang Phải', pct: '75%' },
  { id: 'tilt',  label: '🎯 Bước 4/4: Hơi ngước cằm lên / Mỉm cười', pct: '100%' }
];

async function loadStudents() {
  const q   = document.getElementById('stuSearch')?.value || '';
  const tbl = document.getElementById('stuBody');
  tbl.innerHTML = '<tr><td colspan="8" style="text-align:center;padding:32px;color:var(--muted);">Đang tải...</td></tr>';
  try {
    const rows = await api('GET', `/api/v1/s/${schoolId}/students?q=${encodeURIComponent(q)}`);
    if (!rows.length) { tbl.innerHTML = emptyRow('Không có học sinh nào.', 8); return; }
    window.currentStudentsList = rows;
    tbl.innerHTML = rows.map(s => {
      const photoSrc = s.face_photo_url ? s.face_photo_url : '/assets/icons/default_avatar.png';
      const sampleCnt = (s.face_samples_count !== undefined && s.face_samples_count !== null)
        ? Number(s.face_samples_count)
        : (s.face_photo_url ? 3 : 0);
      let bioBadge = '';
      if (sampleCnt >= 5) {
        bioBadge = `<div style="margin-top:3px;"><span class="chip chip-green" style="font-size:0.65rem;padding:1px 5px;font-weight:700;" title="Đã nạp đủ 5 góc ảnh AI chuẩn FaceID">🟢 5/5 ảnh</span></div>`;
      } else if (sampleCnt > 0) {
        bioBadge = `<div style="margin-top:3px;"><span class="chip chip-amber" style="font-size:0.65rem;padding:1px 5px;font-weight:700;" title="Đã có sẵn ${sampleCnt} ảnh góc cơ bản">🟡 ${sampleCnt}/5 ảnh</span></div>`;
      } else {
        bioBadge = `<div style="margin-top:3px;"><span class="chip chip-red" style="font-size:0.65rem;padding:1px 5px;font-weight:700;" title="Chưa quét sinh trắc học FaceID">⚠️ 0/5 ảnh</span></div>`;
      }
      return `
      <tr>
        <td>
          <div style="display:flex;flex-direction:column;align-items:center;">
            <img src="${photoSrc}" onerror="this.src='/assets/icons/default_avatar.png'" style="width:38px;height:48px;border-radius:6px;object-fit:cover;border:1.5px solid var(--border);">
            ${bioBadge}
          </div>
        </td>
        <td><code style="color:var(--blue);font-weight:700;font-size:0.9rem;">${escHtml(s.student_code)}</code></td>
        <td><strong>${escHtml(s.full_name)}</strong></td>
        <td>${escHtml(s.class_name || '—')}</td>
        <td>
          ${(() => {
            const lps = s.linked_parents || [];
            if (lps.length > 0) {
              return lps.map(p => `
                <div style="margin-bottom:3px;display:flex;align-items:center;gap:4px;">
                  <span class="chip chip-green" style="font-size:0.7rem;padding:2px 6px;" title="TK: @${escHtml(p.parent_username)} | SĐT: ${escHtml(p.parent_phone || '—')}">
                    👨‍👩‍👧 ${escHtml(p.parent_full_name || p.parent_username)}
                  </span>
                  ${['TEACHER','HEADMASTER','ADMIN'].includes(currentUser?.role) ? `
                    <button class="btn btn-outline btn-xs" style="color:var(--red);border-color:transparent;padding:0 3px;font-size:0.68rem;" onclick="promptUnlinkParent(${s.id}, ${p.parent_user_id}, '${escHtml(p.parent_full_name || p.parent_username)}')" title="Gỡ tài khoản phụ huynh này">✕</button>
                  ` : ''}
                </div>
              `).join('');
            } else {
              return `
                <div style="font-size:0.78rem;color:var(--muted);">
                  ${s.parent_phone ? `📞 ${escHtml(s.parent_phone)}` : '<span style="font-style:italic;color:#94a3b8;">Chưa có</span>'}
                  ${['TEACHER','HEADMASTER','ADMIN'].includes(currentUser?.role) ? `
                    <div style="margin-top:2px;">
                      <button class="btn btn-outline btn-xs" style="padding:1px 5px;font-size:0.68rem;color:var(--blue);border-color:var(--blue);" onclick="openAssignParentModal(${s.id}, '${escHtml(s.full_name)}', '${escHtml(s.student_code)}', '${escHtml(s.parent_phone||'')}')">
                        + Gán TK PH
                      </button>
                    </div>
                  ` : ''}
                </div>
              `;
            }
          })()}
        </td>
        <td><span style="color:${(s.current_points??100)>=80?'var(--green)':'var(--red)'};font-weight:700;">${s.current_points ?? 100}</span></td>
        <td>
          <button class="btn btn-outline" style="padding:4px 10px;font-size:0.75rem;border-color:var(--blue);color:var(--blue);" onclick="showStudentCard('${escHtml(s.student_code)}')">
            🪪 Thẻ QR
          </button>
        </td>
        <td>
          <div style="display:flex;gap:4px;">
            <button class="btn btn-sm ${sampleCnt === 0 ? 'btn-danger' : 'btn-outline'}" style="padding:3px 7px;font-size:0.72rem;${sampleCnt < 5 ? 'border-color:var(--purple);color:var(--purple);font-weight:700;' : ''}" onclick="openFaceIDScanner(${s.id})" title="${sampleCnt === 0 ? 'Chưa quét FaceID - Nhận diện người lạ!' : sampleCnt < 5 ? 'Đã có ' + sampleCnt + '/5 ảnh - Quét bổ sung' : 'Đã đủ 5/5 ảnh - Quét lại'}">
              📸 ${sampleCnt === 0 ? 'Quét Ngay' : sampleCnt < 5 ? 'Nâng 5G' : 'Quét Lại'}
            </button>
            ${['TEACHER','HEADMASTER','ADMIN'].includes(currentUser?.role) ? `
              <button class="btn btn-sm btn-outline" style="padding:3px 6px;font-size:0.72rem;" onclick="openAssignParentModal(${s.id}, '${escHtml(s.full_name)}', '${escHtml(s.student_code)}', '${escHtml(s.parent_phone||'')}')" title="Quản lý tài khoản phụ huynh liên kết">
                👨‍👩‍👧
              </button>
            ` : ''}
            ${s.face_approved==='PENDING' && ['TEACHER','HEADMASTER','ADMIN'].includes(currentUser?.role)
              ? `<button class="btn btn-success" style="padding:3px 7px;font-size:0.72rem;" onclick="approveFace(${s.id},'APPROVED')">✓</button>
                 <button class="btn btn-danger"  style="padding:3px 7px;font-size:0.72rem;" onclick="approveFace(${s.id},'REJECTED')">✕</button>`
              : ''}
          </div>
        </td>
      </tr>`;
    }).join('');
    
    // Populate class select in add modal
    const sel = document.getElementById('asStuClass');
    if (sel) sel.innerHTML = classesCache.map(c => `<option value="${c.id}">${c.name}</option>`).join('');
    const selFid = document.getElementById('fidStuClass');
    if (selFid) selFid.innerHTML = classesCache.map(c => `<option value="${c.id}">${c.name}</option>`).join('');
  } catch(e) {
    tbl.innerHTML = errorRow(e, 8);
  }
}



// ── Smart Student ID Card & QR Display ─────────────
async function showStudentCard(studentCode) {
  try {
    const s = await api('GET', `/api/v1/s/${schoolId}/students/by-code/${studentCode}`);
    document.getElementById('scCode').innerText   = s.student_code;
    document.getElementById('scName').innerText   = s.full_name;
    document.getElementById('scClass').innerText  = s.class_name || 'Chưa phân lớp';
    document.getElementById('scPoints').innerText = (s.current_points ?? 100) + 'đ';
    
    const photo = document.getElementById('scPhoto');
    photo.src = s.face_photo_url || '/assets/icons/default_avatar.png';
    photo.onerror = () => { photo.src = '/assets/icons/default_avatar.png'; };

    // Render dynamic QR Code on Canvas
    const qrWrap = document.getElementById('scQrCode');
    qrWrap.innerHTML = '';
    if (typeof QRCode !== 'undefined') {
      new QRCode(qrWrap, {
        text: s.qr_token || s.student_code,
        width: 72,
        height: 72,
        colorDark: '#000000',
        colorLight: '#ffffff',
        correctLevel: QRCode.CorrectLevel.M
      });
    }

    const inviteEl = document.getElementById('scParentInviteCode');
    if (inviteEl) inviteEl.innerText = s.parent_invite_code || '—';

    openModal('modalStudentCard');
  } catch(e) {
    toast('Lỗi', 'Không thể tải thẻ học sinh: ' + (e.detail || e), 'error');
  }
}

function printStudentCard() {
  window.print();
}



function faceChip(status) {
  const map = { APPROVED:'<span class="chip chip-green">✓ Đã Duyệt</span>', REJECTED:'<span class="chip chip-red">✕ Từ Chối</span>', PENDING:'<span class="chip chip-orange">⏳ Chờ Duyệt</span>' };
  return map[status] || '<span class="chip chip-muted">—</span>';
}

async function approveFace(studentId, status) {
  try {
    await api('PUT', `/api/v1/s/${schoolId}/students/${studentId}/face-approval`, { status });
    toast(`${status==='APPROVED'?'✓ Đã Duyệt Ảnh AI':'✕ Đã Từ Chối Ảnh'}`, '', status==='APPROVED'?'success':'info');
    loadStudents();
  } catch(e) { toast('Lỗi', e.detail||'', 'error'); }
}

async function doAddStudent(andScanFace = false) {
  const payload = {
    student_code: document.getElementById('asStuCode').value.trim() || null,
    full_name:    document.getElementById('asStuName').value.trim(),
    dob:          document.getElementById('asStuDob').value || null,
    class_id:     parseInt(document.getElementById('asStuClass').value) || null,
    parent_phone: document.getElementById('asStuPhone').value.trim() || null,
    parent_name:  document.getElementById('asStuParent').value.trim() || null,
  };
  if (!payload.full_name) { toast('Thiếu thông tin','Cần nhập Họ Tên học sinh','error'); return; }
  try {
    const res = await api('POST', `/api/v1/s/${schoolId}/students`, payload);
    closeModal('modalAddStudent');
    toast('✅ Đã Cấp Mã HS', `${res.student_code} — ${payload.full_name}`, 'success');
    loadStudents();

    if (andScanFace && typeof BiometricScanner !== 'undefined') {
      BiometricScanner.start({
        schoolId: schoolId,
        studentId: res.student_id,
        studentCode: res.student_code,
        studentName: payload.full_name,
        verifyAccount: true,
        onComplete: () => {
          toast('✨ Cấp Mã & FaceID Hoàn Tất', `Mã HS: ${res.student_code} · Đã nạp vào bộ nhận diện`, 'success');
          loadStudents();
          showStudentCard(res.student_code);
        }
      });
    } else {
      showStudentCard(res.student_code);
    }
  } catch(e) { toast('Lỗi', e.detail||'', 'error'); }
}



export {
  approveFace, doAddStudent, faceChip, loadStudents, printStudentCard, showStudentCard
};
