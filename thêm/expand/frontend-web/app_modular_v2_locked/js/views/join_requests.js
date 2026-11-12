// app/js/views/join_requests.js — School Membership Join Requests
// ── Join Requests (Gia Nhập Trường) ───────────────
async function loadJoinRequests() {
  const tbl = document.getElementById('joinRequestsBody');
  if (!tbl) return;
  tbl.innerHTML = '<tr><td colspan="7" style="text-align:center;padding:24px;color:var(--muted)">Đang tải danh sách...</td></tr>';
  try {
    const res = await api('GET', `/api/v1/schools/${schoolId}/requests`);
    const rows = res.data || [];
    if (!rows.length) {
      tbl.innerHTML = emptyRow('Không có yêu cầu gia nhập nào đang chờ duyệt.', 7);
      return;
    }
    tbl.innerHTML = rows.map(item => {
      const u = item.user || {};
      const roleColor = {
        STUDENT: 'chip-blue',
        TEACHER: 'chip-purple',
        PARENT: 'chip-green',
        INSPECTOR: 'chip-orange',
      }[u.role] || 'chip-blue';
      const roleLabel = {
        STUDENT: 'Học Sinh',
        TEACHER: 'Giáo Viên',
        PARENT: 'Phụ Huynh',
        INSPECTOR: 'Giám Thị',
      }[u.role] || u.role;
      const createdStr = item.createdAt ? new Date(item.createdAt).toLocaleString('vi-VN') : '—';
      return `
        <tr>
          <td><strong>${escHtml(u.fullName || '—')}</strong></td>
          <td><code>${escHtml(u.username || '—')}</code></td>
          <td><span class="chip ${roleColor}" style="font-weight:700;">${escHtml(roleLabel)}</span></td>
          <td><code style="color:var(--blue);font-weight:700;">${escHtml(u.memberCode || '—')}</code></td>
          <td>${escHtml(u.phone || u.email || '—')}</td>
          <td style="font-size:0.8rem;color:var(--muted);">${createdStr}</td>
          <td>
            <div style="display:flex;gap:6px;flex-wrap:wrap;">
              <button class="btn btn-success" style="padding:5px 10px;font-size:0.75rem;" onclick="handleJoinRequestAction(${u.id}, 'approve')">✓ Chấp Thuận</button>
              <button class="btn btn-danger" style="padding:5px 10px;font-size:0.75rem;" onclick="handleJoinRequestAction(${u.id}, 'reject')">✕ Từ Chối</button>
            </div>
          </td>
        </tr>
      `;
    }).join('');
  } catch(e) {
    tbl.innerHTML = errorRow(e, 7);
  }
}

async function handleJoinRequestAction(userId, action) {
  const confirmMsg = action === 'approve'
    ? 'Bạn có chắc chắn muốn CHẤP THUẬN người dùng này vào trường?'
    : 'Bạn có chắc chắn muốn TỪ CHỐI yêu cầu gia nhập này?';
  if (!confirm(confirmMsg)) return;

  try {
    const res = await api('POST', `/api/v1/schools/requests/${userId}/action`, { action });
    toast(action === 'approve' ? '✅ Đã Chấp Thuận' : '❌ Đã Từ Chối', res.message || 'Thành công', 'success');
    loadJoinRequests();
    if (typeof loadPendingVerify === 'function') loadPendingVerify();
    loadStats().then(updateBadges);
  } catch(e) {
    toast('Lỗi', e.detail || e.message || 'Không thể xử lý yêu cầu', 'error');
  }
}



export {
  handleJoinRequestAction, loadJoinRequests
};
