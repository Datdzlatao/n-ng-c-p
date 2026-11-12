/**
 * js/components/schoolRenderer.js — UI Component Renderers for Schools
 */
import { escHtml } from '../utils/helpers.js';

export function renderSchoolCards(list, containerId = 'schoolGrid') {
  const grid = document.getElementById(containerId);
  if (!grid) return;

  if (!list || !list.length) {
    grid.innerHTML = '<div style="color:var(--muted); grid-column:1/-1; text-align:center; padding:40px;">Không tìm thấy trường học phù hợp.</div>';
    return;
  }

  grid.innerHTML = list.map(s => `
    <div class="school-card" onclick="openJoinModal(${s.id})">
      <div class="school-name">${escHtml(s.name)}</div>
      <div class="school-meta">
        <span>🏷️ Mã: <code style="color:var(--blue)">${escHtml(s.school_code)}</code></span>
        ${s.address ? `<span>📍 ${escHtml(s.address)}</span>` : ''}
        ${s.province_city ? `<span>🗺️ ${escHtml(s.province_city)}</span>` : ''}
        <span>📅 Năm học ${escHtml(s.academic_year)}</span>
      </div>
      <div>
        <span class="school-badge badge-active">✓ Đang Hoạt Động</span>
      </div>
      <div class="school-actions" onclick="event.stopPropagation()">
        <button class="btn btn-primary btn-sm" onclick="openJoinModal(${s.id})">📝 Đăng Ký</button>
        <button class="btn btn-outline btn-sm" onclick="goToDashboard(${s.id})">🚀 Vào Dashboard</button>
      </div>
    </div>
  `).join('');
}

export function populateLoginSchools(list) {
  const loginSel = document.getElementById('loginSchoolId');
  const joinSel = document.getElementById('joinSchoolSelect');

  const optionsHtml = (list && list.length > 0)
    ? list.map(s => `<option value="${s.id}">${escHtml(s.name)}</option>`).join('')
    : '<option value="" disabled>Chưa có trường nào hoạt động</option>';

  if (loginSel) loginSel.innerHTML = optionsHtml;
  if (joinSel) joinSel.innerHTML = optionsHtml;
}

