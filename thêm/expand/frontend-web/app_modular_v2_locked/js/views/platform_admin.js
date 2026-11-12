// app/js/views/platform_admin.js — Platform Super Admin (Multi-School Management)
// ── Ngôi Trường Của Tôi (Create School) ───────────
async function doCreateMySchool() {
  const payload = {
    name:                 document.getElementById('mySchoolName').value.trim(),
    school_code:          document.getElementById('mySchoolCode').value.trim(),
    province_city:        document.getElementById('mySchoolProvince').value.trim(),
    academic_year:        document.getElementById('mySchoolYear').value,
    address:              document.getElementById('mySchoolAddress').value.trim(),
    headmaster_name:      document.getElementById('mySchoolHmName').value.trim(),
    headmaster_phone:     document.getElementById('mySchoolHmPhone').value.trim() || null,
    headmaster_username:  document.getElementById('mySchoolHmUser').value.trim(),
    headmaster_password:  document.getElementById('mySchoolHmPass').value.trim(),
  };

  if (!payload.name || !payload.school_code || !payload.headmaster_name || !payload.headmaster_username || !payload.headmaster_password) {
    toast('Thiếu thông tin', 'Vui lòng điền đầy đủ các mục có dấu *', 'error');
    return;
  }

  try {
    const res = await api('POST', '/api/v1/schools', payload);
    closeModal('modalMySchool');
    toast('🎉 Chúc Mừng', res.message || 'Đã khởi tạo thành công Ngôi Trường Của Tôi!', 'success');
    if (res.school && res.school.id) {
      setTimeout(() => {
        onAdminSchoolChange(res.school.id);
      }, 1200);
    }
  } catch(e) {
    toast('Lỗi Tạo Trường', e.detail || 'Không thể khởi tạo', 'error');
  }
}



// ── Master Platform Admin Logic (Embedded in Dashboard) ───
async function loadPlatformAdminView() {
  // Load global stats
  try {
    const s = await api('GET', '/api/v1/platform/stats');
    document.getElementById('admTotSchools').innerText  = s.total_schools || 0;
    document.getElementById('admTotStudents').innerText = s.total_students || 0;
    document.getElementById('admTotTeachers').innerText = s.total_teachers || 0;
    document.getElementById('admTotAtt').innerText      = s.today_attendance || 0;
  } catch(e) {}

  // Load all schools table
  const tbody = document.getElementById('admSchoolsTbody');
  try {
    const list = await api('GET', '/api/v1/platform/schools');
    if (!list.length) {
      tbody.innerHTML = `
        <tr>
          <td colspan="7" style="text-align:center;padding:48px 24px;">
            <div style="font-size:2.5rem;margin-bottom:10px;">🏫</div>
            <div style="font-size:1.1rem;font-weight:700;color:var(--text);margin-bottom:6px;">Chưa có server trường học nào</div>
            <div style="font-size:0.85rem;color:var(--muted);margin-bottom:18px;">Hệ thống đang ở trạng thái sạch. Hãy khởi tạo ngôi trường thật đầu tiên của bạn!</div>
            <button class="btn btn-primary" style="background:var(--purple);font-weight:700;padding:8px 22px;" onclick="openModal('modalMySchool')">
              ➕ Khởi Tạo Trường Mới Ngay
            </button>
          </td>
        </tr>`;
      return;
    }
    tbody.innerHTML = list.map(s => {
      const safeName = escHtml(s.name);
      const safeAddr = escHtml(s.address || '—');
      const safeCode = escHtml(s.school_code);
      const safeProv = escHtml(s.province_city || '—');
      return `
      <tr style="border-bottom:1px solid var(--border);">
        <td style="color:var(--muted);">${s.id}</td>
        <td><b>${safeName}</b><br><small style="color:var(--muted);">${safeAddr}</small></td>
        <td><code style="color:var(--blue);">${safeCode}</code></td>
        <td>${safeProv}</td>
        <td style="font-size:0.8rem;">👥 ${s.student_count||0} HS · 👩‍🏫 ${s.teacher_count||0} GV · 🎥 ${s.camera_count||0} Cam</td>
        <td><span class="chip ${s.status==='ACTIVE'?'chip-green':'chip-red'}">${s.status==='ACTIVE'?'Đang Hoạt Động':'Tạm Khóa'}</span></td>
        <td>
          <div style="display:flex;gap:4px;">
            <button class="btn btn-sm ${s.status==='ACTIVE'?'btn-outline':'btn-primary'}" style="padding:4px 8px;font-size:0.75rem;" onclick="togglePlatformSchool(${s.id}, '${s.status==='ACTIVE'?'SUSPENDED':'ACTIVE'}')">
              ${s.status==='ACTIVE'?'Khóa':'Mở'}
            </button>
            <button class="btn btn-sm btn-primary" style="padding:4px 8px;font-size:0.75rem;" onclick="onAdminSchoolChange(${s.id})">
              🚀 Vào
            </button>
            <button class="btn btn-sm btn-danger" style="padding:4px 8px;font-size:0.75rem;" onclick="deletePlatformSchool(${s.id}, ${JSON.stringify(s.name)})">
              🗑️ Xóa
            </button>
          </div>
        </td>
      </tr>`;
    }).join('');
  } catch(e) {
    tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;padding:24px;color:var(--red);">Lỗi tải danh sách trường.</td></tr>';
  }
}

