/**
 * js/main.js — Application Master Entry Point (ES Module)
 */
import { escHtml } from './utils/helpers.js';
import { toast } from './utils/toast.js';
import { openModal, closeModal } from './utils/modal.js';
import { getSchools, getSchoolById, createSchool, registerSchoolUser } from './services/schoolService.js';
import { login, platformLogin, logoutAll, goToDashboard, checkAuth } from './services/authService.js';
import { getAdminStats, getAdminSchools, updateSchoolStatus } from './services/adminService.js';
import { renderSchoolCards, populateLoginSchools, renderDynamicFields } from './components/schoolRenderer.js';
import { AUTH_KEY, ADMIN_TOKEN_KEY, SCHOOL_ID_KEY } from './config.js';

// ── Application State ─────────────────────────────
let schools = [];
let currentJoinSchool = null;

// ── School Directory Flow ─────────────────────────
export async function loadSchools(q = '', province = '') {
  const statEl = document.getElementById('statSchools');
  const loginSel = document.getElementById('loginSchoolId');
  const joinSel = document.getElementById('joinSchoolSelect');

  try {
    schools = await getSchools(q, province);
    renderSchoolCards(schools);
    if (statEl) statEl.innerText = schools.length;
    populateLoginSchools(schools);
  } catch (e) {
    console.error('[loadSchools] Lỗi kết nối API:', e);
    const grid = document.getElementById('schoolGrid');
    if (grid) {
      grid.innerHTML = `
        <div style="color:var(--red); grid-column:1/-1; text-align:center; padding:40px;">
          ⚠️ Không thể kết nối máy chủ API (${escHtml(e.message || 'Lỗi mạng')}).<br><br>
          <button class="btn btn-outline btn-sm" onclick="loadSchools('${escHtml(q)}', '${escHtml(province)}')">🔄 Thử Lại</button>
        </div>`;
    }
    if (statEl) statEl.innerText = '0';
    const errorOpt = '<option value="" disabled>⚠️ Lỗi kết nối - Vui lòng thử lại</option>';
    if (loginSel) loginSel.innerHTML = errorOpt;
    if (joinSel) joinSel.innerHTML = errorOpt;
    toast('Lỗi Kết Nối', 'Không thể kết nối máy chủ API.', 'error');
  }
}

export function searchSchools() {
  const q = document.getElementById('searchInput')?.value || '';
  const p = document.getElementById('provinceFilter')?.value || '';
  loadSchools(q, p);
}

export async function openRegisterModal() {
  if (!schools || !schools.length) {
    await loadSchools();
  }
  if (!schools || !schools.length) {
    toast('Chưa Có Trường', 'Hệ thống chưa có trường nào đang hoạt động. Vui lòng liên hệ Quản Trị Viên.', 'info');
    return;
  }
  const targetSchoolId = currentJoinSchool ? currentJoinSchool.id : schools[0].id;
  await openJoinModal(targetSchoolId);
}

export function switchToRegisterFromLogin() {
  const loginSel = document.getElementById('loginSchoolId');
  const schoolId = (loginSel && loginSel.value) ? parseInt(loginSel.value) : (schools[0]?.id || null);
  closeModal('modalLogin');
  if (schoolId) {
    openJoinModal(schoolId);
  } else {
    openRegisterModal();
  }
}

export async function onJoinSchoolSelect(schoolId) {
  if (!schoolId) return;
  await openJoinModal(parseInt(schoolId), false);
}

export async function openJoinModal(schoolId, shouldShowModal = true) {
  if (!schoolId && schools.length > 0) {
    schoolId = schools[0].id;
  }
  if (!schoolId) {
    toast('Lỗi', 'Chưa có thông tin trường để đăng ký.', 'error');
    return;
  }

  try {
    currentJoinSchool = await getSchoolById(schoolId);

    const titleEl = document.getElementById('joinSchoolTitle');
    const subEl = document.getElementById('joinSchoolSub');
    if (titleEl) titleEl.innerText = '📝 Đăng Ký Tài Khoản';
    if (subEl) subEl.innerText = `${currentJoinSchool.name} · Năm học ${currentJoinSchool.academic_year} · ${currentJoinSchool.province_city || ''}`;

    const joinSel = document.getElementById('joinSchoolSelect');
    if (joinSel) {
      if (schools && schools.length) {
        joinSel.innerHTML = schools.map(s => `<option value="${s.id}" ${s.id == currentJoinSchool.id ? 'selected' : ''}>${escHtml(s.name)}</option>`).join('');
      }
      joinSel.value = currentJoinSchool.id;
    }

    renderDynamicFields(currentJoinSchool);
    if (shouldShowModal) openModal('modalJoin');
  } catch (e) {
    toast('Lỗi', 'Không thể tải thông tin trường.', 'error');
  }
}

