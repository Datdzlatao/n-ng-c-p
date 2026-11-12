// app/js/views/account.js — User Profile, Password & Parent-Student Code
// ── Account ───────────────────────────────────────
function loadAccount() {
  if (!currentUser) return;
  const u = currentUser;
  const st = u.verified_status || 'UNVERIFIED';
  const badgeCls = st==='VERIFIED'?'badge-verified':st==='PENDING_REVIEW'?'badge-pending':'badge-unverified';
  const badgeTxt = st==='VERIFIED'?'✓ ĐÃ XÁC MINH CHÍNH CHỦ':st==='PENDING_REVIEW'?'⏳ ĐANG CHỜ XÉT DUYỆT':'⚠️ CHƯA XÁC MINH';

  document.getElementById('accountInfo').innerHTML = `
    <div style="display:flex;align-items:center;gap:14px;margin-bottom:16px;">
      <div style="width:56px;height:56px;background:var(--overlay);border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:1.8rem;">👤</div>
      <div>
        <div style="font-weight:800;font-size:1.05rem;">${u.full_name}</div>
        <div style="font-size:0.82rem;color:var(--muted);">${u.role} · @${u.username} ${u.user_code || u.student_code ? `· <code style="color:var(--blue);font-weight:700;">${u.user_code || u.student_code}</code>` : ''}</div>
        <span class="badge-v ${badgeCls}" style="margin-top:4px;display:inline-block;">${badgeTxt}</span>
      </div>
    </div>
    <div style="display:grid;grid-template-columns:repeat(auto-fit, minmax(200px, 1fr));gap:10px;font-size:0.85rem;width:100%;">
      <div><span style="color:var(--muted)">🏷️ Mã Định Danh:</span> <strong style="color:var(--blue);">${u.user_code || u.student_code || 'Chưa cấp'}</strong></div>
      <div><span style="color:var(--muted)">📞 SĐT:</span> ${u.phone||'—'}</div>
      <div><span style="color:var(--muted)">✉️ Email:</span> ${u.email||'—'}</div>
      <div><span style="color:var(--muted)">🗓️ Ngày sinh:</span> ${u.dob||'—'}</div>
    </div>
    ${u.verification_note ? `<div style="margin-top:10px;font-size:0.8rem;color:var(--muted);background:var(--overlay);padding:8px 12px;border-radius:6px;">${u.verification_note}</div>` : ''}
  `;

  // Hiển thị phần quản lý con em nếu tài khoản là Phụ Huynh (PARENT)
  const parCard = document.getElementById('parentChildrenCard');
  if (parCard) {
    if (u.role === 'PARENT') {
      parCard.style.display = 'block';
      loadParentChildrenList();
    } else {
      parCard.style.display = 'none';
    }
  }

  // Hiển thị thẻ mã mời phụ huynh nếu tài khoản là Học Sinh (STUDENT)
  const stuCard = document.getElementById('studentInviteCard');
  if (stuCard) {
    if (u.role === 'STUDENT') {
      stuCard.style.display = 'block';
      loadStudentParentInviteCode();
    } else {
      stuCard.style.display = 'none';
    }
  }

  // ── Tính toán trạng thái sinh trắc học học sinh (0/5, 3/5, 5/5) ──
  const samplesCount = (u.face_samples_count !== undefined && u.face_samples_count !== null)
    ? Number(u.face_samples_count)
    : (u.student_profile && u.student_profile.face_samples_count !== undefined)
      ? Number(u.student_profile.face_samples_count)
      : (u.face_photo_url ? 3 : 0);

  let bioStatusHtml = '';
  if (samplesCount >= 5) {
    bioStatusHtml = `
      <div style="background:rgba(34,197,94,0.09);border:1.5px solid rgba(34,197,94,0.35);border-radius:12px;padding:16px;margin-bottom:16px;">
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;">
          <div style="font-weight:800;color:var(--green);font-size:0.96rem;display:flex;align-items:center;gap:8px;">
            <span>🟢 ĐÃ NẠP ĐỦ 5/5 ẢNH SINH TRẮC HỌC ĐA GÓC</span>
          </div>
          <span class="chip chip-green" style="font-size:0.72rem;font-weight:700;padding:3px 8px;">ĐẠT CHUẨN TỐI ĐA (5/5)</span>
        </div>
        <div style="font-size:0.83rem;color:var(--text);margin-bottom:12px;line-height:1.5;">
          Dữ liệu khuôn mặt của bạn đã được số hóa đầy đủ <b>5 góc 3D chuẩn Apple FaceID</b> (Chính diện, Nghiêng Trái, Nghiêng Phải, Ngước lên, Cúi nhẹ).
          <br>⚡ Trạm Camera AI tại cổng trường sẽ nhận diện và điểm danh tự động bạn tức thì (&lt;0.2s), không bao giờ bị báo người lạ!
        </div>
        <button class="btn btn-outline btn-sm" style="border-color:var(--purple);color:var(--purple);width:100%;font-weight:700;padding:9px;" onclick="startFaceVerification()">
          📸 Quét Lại Khuôn Mặt (Nếu Muốn Làm Mới Dữ Liệu)
        </button>
      </div>
    `;
  } else if (samplesCount > 0) {
    bioStatusHtml = `
      <div style="background:rgba(245,158,11,0.09);border:1.5px solid rgba(245,158,11,0.45);border-radius:12px;padding:16px;margin-bottom:16px;">
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;">
          <div style="font-weight:800;color:var(--amber);font-size:0.96rem;display:flex;align-items:center;gap:8px;">
            <span>🟡 ĐÃ CÓ SẴN ${samplesCount}/5 ẢNH MẪU CƠ BẢN</span>
          </div>
          <span class="chip chip-amber" style="font-size:0.72rem;font-weight:700;padding:3px 8px;">KHUYẾN NGHỊ BỔ SUNG</span>
        </div>
        <div style="font-size:0.83rem;color:var(--text);margin-bottom:12px;line-height:1.5;">
          Hệ thống nhận diện bạn đã quét sẵn <b>${samplesCount} ảnh góc cơ bản</b> (Chính diện & 2 bên má). Camera cổng trường đã có thể nhận diện bạn.
          <br>💡 <b>Khuyến nghị:</b> Hãy quét bổ sung thêm <b>2 góc mới (Ngước lên cao & Cúi nhẹ)</b> để camera tầm cao lắp ở cổng trường bắt nét khuôn mặt của bạn nhanh nhất trong mọi tư thế di chuyển!
        </div>
        <button class="btn btn-primary" style="background:var(--amber);color:#000;width:100%;font-weight:800;padding:10px;display:flex;align-items:center;justify-content:center;gap:8px;" onclick="startFaceVerification()">
          <span>🔄 Quét Bổ Sung 2 Góc Mới (Nâng Lên 5/5 Ảnh Chuẩn)</span>
        </button>
      </div>
    `;
  } else {
    bioStatusHtml = `
      <div style="background:rgba(239,68,68,0.09);border:1.5px solid rgba(239,68,68,0.45);border-radius:12px;padding:16px;margin-bottom:16px;">
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;">
          <div style="font-weight:800;color:var(--red);font-size:0.96rem;display:flex;align-items:center;gap:8px;">
            <span>⚠️ CHƯA QUÉT SINH TRẮC HỌC (0/5 ẢNH)</span>
          </div>
          <span class="chip chip-red" style="font-size:0.72rem;font-weight:700;padding:3px 8px;">CHƯA CÓ DỮ LIỆU</span>
        </div>
        <div style="font-size:0.83rem;color:var(--text);margin-bottom:12px;line-height:1.5;">
          Bạn <b>chưa quét khuôn mặt nào</b> vào hệ thống!
          <br>🚨 <b>Cảnh báo:</b> Khi bạn đi qua cổng trường, máy camera AI sẽ <b>không nhận diện được bạn và cảnh báo là "Người Lạ"</b>. Hãy quét sinh trắc học ngay bây giờ để được điểm danh tự động!
        </div>
        <button class="btn btn-primary" style="background:var(--red);width:100%;font-weight:800;padding:11px;display:flex;align-items:center;justify-content:center;gap:8px;" onclick="startFaceVerification()">
          <span>🚀 Bắt Đầu Quét Khuôn Mặt Ngay (5 Góc AI Cổng Trường)</span>
        </button>
      </div>
    `;
  }

  document.getElementById('verifySection').innerHTML = bioStatusHtml + (st === 'VERIFIED'
    ? `<div style="background:rgba(34,197,94,.08);border:1px solid rgba(34,197,94,.25);border-radius:10px;padding:16px;font-size:0.85rem;">
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;">
          <span style="color:var(--green);font-weight:700;">✓ Tài khoản đã được xác minh chính chủ.</span>
          <span class="chip chip-green" style="font-size:0.7rem;font-weight:700;">TÍCH XANH HOẠT ĐỘNG</span>
        </div>
        <div style="color:var(--muted);font-size:0.8rem;margin-bottom:12px;">Phương thức: <b>${u.verification_method||'Xác Minh Danh Tính'}</b> · ${u.verified_at?.slice(0,10)||''}</div>
       </div>`
    : `<div style="font-size:0.85rem;margin-bottom:14px;">Chọn phương thức xác minh để nhận <strong style="color:var(--green)">Tích Xanh chính chủ</strong>:</div>
       <div style="display:flex;flex-direction:column;gap:12px;">
         
         <!-- PHƯƠNG THỨC 3 (ƯU TIÊN): QUÉT KHUÔN MẶT SINH TRẮC HỌC -->
         <div style="background:linear-gradient(135deg, rgba(168,85,247,0.14), rgba(79,142,247,0.08));border:1.5px solid var(--purple);border-radius:10px;padding:14px;">
           <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px;">
             <div style="font-weight:800;color:var(--purple);font-size:0.92rem;display:flex;align-items:center;gap:6px;">
               <span>📸 Phương Thức 1: Quét Sinh Trắc Học Khuôn Mặt (AI FaceID)</span>
             </div>
             <span class="chip chip-purple" style="font-size:0.68rem;font-weight:700;padding:2px 6px;">KHUYÊN DÙNG CHO HỌC SINH</span>
           </div>
            <div style="font-size:0.8rem;color:var(--muted);margin-bottom:12px;line-height:1.4;">
              Quét sinh trắc học khuôn mặt đa góc. Dữ liệu sau khi quét sẽ tự động nạp thẳng vào máy camera AI điểm danh tại cổng trường và cấp ngay <strong style="color:var(--green)">Tích Xanh chính chủ</strong>.
            </div>
           <button class="btn btn-primary" style="background:var(--purple);width:100%;font-weight:700;padding:10px;display:flex;align-items:center;justify-content:center;gap:8px;" onclick="startFaceVerification()">
             <span>🚀 Bắt Đầu Quét Khuôn Mặt Để Xác Minh</span>
           </button>
         </div>

         <!-- PHƯƠNG THỨC: OTP -->
         <div style="background:var(--overlay);border-radius:8px;padding:12px;">
           <div style="font-weight:700;margin-bottom:8px;">📱 Phương Thức 2: Xác Thực OTP Qua SĐT</div>
           <div style="display:flex;gap:8px;">
             <input id="otpPhone" type="tel" placeholder="Nhập SĐT" value="${u.phone||''}" style="flex:1;padding:8px 12px;background:var(--card);border:1px solid var(--border);border-radius:7px;color:var(--text);outline:none;">
             <button class="btn btn-primary" onclick="requestOTP()">Gửi OTP</button>
           </div>
           <div id="otpBox" style="display:none;margin-top:8px;">
             <div style="display:flex;gap:8px;">
               <input id="otpCode" type="text" placeholder="Nhập 6 chữ số OTP" maxlength="6" style="flex:1;padding:8px 12px;background:var(--card);border:1px solid var(--border);border-radius:7px;color:var(--text);outline:none;letter-spacing:4px;text-align:center;font-size:1.1rem;">
               <button class="btn btn-success" onclick="submitOTP()">Xác Nhận</button>
             </div>
             <div id="otpHint" style="font-size:0.75rem;color:var(--muted);margin-top:6px;"></div>
           </div>
         </div>

         <!-- PHƯƠNG THỨC: CCCD / THẺ HỌC SINH -->
         <div style="background:var(--overlay);border-radius:8px;padding:12px;">
           <div style="font-weight:700;margin-bottom:8px;">📄 Phương Thức 3: Nộp CCCD / Thẻ Học Sinh</div>
           <div style="font-size:0.78rem;color:var(--muted);margin-bottom:8px;">Chụp rõ 2 mặt thẻ, GVCN sẽ xét duyệt trong 24-48h</div>
           <input id="idCardFile" type="file" accept="image/*" style="width:100%;font-size:0.82rem;color:var(--muted);">
           <button class="btn btn-primary" style="margin-top:8px;width:100%;" onclick="submitIDCard()">📤 Gửi Hồ Sơ</button>
         </div>
       </div>`;
}

async function requestOTP() {
  const phone = document.getElementById('otpPhone').value.trim();
  if (!phone) { toast('Cần nhập SĐT','','error'); return; }
  try {
    const res = await api('POST', '/api/v1/auth/verify/request-otp', { school_id: schoolId, target: phone, otp_type: 'PHONE_REGISTER' });
    document.getElementById('otpBox').style.display = 'block';
    if (res.dev_otp) {
      document.getElementById('otpCode').value = res.dev_otp;
      document.getElementById('otpHint').innerText = `[DEV] OTP: ${res.dev_otp}`;
    }
    toast('📲 Đã Gửi OTP', res.message, 'info');
  } catch(e) { toast('Lỗi', e.detail||'', 'error'); }
}

async function submitOTP() {
  const phone = document.getElementById('otpPhone').value.trim();
  const code  = document.getElementById('otpCode').value.trim();
  try {
    await api('POST', '/api/v1/auth/verify/submit-otp', { school_id: schoolId, target: phone, otp_code: code });
    toast('✅ Xác Thực Thành Công!', 'Tài khoản đã đạt chuẩn Tích Xanh!', 'success');
    await loadMe();
    loadAccount();
  } catch(e) { toast('Lỗi OTP', e.detail||'', 'error'); }
}

async function submitIDCard() {
  const fileInput = document.getElementById('idCardFile');
  if (!fileInput?.files[0]) { toast('Cần chọn ảnh CCCD/Thẻ HS','','error'); return; }
  const reader = new FileReader();
  reader.onload = async (e) => {
    try {
      await api('POST', '/api/v1/auth/verify/submit-id-card', { school_id: schoolId, doc_type: 'CCCD', doc_data_url: e.target.result });
      toast('📤 Đã Gửi Hồ Sơ', 'GVCN sẽ xét duyệt trong 24-48 giờ.', 'success');
      await loadMe(); loadAccount();
    } catch(err) { toast('Lỗi Gửi File', err.detail||'', 'error'); }
  };
  reader.readAsDataURL(fileInput.files[0]);
}

function startFaceVerification() {
  if (!currentUser) {
    toast('Chưa Đăng Nhập', 'Vui lòng đăng nhập lại tài khoản', 'error');
    return;
  }
  const sid = schoolId || currentUser.school_id || 1;
  const studentCode = currentUser.student_code || currentUser.username || `HS${sid}-${currentUser.id}`;
  const studentName = currentUser.full_name || 'Học Sinh';

  if (typeof BiometricScanner === 'undefined') {
    toast('Lỗi Module', 'Module quét sinh trắc học chưa sẵn sàng. Vui lòng tải lại trang.', 'error');
    return;
  }

  BiometricScanner.start({
    schoolId: sid,
    studentId: currentUser.id,
    studentCode: studentCode,
    studentName: studentName,
    verifyAccount: true,
    onComplete: async (uploadData) => {
      toast('🎉 Xác Minh Hoàn Tất!', 'Hồ sơ sinh trắc học FaceID đã được cấp Tích Xanh chính chủ!', 'success');
      try {
        await loadMe();
        loadAccount();
      } catch(e) {}
    },
    onSkip: () => {
      toast('Đã Bỏ Qua', 'Bạn có thể quay lại mục Tài Khoản để quét khuôn mặt bất kỳ lúc nào.', 'info');
    }
  });
}

// ── Student Parent-Invite Code Logic (Học Sinh Cấp Mã Cho Phụ Huynh) ────
let currentStudentInviteCode = '';

async function loadStudentParentInviteCode() {
  const codeEl = document.getElementById('stuParentInviteCode');
  const qrWrap = document.getElementById('stuInviteQrWrap');
  const listEl = document.getElementById('stuLinkedParentsList');
  if (!codeEl) return;

  try {
    const data = await api('GET', `/api/v1/s/${schoolId}/students/me/parent-invite-code`);
    currentStudentInviteCode = data.parent_invite_code || '';
    codeEl.innerText = data.parent_invite_code || 'Chưa cấp';

    // Render dynamic QR Code on Canvas
    if (qrWrap && typeof QRCode !== 'undefined' && data.parent_invite_code) {
      qrWrap.innerHTML = '';
      new QRCode(qrWrap, {
        text: `PARENT_INVITE:${data.parent_invite_code}`,
        width: 64,
        height: 64,
        colorDark: '#000000',
        colorLight: '#ffffff',
        correctLevel: QRCode.CorrectLevel.M
      });
    }

    // Render linked parents
    if (listEl) {
      if (!data.linked_parents || data.linked_parents.length === 0) {
        listEl.innerHTML = '<div style="font-size:0.8rem;color:var(--muted);padding:4px 0;">Chưa có phụ huynh nào liên kết. Hãy gửi mã mời cho Bố/Mẹ nhé!</div>';
      } else {
        listEl.innerHTML = data.linked_parents.map(p => `
          <div style="display:flex;align-items:center;justify-content:space-between;padding:8px 12px;background:var(--overlay);border-radius:8px;margin-bottom:6px;font-size:0.85rem;">
            <div>
              <strong>${escHtml(p.parent_full_name || p.full_name || '')}</strong>
              <span class="chip chip-purple" style="margin-left:6px;font-size:0.7rem;">${escHtml(p.relation_name || 'Phụ huynh')}</span>
              ${p.parent_phone ? `<span style="color:var(--muted);font-size:0.75rem;margin-left:6px;">(${escHtml(p.parent_phone)})</span>` : ''}
            </div>
            <span class="chip chip-green" style="font-size:0.7rem;">✓ Đã Kết Nối</span>
          </div>
        `).join('');
      }
    }
  } catch(e) {
    if (codeEl) codeEl.innerText = 'Lỗi tải mã';
  }
}

async function rotateMyParentInviteCode() {
  if (!confirm('Bạn có chắc chắn muốn đổi Mã Mời Phụ Huynh mới? Mã cũ sẽ hết hiệu lực ngay lập tức.')) return;
  try {
    const res = await api('POST', `/api/v1/s/${schoolId}/students/me/rotate-parent-invite-code`);
    toast('🔄 Đổi Mã Thành Công', `Mã mới của bạn: ${res.new_invite_code}`, 'success');
    loadStudentParentInviteCode();
  } catch(e) {
    toast('Lỗi', e.detail || 'Không thể đổi mã mời.', 'error');
  }
}

function copyParentInviteCode() {
  if (!currentStudentInviteCode) {
    toast('Chưa Có Mã', 'Chưa có mã mời để sao chép.', 'warning');
    return;
  }
  const text = currentStudentInviteCode;
  navigator.clipboard.writeText(text).then(() => {
    toast('📋 Đã Sao Chép Mã Mời', `Đã sao chép: ${text}. Hãy gửi cho Bố/Mẹ qua tin nhắn hoặc Zalo!`, 'success');
  }).catch(() => {
    toast('Sao Chép', `Mã mời của em: ${text}`, 'info');
  });
}

// ── Parent-Student Linking Logic (Dành Cho Phụ Huynh & Nhà Trường) ────
let currentLinkChildTab = 'INVITE';

function switchLinkChildTab(tab) {
  currentLinkChildTab = tab;
  const tabInvite = document.getElementById('linkTabInvite');
  const tabManual = document.getElementById('linkTabManual');
  const btnInvite = document.getElementById('tabBtnInvite');
  const btnManual = document.getElementById('tabBtnManual');
  const submitBtn = document.getElementById('btnSubmitLinkChild');
  const submitText = document.getElementById('btnSubmitLinkChildText');

  if (tab === 'INVITE') {
    if (tabInvite) tabInvite.style.display = 'block';
    if (tabManual) tabManual.style.display = 'none';
    if (btnInvite) {
      btnInvite.style.background = 'var(--card)';
      btnInvite.style.color = 'var(--text)';
      btnInvite.style.boxShadow = '0 1px 4px rgba(0,0,0,0.2)';
    }
    if (btnManual) {
      btnManual.style.background = 'transparent';
      btnManual.style.color = 'var(--muted)';
      btnManual.style.boxShadow = 'none';
    }
    if (submitBtn) submitBtn.style.background = 'var(--purple)';
    if (submitText) submitText.innerText = '🚀 Kết Nối 1 Chạm Ngay';
  } else {
    if (tabInvite) tabInvite.style.display = 'none';
    if (tabManual) tabManual.style.display = 'block';
    if (btnInvite) {
      btnInvite.style.background = 'transparent';
      btnInvite.style.color = 'var(--muted)';
      btnInvite.style.boxShadow = 'none';
    }
    if (btnManual) {
      btnManual.style.background = 'var(--card)';
      btnManual.style.color = 'var(--text)';
      btnManual.style.boxShadow = '0 1px 4px rgba(0,0,0,0.2)';
    }
    if (submitBtn) submitBtn.style.background = 'var(--blue)';
    if (submitText) submitText.innerText = '🔗 Xác Nhận Liên Kết';
  }
}

function openLinkChildModal() {
  const inviteEl = document.getElementById('lcInviteCode');
  const codeEl   = document.getElementById('lcStudentCode');
  const vkeyEl   = document.getElementById('lcVerifyKey');
  const relEl    = document.getElementById('lcRelation');
  if (inviteEl) inviteEl.value = '';
  if (codeEl)   codeEl.value = '';
  if (vkeyEl)   vkeyEl.value = '';
  if (relEl)    relEl.value = 'Phụ huynh';
  switchLinkChildTab('INVITE');
  openModal('modalLinkChild');
}

async function submitLinkChild() {
  const rel = document.getElementById('lcRelation')?.value || 'Phụ huynh';

  if (currentLinkChildTab === 'INVITE') {
    const inviteCode = document.getElementById('lcInviteCode')?.value.trim().toUpperCase();
    if (!inviteCode) {
      toast('Thiếu Thông Tin', 'Vui lòng nhập Mã Mời do con cung cấp (ví dụ: PH-A8C2E9).', 'warning');
      return;
    }
    try {
      const res = await api('POST', `/api/v1/s/${schoolId}/parents/link-by-invite-code`, {
        invite_code: inviteCode,
        relation_name: rel
      });
      toast('🎉 Kết Nối Thành Công', res.message || 'Đã liên kết thành công với con em!', 'success');
      closeModal('modalLinkChild');

      const meRes = await api('GET', '/api/v1/auth/me');
      currentUser = meRes.user;
      loadParentChildrenList();
      if (document.getElementById('view-my-attendance')?.classList.contains('active')) {
        loadMyAttendance();
      }
    } catch(e) {
      toast('Lỗi Liên Kết', e.detail || 'Không thể liên kết bằng mã mời.', 'error');
    }
  } else {
    const code = document.getElementById('lcStudentCode')?.value.trim().toUpperCase();
    const vkey = document.getElementById('lcVerifyKey')?.value.trim();

    if (!code) {
      toast('Thiếu Thông Tin', 'Vui lòng nhập Mã Học Sinh của con.', 'warning');
      return;
    }

    try {
      const res = await api('POST', `/api/v1/s/${schoolId}/parents/link-child`, {
        student_code: code,
        verify_key: vkey || null,
        relation_name: rel
      });
      toast('🎉 Chúc Mừng', res.message || 'Đã liên kết thành công con em vào tài khoản!', 'success');
      closeModal('modalLinkChild');
      
      const meRes = await api('GET', '/api/v1/auth/me');
      currentUser = meRes.user;
      loadParentChildrenList();
      if (document.getElementById('view-my-attendance')?.classList.contains('active')) {
        loadMyAttendance();
      }
    } catch(e) {
      toast('Lỗi Liên Kết', e.detail || 'Không thể liên kết học sinh.', 'error');
    }
  }
}

async function loadParentChildrenList() {
  const container = document.getElementById('parentChildrenList');
  if (!container) return;
  container.innerHTML = '<div style="text-align:center;padding:24px;color:var(--muted);">Đang tải danh sách con em...</div>';
  try {
    const children = await api('GET', `/api/v1/s/${schoolId}/parents/my-children`);
    if (!children.length) {
      container.innerHTML = `
        <div style="text-align:center;padding:28px 16px;background:rgba(59,130,246,0.05);border:1.5px dashed var(--blue);border-radius:10px;">
          <div style="font-size:2rem;margin-bottom:8px;">👨‍👩‍👧</div>
          <div style="font-weight:700;font-size:0.95rem;margin-bottom:4px;">Chưa Có Con Em Nào Được Liên Kết</div>
          <div style="font-size:0.8rem;color:var(--muted);margin-bottom:14px;">Bấm nút bên dưới để nhập Mã Học Sinh do nhà trường cấp.</div>
          <button class="btn btn-primary btn-sm" onclick="openLinkChildModal()" style="background:var(--blue);font-weight:700;padding:6px 14px;">
            + Liên Kết Con Em Ngay
          </button>
        </div>`;
      return;
    }

    container.innerHTML = `
      <div style="display:flex;flex-direction:column;gap:12px;">
        ${children.map(c => `
          <div style="display:flex;align-items:center;justify-content:space-between;padding:12px;background:var(--overlay);border:1px solid var(--border);border-radius:10px;gap:12px;flex-wrap:wrap;">
            <div style="display:flex;align-items:center;gap:12px;">
              <img src="${c.face_photo_url || '/assets/icons/default_avatar.png'}" onerror="this.src='/assets/icons/default_avatar.png'" style="width:42px;height:42px;border-radius:50%;object-fit:cover;border:1.5px solid var(--blue);">
              <div>
                <div style="font-weight:800;font-size:0.95rem;display:flex;align-items:center;gap:6px;">
                  <span>${escHtml(c.full_name)}</span>
                  <span class="chip chip-blue" style="font-size:0.68rem;padding:1px 6px;">${escHtml(c.relation_name || 'Con')}</span>
                </div>
                <div style="font-size:0.78rem;color:var(--muted);margin-top:2px;">
                  Mã HS: <code style="color:var(--blue);font-weight:700;">${escHtml(c.student_code)}</code> · Lớp: <b>${escHtml(c.class_name || 'Chưa xếp lớp')}</b>
                  ${c.dob ? ` · Ngày sinh: ${escHtml(c.dob)}` : ''}
                </div>
              </div>
            </div>
            <div style="display:flex;align-items:center;gap:8px;">
              <span class="chip ${ (c.current_points??100)>=80 ? 'chip-green' : 'chip-red' }" style="font-size:0.75rem;font-weight:700;">
                ⭐ ${c.current_points ?? 100}đ
              </span>
              <button class="btn btn-outline btn-sm" style="padding:4px 8px;font-size:0.72rem;border-color:var(--blue);color:var(--blue);" onclick="showStudentCard('${escHtml(c.student_code)}')">
                🪪 Thẻ QR
              </button>
              <button class="btn btn-outline btn-sm" style="padding:4px 8px;font-size:0.72rem;border-color:var(--red);color:var(--red);" onclick="promptUnlinkChild(${c.id}, '${escHtml(c.full_name)}')">
                🗑️ Gỡ
              </button>
            </div>
          </div>
        `).join('')}
      </div>`;
  } catch(e) {
    container.innerHTML = errorRow(e, 1);
  }
}

async function promptUnlinkChild(studentId, studentName) {
  if (!confirm(`Bạn có chắc chắn muốn hủy liên kết tài khoản với con em "${studentName}"?\nSau khi hủy, bạn sẽ không xem được điểm danh hay gửi đơn xin phép cho con nữa.`)) return;
  try {
    const res = await api('DELETE', `/api/v1/s/${schoolId}/parents/unlink-child/${studentId}`);
    toast('✅ Đã Hủy Liên Kết', res.message, 'success');
    const meRes = await api('GET', '/api/v1/auth/me');
    currentUser = meRes.user;
    loadParentChildrenList();
    if (document.getElementById('view-my-attendance')?.classList.contains('active')) {
      loadMyAttendance();
    }
  } catch(e) {
    toast('Lỗi', e.detail || 'Không thể hủy liên kết.', 'error');
  }
}

// ── Teacher/Headmaster Assign Parent Logic ────────
function openAssignParentModal(studentId, studentName, studentCode, parentPhone) {
  document.getElementById('apStudentId').value = studentId;
  document.getElementById('apStudentSub').innerText = `Học sinh: ${studentName} (${studentCode})`;
  document.getElementById('apParentIdent').value = parentPhone || '';
  document.getElementById('apRelation').value = 'Phụ huynh';

  const stu = (window.currentStudentsList || []).find(s => s.id === studentId);
  const wrap = document.getElementById('apExistingLinksWrap');
  const list = document.getElementById('apExistingLinksList');
  if (stu && stu.linked_parents && stu.linked_parents.length > 0) {
    wrap.style.display = 'block';
    list.innerHTML = stu.linked_parents.map(p => `
      <div style="display:flex;align-items:center;justify-content:space-between;padding:4px 0;font-size:0.8rem;border-bottom:1px solid var(--border);">
        <span>👨‍👩‍👧 <b>${escHtml(p.parent_full_name || p.parent_username)}</b> (@${escHtml(p.parent_username)}) - 📞 ${escHtml(p.parent_phone || '—')}</span>
        <button class="btn btn-outline btn-xs" style="color:var(--red);border-color:transparent;padding:1px 6px;" onclick="promptUnlinkParent(${studentId}, ${p.parent_user_id}, '${escHtml(p.parent_full_name || p.parent_username)}')">Gỡ</button>
      </div>
    `).join('');
  } else {
    wrap.style.display = 'none';
    list.innerHTML = '';
  }

  openModal('modalAssignParent');
}

async function submitAssignParent() {
  const studentId = parseInt(document.getElementById('apStudentId').value);
  const ident = document.getElementById('apParentIdent').value.trim();
  const rel = document.getElementById('apRelation').value;

  if (!ident) {
    toast('Thiếu Thông Tin', 'Vui lòng nhập Số điện thoại, Username hoặc Email của phụ huynh.', 'warning');
    return;
  }

  try {
    const res = await api('POST', `/api/v1/s/${schoolId}/students/${studentId}/assign-parent`, {
      parent_identifier: ident,
      relation_name: rel
    });
    toast('🎉 Gán Thành Công', res.message, 'success');
    closeModal('modalAssignParent');
    loadStudents();
  } catch(e) {
    toast('Lỗi Gán Phụ Huynh', e.detail || 'Không thể gán phụ huynh.', 'error');
  }
}

async function promptUnlinkParent(studentId, parentUserId, parentName) {
  if (!confirm(`Bạn có chắc muốn gỡ tài khoản phụ huynh "${parentName}" khỏi học sinh này?`)) return;
  try {
    const res = await api('DELETE', `/api/v1/s/${schoolId}/students/${studentId}/unlink-parent/${parentUserId}`);
    toast('✅ Đã Gỡ Liên Kết', res.message, 'success');
    closeModal('modalAssignParent');
    loadStudents();
  } catch(e) {
    toast('Lỗi', e.detail || 'Không thể gỡ liên kết.', 'error');
  }
}



export {
  copyParentInviteCode, loadAccount, loadParentChildrenList, loadStudentParentInviteCode, openAssignParentModal, openLinkChildModal, promptUnlinkChild, promptUnlinkParent, requestOTP, rotateMyParentInviteCode, startFaceVerification, submitAssignParent, submitIDCard, submitLinkChild, submitOTP, switchLinkChildTab
};