export function renderDynamicFields(currentJoinSchool) {
  if (!currentJoinSchool) return;
  const role = document.getElementById('joinRole')?.value || 'STUDENT';
  const formCfg = currentJoinSchool.form_config || {};
  const roleCfg = formCfg[role.toLowerCase()] || {};
  let html = '';

  if (role === 'STUDENT') {
    html += `<div class="dynamic-fields" style="background:rgba(79,142,247,0.08);border:1px solid rgba(79,142,247,0.25);border-radius:10px;padding:12px 14px;margin-bottom:12px;">
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:4px;">
        <span style="font-weight:700;color:var(--blue);font-size:0.88rem;">✨ Mã Học Sinh (Mã HS)</span>
        <span class="chip chip-blue" style="font-size:0.68rem;font-weight:700;">HỆ THỐNG TỰ ĐỘNG CẤP</span>
      </div>
      <p style="font-size:0.78rem;color:var(--muted);margin:0;line-height:1.4;">
        Bạn không cần tự tạo mã. Hệ thống sẽ tự cấp mã chuẩn riêng (ví dụ: <strong style="color:var(--text)">HS01-0001</strong>) và kích hoạt FaceID ngay sau khi đăng ký.
      </p>
      ${roleCfg.require_dob ? `<div class="form-group" style="margin-top:10px;"><label>Ngày Sinh <span class="required">*</span></label><input id="joinDob" type="date"></div>` : ''}
    </div>`;
  } else if (role === 'PARENT') {
    html += `<div class="dynamic-fields" style="background:rgba(34,197,94,0.08);border:1px solid rgba(34,197,94,0.25);border-radius:10px;padding:12px 14px;margin-bottom:12px;">
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:4px;">
        <span style="font-weight:700;color:var(--green);font-size:0.88rem;">👨‍👩‍👧 Mã Phụ Huynh (Mã PH)</span>
        <span class="chip chip-green" style="font-size:0.68rem;font-weight:700;">HỆ THỐNG TỰ ĐỘNG CẤP</span>
      </div>
      <p style="font-size:0.78rem;color:var(--muted);margin-bottom:10px;line-height:1.4;">
        Tài khoản phụ huynh sẽ tự động nhận mã riêng (ví dụ: <strong style="color:var(--text)">PH01-0001</strong>).
      </p>
      <div class="form-group">
        <label>Mã Học Sinh của con (Tùy chọn)</label>
        <input id="joinStudentCode" type="text" placeholder="Ví dụ: HS01-0001">
        <small style="color:var(--muted); font-size:0.78rem;">Nếu chưa biết mã của con, bạn có thể để trống và liên kết sau.</small>
      </div>
    </div>`;
  } else if (role === 'TEACHER') {
    html += `<div class="dynamic-fields" style="background:rgba(168,85,247,0.08);border:1px solid rgba(168,85,247,0.25);border-radius:10px;padding:12px 14px;margin-bottom:12px;">
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:4px;">
        <span style="font-weight:700;color:var(--purple);font-size:0.88rem;">👩‍🏫 Mã Giáo Viên (Mã GV)</span>
        <span class="chip chip-purple" style="font-size:0.68rem;font-weight:700;">HỆ THỐNG TỰ ĐỘNG CẤP</span>
      </div>
      <p style="font-size:0.78rem;color:var(--muted);margin-bottom:10px;line-height:1.4;">
        Tài khoản Giáo viên sẽ được tự động cấp mã định danh giáo viên (ví dụ: <strong style="color:var(--text)">GV01-0001</strong>).
      </p>
      <div class="form-group">
        <label>Mã Mời Giáo Viên <span class="required">*</span></label>
        <input id="joinInviteCode" type="text" placeholder="GV_TRUONG_XXXX">
        <small style="color:var(--muted); font-size:0.78rem;">Nhận mã mời từ Ban Giám Hiệu nhà trường.</small>
      </div>
    </div>`;
  } else if (role === 'INSPECTOR') {
    html += `<div class="dynamic-fields" style="background:rgba(245,158,11,0.08);border:1px solid rgba(245,158,11,0.25);border-radius:10px;padding:12px 14px;margin-bottom:12px;">
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:4px;">
        <span style="font-weight:700;color:var(--amber);font-size:0.88rem;">👮 Mã Giám Thị (Mã GT)</span>
        <span class="chip chip-amber" style="font-size:0.68rem;font-weight:700;">HỆ THỐNG TỰ ĐỘNG CẤP</span>
      </div>
      <p style="font-size:0.78rem;color:var(--muted);margin-bottom:10px;line-height:1.4;">
        Tài khoản Giám thị sẽ được tự động cấp mã định danh (ví dụ: <strong style="color:var(--text)">GT01-0001</strong>).
      </p>
      <div class="form-group">
        <label>Mã Mời Giám Thị <span class="required">*</span></label>
        <input id="joinInviteCode" type="text" placeholder="GT_TRUONG_XXXX">
      </div>
    </div>`;
  } else if (role === 'HEADMASTER') {
    html += `<div class="dynamic-fields" style="background:rgba(239,68,68,0.08);border:1px solid rgba(239,68,68,0.25);border-radius:10px;padding:12px 14px;margin-bottom:12px;">
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:4px;">
        <span style="font-weight:700;color:var(--red);font-size:0.88rem;">👑 Mã Ban Giám Hiệu (Mã HT)</span>
        <span class="chip chip-red" style="font-size:0.68rem;font-weight:700;">HỆ THỐNG TỰ ĐỘNG CẤP</span>
      </div>
      <p style="font-size:0.78rem;color:var(--muted);margin-bottom:10px;line-height:1.4;">
        Tài khoản BGH sẽ được tự động cấp mã định danh lãnh đạo (ví dụ: <strong style="color:var(--text)">HT01-0001</strong>).
      </p>
      <div class="form-group">
        <label>Mã Mời Ban Giám Hiệu <span class="required">*</span></label>
        <input id="joinInviteCode" type="text" placeholder="BGH_TRUONG_XXXX">
      </div>
    </div>`;
  }

  const container = document.getElementById('dynamicFields');
  if (container) container.innerHTML = html;
}