export async function doJoinSchool() {
  if (!currentJoinSchool) {
    const sel = document.getElementById('joinSchoolSelect');
    const sid = sel ? parseInt(sel.value) : null;
    if (sid && schools && schools.length) {
      currentJoinSchool = schools.find(s => s.id === sid) || null;
    }
  }
  if (!currentJoinSchool) {
    toast('Chưa Chọn Trường', 'Vui lòng chọn trường học bạn muốn đăng ký tham gia.', 'error');
    return;
  }

  const school_id = currentJoinSchool.id;
  const role = document.getElementById('joinRole')?.value;
  const full_name = document.getElementById('joinName')?.value.trim();
  const username = document.getElementById('joinUsername')?.value.trim();
  const password = document.getElementById('joinPassword')?.value.trim();
  const phone = document.getElementById('joinPhone')?.value.trim();
  const student_code = document.getElementById('joinStudentCode')?.value.trim() || null;
  const invite_code = document.getElementById('joinInviteCode')?.value.trim() || null;
  const dob = document.getElementById('joinDob')?.value || null;

  if (!full_name || !username || !password) {
    toast('Thiếu Thông Tin', 'Vui lòng điền đầy đủ Họ tên, Tên đăng nhập và Mật khẩu.', 'error');
    return;
  }

  try {
    const data = await registerSchoolUser({ school_id, username, password, full_name, phone, role, student_code, invite_code, dob });
    if (data.status === 'success') {
      localStorage.setItem(AUTH_KEY, data.access_token);
      localStorage.setItem(SCHOOL_ID_KEY, school_id);
      closeModal('modalJoin');

      const assignedCode = data.user_code || data.student_code || (data.user && (data.user.user_code || data.user.student_code));

      if (role === 'STUDENT' && window.BiometricScanner) {
        toast('📝 Đăng Ký Thành Công', `Mã HS của bạn: ${assignedCode}. Bắt đầu quét FaceID...`, 'info');
        window.BiometricScanner.start({
          schoolId: school_id,
          studentId: data.user?.id,
          studentCode: assignedCode,
          studentName: data.user?.full_name || full_name,
          onComplete: () => setTimeout(() => goToDashboard(school_id, schools), 1000),
          onSkip: () => goToDashboard(school_id, schools),
        });
        return;
      }

      const isVerified = data.user?.verified_status === 'VERIFIED';
      toast(
        isVerified ? '✅ Đăng Ký & Xác Minh Thành Công' : '📝 Đăng Ký Thành Công',
        `Mã định danh của bạn: ${assignedCode}. Đang chuyển vào Dashboard...`,
        'success'
      );
      setTimeout(() => goToDashboard(school_id, schools), 1500);
    } else {
      toast('Đăng Ký Thất Bại', data.detail || 'Vui lòng kiểm tra lại thông tin.', 'error');
    }
  } catch (e) {
    toast('Lỗi Đăng Ký', e.message || 'Không thể hoàn tất đăng ký.', 'error');
  }
}

// ── Login Flow ────────────────────────────────────
export async function doLogin() {
  const selVal = document.getElementById('loginSchoolId')?.value;
  const school_id = (selVal && !isNaN(parseInt(selVal))) ? parseInt(selVal) : (schools[0]?.id || 1);
  const username_or_phone = document.getElementById('loginUser')?.value.trim();
  const password = document.getElementById('loginPass')?.value.trim();

  if (!username_or_phone || !password) {
    toast('Thiếu Thông Tin', 'Vui lòng nhập Tên đăng nhập và Mật khẩu.', 'error');
    return;
  }

  try {
    const data = await login(school_id, username_or_phone, password);
    if (data.status === 'success') {
      localStorage.setItem(AUTH_KEY, data.access_token);
      if (data.user?.role === 'ADMIN' || data.user?.role === 'PLATFORM_ADMIN') {
        localStorage.setItem(ADMIN_TOKEN_KEY, data.access_token);
      }
      if (data.refresh_token) {
        localStorage.setItem('stem_refresh_token', data.refresh_token);
      }
      const finalSchoolId = data.user?.school_id || school_id || 1;
      localStorage.setItem(SCHOOL_ID_KEY, finalSchoolId);
      closeModal('modalLogin');
      toast('🔑 Đăng Nhập Thành Công', `Xin chào ${data.user.full_name}! Đang chuyển hướng...`, 'success');
      checkAuth(schools);
      setTimeout(() => goToDashboard(finalSchoolId, schools), 800);
    } else {
      toast('Đăng Nhập Thất Bại', data.detail || 'Sai thông tin đăng nhập.', 'error');
    }
  } catch (e) {
    toast('Lỗi Kết Nối', e.message || 'Không thể đăng nhập.', 'error');
  }
}

