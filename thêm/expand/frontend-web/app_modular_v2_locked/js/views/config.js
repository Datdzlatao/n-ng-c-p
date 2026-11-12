// app/js/views/config.js — School Schedule, Rules & Gemini AI Parser
// ── Config ────────────────────────────────────────
async function loadConfig() {
  try {
    const school = await api('GET', `/api/v1/schools/${schoolId}`);
    const fc = school.form_config || {};
    const rc = school.rules_config || {};
    const sc = fc.student || {};
    const pc = fc.parent  || {};
    const tc = fc.teacher || {};

    document.getElementById('formConfigToggles').innerHTML = [
      { label:'Học Sinh: Bắt buộc Mã Học Sinh', desc:'Dùng để auto-match danh bộ', id:'fc_stu_code', val: sc.require_student_code },
      { label:'Học Sinh: Bắt buộc SĐT Phụ Huynh', desc:'Xác minh chính chủ qua SĐT', id:'fc_stu_phone', val: sc.require_phone },
      { label:'Học Sinh: Bắt buộc Ảnh Khuôn Mặt AI', desc:'Dùng cho nhận diện camera', id:'fc_stu_face', val: sc.require_face_photo },
      { label:'Phụ Huynh: Bắt buộc SĐT', desc:'Liên kết phụ huynh với học sinh', id:'fc_par_phone', val: pc.require_phone },
      { label:'Giáo Viên: Bắt buộc Mã Mời', desc:'Ngăn đăng ký giả mạo vai trò GV', id:'fc_tea_invite', val: tc.require_invite_code },
    ].map(f => `
      <div class="config-row">
        <div><div class="config-label">${f.label}</div><div class="config-desc">${f.desc}</div></div>
        <label class="toggle"><input type="checkbox" id="${f.id}" ${f.val?'checked':''}><span class="toggle-slider"></span></label>
      </div>`).join('');

    // Rules — Tải cấu hình 3 ca: Sáng, Chiều, Tối & Nề nếp
    // 🌅 Buổi Sáng
    const mFrom = rc.morning_from || rc.checkin_from || '06:00';
    const mOnTime = rc.morning_on_time || rc.checkin_on_time_until || '07:15';
    const mLate = rc.morning_late_until || rc.checkin_late_until || '07:30';
    const mCheckout = rc.morning_checkout || '11:30';
    const mEnabled = rc.morning_enabled !== false;
    const mName = rc.morning_name || 'Chính khóa buổi sáng';
    const mUniformCheck = rc.morning_uniform_check !== undefined ? rc.morning_uniform_check : (rc.uniform_check !== false);
    const mLateDeduct = rc.morning_late_deduct !== undefined ? rc.morning_late_deduct : (rc.late_deduct_points || 2);
    const mNotify = rc.morning_notify_parent !== false;
    const mAuthMode = rc.morning_auth_mode || 'ALL';

    if (document.getElementById('cfgMorningFrom')) document.getElementById('cfgMorningFrom').value = mFrom;
    if (document.getElementById('cfgMorningOnTime')) document.getElementById('cfgMorningOnTime').value = mOnTime;
    if (document.getElementById('cfgMorningLate')) document.getElementById('cfgMorningLate').value = mLate;
    if (document.getElementById('cfgMorningCheckout')) document.getElementById('cfgMorningCheckout').value = mCheckout;
    if (document.getElementById('cfgMorningEnabled')) document.getElementById('cfgMorningEnabled').checked = mEnabled;
    if (document.getElementById('cfgMorningName')) document.getElementById('cfgMorningName').value = mName;
    if (document.getElementById('cfgMorningLateD')) document.getElementById('cfgMorningLateD').value = mLateDeduct;
    if (document.getElementById('cfgMorningAuthMode')) document.getElementById('cfgMorningAuthMode').value = mAuthMode;
    if (document.getElementById('cfgMorningUniformCheck')) document.getElementById('cfgMorningUniformCheck').checked = mUniformCheck;
    if (document.getElementById('cfgMorningNotify')) document.getElementById('cfgMorningNotify').checked = mNotify;

    // ☀️ Buổi Chiều
    const aFrom = rc.afternoon_from || '12:30';
    const aOnTime = rc.afternoon_on_time || '13:15';
    const aLate = rc.afternoon_late_until || '13:30';
    const aCheckout = rc.afternoon_checkout || rc.checkout_from || '17:00';
    const aEnabled = rc.afternoon_enabled !== false;
    const aName = rc.afternoon_name || 'Buổi 2 / Ngoại khóa';
    const aUniformCheck = rc.afternoon_uniform_check !== undefined ? rc.afternoon_uniform_check : (rc.uniform_check !== false);
    const aLateDeduct = rc.afternoon_late_deduct !== undefined ? rc.afternoon_late_deduct : (rc.late_deduct_points || 2);
    const aNotify = rc.afternoon_notify_parent !== false;
    const aAuthMode = rc.afternoon_auth_mode || 'ALL';

    if (document.getElementById('cfgAfternoonFrom')) document.getElementById('cfgAfternoonFrom').value = aFrom;
    if (document.getElementById('cfgAfternoonOnTime')) document.getElementById('cfgAfternoonOnTime').value = aOnTime;
    if (document.getElementById('cfgAfternoonLate')) document.getElementById('cfgAfternoonLate').value = aLate;
    if (document.getElementById('cfgAfternoonCheckout')) document.getElementById('cfgAfternoonCheckout').value = aCheckout;
    if (document.getElementById('cfgAfternoonEnabled')) document.getElementById('cfgAfternoonEnabled').checked = aEnabled;
    if (document.getElementById('cfgAfternoonName')) document.getElementById('cfgAfternoonName').value = aName;
    if (document.getElementById('cfgAfternoonLateD')) document.getElementById('cfgAfternoonLateD').value = aLateDeduct;
    if (document.getElementById('cfgAfternoonAuthMode')) document.getElementById('cfgAfternoonAuthMode').value = aAuthMode;
    if (document.getElementById('cfgAfternoonUniformCheck')) document.getElementById('cfgAfternoonUniformCheck').checked = aUniformCheck;
    if (document.getElementById('cfgAfternoonNotify')) document.getElementById('cfgAfternoonNotify').checked = aNotify;

    // 🌙 Buổi Tối (Tự học / Nội trú)
    const eFrom = rc.evening_from || '18:00';
    const eOnTime = rc.evening_on_time || '18:45';
    const eLate = rc.evening_late_until || '19:15';
    const eCheckout = rc.evening_checkout || '21:30';
    const eEnabled = rc.evening_enabled === true;
    const eName = rc.evening_name || 'Tự học / Nội trú';
    const eUniformCheck = rc.evening_uniform_check === true;
    const eLateDeduct = rc.evening_late_deduct !== undefined ? rc.evening_late_deduct : 1;
    const eNotify = rc.evening_notify_parent !== false;
    const eAuthMode = rc.evening_auth_mode || 'ALL';

    if (document.getElementById('cfgEveningFrom')) document.getElementById('cfgEveningFrom').value = eFrom;
    if (document.getElementById('cfgEveningOnTime')) document.getElementById('cfgEveningOnTime').value = eOnTime;
    if (document.getElementById('cfgEveningLate')) document.getElementById('cfgEveningLate').value = eLate;
    if (document.getElementById('cfgEveningCheckout')) document.getElementById('cfgEveningCheckout').value = eCheckout;
    if (document.getElementById('cfgEveningEnabled')) document.getElementById('cfgEveningEnabled').checked = eEnabled;
    if (document.getElementById('cfgEveningName')) document.getElementById('cfgEveningName').value = eName;
    if (document.getElementById('cfgEveningLateD')) document.getElementById('cfgEveningLateD').value = eLateDeduct;
    if (document.getElementById('cfgEveningAuthMode')) document.getElementById('cfgEveningAuthMode').value = eAuthMode;
    if (document.getElementById('cfgEveningUniformCheck')) document.getElementById('cfgEveningUniformCheck').checked = eUniformCheck;
    if (document.getElementById('cfgEveningNotify')) document.getElementById('cfgEveningNotify').checked = eNotify;

    // Đồng bộ legacy inputs
    if (document.getElementById('cfgFrom')) document.getElementById('cfgFrom').value = mFrom;
    if (document.getElementById('cfgOnTime')) document.getElementById('cfgOnTime').value = mOnTime;
    if (document.getElementById('cfgLate')) document.getElementById('cfgLate').value = mLate;

    if (rc.late_deduct_points && document.getElementById('cfgLateD')) document.getElementById('cfgLateD').value = rc.late_deduct_points;
    if (rc.violation_deduct_points && document.getElementById('cfgUniformD')) document.getElementById('cfgUniformD').value = rc.violation_deduct_points;
    if (document.getElementById('cfgUniformCheck')) {
      document.getElementById('cfgUniformCheck').checked = (rc.uniform_check !== false);
    }

    // Invite codes (only show to headmaster)
    if (currentUser?.role === 'HEADMASTER') {
      const codes = await api('PUT', `/api/v1/schools/${schoolId}/config/codes`).catch(() => ({ invite_codes: {} }));
      // Actually just display current codes from school object
      document.getElementById('inviteCodes').innerHTML = [
        { label:'👩‍🏫 Giáo Viên', key:'teacher',   code: school.teacher_invite_code   },
        { label:'👮 Giám Thị', key:'inspector', code: school.inspector_invite_code },
        { label:'👑 Ban Giám Hiệu', key:'bgh', code: school.bgh_invite_code       },
      ].map(c => `
        <div style="background:var(--overlay);border-radius:8px;padding:12px;">
          <div style="font-weight:700;font-size:0.8rem;margin-bottom:6px;">${c.label}</div>
          <code style="font-size:0.78rem;color:var(--blue);word-break:break-all">${c.code||'—'}</code>
        </div>`).join('');
    }
  } catch(e) { console.error(e); }
}

