// app/js/views/members.js — Staff & Personnel Management
// ── Members & Personnel Management (Quản Lý Nhân Sự) ───────────────
let schoolMembersCache = [];

async function loadSchoolMembers() {
  const tbl = document.getElementById('membersBody');
  if (!tbl) return;
  tbl.innerHTML = '<tr><td colspan="8" style="text-align:center;padding:24px;color:var(--muted)">Đang tải danh sách thành viên...</td></tr>';
  
  const search = (document.getElementById('memberSearch')?.value || '').trim();
  const roleFilter = document.getElementById('memberRoleFilter')?.value || 'ALL';
  
  let url = `/api/v1/s/${schoolId}/users?limit=100`;
  if (roleFilter !== 'ALL') url += `&role=${encodeURIComponent(roleFilter)}`;
  if (search) url += `&q=${encodeURIComponent(search)}`;
  
  try {
    const res = await api('GET', url);
    const users = res.users || [];
    schoolMembersCache = users;
    
    if (!users.length) {
      tbl.innerHTML = emptyRow('Không tìm thấy thành viên nào phù hợp.', 8);
      return;
    }
    
    tbl.innerHTML = users.map(u => {
      const roleColor = {
        HEADMASTER: 'chip-purple',
        SCHOOL_ADMIN: 'chip-purple',
        TEACHER: 'chip-blue',
        INSPECTOR: 'chip-orange',
        PARENT: 'chip-green',
        STUDENT: 'chip-blue'
      }[u.role] || 'chip-blue';

      const roleLabel = {
        HEADMASTER: 'Hiệu Trưởng',
        SCHOOL_ADMIN: 'Quản Lý',
        TEACHER: 'Giáo Viên',
        INSPECTOR: 'Giám Thị',
        PARENT: 'Phụ Huynh',
        STUDENT: 'Học Sinh'
      }[u.role] || u.role;

      const isSubordinate = ['TEACHER', 'INSPECTOR', 'PARENT', 'STUDENT'].includes(u.role);
      const isCurrentAdmin = (currentUser && ['ADMIN', 'PLATFORM_ADMIN'].includes(currentUser.role));
      const canEdit = isCurrentAdmin || (currentUser && currentUser.role === 'HEADMASTER' && isSubordinate);
      
      const phoneHtml = u.phone 
        ? `<span style="font-family:monospace;color:var(--text);display:inline-flex;align-items:center;gap:4px;">📞 ${escHtml(u.phone)}</span>`
        : `<span style="color:var(--muted);font-style:italic;font-size:0.75rem;">Chưa có SĐT</span>`;
        
      const emailHtml = u.email 
        ? `<span style="color:var(--muted);display:inline-flex;align-items:center;gap:4px;">✉️ ${escHtml(u.email)}</span>`
        : `<span style="color:var(--muted);font-style:italic;font-size:0.75rem;">Chưa có email</span>`;

      const statusHtml = u.status === 'ACTIVE'
        ? `<span class="chip chip-green" style="font-size:0.72rem;">● Hoạt động</span>`
        : `<span class="chip chip-red" style="font-size:0.72rem;">✕ Tạm khóa</span>`;

      let actionsHtml = '';
      if (canEdit) {
        actionsHtml = `
          <div style="display:flex;gap:5px;flex-wrap:wrap;align-items:center;">
            <button class="btn btn-outline btn-xs" style="padding:4px 8px;font-size:0.72rem;color:var(--purple);border-color:rgba(192,132,252,0.4);" onclick="openEditMemberModal(${u.id})" title="Chỉnh sửa SĐT, email, họ tên">
              ✏️ Sửa
            </button>
            <button class="btn btn-outline btn-xs" style="padding:4px 8px;font-size:0.72rem;color:var(--orange);border-color:rgba(245,158,11,0.4);" onclick="openResetMemberPasswordModal(${u.id}, ${JSON.stringify(u.full_name||'')}, ${JSON.stringify(u.username||'')})" title="Đặt lại mật khẩu">
              🔑 Reset MK
            </button>
            <button class="btn btn-outline btn-xs" style="padding:4px 8px;font-size:0.72rem;color:${u.status==='ACTIVE'?'#f87171':'#34d399'};border-color:currentColor;" onclick="toggleMemberStatus(${u.id}, ${JSON.stringify(u.full_name||'')}, '${u.status}')" title="${u.status==='ACTIVE'?'Khóa tài khoản':'Mở khóa tài khoản'}">
              ${u.status === 'ACTIVE' ? '🔒 Khóa' : '🔓 Mở'}
            </button>
          </div>
        `;
      } else {
        actionsHtml = `<span style="font-size:0.72rem;color:var(--muted);font-style:italic;">Tài khoản BGH</span>`;
      }

      return `
        <tr>
          <td><strong>${escHtml(u.full_name || '—')}</strong></td>
          <td><code>${escHtml(u.username || '—')}</code></td>
          <td><span class="chip ${roleColor}" style="font-weight:700;">${escHtml(roleLabel)}</span></td>
          <td><code style="color:var(--blue);font-weight:700;">${escHtml(u.member_code || u.user_code || u.student_code || '—')}</code></td>
          <td>${phoneHtml}</td>
          <td>${emailHtml}</td>
          <td>${statusHtml}</td>
          <td>${actionsHtml}</td>
        </tr>
      `;
    }).join('');
  } catch(e) {
    tbl.innerHTML = errorRow(e, 8);
  }
}

