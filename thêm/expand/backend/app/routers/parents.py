"""
app/routers/parents.py — Parent-Student Account Linking & Family Management
Scoped to /api/v1/s/{school_id}/parents/
"""
import re, logging
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from app.database import get_db
from app.core.deps import get_current_user, require_role

router = APIRouter(prefix="/api/v1/s/{school_id}/parents", tags=["Parents"])
log    = logging.getLogger("stem.parents")


class LinkChildRequest(BaseModel):
    student_code:  Optional[str] = None
    verify_key:    Optional[str] = None   # DOB (YYYY-MM-DD or DD/MM/YYYY) or registered parent phone
    invite_code:   Optional[str] = None   # NEW: Mã Mời Phụ Huynh 1 chạm (PH-XXXXXX) do con cấp
    relation_name: Optional[str] = "Phụ huynh"  # Bố, Mẹ, Phụ huynh, Người giám hộ


class LinkByInviteCodeRequest(BaseModel):
    invite_code:   str                    # Mã Mời Phụ Huynh (PH-XXXXXX)
    relation_name: Optional[str] = "Phụ huynh"


def _check_scope(school_id: int, current: dict):
    if current.get("role") in ("ADMIN", "PLATFORM_ADMIN"):
        return
    if current.get("school_id") != school_id:
        raise HTTPException(403, "Không thuộc trường này.")


def _normalize_date_str(d_str: Optional[str]) -> str:
    """Normalize dates like '2010-05-15', '15/05/2010', '15-05-2010' to 'YYYY-MM-DD'."""
    if not d_str:
        return ""
    d = d_str.strip()
    # DD/MM/YYYY or DD-MM-YYYY
    m = re.match(r"^(\d{1,2})[/-](\d{1,2})[/-](\d{4})$", d)
    if m:
        day, month, year = m.groups()
        return f"{year}-{int(month):02d}-{int(day):02d}"
    # YYYY-MM-DD
    m2 = re.match(r"^(\d{4})[/-](\d{1,2})[/-](\d{1,2})$", d)
    if m2:
        year, month, day = m2.groups()
        return f"{year}-{int(month):02d}-{int(day):02d}"
    return d.lower()


def _normalize_phone(p_str: Optional[str]) -> str:
    if not p_str:
        return ""
    return re.sub(r"[^\d+]", "", p_str.strip())


@router.get("/my-children")
async def get_my_children(
    school_id: int,
    current: dict = Depends(require_role("PARENT", "ADMIN"))
):
    """Lấy danh sách các học sinh (con) đã liên kết với tài khoản phụ huynh hiện tại."""
    _check_scope(school_id, current)
    conn = get_db()
    try:
        user_id = current.get("user_id") or current.get("id")
        user_row = conn.execute("SELECT phone FROM users WHERE id=?", (user_id,)).fetchone()
        user_phone = user_row["phone"] if user_row else None

        rows = conn.execute("""
            SELECT s.id, s.student_code, s.full_name, s.dob, s.gender, s.current_points, 
                   s.face_photo_url, s.qr_token, s.parent_phone,
                   c.name as class_name, c.grade_level,
                   psl.relation_name, psl.verified_status, psl.verified_at, psl.created_at as linked_at
            FROM parent_student_links psl
            JOIN students s ON psl.student_id = s.id
            LEFT JOIN classes c ON s.class_id = c.id
            WHERE psl.parent_user_id = ? AND psl.school_id = ? AND s.is_deleted = 0
            ORDER BY s.full_name ASC
        """, (user_id, school_id)).fetchall()

        children = []
        seen_ids = set()
        for r in rows:
            d = dict(r)
            if d["id"] in seen_ids:
                continue
            seen_ids.add(d["id"])
            d["relation_name"] = d.get("relation_name") or "Phụ huynh"
            d["verified_status"] = d.get("verified_status") or "VERIFIED"
            children.append(d)

        return children
    finally:
        conn.close()