async function saveFormConfig() {
  const g = id => document.getElementById(id)?.checked;
  const payload = {
    student_require_student_code: g('fc_stu_code'),
    student_require_phone:        g('fc_stu_phone'),
    student_require_face_photo:   g('fc_stu_face'),
    parent_require_phone:         g('fc_par_phone'),
    teacher_require_invite_code:  g('fc_tea_invite'),
    parent_require_student_link:  true,
  };
  try {
    await api('PUT', `/api/v1/schools/${schoolId}/config/form`, payload);
    toast('💾 Đã Lưu', 'Cấu hình form đăng ký đã được cập nhật.', 'success');
  } catch(e) { toast('Lỗi', e.detail||'', 'error'); }
}

async function saveRulesConfig() {
  const mFrom = document.getElementById('cfgMorningFrom')?.value || document.getElementById('cfgFrom')?.value || '06:00';
  const mOnTime = document.getElementById('cfgMorningOnTime')?.value || document.getElementById('cfgOnTime')?.value || '07:15';
  const mLate = document.getElementById('cfgMorningLate')?.value || document.getElementById('cfgLate')?.value || '07:30';
  const mCheckout = document.getElementById('cfgMorningCheckout')?.value || '11:30';
  const mEnabled = document.getElementById('cfgMorningEnabled') ? document.getElementById('cfgMorningEnabled').checked : true;

  const aFrom = document.getElementById('cfgAfternoonFrom')?.value || '12:30';
  const aOnTime = document.getElementById('cfgAfternoonOnTime')?.value || '13:15';
  const aLate = document.getElementById('cfgAfternoonLate')?.value || '13:30';
  const aCheckout = document.getElementById('cfgAfternoonCheckout')?.value || '17:00';
  const aEnabled = document.getElementById('cfgAfternoonEnabled') ? document.getElementById('cfgAfternoonEnabled').checked : true;

  const eFrom = document.getElementById('cfgEveningFrom')?.value || '18:00';
  const eOnTime = document.getElementById('cfgEveningOnTime')?.value || '18:45';
  const eLate = document.getElementById('cfgEveningLate')?.value || '19:15';
  const eCheckout = document.getElementById('cfgEveningCheckout')?.value || '21:30';
  const eEnabled = document.getElementById('cfgEveningEnabled') ? document.getElementById('cfgEveningEnabled').checked : false;

  const payload = {
    // 🌅 Ca Sáng
    morning_enabled: mEnabled,
    morning_name: document.getElementById('cfgMorningName')?.value || 'Chính khóa buổi sáng',
    morning_from: mFrom,
    morning_on_time: mOnTime,
    morning_late_until: mLate,
    morning_checkout: mCheckout,
    morning_uniform_check: document.getElementById('cfgMorningUniformCheck') ? document.getElementById('cfgMorningUniformCheck').checked : true,
    morning_late_deduct: parseInt(document.getElementById('cfgMorningLateD')?.value || '2'),
    morning_notify_parent: document.getElementById('cfgMorningNotify') ? document.getElementById('cfgMorningNotify').checked : true,
    morning_auth_mode: document.getElementById('cfgMorningAuthMode')?.value || 'ALL',

    // ☀️ Ca Chiều
    afternoon_enabled: aEnabled,
    afternoon_name: document.getElementById('cfgAfternoonName')?.value || 'Buổi 2 / Ngoại khóa',
    afternoon_from: aFrom,
    afternoon_on_time: aOnTime,
    afternoon_late_until: aLate,
    afternoon_checkout: aCheckout,
    afternoon_uniform_check: document.getElementById('cfgAfternoonUniformCheck') ? document.getElementById('cfgAfternoonUniformCheck').checked : true,
    afternoon_late_deduct: parseInt(document.getElementById('cfgAfternoonLateD')?.value || '2'),
    afternoon_notify_parent: document.getElementById('cfgAfternoonNotify') ? document.getElementById('cfgAfternoonNotify').checked : true,
    afternoon_auth_mode: document.getElementById('cfgAfternoonAuthMode')?.value || 'ALL',

    // 🌙 Ca Tối
    evening_enabled: eEnabled,
    evening_name: document.getElementById('cfgEveningName')?.value || 'Tự học / Nội trú',
    evening_from: eFrom,
    evening_on_time: eOnTime,
    evening_late_until: eLate,
    evening_checkout: eCheckout,
    evening_uniform_check: document.getElementById('cfgEveningUniformCheck') ? document.getElementById('cfgEveningUniformCheck').checked : false,
    evening_late_deduct: parseInt(document.getElementById('cfgEveningLateD')?.value || '1'),
    evening_notify_parent: document.getElementById('cfgEveningNotify') ? document.getElementById('cfgEveningNotify').checked : true,
    evening_auth_mode: document.getElementById('cfgEveningAuthMode')?.value || 'ALL',

    // Tương thích ngược
    checkin_from: mFrom,
    checkin_on_time_until: mOnTime,
    checkin_late_until: mLate,
    checkout_from: aCheckout,

    late_deduct_points: parseInt(document.getElementById('cfgLateD')?.value || '2'),
    violation_deduct_points: parseInt(document.getElementById('cfgUniformD')?.value || '3'),
    uniform_check: document.getElementById('cfgUniformCheck') ? document.getElementById('cfgUniformCheck').checked : true,
    min_points_warning: 80,
    absent_deduct_points: 5,
  };
  try {
    const res = await api('PUT', `/api/v1/schools/${schoolId}/config/rules`, payload);
    toast('💾 Đã Lưu & Đồng Bộ', res.message || 'Quy định giờ Sáng · Chiều · Tối đã đồng bộ tức thì với camera!', 'success');
  } catch(e) { toast('Lỗi', e.detail||'', 'error'); }
}

