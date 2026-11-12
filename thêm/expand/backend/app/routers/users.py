"""
app/routers/users.py — Quản lý Thành Viên & Phân Quyền Trường Học
Cung cấp API cho Hiệu Trưởng (HEADMASTER) và Ban Quản Trị:
- Xem danh sách thành viên trong trường (Giáo viên, Giám thị, Phụ huynh, Học sinh).
- Chủ động thay đổi thông tin: Số điện thoại, Email, Họ tên, Ngày sinh, Giới tính, Trạng thái hoạt động, Vai trò.
- Kiểm soát phân quyền: Hiệu trưởng chỉ có quyền chỉnh sửa tài khoản thuộc các vai trò cấp dưới (TEACHER, INSPECTOR, PARENT, STUDENT).
- Tự động đồng bộ số điện thoại và họ tên sang hồ sơ học sinh / liên kết phụ huynh.
"""
import re
import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.database import get_db
from app.core.deps import get_current_user, require_role
from app.core.security import generate_salt, hash_password

router = APIRouter(prefix="/api/v1/s/{school_id}/users", tags=["School Users"])
log = logging.getLogger("stem.users")

SUBORDINATE_ROLES = {"TEACHER", "INSPECTOR", "PARENT", "STUDENT"}
MANAGEMENT_ROLES = {"HEADMASTER", "ADMIN", "PLATFORM_ADMIN"}


class UpdateSchoolUserRequest(BaseModel):
    full_name:   Optional[str] = None
    phone:       Optional[str] = None
    email:       Optional[str] = None
    dob:         Optional[str] = None
    gender:      Optional[str] = None
    role:        Optional[str] = None
    status:      Optional[str] = None  # ACTIVE | SUSPENDED | PENDING_APPROVAL
    class_name:  Optional[str] = None
    grade_level: Optional[int] = None
    note:        Optional[str] = None


class ResetUserPasswordRequest(BaseModel):
    new_password: str


class ToggleUserStatusRequest(BaseModel):
    status: Optional[str] = None  # ACTIVE | SUSPENDED (hoặc None để tự đảo trạng thái)


def _check_school_scope(school_id: int, current: dict):
    """Đảm bảo tài khoản thao tác thuộc đúng trường hoặc là Super Admin."""
    if current.get("role") in ("ADMIN", "PLATFORM_ADMIN"):
        return
    if current.get("school_id") != school_id:
        raise HTTPException(403, "Bạn không có quyền truy cập dữ liệu của trường này.")


def _verify_subordinate_access(current: dict, target_user: dict, requested_new_role: Optional[str] = None):
    """
    Ràng buộc phân quyền:
    Hiệu trưởng (HEADMASTER) chỉ được thao tác trên các role cấp dưới: TEACHER, INSPECTOR, PARENT, STUDENT.
    Không được sửa tài khoản Hiệu trưởng khác hoặc Super Admin.
    Không được nâng quyền tài khoản cấp dưới lên Hiệu trưởng hay Admin.
    """
    caller_role = current.get("role")
    if caller_role in ("ADMIN", "PLATFORM_ADMIN"):
        return  # Super Admin có toàn quyền

    target_role = target_user.get("role")
    if target_role not in SUBORDINATE_ROLES:
        raise HTTPException(
            status_code=403,
            detail=(
                f"Hiệu trưởng chỉ có quyền quản lý và chỉnh sửa thông tin các tài khoản thuộc vai trò cấp dưới "
                f"(Giáo viên, Giám thị, Phụ huynh, Học sinh). Tài khoản này có vai trò '{target_role}' vượt thẩm quyền."
            )
        )

    if requested_new_role:
        norm_new_role = requested_new_role.strip().upper()
        if norm_new_role not in SUBORDINATE_ROLES:
            raise HTTPException(
                status_code=403,
                detail=(
                    f"Hiệu trưởng chỉ có thể phân vai trò thuộc cấp dưới: "
                    f"{', '.join(sorted(SUBORDINATE_ROLES))}. Không thể phân vai trò '{norm_new_role}'."
                )
            )


