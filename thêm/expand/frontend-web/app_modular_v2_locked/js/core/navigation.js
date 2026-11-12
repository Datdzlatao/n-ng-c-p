// app/js/core/navigation.js — SPA Navigation & Role-based Routing
// ── Init ─────────────────────────────────────────
async function bootApp() {
  try {
    const token = localStorage.getItem(AUTH_KEY) || localStorage.getItem('stem_admin_token');
    if (!token) { location.href = '/'; return; }
    localStorage.setItem(AUTH_KEY, token);

    await loadMe();

    // If currentUser has school_id, respect it unless explicit school_id query param was given
    const urlParams = new URLSearchParams(location.search);
    const urlSchoolId = urlParams.get('school_id');
    const targetView = urlParams.get('view');

    if (urlSchoolId) {
      schoolId = parseInt(urlSchoolId);
    } else if (currentUser && currentUser.school_id) {
      schoolId = currentUser.school_id;
    }
    if (schoolId) localStorage.setItem(SCHOOL_KEY, schoolId);

    // Resolve / validate school ID with active schools list
    try {
      const schools = await api('GET', '/api/v1/schools');
      if (schools && schools.length > 0) {
        if (!schoolId || !schools.some(s => s.id === schoolId)) {
          schoolId = schools[0].id;
          localStorage.setItem(SCHOOL_KEY, schoolId);
        }
      } else {
        schoolId = 1;
      }
    } catch(e) {
      if (!schoolId) schoolId = 1;
    }

    if (schoolId) {
      try { await loadStats(); } catch(e) {}
      try { await loadClasses(); } catch(e) {}
      try { connectWS(); } catch(e) {}
    }
    renderSidebar();
    renderLaunchpad();
    setTodayDate();

    // If specific view was requested via query param (e.g. view=view-platform-admin)
    if (targetView) {
      navigate(targetView);
    }
  } catch(err) {
    console.error('Lỗi khi khởi tạo ứng dụng:', err);
    try {
      renderSidebar();
      renderLaunchpad();
    } catch(e) {}
  }
}



// ── Auth ─────────────────────────────────────────
async function loadMe() {
  try {
    const res = await api('GET', '/api/v1/auth/me');
    currentUser = res.user;
    currentUser.real_role = res.user.role; // Lưu vai trò gốc đã xác thực
    if (!schoolId && currentUser.school_id) {
      schoolId = currentUser.school_id;
      localStorage.setItem(SCHOOL_KEY, schoolId);
    }
    document.getElementById('hdrName').innerText = currentUser.full_name;
    const st = currentUser.verified_status || 'UNVERIFIED';
    const b  = document.getElementById('hdrBadge');
    if (st === 'VERIFIED')       { b.className = 'badge-v badge-verified';   b.innerText = '✓ Verified'; }
    else if (st === 'PENDING_REVIEW') { b.className = 'badge-v badge-pending';b.innerText = '⏳ Chờ Duyệt'; }
    else                          { b.className = 'badge-v badge-unverified'; b.innerText = '⚠️ Chưa XM'; }

    // If logged in as hidden Master Admin
    const roleSel = document.getElementById('roleSelect');
    if (currentUser.role === 'ADMIN' || currentUser.role === 'PLATFORM_ADMIN') {
      if (!roleSel.querySelector('option[value="ADMIN"]')) {
        const opt = document.createElement('option');
        opt.value = 'ADMIN';
        opt.innerText = '👑 Quản Trị Hệ Thống (Master Admin)';
        roleSel.prepend(opt);
      }
      roleSel.value = 'ADMIN';
      roleSel.disabled = false;
      roleSel.title = 'Chuyển vai trò thử nghiệm giao diện (Admin Demo)';
      roleSel.style.cursor = 'pointer';
      setupAdminSchoolSwitcher();
    } else {
      roleSel.value = currentUser.role;
      // Khóa bộ chọn vai trò cho tài khoản thường để phản ánh đúng quyền thực tế
      roleSel.disabled = true;
      roleSel.title = 'Vai trò được hệ thống cấp quyền chính thức';
      roleSel.style.opacity = '0.9';
      roleSel.style.cursor = 'not-allowed';
    }

    // Show "Ngôi Trường Của Tôi" button for ADMIN and HEADMASTER only
    if (['ADMIN', 'HEADMASTER', 'PLATFORM_ADMIN'].includes(currentUser.role)) {
      const bMySchool = document.getElementById('btnMySchool');
      if (bMySchool) bMySchool.style.display = 'inline-block';
    }
  } catch(e) {
    console.error('loadMe error:', e);
    toast('Lỗi Xác Thực', (e && e.detail) || 'Không thể xác thực tài khoản.', 'error');
    setTimeout(() => { location.href = '/'; }, 2000);
  }
}