async function rotateInviteCodes() {
  if (!confirm('Tạo mã mời mới sẽ VÔ HIỆU HÓA tất cả mã cũ. Tiếp tục?')) return;
  try {
    const res = await api('PUT', `/api/v1/schools/${schoolId}/config/codes`);
    toast('🔄 Mã Mới Đã Tạo', 'Thông báo ngay cho Giáo Viên và Giám Thị.', 'success');
    loadConfig();
  } catch(e) { toast('Lỗi', e.detail||'', 'error'); }
}

// ── Gemini AI Rule Generator (Text & 50MB File) ───
let selectedRuleFile = null;

function switchRuleInputTab(tab) {
  const isFile = (tab === 'file');
  document.getElementById('ruleTabFile').style.display = isFile ? 'block' : 'none';
  document.getElementById('ruleTabText').style.display = isFile ? 'none' : 'block';
  document.getElementById('tabBtnFile').style.fontWeight = isFile ? '700' : 'normal';
  document.getElementById('tabBtnFile').style.color = isFile ? 'var(--purple)' : 'var(--muted)';
  document.getElementById('tabBtnText').style.fontWeight = isFile ? 'normal' : '700';
  document.getElementById('tabBtnText').style.color = isFile ? 'var(--muted)' : 'var(--purple)';
}

