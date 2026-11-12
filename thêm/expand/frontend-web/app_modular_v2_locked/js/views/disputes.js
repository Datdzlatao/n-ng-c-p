// app/js/views/disputes.js — Attendance Disputes Management
// ── Disputes ──────────────────────────────────────
async function loadDisputes() {
  const status = document.getElementById('disputeFilter')?.value || '';
  const tbl    = document.getElementById('disputeBody');
  tbl.innerHTML = '<tr><td colspan="7" style="text-align:center;padding:24px;color:var(--muted)">Đang tải...</td></tr>';
  try {
    const rows = await api('GET', `/api/v1/s/${schoolId}/disputes?status=${status}`);
    if (!rows.length) { tbl.innerHTML = emptyRow('Không có khiếu nại nào.',7); return; }
    tbl.innerHTML = rows.map(d => `
      <tr>
        <td><strong>${escHtml(d.student_name)}</strong></td>
        <td>${escHtml(d.class_name||'—')}</td>
        <td>${escHtml(d.reason)}</td>
        <td><span class="chip ${d.level==='LEVEL_1_TEACHER'?'chip-blue':'chip-purple'}">${d.level==='LEVEL_1_TEACHER'?'Cấp 1':'Cấp 2'}</span></td>
        <td>${disputeChip(d.status)}</td>
        <td style="font-size:0.78rem;color:var(--muted)">${escHtml(d.created_at?.slice(0,10)||'—')}</td>
        <td>
          ${d.status==='PENDING' ? `
            <button class="btn btn-success" style="padding:4px 8px;font-size:0.72rem;" onclick="resolveDispute(${d.id},'APPROVE')">✓ Duyệt</button>
            <button class="btn btn-danger"  style="padding:4px 8px;font-size:0.72rem;" onclick="resolveDispute(${d.id},'REJECT')">✕</button>
            ${d.level==='LEVEL_1_TEACHER'?`<button class="btn btn-outline" style="padding:4px 8px;font-size:0.72rem;" onclick="resolveDispute(${d.id},'ESCALATE')">↑ Cấp 2</button>`:''}
          ` : '—'}
        </td>
      </tr>`).join('');
  } catch(e) { tbl.innerHTML = errorRow(e,7); }
}

function disputeChip(s) {
  const m = {
    PENDING: '<span class="chip chip-orange">Chờ Xử</span>',
    APPROVE: '<span class="chip chip-green">Chấp Nhận</span>',
    APPROVED: '<span class="chip chip-green">Chấp Nhận</span>',
    REJECT: '<span class="chip chip-red">Từ Chối</span>',
    REJECTED: '<span class="chip chip-red">Từ Chối</span>',
    ESCALATE: '<span class="chip chip-purple">Leo Thang</span>',
    ESCALATED: '<span class="chip chip-purple">Leo Thang</span>'
  };
  return m[s] || `<span class="chip chip-muted">${escHtml(s)}</span>`;
}

async function resolveDispute(id, action) {
  try {
    const res = await api('PUT', `/api/v1/s/${schoolId}/disputes/${id}/resolve`, { action });
    toast('✅ Đã Xử Lý', res.message, 'success');
    loadDisputes(); loadStats().then(updateBadges);
  } catch(e) { toast('Lỗi', e.detail||'', 'error'); }
}



export {
  disputeChip, loadDisputes, resolveDispute
};
