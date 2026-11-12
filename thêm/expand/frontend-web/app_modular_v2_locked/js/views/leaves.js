// app/js/views/leaves.js — Absence Leave Requests & Approvals
// ── Leaves ────────────────────────────────────────
async function loadLeaves() {
  const status = document.getElementById('leaveFilter')?.value || '';
  const tbl    = document.getElementById('leaveBody');
  tbl.innerHTML = '<tr><td colspan="7" style="text-align:center;padding:24px;color:var(--muted)">Đang tải...</td></tr>';
  try {
    const rows = await api('GET', `/api/v1/s/${schoolId}/leaves?status=${status}`);
    if (!rows.length) { tbl.innerHTML = emptyRow('Không có đơn nào.', 7); return; }
    tbl.innerHTML = rows.map(l => `
      <tr>
        <td><strong>${escHtml(l.student_name)}</strong></td>
        <td>${escHtml(l.class_name||'—')}</td>
        <td>${escHtml(l.start_date)}</td>
        <td>${escHtml(l.end_date)}</td>
        <td>${escHtml(l.reason)}</td>
        <td>${leaveChip(l.status)}</td>
        <td>
          ${l.status==='PENDING'?`
            <button class="btn btn-success" style="padding:4px 8px;font-size:0.72rem;" onclick="approveLeave(${l.id},'APPROVE')">✓</button>
            <button class="btn btn-danger" style="padding:4px 8px;font-size:0.72rem;" onclick="approveLeave(${l.id},'REJECT')">✕</button>
          `:'—'}
        </td>
      </tr>`).join('');
  } catch(e) { tbl.innerHTML = errorRow(e,7); }
}

function leaveChip(s) {
  const m = { PENDING:'<span class="chip chip-orange">Chờ Duyệt</span>', APPROVE:'<span class="chip chip-green">Đã Duyệt</span>', REJECTED:'<span class="chip chip-red">Từ Chối</span>' };
  return m[s]||`<span class="chip chip-muted">${s}</span>`;
}
async function approveLeave(id, action) {
  try {
    await api('PUT', `/api/v1/s/${schoolId}/leaves/${id}/approve`, { action });
    toast('✅ Đã Cập Nhật','','success');
    loadLeaves(); loadStats().then(updateBadges);
  } catch(e) { toast('Lỗi', e.detail||'', 'error'); }
}



export {
  approveLeave, leaveChip, loadLeaves
};