function onRuleFileSelected(input) {
  if (input.files && input.files[0]) {
    const file = input.files[0];
    const sizeMb = file.size / (1024 * 1024);
    if (sizeMb > 50) {
      toast('File Quá Lớn', `Dung lượng file (${sizeMb.toFixed(1)}MB) vượt quá giới hạn 50MB.`, 'error');
      input.value = '';
      selectedRuleFile = null;
      return;
    }
    selectedRuleFile = file;
    document.getElementById('ruleFileLabel').innerText = `📄 ${file.name}`;
    const info = document.getElementById('ruleFileInfo');
    info.style.display = 'block';
    info.innerText = `Kích thước: ${sizeMb.toFixed(2)} MB · Định dạng: ${file.name.split('.').pop().toUpperCase()} · Sẵn sàng phân tích`;
  }
}

async function uploadRulesFileWithAI() {
  if (!selectedRuleFile) {
    toast('Chưa Chọn File', 'Vui lòng chọn file PDF, Word (.docx) hoặc Text (tối đa 50MB).', 'error');
    return;
  }

  const btn = document.getElementById('btnUploadAiFile');
  const st  = document.getElementById('aiRuleFileStatus');
  btn.disabled = true;
  btn.innerText = '⏳ Đang tải file & AI phân tích...';
  st.innerText = `Đang đọc ${selectedRuleFile.name}...`;

  const token = localStorage.getItem(AUTH_KEY);
  const apiBase = (typeof STEM_CONFIG !== 'undefined' && STEM_CONFIG.API_BASE) ? STEM_CONFIG.API_BASE : '';
  const url = `${apiBase}/api/v1/schools/${schoolId}/ai-rules/upload-file`;

  const formData = new FormData();
  formData.append('file', selectedRuleFile);

  try {
    const res = await fetch(url, {
      method: 'POST',
      headers: {
        ...(token ? { 'Authorization': `Bearer ${token}` } : {})
      },
      body: formData
    });
    const data = await res.json();
    if (!res.ok) throw data;

    toast('✨ Thành Công', data.message || 'AI đã phân tích nội quy và nạp xuống Camera Pi!', 'success');
    
    // Display result
    const box = document.getElementById('aiRuleResultBox');
    box.style.display = 'block';
    const profile = data.rules_profile || {};
    document.getElementById('aiRuleSummaryText').innerText = profile.summary_vi || 'Đã thiết lập bộ lọc lỗi thành công.';
    document.getElementById('aiRuleJsonPreview').innerText = JSON.stringify(profile, null, 2);
    
    // Auto sync back into manual inputs
    if (profile.time_rules) {
      if (profile.time_rules.gate_open) {
        if (document.getElementById('cfgMorningFrom')) document.getElementById('cfgMorningFrom').value = profile.time_rules.gate_open;
        if (document.getElementById('cfgFrom')) document.getElementById('cfgFrom').value = profile.time_rules.gate_open;
      }
      if (profile.time_rules.on_time_deadline) {
        if (document.getElementById('cfgMorningOnTime')) document.getElementById('cfgMorningOnTime').value = profile.time_rules.on_time_deadline;
        if (document.getElementById('cfgOnTime')) document.getElementById('cfgOnTime').value = profile.time_rules.on_time_deadline;
      }
      if (profile.time_rules.late_cutoff) {
        if (document.getElementById('cfgMorningLate')) document.getElementById('cfgMorningLate').value = profile.time_rules.late_cutoff;
        if (document.getElementById('cfgLate')) document.getElementById('cfgLate').value = profile.time_rules.late_cutoff;
      }
      if (profile.time_rules.late_deduct_points) {
        if (document.getElementById('cfgLateD')) document.getElementById('cfgLateD').value = profile.time_rules.late_deduct_points;
      }
    }
    st.innerText = `✅ Đã nạp từ file (${data.file_size_mb}MB)`;
  } catch(e) {
    toast('Lỗi Phân Tích File', e.detail || 'Không thể trích xuất nội dung file.', 'error');
    st.innerText = '❌ Thất bại';
  } finally {
    btn.disabled = false;
    btn.innerText = '🚀 Tải Lên & Để AI Phân Tích (Max 50MB)';
  }
}