async function togglePlatformSchool(id, newStatus) {
  try {
    const res = await api('PUT', `/api/v1/platform/schools/${id}/status`, { status: newStatus });
    toast('✅ Cập nhật', res.message, 'success');
    loadPlatformAdminView();
  } catch(e) {
    toast('Lỗi', e.detail || 'Không thể đổi trạng thái', 'error');
  }
}

async function deletePlatformSchool(id, name) {
  if (!confirm(`⚠️ CẢNH BÁO MASTER ADMIN:\nBạn có chắc chắn muốn xóa vĩnh viễn trường "${name}" (ID #${id}) và toàn bộ học sinh, camera, điểm danh liên quan không?`)) return;
  try {
    const res = await api('DELETE', `/api/v1/platform/schools/${id}`);
    toast('🗑️ Đã Xóa Trường', res.message, 'success');

    // Nếu trường vừa bị xóa là trường đang được chọn trên URL/session, chuyển sang trường còn lại
    if (String(schoolId) === String(id)) {
      try {
        const remainingSchools = await api('GET', '/api/v1/platform/schools');
        if (remainingSchools && remainingSchools.length > 0) {
          const nextSchool = remainingSchools.find(s => s.id !== id) || remainingSchools[0];
          localStorage.setItem('stem_school_id', nextSchool.id);
          window.location.href = `/app/index.html?school_id=${nextSchool.id}&view=view-platform-admin`;
          return;
        } else {
          localStorage.removeItem('stem_school_id');
          window.location.href = `/app/index.html?view=view-platform-admin`;
          return;
        }
      } catch(_) {}
    }

    loadPlatformAdminView();
    setupAdminSchoolSwitcher();
  } catch(e) {
    toast('Lỗi Xóa Trường', (e && (e.detail || e.message)) || 'Không thể xóa trường học này.', 'error');
  }
}

async function doResetPlatformDemoData() {
  if (!confirm('⚠️ CẢNH BÁO TOÀN QUỐC:\nBạn có chắc chắn muốn DỌN SẠCH TẤT CẢ các trường demo mẫu để đưa hệ thống về trạng thái TRẮNG TINH (100% Sạch) không?\n(Chỉ giữ lại tài khoản Master Admin của bạn)')) return;
  try {
    const res = await api('POST', '/api/v1/platform/reset-demo-data');
    toast('🧹 Đã Dọn Sạch Dữ Liệu', res.message, 'success');
    localStorage.removeItem('stem_school_id');
    window.location.href = `/app/index.html?view=view-platform-admin`;
  } catch(e) {
    toast('Lỗi', (e && (e.detail || e.message)) || 'Không thể reset', 'error');
  }
}



export {
  deletePlatformSchool, doCreateMySchool, doResetPlatformDemoData, loadPlatformAdminView, togglePlatformSchool
};