@router.get("")
async def list_school_users(
    school_id: int,
    role: Optional[str] = Query(None, description="Lọc theo vai trò: TEACHER, INSPECTOR, PARENT, STUDENT, HEADMASTER"),
    status: Optional[str] = Query(None, description="Lọc theo trạng thái: ACTIVE, SUSPENDED, PENDING_APPROVAL"),
    q: Optional[str] = Query(None, description="Tìm kiếm họ tên, username, sđt, email, mã định danh"),
    subordinate_only: bool = Query(False, description="Chỉ lấy các tài khoản cấp dưới"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    current: dict = Depends(require_role("HEADMASTER", "ADMIN", "INSPECTOR"))
):
    """
    Danh sách thành viên trong trường học dành cho Hiệu Trưởng & Ban Quản Trị.
    Cho phép lọc theo vai trò cấp dưới, tìm kiếm thông tin và kiểm tra trạng thái.
    """
    _check_school_scope(school_id, current)
    caller_role = current.get("role")

    conn = get_db()
    try:
        query = """
            SELECT id, school_id, username, email, phone, full_name, dob, gender,
                   avatar_url, role, status, verified_status, verification_method,
                   user_code, student_code, class_name, grade_level,
                   last_login_at, created_at, updated_at
            FROM users
            WHERE school_id=?
        """
        params = [school_id]

        if role:
            query += " AND role=?"
            params.append(role.strip().upper())
        elif subordinate_only:
            query += f" AND role IN ({','.join(['?']*len(SUBORDINATE_ROLES))})"
            params.extend(list(SUBORDINATE_ROLES))

        if status:
            query += " AND status=?"
            params.append(status.strip().upper())

        if q and q.strip():
            kw = f"%{q.strip().lower()}%"
            query += """ AND (
                LOWER(full_name) LIKE ? OR
                LOWER(username) LIKE ? OR
                LOWER(phone) LIKE ? OR
                LOWER(email) LIKE ? OR
                LOWER(COALESCE(user_code,'')) LIKE ? OR
                LOWER(COALESCE(student_code,'')) LIKE ?
            )"""
            params.extend([kw, kw, kw, kw, kw, kw])

        # Đếm tổng số lượng bản ghi
        count_sql = f"SELECT COUNT(*) FROM ({query})"
        total = conn.execute(count_sql, params).fetchone()[0]

        query += " ORDER BY role ASC, id DESC LIMIT ? OFFSET ?"
        offset = (page - 1) * limit
        params.extend([limit, offset])

        rows = conn.execute(query, params).fetchall()

        users_list = []
        for r in rows:
            u = dict(r)
            u_role = u.get("role")
            is_sub = u_role in SUBORDINATE_ROLES
            # Kiểm tra quyền sửa của caller hiện tại
            can_edit = (caller_role in ("ADMIN", "PLATFORM_ADMIN")) or (caller_role == "HEADMASTER" and is_sub)

            users_list.append({
                **u,
                "member_code": u.get("user_code") or u.get("student_code") or f"ID-{u['id']}",
                "is_subordinate": is_sub,
                "can_edit": can_edit,
            })

        return {
            "status": "success",
            "school_id": school_id,
            "total": total,
            "page": page,
            "limit": limit,
            "users": users_list,
        }
    finally:
        conn.close()


@router.get("/{user_id}")
async def get_school_user_detail(
    school_id: int,
    user_id: int,
    current: dict = Depends(require_role("HEADMASTER", "ADMIN", "INSPECTOR"))
):
    """Lấy chi tiết hồ sơ thành viên trong trường."""
    _check_school_scope(school_id, current)
    caller_role = current.get("role")

    conn = get_db()
    try:
        row = conn.execute(
            """SELECT id, school_id, username, email, phone, full_name, dob, gender,
                      avatar_url, role, status, verified_status, verification_method,
                      verification_note, verified_at, user_code, student_code,
                      class_name, grade_level, last_login_at, created_at, updated_at
               FROM users WHERE id=? AND school_id=?""",
            (user_id, school_id)
        ).fetchone()

        if not row:
            raise HTTPException(404, "Không tìm thấy người dùng trong trường này.")

        u = dict(row)
        is_sub = u.get("role") in SUBORDINATE_ROLES
        can_edit = (caller_role in ("ADMIN", "PLATFORM_ADMIN")) or (caller_role == "HEADMASTER" and is_sub)

        # Lấy thông tin bổ sung tùy theo role
        extra = {}
        if u.get("role") == "STUDENT":
            stu_row = conn.execute(
                "SELECT id, current_points, parent_phone, parent_name, qr_token FROM students WHERE user_id=? OR (school_id=? AND student_code=?)",
                (user_id, school_id, u.get("student_code") or u.get("user_code"))
            ).fetchone()
            if stu_row:
                extra["student_profile"] = dict(stu_row)

        elif u.get("role") == "PARENT":
            linked_students = conn.execute(
                """SELECT s.id, s.student_code, s.full_name, c.name as class_name, psl.relation_name
                   FROM parent_student_links psl
                   JOIN students s ON psl.student_id = s.id
                   LEFT JOIN classes c ON s.class_id = c.id
                   WHERE psl.parent_user_id=? AND psl.school_id=?""",
                (user_id, school_id)
            ).fetchall()
            extra["linked_children"] = [dict(c) for c in linked_students]

        return {
            "status": "success",
            "user": {
                **u,
                "member_code": u.get("user_code") or u.get("student_code") or f"ID-{u['id']}",
                "is_subordinate": is_sub,
                "can_edit": can_edit,
                **extra,
            }
        }
    finally:
        conn.close()


@router.put("/{user_id}")
async def update_school_user(
    school_id: int,
    user_id: int,
    req: UpdateSchoolUserRequest,
    current: dict = Depends(require_role("HEADMASTER", "ADMIN"))
):
    """
    Hiệu trưởng cập nhật chủ động thông tin người dùng cấp dưới:
    - Sửa số điện thoại (phone): Kiểm tra trùng lặp trong trường và tự động đồng bộ sang hồ sơ học sinh/phụ huynh.
    - Sửa email: Kiểm tra định dạng và trùng lặp trong trường.
    - Sửa họ tên, ngày sinh, giới tính, trạng thái hoạt động (ACTIVE/SUSPENDED), vai trò cấp dưới.
    """
    _check_school_scope(school_id, current)

    conn = get_db()
    try:
        target = conn.execute("SELECT * FROM users WHERE id=? AND school_id=?", (user_id, school_id)).fetchone()
        if not target:
            raise HTTPException(404, "Không tìm thấy người dùng cần chỉnh sửa trong trường này.")

        target_dict = dict(target)

        # 1. Kiểm tra thẩm quyền phân quyền cấp dưới
        _verify_subordinate_access(current, target_dict, requested_new_role=req.role)

        updates = []
        params = []

        # 2. Xử lý Họ và tên
        if req.full_name is not None:
            full_name_clean = req.full_name.strip()
            if len(full_name_clean) < 2:
                raise HTTPException(422, "Họ và tên phải có ít nhất 2 ký tự.")
            updates.append("full_name=?")
            params.append(full_name_clean)

        # 3. Xử lý Số điện thoại
        new_phone = None
        if req.phone is not None:
            phone_clean = req.phone.strip()
            if phone_clean:
                # Kiểm tra định dạng số điện thoại
                if not re.match(r"^[0-9+]{9,15}$", phone_clean):
                    raise HTTPException(422, "Số điện thoại không hợp lệ (cần từ 9 đến 15 chữ số).")
                # Kiểm tra tính duy nhất trong trường (ngoại trừ chính tài khoản này)
                dup_phone = conn.execute(
                    "SELECT id, full_name, username FROM users WHERE school_id=? AND phone=? AND id!=?",
                    (school_id, phone_clean, user_id)
                ).fetchone()
                if dup_phone:
                    raise HTTPException(
                        409,
                        f"Số điện thoại '{phone_clean}' đã được đăng ký bởi {dup_phone['full_name']} (@{dup_phone['username']}) trong trường."
                    )
                new_phone = phone_clean
            else:
                new_phone = None  # Xóa số điện thoại

            updates.append("phone=?")
            params.append(new_phone)

        # 4. Xử lý Email
        new_email = None
        if req.email is not None:
            email_clean = req.email.strip().lower()
            if email_clean:
                if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email_clean):
                    raise HTTPException(422, "Định dạng email không hợp lệ.")
                dup_email = conn.execute(
                    "SELECT id, full_name, username FROM users WHERE school_id=? AND LOWER(email)=? AND id!=?",
                    (school_id, email_clean, user_id)
                ).fetchone()
                if dup_email:
                    raise HTTPException(
                        409,
                        f"Email '{email_clean}' đã được sử dụng bởi {dup_email['full_name']} (@{dup_email['username']}) trong trường."
                    )
                new_email = email_clean
            else:
                new_email = None

            updates.append("email=?")
            params.append(new_email)

        # 5. Xử lý Ngày sinh & Giới tính
        if req.dob is not None:
            updates.append("dob=?")
            params.append(req.dob.strip() if req.dob else None)

        if req.gender is not None:
            updates.append("gender=?")
            params.append(req.gender.strip() if req.gender else None)

        # 6. Xử lý Vai trò (Role)
        if req.role is not None:
            new_role_norm = req.role.strip().upper()
            updates.append("role=?")
            params.append(new_role_norm)

        # 7. Xử lý Trạng thái tài khoản (Status)
        if req.status is not None:
            status_norm = req.status.strip().upper()
            if status_norm not in ("ACTIVE", "SUSPENDED", "PENDING_APPROVAL"):
                raise HTTPException(422, "Trạng thái không hợp lệ (chỉ chấp nhận: ACTIVE, SUSPENDED, PENDING_APPROVAL).")
            updates.append("status=?")
            params.append(status_norm)

        # 8. Lớp học & Khối
        if req.class_name is not None:
            updates.append("class_name=?")
            params.append(req.class_name.strip() if req.class_name else None)

        if req.grade_level is not None:
            updates.append("grade_level=?")
            params.append(req.grade_level)

        if not updates:
            return {"status": "success", "message": "Không có trường nào cần cập nhật.", "user": target_dict}

        updates.append("updated_at=datetime('now','localtime')")
        params.append(user_id)

        sql_update = f"UPDATE users SET {', '.join(updates)} WHERE id=?"
        conn.execute(sql_update, params)

        # 9. Tự động đồng bộ dữ liệu liên quan
        target_effective_role = (req.role.strip().upper() if req.role else target_dict.get("role"))

        # a) Nếu là Học sinh: Đồng bộ tên, ngày sinh, giới tính sang bảng `students`
        if target_effective_role == "STUDENT":
            stu_upd = []
            stu_params = []
            if req.full_name is not None:
                stu_upd.append("full_name=?")
                stu_params.append(req.full_name.strip())
            if req.dob is not None:
                stu_upd.append("dob=?")
                stu_params.append(req.dob.strip() if req.dob else None)
            if req.gender is not None:
                stu_upd.append("gender=?")
                stu_params.append(req.gender.strip() if req.gender else None)

            if stu_upd:
                stu_params.extend([user_id, school_id, target_dict.get("student_code") or target_dict.get("user_code") or ""])
                conn.execute(
                    f"UPDATE students SET {', '.join(stu_upd)} WHERE user_id=? OR (school_id=? AND student_code=?)",
                    stu_params
                )

        # b) Nếu là Phụ huynh và có đổi số điện thoại: cập nhật parent_phone liên kết
        elif target_effective_role == "PARENT" and new_phone and target_dict.get("phone"):
            conn.execute(
                "UPDATE students SET parent_phone=? WHERE school_id=? AND parent_phone=?",
                (new_phone, school_id, target_dict["phone"])
            )

        conn.commit()

        # Lấy lại hồ sơ đã cập nhật
        updated_row = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        res_user = dict(updated_row)
        res_user.pop("password_hash", None)
        res_user.pop("salt", None)

        log.info(
            f"[USERS] Hiệu trưởng #{current.get('id')} ({current.get('full_name')}) đã sửa thông tin user #{user_id} ({res_user.get('full_name')}) tại trường #{school_id}."
        )

        return {
            "status": "success",
            "message": f"Đã cập nhật thông tin thành viên '{res_user.get('full_name')}' thành công.",
            "user": {
                **res_user,
                "member_code": res_user.get("user_code") or res_user.get("student_code") or f"ID-{res_user['id']}",
            }
        }
    finally:
        conn.close()