function fillSampleSchoolRules() {
  const sample = `Nội quy nề nếp Trường THPT:
1. Giờ giấc: Học sinh có mặt tại trường trước 07:15. Sau 07:15 tính đi trễ (trừ 2 điểm thi đua). Sau 07:30 đóng cổng hoàn toàn.
2. Trang phục: Bắt buộc mặc áo sơ mi trắng đồng phục có may phù hiệu/bảng tên trường bên ngực trái. Quần tây màu xanh đen hoặc đen (cấm mặc quần short, quần lửng, váy ngắn trên đầu gối).
3. Giày dép: Đi giày bata, giày thể thao hoặc dép quai hậu (sandals). Tuyệt đối CẤM đi dép lê, dép xỏ ngón không quai hậu.
4. Tác phong: Cấm nhuộm tóc các màu sặc sỡ (chỉ chấp nhận tóc đen hoặc nâu tự nhiên). Cấm đội mũ bảo hiểm hoặc mũ lưỡi trai trong sân trường. Cấm đeo tai nghe khi đi qua cổng điểm danh.`;
  document.getElementById('aiRuleInput').value = sample;
}

async function parseRulesWithAI() {
  const text = document.getElementById('aiRuleInput').value.trim();
  if (!text) {
    toast('Thiếu Nội Dung', 'Vui lòng dán văn bản nội quy trường vào ô trên.', 'error');
    return;
  }
  const btn = document.getElementById('btnParseAiRule');
  const st  = document.getElementById('aiRuleStatus');
  btn.disabled = true;
  btn.innerText = '⏳ AI Gemini đang phân tích...';
  st.innerText = 'Đang trích xuất luật nề nếp...';
  
  try {
    const res = await api('POST', `/api/v1/schools/${schoolId}/ai-rules/parse`, { raw_text: text });
    toast('✨ Thành Công', 'AI đã phân tích nội quy và nạp xuống Camera Pi!', 'success');
    
    // Display result
    const box = document.getElementById('aiRuleResultBox');
    box.style.display = 'block';
    const profile = res.rules_profile || {};
    document.getElementById('aiRuleSummaryText').innerText = profile.summary_vi || 'Đã thiết lập bộ lọc lỗi thành công.';
    document.getElementById('aiRuleJsonPreview').innerText = JSON.stringify(profile, null, 2);
    
    // Auto sync back into manual inputs
    if (profile.time_rules) {
      if (profile.time_rules.gate_open) {
        if (document.getElementById('cfgMorningFrom')) document.getElementById('cfgMorningFrom').value = profile.time_rules.gate_open;
        if (document.getElementById('cfgFrom')) document.getElementById('cfgFrom').value = profile.time_rules.gate_open;
      }
      if (profile.time_rules.on_time_deadline) {
        if (document.getElementById('cfgMorningOnTime')) document.getElementById('cfgMorningOnTime').value = profile.time_rules.on_time_deadline;
        if (document.getElementById('cfgOnTime')) document.getElementById('cfgOnTime').value = profile.time_rules.on_time_deadline;
      }
      if (profile.time_rules.late_cutoff) {
        if (document.getElementById('cfgMorningLate')) document.getElementById('cfgMorningLate').value = profile.time_rules.late_cutoff;
        if (document.getElementById('cfgLate')) document.getElementById('cfgLate').value = profile.time_rules.late_cutoff;
      }
      if (profile.time_rules.late_deduct_points) {
        if (document.getElementById('cfgLateD')) document.getElementById('cfgLateD').value = profile.time_rules.late_deduct_points;
      }
    }
    st.innerText = '✅ Đã đồng bộ với Camera';
  } catch(e) {
    toast('Lỗi Phân Tích AI', e.detail || 'Không thể phân tích văn bản.', 'error');
    st.innerText = '❌ Thất bại';
  } finally {
    btn.disabled = false;
    btn.innerText = '✨ AI Phân Tích & Nạp Xuống Camera Pi';
  }
}



export {
  fillSampleSchoolRules, loadConfig, onRuleFileSelected, parseRulesWithAI, rotateInviteCodes, saveFormConfig, saveRulesConfig, switchRuleInputTab, uploadRulesFileWithAI
};
