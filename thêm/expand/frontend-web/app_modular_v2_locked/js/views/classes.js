// app/js/views/classes.js — Class Management & Teacher Assignment
// ── Classes & Phân Công GVCN ───────────────────────
let cachedTeachersList = [];

async function loadSchoolTeachers() {
  try {
    cachedTeachersList = await api('GET', `/api/v1/s/${schoolId}/classes/teachers`);
    return cachedTeachersList;
  } catch(e) {
    console.error('Failed to load teachers:', e);
    return [];
  }
}

async function populateTeacherSelect(selectId, selectedTeacherId = null) {
  const sel = document.getElementById(selectId);
  if (!sel) return;
  sel.innerHTML = '<option value="">⏳ Đang tải danh sách giáo viên...</option>';
  const teachers = await loadSchoolTeachers();
  if (!teachers.length) {
    sel.innerHTML = '<option value="">(Chưa có tài khoản Giáo viên nào được kích hoạt trong trường)</option>';
    return;
  }
  const defaultLabel = (selectId === 'asgTeacherSelect')
    ? '-- Chưa phân công GVCN (Hủy bổ nhiệm) --'
    : '-- Chưa phân công GVCN (Bổ nhiệm sau) --';
  let html = `<option value="">${defaultLabel}</option>`;
  teachers.forEach(t => {
    const isSelected = selectedTeacherId && t.id === selectedTeacherId ? 'selected' : '';
    const classNote = t.current_class ? ` (Đang là GVCN ${t.current_class})` : '';
    html += `<option value="${t.id}" ${isSelected}>👨‍🏫 ${escHtml(t.full_name)} (@${escHtml(t.username)})${classNote}</option>`;
  });
  sel.innerHTML = html;
  if (!selectedTeacherId) sel.value = '';
}

async function openAddClassModal() {
  document.getElementById('aclName').value = '';
  document.getElementById('aclGrade').value = '10';
  await populateTeacherSelect('aclTeacher', null);
  const sel = document.getElementById('aclTeacher');
  if (sel) sel.value = '';
  openModal('modalAddClass');
}

let classesViewCache = [];

async function openEditClassModal(classId) {
  const cls = classesViewCache.find(c => c.id === classId);
  if (!cls) return;

  document.getElementById('eclClassId').value = classId;
  document.getElementById('eclName').value = cls.name || '';
  document.getElementById('eclGrade').value = cls.grade_level || 10;
  document.getElementById('eclYear').value = cls.academic_year || '2025-2026';

  await populateTeacherSelect('eclTeacher', cls.homeroom_teacher_id);
  openModal('modalEditClass');
}

async function doEditClass() {
  const classId = document.getElementById('eclClassId').value;
  const name = document.getElementById('eclName').value.trim();
  const grade = parseInt(document.getElementById('eclGrade').value);
  const teacherIdVal = document.getElementById('eclTeacher').value;
  const teacherId = (teacherIdVal && teacherIdVal.trim() !== '') ? parseInt(teacherIdVal) : 0;
  const academicYear = document.getElementById('eclYear').value.trim() || '2025-2026';

  if (!name) { toast('Thiếu thông tin', 'Vui lòng nhập Tên Lớp', 'error'); return; }

  try {
    const payload = {
      name: name,
      grade_level: grade,
      homeroom_teacher_id: teacherId,
      academic_year: academicYear
    };
    let res;
    try {
      res = await api('PUT', `/api/v1/s/${schoolId}/classes/${classId}`, payload);
    } catch(err) {
      res = await api('POST', `/api/v1/s/${schoolId}/classes/${classId}/update`, payload);
    }
    closeModal('modalEditClass');
    toast('✅ Cập Nhật Thành Công', res.message, 'success');
    loadClassesView();
    if (typeof loadClasses === 'function') loadClasses();
  } catch(e) {
    toast('Lỗi cập nhật lớp', e.detail || e.message || 'Không thể cập nhật thông tin lớp', 'error');
  }
}

async function doDeleteClass() {
  const classId = document.getElementById('eclClassId').value;
  const name = document.getElementById('eclName').value;
  if (!confirm(`Bạn có chắc chắn muốn xóa lớp "${name}" không?\n(Chỉ có thể xóa khi lớp không còn học sinh).`)) return;

  try {
    let res;
    try {
      res = await api('DELETE', `/api/v1/s/${schoolId}/classes/${classId}`);
    } catch(err) {
      res = await api('POST', `/api/v1/s/${schoolId}/classes/${classId}/delete`);
    }
    closeModal('modalEditClass');
    toast('✅ Đã Xóa Lớp', res.message, 'success');
    loadClassesView();
    if (typeof loadClasses === 'function') loadClasses();
  } catch(e) {
    toast('Lỗi xóa lớp', e.detail || e.message || 'Không thể xóa lớp này', 'error');
  }
}

