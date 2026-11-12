"""
app/routers/classes.py — Class management
GET  /api/v1/s/{school_id}/classes
POST /api/v1/s/{school_id}/classes
GET  /api/v1/s/{school_id}/classes/{id}/students
GET  /api/v1/s/{school_id}/classes/{id}/scores
"""
import secrets, logging
from datetime import datetime, date
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel

from app.database import get_db
from app.core.deps import get_current_user, require_role

router = APIRouter(prefix="/api/v1/s/{school_id}/classes", tags=["Classes"])
log    = logging.getLogger("stem.classes")


class CreateClass(BaseModel):
    name:                   str
    grade_level:            int
    homeroom_teacher_id:    Optional[int] = None
    academic_year:          str = "2025-2026"


class UpdateClass(BaseModel):
    name:                   Optional[str] = None
    grade_level:            Optional[int] = None
    homeroom_teacher_id:    Optional[int] = None
    academic_year:          Optional[str] = None


class RollCallItem(BaseModel):
    student_id:     int
    status:         str  # ON_TIME | LATE | EXCUSED | ABSENT
    uniform_status: Optional[str] = "OK"  # OK | VIOLATION
    note:           Optional[str] = None


class RollCallRequest(BaseModel):
    items: List[RollCallItem]


class JoinClassRequest(BaseModel):
    invite_code: str


class AssignTeacherRequest(BaseModel):
    teacher_id: Optional[int] = None


def _check_scope(school_id: int, current: dict):
    if current.get("role") in ("ADMIN", "PLATFORM_ADMIN"):
        return
    if current.get("school_id") != school_id:
        raise HTTPException(403, "Không thuộc trường này.")


def _check_teacher_class_access(conn, school_id: int, class_id: int, current: dict):
    """
    Kiểm tra quyền truy cập lớp học:
    - ADMIN / PLATFORM_ADMIN / HEADMASTER / INSPECTOR: toàn quyền trong trường.
    - TEACHER: bắt buộc phải là GVCN của class_id này.
    """
    _check_scope(school_id, current)
    if current.get("role") in ("ADMIN", "PLATFORM_ADMIN", "HEADMASTER", "INSPECTOR"):
        return
    if current.get("role") == "TEACHER":
        user_id = current.get("user_id") or current.get("id")
        username = current.get("username")
        cls = conn.execute("""
            SELECT id FROM classes
            WHERE id=? AND school_id=? AND is_active=1
              AND (homeroom_teacher_id=? OR homeroom_teacher_id=(SELECT id FROM users WHERE school_id=? AND username=?))
        """, (class_id, school_id, user_id, school_id, username)).fetchone()
        if not cls:
            raise HTTPException(403, "Bạn không có quyền quản lý lớp này (chỉ dành cho GVCN của lớp).")
    else:
        raise HTTPException(403, "Bạn không có quyền truy cập thông tin lớp này.")