// ── Create School Flow ────────────────────────────
export async function doCreateSchool() {
  const payload = {
    school_code: document.getElementById('csCode')?.value.trim(),
    name: document.getElementById('csName')?.value.trim(),
    address: document.getElementById('csAddress')?.value.trim(),
    province_city: document.getElementById('csProvince')?.value.trim(),
    academic_year: document.getElementById('csYear')?.value,
    headmaster_username: document.getElementById('csHmUser')?.value.trim(),
    headmaster_password: document.getElementById('csHmPass')?.value.trim(),
    headmaster_name: document.getElementById('csHmName')?.value.trim(),
    headmaster_phone: document.getElementById('csHmPhone')?.value.trim(),
  };

  if (!payload.school_code || !payload.name || !payload.headmaster_username || !payload.headmaster_password || !payload.headmaster_name) {
    toast('Thiếu Thông Tin', 'Vui lòng điền đầy đủ tên trường, mã trường và thông tin Hiệu Trưởng.', 'error');
    return;
  }

  try {
    const data = await createSchool(payload);
    if (data.status === 'success') {
      closeModal('modalCreateSchool');
      loadSchools();
      if (localStorage.getItem(ADMIN_TOKEN_KEY)) {
        loadAdminSchools();
        loadAdminStats();
        toast('🏫 Tạo Server Thành Công!', `Đã tạo server: ${payload.name} · Mã mời GV: ${data.invite_codes?.teacher || ''}`, 'success');
      } else {
        localStorage.setItem(AUTH_KEY, data.access_token);
        localStorage.setItem(SCHOOL_ID_KEY, data.school_id);
        toast('🏫 Tạo Server Thành Công!', `Mã mời Giáo Viên: ${data.invite_codes?.teacher || ''} · Đang chuyển vào Dashboard...`, 'success');
        setTimeout(() => goToDashboard(data.school_id, schools), 2000);
      }
    } else {
      toast('Tạo Thất Bại', data.detail || 'Lỗi tạo server trường.', 'error');
    }
  } catch (e) {
    toast('Lỗi Kết Nối', e.message || 'Không thể tạo trường.', 'error');
  }
}

// ── Platform Super Admin Flow ─────────────────────
export async function doPlatformLogin() {
  const username_or_email = document.getElementById('adminUser')?.value.trim();
  const password = document.getElementById('adminPass')?.value.trim();

  if (!username_or_email || !password) {
    toast('Thiếu thông tin', 'Vui lòng nhập tài khoản và mật khẩu Admin.', 'error');
    return;
  }

  try {
    const data = await platformLogin(username_or_email, password);
    if (data.status === 'success') {
      localStorage.setItem(ADMIN_TOKEN_KEY, data.access_token);
      localStorage.setItem(AUTH_KEY, data.access_token);
      if (data.refresh_token) {
        localStorage.setItem('stem_refresh_token', data.refresh_token);
      }
      const sid = (schools && schools.length > 0) ? schools[0].id : 1;
      localStorage.setItem(SCHOOL_ID_KEY, sid);
      closeModal('modalPlatformAdmin');
      toast('👑 Đăng Nhập Admin Thành Công', 'Đang mở Platform Control Center...', 'success');
      checkAuth(schools);
      openAdminDashboard();
    } else {
      toast('Đăng Nhập Thất Bại', data.detail || 'Sai tài khoản hoặc mật khẩu Admin.', 'error');
    }
  } catch (e) {
    toast('Lỗi Kết Nối', e.message || 'Không thể kết nối đến máy chủ.', 'error');
  }
}