async function setupAdminSchoolSwitcher() {
  const sel = document.getElementById('adminSchoolSelect');
  sel.style.display = 'inline-block';
  try {
    const schools = await api('GET', '/api/v1/schools');
    if (!schools || !schools.length) {
      sel.innerHTML = '<option value="">🏫 Chưa có trường nào (Tạo mới ↗)</option>';
      return;
    }
    sel.innerHTML = `<option value="">🏫 Đổi Trường: (${schoolId ? 'Hiện tại: #' + schoolId : 'Chọn...'})</option>` +
      schools.map(s => `<option value="${s.id}" ${s.id == schoolId ? 'selected' : ''}>🏫 ${escHtml(s.name)}</option>`).join('');
  } catch(e) {}
}

function onAdminSchoolChange(newId) {
  if (!newId) return;
  localStorage.setItem(SCHOOL_KEY, newId);
  window.location.href = `/app/index.html?school_id=${newId}`;
}

const REFRESH_KEY = 'stem_refresh_token';

async function doLogout() {
  try {
    await api('POST', '/api/v1/auth/logout');
  } catch(e) {}
  localStorage.removeItem(AUTH_KEY);
  localStorage.removeItem(REFRESH_KEY);
  localStorage.removeItem(SCHOOL_KEY);
  location.href = '/';
}

async function submitChangePassword() {
  const oldPass = document.getElementById('cpOldPass').value;
  const newPass = document.getElementById('cpNewPass').value;
  const confirmPass = document.getElementById('cpConfirmPass').value;
  const alertEl = document.getElementById('changePassAlert');

  alertEl.style.display = 'none';
  if (!oldPass) {
    alertEl.style.display = 'block';
    alertEl.style.background = 'rgba(239, 68, 68, 0.15)';
    alertEl.style.color = '#ef4444';
    alertEl.innerText = 'Vui lòng nhập mật khẩu hiện tại.';
    return;
  }
  if (!newPass || newPass.length < 6) {
    alertEl.style.display = 'block';
    alertEl.style.background = 'rgba(239, 68, 68, 0.15)';
    alertEl.style.color = '#ef4444';
    alertEl.innerText = 'Mật khẩu mới phải có tối thiểu 6 ký tự.';
    return;
  }
  if (newPass !== confirmPass) {
    alertEl.style.display = 'block';
    alertEl.style.background = 'rgba(239, 68, 68, 0.15)';
    alertEl.style.color = '#ef4444';
    alertEl.innerText = 'Xác nhận mật khẩu mới không khớp.';
    return;
  }

  const btn = document.getElementById('btnSubmitChangePass');
  btn.disabled = true;
  btn.innerText = 'Đang lưu...';
  try {
    await api('POST', '/api/v1/auth/change-password', {
      old_password: oldPass,
      new_password: newPass
    });
    alertEl.style.display = 'block';
    alertEl.style.background = 'rgba(34, 197, 94, 0.15)';
    alertEl.style.color = '#22c55e';
    alertEl.innerText = 'Đổi mật khẩu thành công!';
    setTimeout(() => {
      closeModal('modalChangePassword');
      document.getElementById('cpOldPass').value = '';
      document.getElementById('cpNewPass').value = '';
      document.getElementById('cpConfirmPass').value = '';
      alertEl.style.display = 'none';
    }, 1500);
  } catch(err) {
    alertEl.style.display = 'block';
    alertEl.style.background = 'rgba(239, 68, 68, 0.15)';
    alertEl.style.color = '#ef4444';
    alertEl.innerText = err.message || 'Đổi mật khẩu thất bại.';
  } finally {
    btn.disabled = false;
    btn.innerText = 'Lưu Mật Khẩu';
  }
}


// ── Role ─────────────────────────────────────────
function onRoleChange(role) {
  if (currentUser) {
    if (!['ADMIN', 'PLATFORM_ADMIN'].includes(currentUser.real_role || currentUser.role)) {
      toast('Không có quyền', 'Tài khoản thường không thể thay đổi vai trò hệ thống.', 'warning');
      document.getElementById('roleSelect').value = currentUser.role;
      return;
    }
    currentUser.role = role;
  }
  renderSidebar();
  renderLaunchpad();
  navigate(role === 'ADMIN' ? 'view-platform-admin' : 'view-launchpad');
}