@router.post("/link-child")
async def link_child_to_parent(
    school_id: int,
    req: LinkChildRequest,
    current: dict = Depends(require_role("PARENT", "ADMIN"))
):
    """
    Phụ huynh liên kết tài khoản với con em. Hỗ trợ 2 phương thức:
    1. [Khuyên Dùng / 1 Chạm]: Nhập Mã Mời Phụ Huynh (parent_invite_code dạng PH-XXXXXX) do học sinh cấp.
    2. [Thủ công]: Nhập Mã Học Sinh + Thông tin đối soát (Ngày sinh hoặc SĐT phụ huynh đăng ký).
    """
    _check_scope(school_id, current)
    conn = get_db()
    try:
        user_id = current.get("user_id") or current.get("id")
        p_user = conn.execute("SELECT id, full_name, phone, school_id FROM users WHERE id=?", (user_id,)).fetchone()
        if not p_user:
            raise HTTPException(404, "Không tìm thấy thông tin tài khoản phụ huynh.")

        user_phone = _normalize_phone(p_user["phone"])

        # ── PHƯƠNG THỨC 1: LIÊN KẾT 1 CHẠM BẰNG MÃ MỜI PHỤ HUYNH ─────────
        inv_code = (req.invite_code or "").strip().upper()
        raw_code = (req.student_code or "").strip().upper()
        if not inv_code and raw_code.startswith("PH-"):
            inv_code = raw_code

        if inv_code:
            student = conn.execute(
                "SELECT * FROM students WHERE UPPER(parent_invite_code)=? AND is_deleted=0",
                (inv_code,)
            ).fetchone()
            if not student:
                raise HTTPException(404, f"Mã mời phụ huynh '{inv_code}' không hợp lệ hoặc đã đổi mới. Vui lòng kiểm tra lại mã trên ứng dụng của con em.")

            # Check existing link
            existing_link = conn.execute(
                "SELECT id FROM parent_student_links WHERE parent_user_id=? AND student_id=?",
                (user_id, student["id"])
            ).fetchone()
            if existing_link:
                raise HTTPException(400, f"Học sinh '{student['full_name']}' ({student['student_code']}) đã được liên kết với tài khoản của bạn từ trước.")

            rel_name = (req.relation_name or "Phụ huynh").strip()
            conn.execute("""
                INSERT INTO parent_student_links (parent_user_id, student_id, school_id, relation_name, verified_status, verified_at)
                VALUES (?, ?, ?, ?, 'VERIFIED', datetime('now','localtime'))
                ON CONFLICT(parent_user_id, student_id) DO UPDATE SET
                    school_id = excluded.school_id,
                    relation_name = excluded.relation_name,
                    verified_status = 'VERIFIED',
                    verified_at = datetime('now','localtime')
            """, (user_id, student["id"], student["school_id"], rel_name))

            if not p_user["school_id"] or p_user["school_id"] != student["school_id"]:
                conn.execute("UPDATE users SET school_id=? WHERE id=?", (student["school_id"], user_id))

            if not student["parent_phone"] and p_user["phone"]:
                conn.execute(
                    "UPDATE students SET parent_phone=?, parent_name=COALESCE(parent_name, ?), updated_at=datetime('now','localtime') WHERE id=?",
                    (p_user["phone"], p_user["full_name"], student["id"])
                )

            conn.commit()
            cls = conn.execute("SELECT name FROM classes WHERE id=?", (student["class_id"],)).fetchone()
            class_name = cls["name"] if cls else "Chưa xếp lớp"

            log.info(f"[PARENT] User #{user_id} linked to student #{student['id']} via Parent Invite Code {inv_code}")

            return {
                "status": "success",
                "message": f"Liên kết 1 chạm thành công với con em: {student['full_name']} (Mã HS: {student['student_code']}) qua Mã Mời Phụ Huynh!",
                "match_reason": "Mã mời phụ huynh 1 chạm từ con em",
                "student": {
                    "id": student["id"],
                    "student_code": student["student_code"],
                    "parent_invite_code": student["parent_invite_code"],
                    "full_name": student["full_name"],
                    "dob": student["dob"],
                    "class_name": class_name,
                    "current_points": student["current_points"],
                    "qr_token": student["qr_token"],
                    "relation_name": rel_name
                }
            }

        # ── PHƯƠNG THỨC 2: NHẬP THỦ CÔNG MÃ HỌC SINH + ĐỐI SOÁT ───────────
        code = raw_code
        if not code:
            raise HTTPException(400, "Vui lòng nhập Mã Mời Phụ Huynh (ví dụ: PH-XXXXXX) hoặc Mã Học Sinh của con.")

        student = conn.execute(
            "SELECT * FROM students WHERE school_id=? AND UPPER(student_code)=? AND is_deleted=0",
            (school_id, code)
        ).fetchone()

        if not student:
            raise HTTPException(404, f"Không tìm thấy học sinh có mã '{code}' trong trường.")

        # Check existing link
        existing_link = conn.execute(
            "SELECT id FROM parent_student_links WHERE parent_user_id=? AND student_id=?",
            (user_id, student["id"])
        ).fetchone()
        if existing_link:
            raise HTTPException(400, f"Học sinh '{student['full_name']}' ({code}) đã được liên kết với tài khoản của bạn từ trước.")

        # Verification matching logic
        stu_parent_phone = _normalize_phone(student["parent_phone"])
        stu_dob = _normalize_date_str(student["dob"])

        verified = False
        match_reason = ""

        # Check 1: User phone matches student's registered parent phone
        if user_phone and stu_parent_phone and user_phone == stu_parent_phone:
            verified = True
            match_reason = "Khớp số điện thoại phụ huynh đăng ký với trường"

        # Check 2: If verify_key provided
        if not verified and req.verify_key and req.verify_key.strip():
            vk = req.verify_key.strip()
            vk_date = _normalize_date_str(vk)
            vk_phone = _normalize_phone(vk)

            if stu_dob and vk_date and vk_date == stu_dob:
                verified = True
                match_reason = "Khớp ngày sinh của học sinh"
            elif stu_parent_phone and vk_phone and vk_phone == stu_parent_phone:
                verified = True
                match_reason = "Khớp số điện thoại phụ huynh"

        # Check 3: Student profile in system does not have DOB or parent phone set yet
        if not verified and not stu_dob and not stu_parent_phone:
            verified = True
            match_reason = "Hồ sơ học sinh ban đầu chưa có thông tin bảo mật, tự động cập nhật SĐT phụ huynh"

        if not verified:
            raise HTTPException(
                400,
                "Thông tin đối soát (Ngày sinh con hoặc Số điện thoại phụ huynh đăng ký) không khớp với hồ sơ học sinh tại trường. "
                "Vui lòng kiểm tra lại hoặc liên hệ GVCN / Ban giám hiệu để được hỗ trợ."
            )

        # Insert or replace link
        rel_name = (req.relation_name or "Phụ huynh").strip()
        conn.execute("""
            INSERT INTO parent_student_links (parent_user_id, student_id, school_id, relation_name, verified_status, verified_at)
            VALUES (?, ?, ?, ?, 'VERIFIED', datetime('now','localtime'))
            ON CONFLICT(parent_user_id, student_id) DO UPDATE SET
                school_id = excluded.school_id,
                relation_name = excluded.relation_name,
                verified_status = 'VERIFIED',
                verified_at = datetime('now','localtime')
        """, (user_id, student["id"], school_id, rel_name))

        # Sync parent phone to student profile if missing
        if not student["parent_phone"] and p_user["phone"]:
            conn.execute(
                "UPDATE students SET parent_phone=?, parent_name=COALESCE(parent_name, ?), updated_at=datetime('now','localtime') WHERE id=?",
                (p_user["phone"], p_user["full_name"], student["id"])
            )

        conn.commit()

        # Fetch updated class info
        cls = conn.execute("SELECT name FROM classes WHERE id=?", (student["class_id"],)).fetchone()
        class_name = cls["name"] if cls else "Chưa xếp lớp"

        log.info(f"[PARENT] User #{user_id} linked to student #{student['id']} ({code}) via {match_reason}")

        return {
            "status": "success",
            "message": f"Liên kết thành công với con em: {student['full_name']} (Mã: {code})",
            "match_reason": match_reason,
            "student": {
                "id": student["id"],
                "student_code": student["student_code"],
                "full_name": student["full_name"],
                "dob": student["dob"],
                "class_name": class_name,
                "current_points": student["current_points"],
                "qr_token": student["qr_token"],
                "relation_name": rel_name
            }
        }
    finally:
        conn.close()


