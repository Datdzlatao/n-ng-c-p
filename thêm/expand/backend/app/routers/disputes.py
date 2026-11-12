"""
app/routers/disputes.py — 2-level dispute system
POST /api/v1/s/{school_id}/disputes              — Create dispute (STUDENT/PARENT)
GET  /api/v1/s/{school_id}/disputes              — List disputes (TEACHER/INSPECTOR)
PUT  /api/v1/s/{school_id}/disputes/{id}/resolve — Resolve or escalate (TEACHER→INSPECTOR)
"""
import json
import logging
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import Optional

from app.database import get_db
from app.core.deps import get_current_user, require_role

router = APIRouter(prefix="/api/v1/s/{school_id}/disputes", tags=["Disputes"])
log    = logging.getLogger("stem.disputes")


class CreateDispute(BaseModel):
    attendance_log_id: Optional[int] = None
    student_id:        int
    reason:            str
    proof_image_url:   Optional[str] = None


class ResolveDispute(BaseModel):
    action:          str           # APPROVE | REJECT | ESCALATE
    resolution_note: Optional[str] = None


def _check_scope(school_id: int, current: dict):
    if current.get("role") in ("ADMIN", "PLATFORM_ADMIN"):
        return
    if current.get("school_id") != school_id:
        raise HTTPException(403, "Không thuộc trường này.")


@router.post("")
async def create_dispute(school_id: int, req: CreateDispute, current: dict = Depends(get_current_user)):
    _check_scope(school_id, current)
    conn = get_db()
    try:
        # Kiểm tra quyền: Chỉ chính học sinh đó, phụ huynh liên kết, hoặc giáo viên/admin mới được tạo khiếu nại
        if current["role"] == "STUDENT":
            stu = conn.execute("SELECT id FROM students WHERE user_id=? AND school_id=?", (current["user_id"], school_id)).fetchone()
            if not stu or stu["id"] != req.student_id:
                raise HTTPException(403, "Bạn chỉ có thể gửi khiếu nại cho chính mình.")
        elif current["role"] == "PARENT":
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
                    raise HTTPException(403, "Bạn chỉ có thể gửi khiếu nại cho con mình.")

        # Mark attendance log as disputed
        if req.attendance_log_id:
            att = conn.execute("SELECT id FROM attendance_logs WHERE id=? AND student_id=? AND school_id=?",
                               (req.attendance_log_id, req.student_id, school_id)).fetchone()
            if not att:
                raise HTTPException(404, "Bản ghi điểm danh không tồn tại hoặc không khớp với học sinh.")
            conn.execute("UPDATE attendance_logs SET is_disputed=1 WHERE id=? AND school_id=?",
                         (req.attendance_log_id, school_id))

        conn.execute("""
            INSERT INTO disputes (attendance_log_id, student_id, school_id, reason, proof_image_url, level, status)
            VALUES (?,?,?,?,?,'LEVEL_1_TEACHER','PENDING')
        """, (req.attendance_log_id, req.student_id, school_id, req.reason, req.proof_image_url))
        conn.commit()
        return {"status": "success", "message": "Đã gửi khiếu nại đến GVCN. Thời gian xử lý: 24-48 giờ."}
    finally:
        conn.close()


@router.get("")
async def list_disputes(
    school_id: int,
    status:    Optional[str] = Query(None),
    level:     Optional[str] = Query(None),
    student_id: Optional[int] = Query(None),
    current:   dict = Depends(get_current_user)
):
    _check_scope(school_id, current)
    conn = get_db()
    try:
        sql    = """
            SELECT d.*, s.full_name as student_name, s.student_code, c.name as class_name
            FROM disputes d
            JOIN students s ON d.student_id = s.id
            LEFT JOIN classes c ON s.class_id = c.id
            WHERE d.school_id=?
        """
        params = [school_id]
        if status:
            sql += " AND d.status=?"
            params.append(status)
        if level:
            sql += " AND d.level=?"
            params.append(level)
        if student_id:
            sql += " AND d.student_id=?"
            params.append(student_id)

        # STUDENT: only see own disputes
        if current["role"] == "STUDENT":
            sql += " AND s.user_id=?"
            params.append(current["user_id"])
        # PARENT: only see own children's disputes
        elif current["role"] == "PARENT":
            sql += """ AND (
                s.id IN (SELECT student_id FROM parent_student_links WHERE parent_user_id=?)
                OR s.parent_phone=(SELECT phone FROM users WHERE id=?)
            )"""
            params += [current["user_id"], current["user_id"]]
        # TEACHER: only their class's disputes at level 1
        elif current["role"] == "TEACHER":
            sql += " AND d.level='LEVEL_1_TEACHER' AND c.homeroom_teacher_id=(SELECT id FROM users WHERE school_id=? AND username=?)"
            params += [school_id, current["username"]]
        # INSPECTOR: sees all level 2
        elif current["role"] == "INSPECTOR":
            sql += " AND d.level='LEVEL_2_INSPECTOR'"

        sql += " ORDER BY d.created_at DESC LIMIT 200"
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