async function openAssignTeacherModal(classId, className, currentTeacherId) {
  document.getElementById('asgClassId').value = classId;
  document.getElementById('asgClassName').value = className;
  await populateTeacherSelect('asgTeacherSelect', currentTeacherId);
  openModal('modalAssignTeacher');
}

async function doAssignTeacher() {
  const classId = document.getElementById('asgClassId').value;
  const teacherIdVal = document.getElementById('asgTeacherSelect').value;
  const teacherId = (teacherIdVal && teacherIdVal.trim() !== '') ? parseInt(teacherIdVal) : null;
  try {
    const res = await api('PUT', `/api/v1/s/${schoolId}/classes/${classId}/assign-teacher`, { teacher_id: teacherId });
    closeModal('modalAssignTeacher');
    toast('✅ Cập Nhật Thành Công', res.message, 'success');
    loadClassesView();
    if (typeof loadClasses === 'function') loadClasses();
  } catch(e) {
    toast('Lỗi cập nhật GVCN', e.detail || e.message || 'Không thể cập nhật GVCN cho lớp', 'error');
  }
}

async function loadClassesView() {
  const tbl = document.getElementById('classBody');
  try {
    const rows = await api('GET', `/api/v1/s/${schoolId}/classes`);
    classesViewCache = rows || [];
    if (!rows.length) { tbl.innerHTML = emptyRow('Chưa có lớp nào.',6); return; }
    tbl.innerHTML = rows.map(c => `
      <tr>
        <td>
          <div style="font-weight:700;font-size:0.95rem;color:var(--text);">${escHtml(c.name)}</div>
          <div style="font-size:0.72rem;color:var(--muted);font-family:var(--font-mono);">${escHtml(c.academic_year || '2025-2026')}</div>
        </td>
        <td>
          <span class="chip chip-blue" style="font-weight:700;font-size:0.75rem;">Khối ${escHtml(c.grade_level)}</span>
        </td>
        <td>
          ${c.teacher_name 
            ? `<span class="chip chip-purple" style="font-weight:700;display:inline-flex;align-items:center;gap:4px;">👨‍🏫 ${escHtml(c.teacher_name)}</span>`
            : `<span class="chip" style="background:rgba(239,68,68,0.15);color:#f87171;border:1px solid rgba(239,68,68,0.3);font-size:0.75rem;">⚠️ Chưa phân công</span>`}
        </td>
        <td>
          <strong style="color:var(--text);font-size:0.9rem;">${c.student_count||0}</strong> <span style="font-size:0.75rem;color:var(--muted);">học sinh</span>
        </td>
        <td><code style="font-size:0.78rem;color:var(--blue)">${escHtml(c.invite_code||'—')}</code></td>
        <td>
          <div style="display:flex;gap:6px;flex-wrap:wrap;align-items:center;">
            <button class="btn btn-outline btn-xs" style="padding:4px 9px;font-size:0.75rem;border-color:rgba(56,189,248,0.4);color:var(--blue);display:inline-flex;align-items:center;gap:4px;" onclick="openEditClassModal(${c.id})" title="Chỉnh sửa tên lớp, khối, GVCN, năm học">
              ✏️ Sửa Lớp
            </button>
            <button class="btn btn-primary btn-xs" style="padding:4px 9px;font-size:0.75rem;background:var(--blue);display:inline-flex;align-items:center;gap:4px;" onclick="openAssignTeacherModal(${c.id}, '${escHtml(c.name)}', ${c.homeroom_teacher_id || 'null'})" title="Bổ nhiệm hoặc bàn giao GVCN">
              👨‍🏫 Phân GVCN
            </button>
            <button class="btn btn-outline btn-xs" style="padding:4px 8px;font-size:0.72rem;" onclick="navigate('view-students')">Xem DS</button>
          </div>
        </td>
      </tr>`).join('');
  } catch(e) { tbl.innerHTML = errorRow(e,6); }
}

async function doAddClass() {
  const name  = document.getElementById('aclName').value.trim();
  const grade = parseInt(document.getElementById('aclGrade').value);
  const teacherIdVal = document.getElementById('aclTeacher') ? document.getElementById('aclTeacher').value : '';
  const teacherId = (teacherIdVal && teacherIdVal.trim() !== '') ? parseInt(teacherIdVal) : null;
  if (!name) { toast('Cần nhập Tên Lớp','','error'); return; }
  try {
    const payload = { name, grade_level: grade, homeroom_teacher_id: teacherId };
    const res = await api('POST', `/api/v1/s/${schoolId}/classes`, payload);
    closeModal('modalAddClass');
    toast('✅ Tạo Lớp Thành Công', `Mã mời: ${res.invite_code}`, 'success');
    loadClassesView();
    if (typeof loadClasses === 'function') loadClasses();
  } catch(e) { toast('Lỗi tạo lớp', e.detail||'', 'error'); }
}



export {
  doAddClass, doAssignTeacher, doDeleteClass, doEditClass, loadClassesView, loadSchoolTeachers, openAddClassModal, openAssignTeacherModal, openEditClassModal, populateTeacherSelect
};
