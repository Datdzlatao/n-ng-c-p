"""
app/routers/leaves.py — Leave request management
POST /api/v1/s/{school_id}/leaves             — Submit (STUDENT/PARENT)
GET  /api/v1/s/{school_id}/leaves             — List (TEACHER/HEADMASTER)
PUT  /api/v1/s/{school_id}/leaves/{id}/approve — Approve/reject (TEACHER/HEADMASTER)
"""
import json
import logging
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import Optional

from app.database import get_db
from app.core.deps import get_current_user, require_role

router = APIRouter(prefix="/api/v1/s/{school_id}/leaves", tags=["Leave Requests"])
log    = logging.getLogger("stem.leaves")


class CreateLeave(BaseModel):
    student_id: int
    start_date: str
    end_date:   str
    reason:     str


class ApproveLeave(BaseModel):
    action: str      # APPROVE | REJECT
    note:   Optional[str] = None


def _check_scope(school_id: int, current: dict):
    if current.get("role") in ("ADMIN", "PLATFORM_ADMIN"):
        return
    if current.get("school_id") != school_id:
        raise HTTPException(403, "Không thuộc trường này.")


@router.post("")
async def create_leave(school_id: int, req: CreateLeave, current: dict = Depends(get_current_user)):
    _check_scope(school_id, current)
    if req.start_date > req.end_date:
        raise HTTPException(422, "Ngày bắt đầu không được lớn hơn ngày kết thúc.")

    conn = get_db()
    try:
        parent_user_id = None
        # Kiểm tra tính hợp lệ của người tạo đơn
        if current["role"] == "STUDENT":
            stu = conn.execute("SELECT id FROM students WHERE user_id=? AND school_id=?", (current["user_id"], school_id)).fetchone()
            if not stu or stu["id"] != req.student_id:
                raise HTTPException(403, "Bạn chỉ có thể tạo đơn xin phép cho chính mình.")
        elif current["role"] == "PARENT":
            parent_user_id = current["user_id"]
            link = conn.execute(
                "SELECT id FROM parent_student_links WHERE parent_user_id=? AND student_id=? AND school_id=?",
                (current["user_id"], req.student_id, school_id)
            ).fetchone()
            if not link:
                stu = conn.execute("""
                    SELECT id FROM students
                    WHERE id=? AND school_id=? AND parent_phone=(SELECT phone FROM users WHERE id=?)
                """, (req.student_id, school_id, current["user_id"])).fetchone()
                if not stu:
                    raise HTTPException(403, "Bạn chỉ có thể tạo đơn xin phép cho con mình.")
        elif current["role"] in ("TEACHER", "HEADMASTER", "ADMIN"):
            parent_user_id = current["user_id"]

        conn.execute("""
            INSERT INTO leave_requests (student_id, parent_user_id, school_id, start_date, end_date, reason)
            VALUES (?,?,?,?,?,?)
        """, (req.student_id, parent_user_id, school_id, req.start_date, req.end_date, req.reason))
        conn.commit()
        return {"status": "success", "message": "Đã gửi đơn xin phép đến GVCN."}
    finally:
        conn.close()


@router.get("")
async def list_leaves(
    school_id: int,
    status:     Optional[str] = Query(None),
    student_id: Optional[int] = Query(None),
    current:    dict = Depends(get_current_user)
):
    _check_scope(school_id, current)
    conn = get_db()
    try:
        sql    = """
            SELECT l.*, s.full_name as student_name, s.student_code, c.name as class_name
            FROM leave_requests l
            JOIN students s ON l.student_id = s.id
            LEFT JOIN classes c ON s.class_id = c.id
            WHERE l.school_id=?
        """
        params = [school_id]
        if status:
            sql += " AND l.status=?"
            params.append(status)
        if student_id:
            sql += " AND l.student_id=?"
            params.append(student_id)

        # STUDENT: only own leave requests
        if current["role"] == "STUDENT":
            sql += " AND s.user_id=?"
            params.append(current["user_id"])
        # PARENT: only own children's leave requests
        elif current["role"] == "PARENT":
            sql += """ AND (
                s.id IN (SELECT student_id FROM parent_student_links WHERE parent_user_id=?)
                OR s.parent_phone=(SELECT phone FROM users WHERE id=?)
            )"""
            params += [current["user_id"], current["user_id"]]
        # TEACHER: only their class's requests
        elif current["role"] == "TEACHER":
            sql += " AND c.homeroom_teacher_id=(SELECT id FROM users WHERE school_id=? AND username=?)"
            params += [school_id, current["username"]]

        sql += " ORDER BY l.created_at DESC LIMIT 200"
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


@router.put("/{leave_id}/approve")
async def approve_leave(
    school_id: int, leave_id: int, req: ApproveLeave,
    current: dict = Depends(require_role("TEACHER", "HEADMASTER", "ADMIN"))
):
    _check_scope(school_id, current)
    if req.action not in ("APPROVE", "REJECT"):
        raise HTTPException(422, "action phải là APPROVE hoặc REJECT.")
    conn = get_db()
    try:
        row = conn.execute("SELECT * FROM leave_requests WHERE id=? AND school_id=?", (leave_id, school_id)).fetchone()
        if not row:
            raise HTTPException(404, "Không tìm thấy đơn xin phép.")

        # Nếu là TEACHER, bắt buộc phải là GVCN của lớp học sinh đó
        if current.get("role") == "TEACHER":
            homeroom = conn.execute("""
                SELECT c.id FROM classes c
                JOIN students s ON s.class_id = c.id
                WHERE s.id=? AND c.homeroom_teacher_id=(SELECT id FROM users WHERE school_id=? AND username=?)
            """, (row["student_id"], school_id, current["username"])).fetchone()
            if not homeroom:
                raise HTTPException(403, "Chỉ Giáo Viên Chủ Nhiệm của học sinh này mới có quyền duyệt đơn nghỉ phép.")

        conn.execute("""
            UPDATE leave_requests SET status=?, approved_by=?, approved_at=datetime('now','localtime')
            WHERE id=?
        """, (req.action if req.action == "APPROVE" else "REJECTED", current["user_id"], leave_id))

        # Nếu duyệt đơn: Hoàn lại điểm vắng (nếu có) và cập nhật status sang EXCUSED
        if req.action == "APPROVE":
            deducted_logs = conn.execute("""
                SELECT id, status FROM attendance_logs
                WHERE student_id=? AND date_only BETWEEN ? AND ? AND school_id=? AND status IN ('ABSENT', 'LATE')
            """, (row["student_id"], row["start_date"], row["end_date"], school_id)).fetchall()

            if deducted_logs:
                school_row = conn.execute("SELECT rules_config FROM schools WHERE id=?", (school_id,)).fetchone()
                rules = json.loads(school_row["rules_config"] or "{}") if school_row else {}
                absent_pts = rules.get("absent_deduct_points", 5)
                total_refund = len(deducted_logs) * absent_pts
                conn.execute("UPDATE students SET current_points = MIN(100, current_points + ?) WHERE id=?", (total_refund, row["student_id"]))

            conn.execute("""
                UPDATE attendance_logs SET status='EXCUSED'
                WHERE student_id=? AND date_only BETWEEN ? AND ? AND school_id=?
            """, (row["student_id"], row["start_date"], row["end_date"], school_id))

        conn.commit()
        msg = "Đã duyệt đơn xin phép." if req.action == "APPROVE" else "Đã từ chối đơn xin phép."
        return {"status": "success", "message": msg}
    finally:
        conn.close()