@router.delete("/unlink-child/{student_id}")
async def unlink_child(
    school_id: int,
    student_id: int,
    current: dict = Depends(require_role("PARENT", "ADMIN"))
):
    """Phụ huynh hủy liên kết một học sinh khỏi tài khoản của mình."""
    _check_scope(school_id, current)
    conn = get_db()
    try:
        user_id = current.get("user_id") or current.get("id")
        link = conn.execute(
            "SELECT id FROM parent_student_links WHERE parent_user_id=? AND student_id=? AND school_id=?",
            (user_id, student_id, school_id)
        ).fetchone()
        if not link:
            raise HTTPException(404, "Không tìm thấy liên kết giữa bạn và học sinh này.")

        user_row = conn.execute("SELECT phone FROM users WHERE id=?", (user_id,)).fetchone()
        conn.execute("DELETE FROM parent_student_links WHERE id=?", (link["id"],))
        if user_row and user_row["phone"]:
            conn.execute("UPDATE students SET parent_phone=NULL WHERE id=? AND parent_phone=?", (student_id, user_row["phone"]))
        conn.commit()
        return {"status": "success", "message": "Đã hủy liên kết học sinh thành công."}
    finally:
        conn.close()


@router.post("/link-by-invite-code")
async def link_by_invite_code(
    school_id: int,
    req: LinkByInviteCodeRequest,
    current: dict = Depends(require_role("PARENT", "ADMIN"))
):
    """Phụ huynh liên kết tài khoản 1 chạm bằng Mã Mời Phụ Huynh (PH-XXXXXX) do con em cấp."""
    payload = LinkChildRequest(invite_code=req.invite_code, relation_name=req.relation_name)
    return await link_child_to_parent(school_id, payload, current)