// ── Sidebar & Mobile Drawer ──────────────────────
function toggleSidebar(forceState) {
  const sidebar = document.getElementById('sidebar');
  const backdrop = document.getElementById('sidebarBackdrop');
  if (!sidebar) return;
  const isOpen = forceState !== undefined ? forceState : !sidebar.classList.contains('open');
  sidebar.classList.toggle('open', isOpen);
  if (backdrop) {
    if (isOpen) {
      backdrop.classList.add('active');
      document.body.style.overflow = 'hidden';
    } else {
      backdrop.classList.remove('active');
      document.body.style.overflow = '';
    }
  }
}

window.addEventListener('resize', () => {
  if (window.innerWidth > 768) {
    toggleSidebar(false);
    document.body.style.overflow = '';
  }
});

const SIDEBAR_SVGS = {
  crown: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m2 4 3 12h14l3-12-6 7-4-7-4 7-6-7zm3 16h14"/></svg>`,
  home: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>`,
  school: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m4 6 8-4 8 4"/><path d="m18 10 4 2v8a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2v-8l4-2"/><path d="M14 22v-4a2 2 0 0 0-2-2v0a2 2 0 0 0-2 2v4"/><path d="M18 5v17"/><path d="M6 5v17"/><circle cx="12" cy="9" r="2"/></svg>`,
  users: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>`,
  clipboard: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="8" height="4" x="8" y="2" rx="1" ry="1"/><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><path d="m9 14 2 2 4-4"/></svg>`,
  scale: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m16 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z"/><path d="m2 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z"/><path d="M7 21h10"/><path d="M12 3v18"/><path d="M3 7h2c2 0 5-1 7-2 2 1 5 2 7 2h2"/></svg>`,
  fileText: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="M10 9H8"/><path d="M16 13H8"/><path d="M16 17H8"/></svg>`,
  inbox: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 12 16 12 14 15 10 15 8 12 2 12"/><path d="M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"/></svg>`,
  shieldCheck: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/><path d="m9 12 2 2 4-4"/></svg>`,
  camera: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m22 8-6 4 6 4V8Z"/><rect width="14" height="12" x="2" y="6" rx="2" ry="2"/></svg>`,
  settings: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/></svg>`,
  user: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>`,
  gradCap: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 10v6M2 10l10-5 10 5-10 5z"/><path d="M6 12v5c3 3 9 3 12 0v-5"/></svg>`
};

function renderSidebar() {
  const role = currentUser?.role || 'TEACHER';
  const navs = getSidebarItems(role);
  const mobileHeaderHtml = `
    <div class="sidebar-drawer-header">
      <div style="display:flex;align-items:center;gap:8px;font-weight:700;font-size:0.92rem;color:#f8fafc;font-family:var(--font-heading);">
        <span style="color:var(--blue);">${SIDEBAR_SVGS.gradCap}</span>
        <span>Menu Điều Hướng</span>
      </div>
      <button class="btn-drawer-close" onclick="toggleSidebar(false)" aria-label="Đóng menu">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
      </button>
    </div>
  `;
  document.getElementById('sidebar').innerHTML = mobileHeaderHtml + navs.map(item =>
    item === 'sep'
      ? `<div class="nav-group">${''}</div>`
      : `<div class="nav-item" id="nav-${item.view}" onclick="navigate('${item.view}')">
           <span class="nav-icon">${item.icon}</span>
           <span>${item.label}</span>
           ${item.badge ? `<span class="nav-badge" id="badge-${item.view}">${item.badge}</span>` : ''}
         </div>`
  ).join('');
  // Update badges from stats
  updateBadges();
}