function openEditMemberModal(userId) {
  const u = schoolMembersCache.find(item => item.id === userId);
  if (!u) return;

  document.getElementById('editMemberId').value = u.id;
  document.getElementById('editMemberFullName').value = u.full_name || '';
  document.getElementById('editMemberPhone').value = u.phone || '';
  document.getElementById('editMemberEmail').value = u.email || '';
  document.getElementById('editMemberDob').value = u.dob || '';
  document.getElementById('editMemberGender').value = u.gender || 'Nam';
  document.getElementById('editMemberRole').value = u.role || 'TEACHER';
  document.getElementById('editMemberStatus').value = u.status || 'ACTIVE';
  
  const sub = document.getElementById('editMemberSub');
  if (sub) sub.innerText = `Chỉnh sửa thông tin cho tài khoản @${u.username} (${u.member_code || ''})`;

  const alertBox = document.getElementById('editMemberAlert');
  if (alertBox) alertBox.style.display = 'none';

  openModal('modalEditMember');
}

async function saveEditMember(e) {
  e.preventDefault();
  const userId = document.getElementById('editMemberId').value;
  const fullName = document.getElementById('editMemberFullName').value.trim();
  const phone = document.getElementById('editMemberPhone').value.trim();
  const email = document.getElementById('editMemberEmail').value.trim();
  const dob = document.getElementById('editMemberDob').value;
  const gender = document.getElementById('editMemberGender').value;
  const role = document.getElementById('editMemberRole').value;
  const status = document.getElementById('editMemberStatus').value;
  
  const alertBox = document.getElementById('editMemberAlert');
  const btn = document.getElementById('btnSaveEditMember');
  btn.disabled = true;
  btn.innerText = 'Đang lưu...';

  try {
    const payload = {
      full_name: fullName,
      phone: phone || null,
      email: email || null,
      dob: dob || null,
      gender: gender,
      role: role,
      status: status
    };
    const res = await api('PUT', `/api/v1/s/${schoolId}/users/${userId}`, payload);
    toast('✅ Thành Công', res.message || 'Đã cập nhật thông tin thành viên', 'success');
    closeModal('modalEditMember');
    loadSchoolMembers();
  } catch(err) {
    if (alertBox) {
      alertBox.style.display = 'block';
      alertBox.style.background = 'rgba(239,68,68,0.15)';
      alertBox.style.color = '#f87171';
      alertBox.style.border = '1px solid rgba(239,68,68,0.3)';
      alertBox.innerText = err.detail || err.message || 'Lỗi cập nhật thông tin';
    }
  } finally {
    btn.disabled = false;
    btn.innerText = 'Lưu Thay Đổi';
  }
}

function openResetMemberPasswordModal(userId, fullName, username) {
  document.getElementById('resetMemberId').value = userId;
  document.getElementById('resetMemberNewPass').value = '123456';
  const sub = document.getElementById('resetMemberSub');
  if (sub) sub.innerText = `Cấp lại mật khẩu mới cho ${fullName} (@${username})`;
  
  const alertBox = document.getElementById('resetMemberAlert');
  if (alertBox) alertBox.style.display = 'none';

  openModal('modalResetMemberPassword');
}

async function submitResetMemberPassword(e) {
  e.preventDefault();
  const userId = document.getElementById('resetMemberId').value;
  const newPass = document.getElementById('resetMemberNewPass').value;
  const btn = document.getElementById('btnSubmitResetMember');
  const alertBox = document.getElementById('resetMemberAlert');

  if (newPass.length < 6) {
    if (alertBox) {
      alertBox.style.display = 'block';
      alertBox.style.background = 'rgba(239,68,68,0.15)';
      alertBox.style.color = '#f87171';
      alertBox.innerText = 'Mật khẩu phải có tối thiểu 6 ký tự.';
    }
    return;
  }

  btn.disabled = true;
  btn.innerText = 'Đang xử lý...';
  try {
    const res = await api('POST', `/api/v1/s/${schoolId}/users/${userId}/reset-password`, { new_password: newPass });
    toast('✅ Thành Công', res.message || 'Đã đặt lại mật khẩu thành công', 'success');
    closeModal('modalResetMemberPassword');
  } catch(err) {
    if (alertBox) {
      alertBox.style.display = 'block';
      alertBox.style.background = 'rgba(239,68,68,0.15)';
      alertBox.style.color = '#f87171';
      alertBox.style.border = '1px solid rgba(239,68,68,0.3)';
      alertBox.innerText = err.detail || err.message || 'Lỗi khi đặt lại mật khẩu';
    }
  } finally {
    btn.disabled = false;
    btn.innerText = 'Cập Nhật Mật Khẩu';
  }
}

async function toggleMemberStatus(userId, name, currentStatus) {
  const nextStatus = currentStatus === 'ACTIVE' ? 'SUSPENDED' : 'ACTIVE';
  const actionName = nextStatus === 'ACTIVE' ? 'mở khóa' : 'tạm khóa';
  if (!confirm(`Bạn có chắc chắn muốn ${actionName} tài khoản của "${name}"?`)) return;

  try {
    const res = await api('POST', `/api/v1/s/${schoolId}/users/${userId}/toggle-status`, { status: nextStatus });
    toast('✅ Thành Công', res.message || `Đã ${actionName} tài khoản`, 'success');
    loadSchoolMembers();
  } catch(err) {
    toast('Lỗi', err.detail || err.message || 'Không thể đổi trạng thái tài khoản', 'error');
  }
}



export {
  loadSchoolMembers, openEditMemberModal, openResetMemberPasswordModal, saveEditMember, submitResetMemberPassword, toggleMemberStatus
};