@router.put("/{dispute_id}/resolve")
async def resolve_dispute(
    school_id: int, dispute_id: int, req: ResolveDispute,
    current: dict = Depends(require_role("TEACHER", "INSPECTOR", "HEADMASTER", "ADMIN"))
):
    _check_scope(school_id, current)
    if req.action not in ("APPROVE", "REJECT", "ESCALATE"):
        raise HTTPException(422, "action phải là APPROVE, REJECT hoặc ESCALATE.")
    conn = get_db()
    try:
        row = conn.execute("SELECT * FROM disputes WHERE id=? AND school_id=?", (dispute_id, school_id)).fetchone()
        if not row:
            raise HTTPException(404, "Không tìm thấy khiếu nại.")
        if row["status"] not in ("PENDING", "ESCALATED"):
            raise HTTPException(409, f"Khiếu nại đã được xử lý: {row['status']}.")

        # Phân quyền xử lý cấp độ
        if current.get("role") == "TEACHER":
            if row["level"] != "LEVEL_1_TEACHER":
                raise HTTPException(403, "Khiếu nại này đã chuyển lên Giám Thị Cấp 2, GVCN không thể xử lý.")
            # Kiểm tra GVCN đúng lớp
            homeroom = conn.execute("""
                SELECT c.id FROM classes c
                JOIN students s ON s.class_id = c.id
                WHERE s.id=? AND c.homeroom_teacher_id=(SELECT id FROM users WHERE school_id=? AND username=?)
            """, (row["student_id"], school_id, current["username"])).fetchone()
            if not homeroom:
                raise HTTPException(403, "Chỉ Giáo Viên Chủ Nhiệm của học sinh này mới có quyền xử lý khiếu nại.")

        new_status = req.action if req.action != "ESCALATE" else "ESCALATED"
        new_level  = row["level"]
        if req.action == "ESCALATE":
            new_level = "LEVEL_2_INSPECTOR"

        conn.execute("""
            UPDATE disputes SET status=?, level=?, resolver_id=?, resolution_note=?,
                                updated_at=datetime('now','localtime')
            WHERE id=?
        """, (new_status, new_level, current["user_id"], req.resolution_note, dispute_id))

        # Nếu chấp nhận khiếu nại: Đổi log sang EXCUSED và HOÀN LẠI ĐIỂM KỶ LUẬT
        if req.action == "APPROVE" and row["attendance_log_id"]:
            att_row = conn.execute("SELECT status, uniform_status FROM attendance_logs WHERE id=?", (row["attendance_log_id"],)).fetchone()
            conn.execute("UPDATE attendance_logs SET status='EXCUSED', is_disputed=0 WHERE id=?", (row["attendance_log_id"],))

            # Tính toán điểm cần hoàn trả
            school_row = conn.execute("SELECT rules_config FROM schools WHERE id=?", (school_id,)).fetchone()
            rules = json.loads(school_row["rules_config"] or "{}") if school_row else {}
            time_rules = rules.get("time_rules") if isinstance(rules.get("time_rules"), dict) else {}
            uniform_rules = rules.get("uniform_rules") if isinstance(rules.get("uniform_rules"), dict) else {}

            restore_pts = 0
            if att_row:
                if att_row["status"] == "LATE":
                    restore_pts += rules.get("late_deduct_points") or time_rules.get("late_deduct_points", 2)
                elif att_row["status"] == "ABSENT":
                    restore_pts += rules.get("absent_deduct_points", 5)
                if att_row["uniform_status"] == "VIOLATION":
                    restore_pts += rules.get("violation_deduct_points") or uniform_rules.get("shirt", {}).get("violation_deduct_points", 3)

            if restore_pts > 0:
                conn.execute("UPDATE students SET current_points = MIN(100, current_points + ?) WHERE id=?", (restore_pts, row["student_id"]))

        elif req.action == "REJECT" and row["attendance_log_id"]:
            conn.execute("UPDATE attendance_logs SET is_disputed=0 WHERE id=?", (row["attendance_log_id"],))

        conn.commit()
        msg = {"APPROVE": "Đã chấp nhận khiếu nại và hoàn trả điểm hạnh kiểm.", "REJECT": "Đã từ chối khiếu nại.", "ESCALATE": "Đã chuyển lên Giám Thị Cấp 2."}[req.action]
        return {"status": "success", "message": msg}
    finally:
        conn.close()