export function openAdminDashboard() {
  openModal('modalPlatformDashboard');
  loadAdminStats();
  loadAdminSchools();
}

export async function loadAdminStats() {
  try {
    const s = await getAdminStats();
    const setVal = (id, val) => {
      const el = document.getElementById(id);
      if (el) el.innerText = val || 0;
    };
    setVal('admStatSchools', s.total_schools);
    setVal('admStatStudents', s.total_students);
    setVal('admStatTeachers', s.total_teachers);
    setVal('admStatAttendance', s.today_attendance);
  } catch (e) {
    logoutAdmin();
  }
}

export async function loadAdminSchools() {
  const tbody = document.getElementById('adminSchoolsBody');
  if (!tbody) return;
  try {
    const list = await getAdminSchools();
    if (!list.length) {
      tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;padding:24px;color:var(--muted);">Chưa có trường nào.</td></tr>';
      return;
    }
    tbody.innerHTML = list.map(s => `
      <tr style="border-bottom:1px solid var(--border);">
        <td style="padding:10px 12px;color:var(--muted);">${s.id}</td>
        <td style="padding:10px 12px;"><b>${escHtml(s.name)}</b><br><small style="color:var(--muted);">${escHtml(s.address) || '—'}</small></td>
        <td style="padding:10px 12px;"><code style="color:var(--blue);">${escHtml(s.school_code)}</code></td>
        <td style="padding:10px 12px;">${escHtml(s.province_city) || '—'}</td>
        <td style="padding:10px 12px;font-size:0.8rem;">
          👥 ${s.student_count || 0} HS · 👩‍🏫 ${s.teacher_count || 0} GV · 🎥 ${s.camera_count || 0} Cam
        </td>
        <td style="padding:10px 12px;">
          <span class="chip ${s.status === 'ACTIVE' ? 'chip-green' : 'chip-red'}">${s.status === 'ACTIVE' ? 'Đang Chạy' : 'Tạm Ngưng'}</span>
        </td>
        <td style="padding:10px 12px;">
          <button class="btn btn-sm ${s.status === 'ACTIVE' ? 'btn-outline' : 'btn-primary'}" onclick="toggleSchoolStatus(${s.id}, '${s.status === 'ACTIVE' ? 'SUSPENDED' : 'ACTIVE'}')">
            ${s.status === 'ACTIVE' ? 'Khóa' : 'Kích Hoạt'}
          </button>
          <button class="btn btn-sm btn-primary" onclick="goToDashboard(${s.id})">Vào Trường</button>
        </td>
      </tr>
    `).join('');
  } catch (e) {
    tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;padding:24px;color:var(--red);">Lỗi tải danh sách trường.</td></tr>';
  }
}

export async function toggleSchoolStatus(schoolId, newStatus) {
  try {
    const d = await updateSchoolStatus(schoolId, newStatus);
    toast('✅ Cập nhật', d.message || 'Cập nhật trạng thái thành công', 'success');
    loadAdminSchools();
    loadSchools();
  } catch (e) {
    toast('Lỗi', 'Không thể đổi trạng thái', 'error');
  }
}

export function logoutAdmin() {
  logoutAll();
}

// ── Global Scope Binding (Ensures inline HTML onclick attributes work seamlessly) ──
window.loadSchools = loadSchools;
window.searchSchools = searchSchools;
window.openRegisterModal = openRegisterModal;
window.switchToRegisterFromLogin = switchToRegisterFromLogin;
window.onJoinSchoolSelect = onJoinSchoolSelect;
window.openJoinModal = openJoinModal;
window.doJoinSchool = doJoinSchool;
window.doLogin = doLogin;
window.doCreateSchool = doCreateSchool;
window.doPlatformLogin = doPlatformLogin;
window.openAdminDashboard = openAdminDashboard;
window.loadAdminStats = loadAdminStats;
window.loadAdminSchools = loadAdminSchools;
window.toggleSchoolStatus = toggleSchoolStatus;
window.logoutAdmin = logoutAdmin;
window.renderDynamicFields = () => renderDynamicFields(currentJoinSchool);

// ── Initialize App on DOM Ready ───────────────────
window.addEventListener('DOMContentLoaded', () => {
  loadSchools();
  checkAuth(schools);
});