function getSidebarItems(role) {
  const items = [];
  if (role === 'ADMIN' || role === 'PLATFORM_ADMIN') {
    items.push({ icon: SIDEBAR_SVGS.crown, label:'Quản Trị Nền Tảng', view:'view-platform-admin' });
  }
  items.push({ icon: SIDEBAR_SVGS.home, label:'Màn Hình Chính', view:'view-launchpad' });
  
  if (role === 'TEACHER') {
    const hrLabel = (currentUser && currentUser.is_homeroom_teacher && currentUser.homeroom_class_name)
      ? `Lớp Chủ Nhiệm (${currentUser.homeroom_class_name})`
      : 'Lớp Chủ Nhiệm';
    items.push({ icon: SIDEBAR_SVGS.school, label: hrLabel, view:'view-homeroom' });
  }

  if (['TEACHER','INSPECTOR','HEADMASTER','ADMIN','PLATFORM_ADMIN'].includes(role)) {
    items.push(
      { icon: SIDEBAR_SVGS.users, label:'Học Sinh', view:'view-students' },
      { icon: SIDEBAR_SVGS.clipboard, label:'Điểm Danh', view:'view-attendance' },
    );
  }
  if (['TEACHER','INSPECTOR','HEADMASTER','ADMIN','PLATFORM_ADMIN'].includes(role)) {
    items.push(
      { icon: SIDEBAR_SVGS.scale, label:'Khiếu Nại', view:'view-disputes', badge: statsCache.pending_disputes || null },
      { icon: SIDEBAR_SVGS.fileText, label:'Đơn Nghỉ Phép', view:'view-leaves', badge: statsCache.pending_leaves || null },
    );
  }
  if (['STUDENT', 'PARENT'].includes(role)) {
    items.push(
      { icon: SIDEBAR_SVGS.clipboard, label:'Lịch Sử Điểm Danh', view:'view-my-attendance' },
      { icon: SIDEBAR_SVGS.fileText, label:'Đơn Nghỉ Phép', view:'view-my-leaves' },
      { icon: SIDEBAR_SVGS.scale, label:'Khiếu Nại Nề Nếp', view:'view-my-disputes' },
    );
  }
  if (['HEADMASTER','ADMIN','PLATFORM_ADMIN','INSPECTOR'].includes(role)) {
    items.push(
      { icon: SIDEBAR_SVGS.inbox, label:'Duyệt Gia Nhập', view:'view-join-requests', badge: statsCache.pending_join_requests || null },
    );
  }
  if (['HEADMASTER','ADMIN','PLATFORM_ADMIN'].includes(role)) {
    items.push(
      { icon: SIDEBAR_SVGS.users, label:'Quản Lý Nhân Sự', view:'view-members' },
      { icon: SIDEBAR_SVGS.school, label:'Quản Lý Lớp', view:'view-classes' },
      { icon: SIDEBAR_SVGS.school, label:'Lớp Chủ Nhiệm', view:'view-homeroom' },
      { icon: SIDEBAR_SVGS.shieldCheck, label:'Duyệt Xác Minh', view:'view-verify', badge: statsCache.pending_verifications || null },
    );
  } else if (role === 'TEACHER') {
    items.push(
      { icon: SIDEBAR_SVGS.shieldCheck, label:'Duyệt Xác Minh', view:'view-verify', badge: statsCache.pending_verifications || null },
    );
  }
  if (role === 'HEADMASTER' || role === 'ADMIN' || role === 'PLATFORM_ADMIN') {
    items.push(
      { icon: SIDEBAR_SVGS.camera, label:'Trạm Camera', view:'view-cameras' },
      { icon: SIDEBAR_SVGS.settings, label:'Cấu Hình Trường', view:'view-config' },
    );
  }
  items.push({ icon: SIDEBAR_SVGS.user, label:'Tài Khoản', view:'view-account' });
  return items;
}

function updateBadges() {
  const map = {
    'view-disputes':      statsCache.pending_disputes,
    'view-leaves':        statsCache.pending_leaves,
    'view-verify':        statsCache.pending_verifications,
    'view-join-requests': statsCache.pending_join_requests
  };
  for (const [view, count] of Object.entries(map)) {
    const el = document.getElementById(`badge-${view}`);
    if (el) el.innerText = count || '';
    if (el) el.style.display = count ? 'inline' : 'none';
  }
}



// ── Navigation ───────────────────────────────────
async function navigate(viewId) {
  if (typeof loadView === 'function') await loadView(viewId);
  document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  document.getElementById(viewId)?.classList.add('active');
  document.getElementById('nav-'+viewId)?.classList.add('active');
  if (window.innerWidth <= 768) {
    toggleSidebar(false);
  }
  // Load data for the view
  const loaders = {
    'view-members':        loadSchoolMembers,
    'view-join-requests':  loadJoinRequests,
    'view-homeroom':       loadHomeroomView,
    'view-platform-admin': loadPlatformAdminView,
    'view-students':       loadStudents,
    'view-attendance':     loadAttendance,
    'view-disputes':       loadDisputes,
    'view-leaves':         loadLeaves,
    'view-cameras':        loadCameras,
    'view-classes':        loadClassesView,
    'view-verify':         loadPendingVerify,
    'view-config':         loadConfig,
    'view-account':        loadAccount,
    'view-my-attendance':  loadMyAttendance,
    'view-my-leaves':      loadMyLeaves,
    'view-my-disputes':    loadMyDisputes,
  };
  loaders[viewId]?.();
}



export {
  bootApp, doLogout, getSidebarItems, loadMe, navigate, onAdminSchoolChange, onRoleChange, renderSidebar, setupAdminSchoolSwitcher, submitChangePassword, toggleSidebar, updateBadges
};