@router.get("")
async def list_classes(school_id: int, current: dict = Depends(get_current_user)):
    _check_scope(school_id, current)
    conn = get_db()
    try:
        rows = conn.execute("""
            SELECT c.*, u.full_name as teacher_name,
                   (SELECT COUNT(*) FROM students s WHERE s.class_id=c.id AND s.is_active=1) as student_count
            FROM classes c
            LEFT JOIN users u ON c.homeroom_teacher_id = u.id
            WHERE c.school_id=? AND c.is_active=1
            ORDER BY c.grade_level, c.name
        """, (school_id,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


@router.get("/my-homeroom")
async def get_my_homeroom(
    school_id: int,
    class_id: Optional[int] = Query(None),
    current: dict = Depends(get_current_user)
):
    """
    Lấy thông tin tổng quan lớp chủ nhiệm của giáo viên đang đăng nhập:
    - Metadata lớp (tên lớp, khối, sĩ số, năm học)
    - Thống kê sĩ số tiết 1 hôm nay (có mặt, đi trễ, có phép, vắng/chưa tới, vi phạm đồng phục)
    - Tỷ lệ chuyên cần realtime (%)
    - Đơn xin phép và khiếu nại chờ xử lý
    """
    _check_scope(school_id, current)
    conn = get_db()
    try:
        user_id = current.get("user_id") or current.get("id")
        username = current.get("username")
        role = current.get("role", "TEACHER")

        # 1. Tìm lớp chủ nhiệm
        cls = None
        if class_id:
            cls = conn.execute("""
                SELECT c.*, u.full_name as teacher_name
                FROM classes c
                LEFT JOIN users u ON c.homeroom_teacher_id = u.id
                WHERE c.id=? AND c.school_id=? AND c.is_active=1
            """, (class_id, school_id)).fetchone()
        elif role == "TEACHER":
            cls = conn.execute("""
                SELECT c.*, u.full_name as teacher_name
                FROM classes c
                LEFT JOIN users u ON c.homeroom_teacher_id = u.id
                WHERE c.school_id=? AND c.is_active=1
                  AND (c.homeroom_teacher_id=? OR c.homeroom_teacher_id=(SELECT id FROM users WHERE school_id=? AND username=?))
                LIMIT 1
            """, (school_id, user_id, school_id, username)).fetchone()
        elif role in ("HEADMASTER", "ADMIN", "PLATFORM_ADMIN", "INSPECTOR"):
            cls = conn.execute("""
                SELECT c.*, u.full_name as teacher_name
                FROM classes c
                LEFT JOIN users u ON c.homeroom_teacher_id = u.id
                WHERE c.school_id=? AND c.is_active=1
                ORDER BY c.grade_level, c.name
                LIMIT 1
            """, (school_id,)).fetchone()

        if not cls:
            return {
                "has_class": False,
                "is_homeroom": False,
                "message": "Tài khoản Giáo viên chưa được Ban Giám Hiệu bổ nhiệm làm GVCN cho lớp nào."
            }

        target_class_id = cls["id"]
        today = datetime.now().strftime("%Y-%m-%d")

        # 2. Thống kê sĩ số học sinh
        total_students = conn.execute(
            "SELECT COUNT(*) FROM students WHERE class_id=? AND school_id=? AND is_active=1 AND is_deleted=0",
            (target_class_id, school_id)
        ).fetchone()[0]

        # Log điểm danh hôm nay
        att_rows = conn.execute("""
            SELECT a.status, a.uniform_status, COUNT(*) as cnt
            FROM attendance_logs a
            JOIN students s ON a.student_id = s.id
            WHERE s.class_id=? AND a.school_id=? AND a.date_only=?
            GROUP BY a.status, a.uniform_status
        """, (target_class_id, school_id, today)).fetchall()

        on_time_count = 0
        late_count = 0
        excused_count = 0
        absent_count = 0
        uniform_violation_count = 0

        for r in att_rows:
            st = r["status"]
            if st == "ON_TIME":
                on_time_count += r["cnt"]
            elif st == "LATE":
                late_count += r["cnt"]
            elif st == "EXCUSED":
                excused_count += r["cnt"]
            elif st == "ABSENT":
                absent_count += r["cnt"]

            if r["uniform_status"] == "VIOLATION":
                uniform_violation_count += r["cnt"]

        # Đơn xin phép đã duyệt hôm nay nhưng chưa có log điểm danh
        approved_leaves_today = conn.execute("""
            SELECT COUNT(DISTINCT l.student_id)
            FROM leave_requests l
            JOIN students s ON l.student_id = s.id
            WHERE s.class_id=? AND l.school_id=? AND l.status='APPROVED'
              AND ? BETWEEN l.start_date AND l.end_date
              AND l.student_id NOT IN (
                  SELECT student_id FROM attendance_logs WHERE date_only=? AND school_id=?
              )
        """, (target_class_id, school_id, today, today, school_id)).fetchone()[0]

        excused_count += approved_leaves_today
        present_count = on_time_count + late_count

        # Vắng / Chưa tới = Tổng số - (Có mặt + Có phép)
        unexcused_count = max(0, total_students - (present_count + excused_count))
        attendance_rate = round((present_count / max(1, total_students)) * 100, 1)

        # Đơn phép đang chờ duyệt của lớp
        pending_leaves_count = conn.execute("""
            SELECT COUNT(*) FROM leave_requests l
            JOIN students s ON l.student_id = s.id
            WHERE s.class_id=? AND l.school_id=? AND l.status='PENDING'
        """, (target_class_id, school_id)).fetchone()[0]

        # Khiếu nại Cấp 1 đang chờ xử lý của lớp
        pending_disputes_count = conn.execute("""
            SELECT COUNT(*) FROM disputes d
            JOIN students s ON d.student_id = s.id
            WHERE s.class_id=? AND d.school_id=? AND d.status='PENDING' AND d.level='LEVEL_1_TEACHER'
        """, (target_class_id, school_id)).fetchone()[0]

        return {
            "has_class": True,
            "class": {
                "id": cls["id"],
                "name": cls["name"],
                "grade_level": cls["grade_level"],
                "academic_year": cls["academic_year"],
                "teacher_name": cls["teacher_name"] or current.get("full_name"),
                "invite_code": cls["invite_code"]
            },
            "stats": {
                "date": today,
                "total_students": total_students,
                "present_count": present_count,
                "on_time_count": on_time_count,
                "late_count": late_count,
                "excused_count": excused_count,
                "unexcused_count": unexcused_count,
                "uniform_violation_count": uniform_violation_count,
                "attendance_rate": attendance_rate,
                "pending_leaves_count": pending_leaves_count,
                "pending_disputes_count": pending_disputes_count
            }
        }
    finally:
        conn.close()


@router.post("")
async def create_class(school_id: int, req: CreateClass, current: dict = Depends(require_role("HEADMASTER"))):
    _check_scope(school_id, current)
    conn = get_db()
    try:
        teacher_id = req.homeroom_teacher_id
        if teacher_id:
            # Xác thực giáo viên có thuộc trường và có role TEACHER không
            t = conn.execute("""
                SELECT id, full_name FROM users
                WHERE id=? AND school_id=? AND role='TEACHER' AND status='ACTIVE'
            """, (teacher_id, school_id)).fetchone()
            if not t:
                teacher_id = None
            else:
                # Nếu giáo viên này đang chủ nhiệm lớp khác, gỡ khỏi lớp đó
                conn.execute("""
                    UPDATE classes SET homeroom_teacher_id=NULL WHERE school_id=? AND homeroom_teacher_id=?
                """, (school_id, teacher_id))
                conn.execute("UPDATE users SET class_name=? WHERE id=?", (req.name, teacher_id))

        invite_code = f"INVITE_{req.name.upper().replace(' ','')}_{secrets.token_hex(4).upper()}"
        conn.execute("""
            INSERT INTO classes (school_id, name, grade_level, homeroom_teacher_id, academic_year, invite_code)
            VALUES (?,?,?,?,?,?)
        """, (school_id, req.name, req.grade_level, teacher_id, req.academic_year, invite_code))
        conn.commit()
        return {"status": "success", "message": f"Đã tạo lớp {req.name}.", "invite_code": invite_code}
    finally:
        conn.close()


@router.get("/teachers")
async def list_school_teachers(school_id: int, current: dict = Depends(get_current_user)):
    """
    Lấy danh sách giáo viên trong trường và lớp đang chủ nhiệm (nếu có)
    để Hiệu trưởng phân công / bàn giao lớp.
    """
    _check_scope(school_id, current)
    conn = get_db()
    try:
        rows = conn.execute("""
            SELECT u.id, u.full_name, u.username, u.phone, u.email,
                   (SELECT name FROM classes c WHERE c.homeroom_teacher_id=u.id AND c.school_id=? AND c.is_active=1 LIMIT 1) as current_class,
                   (SELECT id FROM classes c WHERE c.homeroom_teacher_id=u.id AND c.school_id=? AND c.is_active=1 LIMIT 1) as current_class_id
            FROM users u
            WHERE u.school_id=? AND u.role='TEACHER' AND u.status='ACTIVE'
            ORDER BY u.full_name
        """, (school_id, school_id, school_id)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


@router.put("/{class_id}/assign-teacher")
async def assign_homeroom_teacher(
    school_id: int,
    class_id: int,
    req: AssignTeacherRequest,
    current: dict = Depends(require_role("HEADMASTER"))
):
    """
    Hiệu trưởng bàn giao / phân công hoặc hủy phân công Giáo viên chủ nhiệm (GVCN) cho lớp học.
    """
    _check_scope(school_id, current)
    conn = get_db()
    try:
        cls = conn.execute("""
            SELECT id, name, homeroom_teacher_id FROM classes WHERE id=? AND school_id=? AND is_active=1
        """, (class_id, school_id)).fetchone()
        if not cls:
            raise HTTPException(404, "Không tìm thấy lớp học.")

        old_teacher_id = cls["homeroom_teacher_id"]
        target_teacher_id = req.teacher_id if (req.teacher_id and req.teacher_id > 0) else None
        teacher_name = None

        if target_teacher_id:
            t = conn.execute("""
                SELECT id, full_name, username, role FROM users
                WHERE id=? AND school_id=? AND role='TEACHER'
            """, (target_teacher_id, school_id)).fetchone()
            if not t:
                raise HTTPException(400, "Giáo viên không hợp lệ hoặc không thuộc trường này.")
            teacher_name = t["full_name"]

            # Nếu giáo viên này đang chủ nhiệm lớp khác trong trường, giải phóng lớp đó
            conn.execute("""
                UPDATE classes SET homeroom_teacher_id=NULL
                WHERE school_id=? AND homeroom_teacher_id=? AND id!=?
            """, (school_id, target_teacher_id, class_id))

            # Đồng bộ class_name cho giáo viên mới
            conn.execute("UPDATE users SET class_name=? WHERE id=?", (cls["name"], target_teacher_id))

        # Nếu lớp có GVCN cũ và khác GVCN mới, gỡ bỏ class_name của GVCN cũ
        if old_teacher_id and old_teacher_id != target_teacher_id:
            conn.execute("UPDATE users SET class_name=NULL WHERE id=? AND class_name=?", (old_teacher_id, cls["name"]))

        conn.execute("""
            UPDATE classes SET homeroom_teacher_id=? WHERE id=? AND school_id=?
        """, (target_teacher_id, class_id, school_id))
        conn.commit()

        msg = f"Đã bàn giao lớp {cls['name']} cho GVCN {teacher_name}." if teacher_name else f"Đã hủy phân công GVCN cho lớp {cls['name']}."
        return {
            "status": "success",
            "message": msg,
            "class_id": class_id,
            "teacher_id": target_teacher_id,
            "teacher_name": teacher_name
        }
    finally:
        conn.close()


@router.put("/{class_id}")
@router.post("/{class_id}/update")
async def update_class(
    school_id: int,
    class_id: int,
    req: UpdateClass,
    current: dict = Depends(require_role("HEADMASTER"))
):
    """
    Chỉnh sửa thông tin lớp học: Đổi tên lớp, đổi khối, cập nhật bổ nhiệm GVCN, đổi năm học.
    """
    _check_scope(school_id, current)
    conn = get_db()
    try:
        cls = conn.execute("""
            SELECT id, name, grade_level, homeroom_teacher_id, academic_year
            FROM classes WHERE id=? AND school_id=? AND is_active=1
        """, (class_id, school_id)).fetchone()
        if not cls:
            raise HTTPException(404, "Không tìm thấy lớp học.")

        old_name = cls["name"]
        old_teacher_id = cls["homeroom_teacher_id"]

        new_name = req.name.strip() if req.name is not None and req.name.strip() else old_name
        new_grade = req.grade_level if req.grade_level is not None else cls["grade_level"]
        new_year = req.academic_year.strip() if req.academic_year is not None and req.academic_year.strip() else cls["academic_year"]

        # Kiểm tra trùng tên lớp khác trong cùng trường
        if new_name != old_name:
            dup = conn.execute("""
                SELECT id FROM classes WHERE school_id=? AND name=? AND id!=? AND is_active=1
            """, (school_id, new_name, class_id)).fetchone()
            if dup:
                raise HTTPException(400, f"Đã tồn tại lớp '{new_name}' trong trường.")

        # Xử lý GVCN nếu có truyền vào (có thể là None/0 để gỡ bỏ, hoặc int để đổi)
        new_teacher_id = old_teacher_id
        teacher_name = None

        if hasattr(req, 'homeroom_teacher_id') and req.homeroom_teacher_id is not None:
            if req.homeroom_teacher_id > 0:
                t = conn.execute("""
                    SELECT id, full_name, username, role FROM users
                    WHERE id=? AND school_id=? AND role='TEACHER'
                """, (req.homeroom_teacher_id, school_id)).fetchone()
                if not t:
                    raise HTTPException(400, "Giáo viên không hợp lệ hoặc không thuộc trường này.")
                new_teacher_id = t["id"]
                teacher_name = t["full_name"]

                # Gỡ giáo viên này khỏi lớp khác nếu đang chủ nhiệm
                conn.execute("""
                    UPDATE classes SET homeroom_teacher_id=NULL
                    WHERE school_id=? AND homeroom_teacher_id=? AND id!=?
                """, (school_id, new_teacher_id, class_id))

                # Gán class_name cho giáo viên mới
                conn.execute("UPDATE users SET class_name=? WHERE id=?", (new_name, new_teacher_id))
            else:
                new_teacher_id = None

            # Nếu có giáo viên cũ và bị thay đổi, gỡ class_name
            if old_teacher_id and old_teacher_id != new_teacher_id:
                conn.execute("UPDATE users SET class_name=NULL WHERE id=? AND class_name=?", (old_teacher_id, old_name))
        else:
            # Nếu giữ nguyên GVCN cũ nhưng đổi tên lớp, cập nhật class_name cho GVCN cũ
            if new_name != old_name and old_teacher_id:
                conn.execute("UPDATE users SET class_name=? WHERE id=?", (new_name, old_teacher_id))

        conn.execute("""
            UPDATE classes
            SET name=?, grade_level=?, homeroom_teacher_id=?, academic_year=?
            WHERE id=? AND school_id=?
        """, (new_name, new_grade, new_teacher_id, new_year, class_id, school_id))
        conn.commit()

        return {
            "status": "success",
            "message": f"Đã cập nhật thông tin lớp {new_name} thành công.",
            "class": {
                "id": class_id,
                "name": new_name,
                "grade_level": new_grade,
                "homeroom_teacher_id": new_teacher_id,
                "teacher_name": teacher_name,
                "academic_year": new_year
            }
        }
    finally:
        conn.close()


@router.delete("/{class_id}")
@router.post("/{class_id}/delete")
async def delete_class(
    school_id: int,
    class_id: int,
    current: dict = Depends(require_role("HEADMASTER"))
):
    """
    Xóa lớp học (chỉ cho phép khi không còn học sinh hoặc gỡ học sinh trước).
    """
    _check_scope(school_id, current)
    conn = get_db()
    try:
        cls = conn.execute("""
            SELECT id, name, homeroom_teacher_id FROM classes WHERE id=? AND school_id=? AND is_active=1
        """, (class_id, school_id)).fetchone()
        if not cls:
            raise HTTPException(404, "Không tìm thấy lớp học.")

        student_count = conn.execute("""
            SELECT COUNT(*) FROM students WHERE class_id=? AND school_id=? AND is_active=1
        """, (class_id, school_id)).fetchone()[0]

        if student_count > 0:
            raise HTTPException(400, f"Lớp {cls['name']} hiện đang có {student_count} học sinh. Vui lòng chuyển hoặc xóa học sinh trước khi xóa lớp.")

        if cls["homeroom_teacher_id"]:
            conn.execute("UPDATE users SET class_name=NULL WHERE id=?", (cls["homeroom_teacher_id"],))

        conn.execute("""
            UPDATE classes SET is_active=0, homeroom_teacher_id=NULL WHERE id=? AND school_id=?
        """, (class_id, school_id))
        conn.commit()

        return {
            "status": "success",
            "message": f"Đã xóa lớp {cls['name']} thành công."
        }
    finally:
        conn.close()


@router.get("/{class_id}/students")
async def class_students(school_id: int, class_id: int, current: dict = Depends(get_current_user)):
    _check_scope(school_id, current)
    conn = get_db()
    try:
        rows = conn.execute("""
            SELECT s.id, s.student_code, s.full_name, s.dob, s.parent_phone,
                   s.face_approved, s.current_points, s.qr_token
            FROM students s
            WHERE s.class_id=? AND s.school_id=? AND s.is_active=1
            ORDER BY s.full_name
        """, (class_id, school_id)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


@router.get("/{class_id}/scores")
async def class_scores(school_id: int, class_id: int,
                       week: Optional[int] = Query(None), current: dict = Depends(get_current_user)):
    _check_scope(school_id, current)
    conn = get_db()
    try:
        sql    = "SELECT * FROM discipline_scores WHERE school_id=? AND class_id=?"
        params = [school_id, class_id]
        if week:
            sql += " AND week_number=?"
            params.append(week)
        sql += " ORDER BY year DESC, week_number DESC LIMIT 20"
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


@router.get("/{class_id}/roster-today")
async def class_roster_today(
    school_id: int,
    class_id: int,
    current: dict = Depends(get_current_user)
):
    """
    Trả về bảng sĩ số realtime của lớp hôm nay với đầy đủ thông tin:
    - Ảnh đại diện, họ tên, mã HS, số ĐT phụ huynh
    - Trạng thái vào cổng: ON_TIME | LATE | EXCUSED | ABSENT | NOT_CHECKED_IN
    - Giờ check-in, ảnh bằng chứng từ camera AI, lỗi đồng phục
    - Trạng thái đơn xin phép hôm nay
    """
    conn = get_db()
    try:
        _check_teacher_class_access(conn, school_id, class_id, current)
        today = datetime.now().strftime("%Y-%m-%d")

        students = conn.execute("""
            SELECT s.id, s.student_code, s.full_name, s.parent_phone,
                   s.face_photo_url, s.face_approved, s.current_points
            FROM students s
            WHERE s.class_id=? AND s.school_id=? AND s.is_active=1 AND s.is_deleted=0
            ORDER BY s.full_name ASC
        """, (class_id, school_id)).fetchall()

        roster = []
        for s in students:
            sid = s["id"]

            # 1. Lấy log điểm danh mới nhất hôm nay
            att = conn.execute("""
                SELECT id, timestamp, status, uniform_status, check_type, proof_image_url
                FROM attendance_logs
                WHERE student_id=? AND school_id=? AND date_only=?
                ORDER BY id DESC LIMIT 1
            """, (sid, school_id, today)).fetchone()

            # 2. Kiểm tra đơn nghỉ phép hôm nay
            leave = conn.execute("""
                SELECT id, reason, status FROM leave_requests
                WHERE student_id=? AND school_id=?
                  AND ? BETWEEN start_date AND end_date
                ORDER BY id DESC LIMIT 1
            """, (sid, school_id, today)).fetchone()

            has_approved_leave = bool(leave and leave["status"] == "APPROVED")
            leave_pending = bool(leave and leave["status"] == "PENDING")

            if att:
                effective_status = att["status"]
                time_str = att["timestamp"].split("T")[-1][:8] if "T" in att["timestamp"] else att["timestamp"][-8:]
                proof_url = att["proof_image_url"]
                uniform_status = att["uniform_status"]
                checkin_method = att["check_type"]
                violation_details = None
                att_id = att["id"]
            elif has_approved_leave:
                effective_status = "EXCUSED"
                time_str = None
                proof_url = None
                uniform_status = "OK"
                checkin_method = "LEAVE_REQUEST"
                violation_details = None
                att_id = None
            else:
                effective_status = "NOT_CHECKED_IN"
                time_str = None
                proof_url = None
                uniform_status = "OK"
                checkin_method = None
                violation_details = None
                att_id = None

            roster.append({
                "student_id": sid,
                "student_code": s["student_code"],
                "full_name": s["full_name"],
                "parent_phone": s["parent_phone"] or "",
                "face_photo_url": s["face_photo_url"],
                "face_approved": s["face_approved"],
                "current_points": s["current_points"],
                "attendance_id": att_id,
                "status": effective_status,
                "time": time_str,
                "uniform_status": uniform_status,
                "checkin_method": checkin_method,
                "proof_image_url": proof_url,
                "violation_details": violation_details,
                "has_approved_leave": has_approved_leave,
                "leave_pending": leave_pending,
                "leave_reason": leave["reason"] if leave else None
            })

        return roster
    finally:
        conn.close()


@router.post("/{class_id}/roll-call")
async def classroom_roll_call(
    school_id: int,
    class_id: int,
    req: RollCallRequest,
    current: dict = Depends(get_current_user)
):
    """
    Điểm danh nhanh tại lớp bởi GVCN:
    - Cho phép đổi trạng thái 1-chạm hoặc ghi nhận học sinh quên quét cổng
    - Trạng thái hợp lệ: ON_TIME | LATE | EXCUSED | ABSENT
    - Ghi nhận check_type = 'MANUAL'
    """
    conn = get_db()
    try:
        _check_teacher_class_access(conn, school_id, class_id, current)
        today = datetime.now().strftime("%Y-%m-%d")
        now_ts = datetime.now().isoformat()
        teacher_name = current.get("full_name") or current.get("username")

        updated_count = 0
        for item in req.items:
            # Xác thực học sinh thuộc lớp này
            stu = conn.execute(
                "SELECT id, full_name, current_points FROM students WHERE id=? AND class_id=? AND school_id=?",
                (item.student_id, class_id, school_id)
            ).fetchone()
            if not stu:
                continue

            existing = conn.execute("""
                SELECT id, status FROM attendance_logs
                WHERE student_id=? AND school_id=? AND date_only=?
                ORDER BY id DESC LIMIT 1
            """, (item.student_id, school_id, today)).fetchone()

            if existing:
                conn.execute("""
                    UPDATE attendance_logs
                    SET status=?, uniform_status=?, check_type='MANUAL'
                    WHERE id=?
                """, (item.status, item.uniform_status or "OK", existing["id"]))
            else:
                conn.execute("""
                    INSERT INTO attendance_logs
                        (school_id, student_id, timestamp, date_only, status, uniform_status, check_type)
                    VALUES (?, ?, ?, ?, ?, ?, 'MANUAL')
                """, (school_id, item.student_id, now_ts, today, item.status, item.uniform_status or "OK"))

            updated_count += 1

        conn.commit()
        return {
            "status": "success",
            "message": f"GVCN {teacher_name} đã cập nhật điểm danh cho {updated_count} học sinh.",
            "updated_count": updated_count
        }
    finally:
        conn.close()


@router.post("/{class_id}/notify-absent-parents")
async def notify_absent_parents(
    school_id: int,
    class_id: int,
    current: dict = Depends(get_current_user)
):
    """
    1-Click gửi cảnh báo vắng mặt tới phụ huynh của các học sinh chưa có mặt sáng nay (và không có phép).
    """
    conn = get_db()
    try:
        _check_teacher_class_access(conn, school_id, class_id, current)
        today = datetime.now().strftime("%Y-%m-%d")

        cls_row = conn.execute("SELECT name FROM classes WHERE id=?", (class_id,)).fetchone()
        class_name = cls_row["name"] if cls_row else "Lớp"

        students = conn.execute("""
            SELECT s.id, s.student_code, s.full_name, s.parent_phone
            FROM students s
            WHERE s.class_id=? AND s.school_id=? AND s.is_active=1 AND s.is_deleted=0
        """, (class_id, school_id)).fetchall()

        notified_list = []
        for s in students:
            sid = s["id"]
            # Kiểm tra xem có log điểm danh có mặt hoặc đi trễ hoặc có phép không
            att = conn.execute("""
                SELECT status FROM attendance_logs
                WHERE student_id=? AND school_id=? AND date_only=? AND status IN ('ON_TIME', 'LATE', 'EXCUSED')
            """, (sid, school_id, today)).fetchone()

            if att:
                continue  # Học sinh đã có mặt hoặc có phép

            # Kiểm tra đơn nghỉ phép đã duyệt
            leave = conn.execute("""
                SELECT id FROM leave_requests
                WHERE student_id=? AND school_id=? AND status='APPROVED'
                  AND ? BETWEEN start_date AND end_date
            """, (sid, school_id, today)).fetchone()

            if leave:
                continue  # Đã có đơn nghỉ phép

            # Học sinh này vắng không phép / chưa đến trường!
            phone = (s["parent_phone"] or "").strip()
            if phone:
                log.info(f"[NOTIFY] Gửi cảnh báo vắng tới {phone} cho học sinh {s['full_name']} ({class_name})")
                notified_list.append({
                    "student_id": sid,
                    "student_code": s["student_code"],
                    "student_name": s["full_name"],
                    "parent_phone": phone
                })

        return {
            "status": "success",
            "message": f"Đã gửi cảnh báo vắng mặt tới {len(notified_list)} phụ huynh học sinh {class_name}.",
            "notified_count": len(notified_list),
            "notified_parents": notified_list
        }
    finally:
        conn.close()


@router.get("/my-class")
async def get_my_student_class(
    school_id: int,
    current: dict = Depends(get_current_user)
):
    """
    Dành cho học sinh: Lấy thông tin lớp học hiện tại của mình,
    thông tin GVCN, danh sách bạn cùng lớp, điểm thi đua tuần gần nhất.
    """
    _check_scope(school_id, current)
    user_id = current.get("user_id") or current.get("id")
    conn = get_db()
    try:
        # Tìm student record liên kết với user
        stu = conn.execute("""
            SELECT s.*, c.name as class_name, c.grade_level, c.academic_year, c.homeroom_teacher_id
            FROM students s
            LEFT JOIN classes c ON s.class_id = c.id
            WHERE s.user_id=? AND s.school_id=? AND s.is_active=1 AND s.is_deleted=0
        """, (user_id, school_id)).fetchone()

        if not stu or not stu["class_id"]:
            return {
                "has_class": False,
                "message": "Bạn chưa được xếp vào lớp nào hoặc chưa nhập mã tham gia lớp."
            }

        class_id = stu["class_id"]

        # Lấy thông tin lớp & GVCN
        cls_row = conn.execute("""
            SELECT c.*, u.full_name as teacher_name, u.phone as teacher_phone, u.email as teacher_email
            FROM classes c
            LEFT JOIN users u ON c.homeroom_teacher_id = u.id
            WHERE c.id=? AND c.school_id=?
        """, (class_id, school_id)).fetchone()

        # Danh sách bạn cùng lớp
        classmates_rows = conn.execute("""
            SELECT s.id, s.student_code, s.full_name, s.gender, s.dob, s.current_points, s.face_photo_url,
                   u.avatar_url
            FROM students s
            LEFT JOIN users u ON s.user_id = u.id
            WHERE s.class_id=? AND s.school_id=? AND s.is_active=1 AND s.is_deleted=0
            ORDER BY s.full_name ASC
        """, (class_id, school_id)).fetchall()

        # Điểm nề nếp thi đua gần nhất
        latest_score = conn.execute("""
            SELECT * FROM discipline_scores
            WHERE class_id=? AND school_id=?
            ORDER BY year DESC, week_number DESC
            LIMIT 1
        """, (class_id, school_id)).fetchone()

        # Thống kê tổng số thảo luận trong lớp
        discussions_count = conn.execute("""
            SELECT COUNT(*) FROM posts
            WHERE class_id=? AND school_id=?
        """, (class_id, school_id)).fetchone()[0]

        return {
            "has_class": True,
            "class": {
                "id": cls_row["id"],
                "name": cls_row["name"],
                "grade_level": cls_row["grade_level"],
                "academic_year": cls_row["academic_year"],
                "invite_code": cls_row["invite_code"],
                "teacher_name": cls_row["teacher_name"] or "Chưa phân công",
                "teacher_phone": cls_row["teacher_phone"] or "",
                "teacher_email": cls_row["teacher_email"] or "",
                "student_count": len(classmates_rows),
                "discussions_count": discussions_count,
            },
            "classmates": [dict(r) for r in classmates_rows],
            "latest_score": dict(latest_score) if latest_score else None
        }
    finally:
        conn.close()


@router.post("/join")
async def join_class_by_invite(
    school_id: int,
    req: JoinClassRequest,
    current: dict = Depends(get_current_user)
):
    """
    Học sinh nhập mã mời lớp (invite_code) để tham gia lớp học.
    Hỗ trợ linh hoạt:
    - Mã đầy đủ: INVITE_12C1_E124DEA9
    - Mã không có tiền tố INVITE_: 12C1_E124DEA9
    - Hoặc tên lớp nếu trong trường chỉ có 1 lớp tên đó: 12C1
    - Tự động đồng bộ trường học nếu mã thuộc trường khác (tránh lỗi mismatch school_id).
    """
    code = req.invite_code.strip().upper()
    if not code:
        raise HTTPException(400, "Vui lòng nhập mã mời lớp.")

    user_id = current.get("user_id") or current.get("id")
    conn = get_db()
    try:
        # 1. Tìm lớp theo mã mời hoặc tiền tố hoặc tên lớp trong trường hiện tại
        cls = conn.execute("""
            SELECT id, school_id, name, grade_level FROM classes
            WHERE school_id=? AND is_active=1 AND (
                UPPER(invite_code)=? OR
                UPPER(invite_code)=? OR
                UPPER(name)=?
            )
            LIMIT 1
        """, (school_id, code, f"INVITE_{code}", code)).fetchone()

        # 2. Nếu không thấy trong trường hiện tại, tìm trên toàn bộ hệ thống (xử lý lệch school_id)
        if not cls:
            cls = conn.execute("""
                SELECT id, school_id, name, grade_level FROM classes
                WHERE is_active=1 AND (
                    UPPER(invite_code)=? OR
                    UPPER(invite_code)=?
                )
                LIMIT 1
            """, (code, f"INVITE_{code}")).fetchone()
            if cls:
                # Tìm thấy lớp ở trường cls["school_id"], tự động cập nhật trường cho học sinh
                target_school_id = cls["school_id"]
                conn.execute("UPDATE users SET school_id=? WHERE id=?", (target_school_id, user_id))
                school_id = target_school_id

        if not cls:
            raise HTTPException(404, "Mã mời lớp không chính xác hoặc lớp không tồn tại. Vui lòng kiểm tra lại mã do GVCN hoặc BGH cung cấp.")

        class_id = cls["id"]
        class_name = cls["name"]

        # Cập nhật hoặc tạo student record cho user này
        stu = conn.execute("""
            SELECT id FROM students WHERE user_id=? AND school_id=?
        """, (user_id, school_id)).fetchone()

        if stu:
            conn.execute("""
                UPDATE students SET class_id=? WHERE id=?
            """, (class_id, stu["id"]))
        else:
            student_code = current.get("user_code") or current.get("student_code") or f"HS-{secrets.token_hex(3).upper()}"
            full_name = current.get("full_name") or current.get("username")
            conn.execute("""
                INSERT INTO students (user_id, school_id, class_id, student_code, full_name, is_active)
                VALUES (?, ?, ?, ?, ?, 1)
            """, (user_id, school_id, class_id, student_code, full_name))

        # Cập nhật class_name trong users table
        conn.execute("""
            UPDATE users SET class_name=? WHERE id=?
        """, (class_name, user_id))

        conn.commit()
        return {
            "status": "success",
            "message": f"Bạn đã tham gia thành công lớp {class_name}!",
            "class_id": class_id,
            "class_name": class_name
        }
    finally:
        conn.close()