@router.post("/{user_id}/reset-password")
async def reset_school_user_password(
    school_id: int,
    user_id: int,
    req: ResetUserPasswordRequest,
    current: dict = Depends(require_role("HEADMASTER", "ADMIN"))
):
    """
    Hiệu trưởng chủ động cấp lại hoặc đổi mật khẩu cho tài khoản cấp dưới.
    """
    _check_school_scope(school_id, current)

    if len(req.new_password) < 6:
        raise HTTPException(400, "Mật khẩu mới phải có tối thiểu 6 ký tự.")

    conn = get_db()
    try:
        target = conn.execute("SELECT * FROM users WHERE id=? AND school_id=?", (user_id, school_id)).fetchone()
        if not target:
            raise HTTPException(404, "Không tìm thấy người dùng trong trường này.")

        target_dict = dict(target)
        _verify_subordinate_access(current, target_dict)

        new_salt = generate_salt()
        new_hash = hash_password(req.new_password, new_salt)

        conn.execute(
            "UPDATE users SET password_hash=?, salt=?, updated_at=datetime('now','localtime') WHERE id=?",
            (new_hash, new_salt, user_id)
        )
        # Thu hồi tất cả refresh token cũ của tài khoản này
        conn.execute("DELETE FROM user_refresh_tokens WHERE user_id=?", (user_id,))
        conn.commit()

        log.info(f"[USERS] Hiệu trưởng #{current.get('id')} đã đặt lại mật khẩu cho user #{user_id}.")

        return {
            "status": "success",
            "message": f"Đã đặt lại mật khẩu cho '{target_dict['full_name']}' thành công."
        }
    finally:
        conn.close()


@router.post("/{user_id}/toggle-status")
async def toggle_school_user_status(
    school_id: int,
    user_id: int,
    req: ToggleUserStatusRequest,
    current: dict = Depends(require_role("HEADMASTER", "ADMIN"))
):
    """
    Khóa hoặc kích hoạt nhanh trạng thái hoạt động của tài khoản cấp dưới.
    """
    _check_school_scope(school_id, current)

    conn = get_db()
    try:
        target = conn.execute("SELECT * FROM users WHERE id=? AND school_id=?", (user_id, school_id)).fetchone()
        if not target:
            raise HTTPException(404, "Không tìm thấy người dùng trong trường này.")

        target_dict = dict(target)
        _verify_subordinate_access(current, target_dict)

        if req.status:
            new_status = req.status.strip().upper()
            if new_status not in ("ACTIVE", "SUSPENDED"):
                raise HTTPException(422, "Trạng thái chỉ có thể là ACTIVE hoặc SUSPENDED.")
        else:
            new_status = "SUSPENDED" if target_dict.get("status") == "ACTIVE" else "ACTIVE"

        conn.execute(
            "UPDATE users SET status=?, updated_at=datetime('now','localtime') WHERE id=?",
            (new_status, user_id)
        )
        if new_status == "SUSPENDED":
            conn.execute("DELETE FROM user_refresh_tokens WHERE user_id=?", (user_id,))
        conn.commit()

        status_text = "kích hoạt" if new_status == "ACTIVE" else "tạm khóa"
        return {
            "status": "success",
            "new_status": new_status,
            "message": f"Đã {status_text} tài khoản '{target_dict['full_name']}'."
        }
    finally:
        conn.close()
