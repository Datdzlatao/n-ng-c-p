"""
app/routers/auth.py — Authentication & Verified Account endpoints
POST /api/v1/auth/register
POST /api/v1/auth/login
GET  /api/v1/auth/me
POST /api/v1/auth/verify/request-otp
POST /api/v1/auth/verify/submit-otp
POST /api/v1/auth/verify/submit-id-card
GET  /api/v1/auth/verify/pending-list
POST /api/v1/auth/verify/approve
"""
import json, secrets, logging
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends, Header, Request, Response
from pydantic import BaseModel
from typing import Optional

from app.database import get_db
from app.core.security import (
    generate_salt, hash_password, verify_password,
    create_access_token, decode_access_token,
    create_access_token_with_jti, create_refresh_token
)
from app.core.deps import get_current_user, get_current_user_optional, require_role
from app.config import OTP_EXPIRE_MINUTES, OTP_LENGTH, OTP_DEV_MODE
from app.core.rate_limit import check_rate_limit, get_client_ip
from app.core.code_generator import generate_role_code, get_role_prefix

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])
log    = logging.getLogger("stem.auth")


# ─────────────────────────────────────────────────
# PYDANTIC MODELS
# ─────────────────────────────────────────────────
class RegisterRequest(BaseModel):
    school_id:    Optional[int] = None
    username:     str
    password:     str
    full_name:    str
    role:         str = "STUDENT"    # STUDENT|PARENT|TEACHER|INSPECTOR|HEADMASTER
    phone:        Optional[str] = None
    email:        Optional[str] = None
    dob:          Optional[str] = None
    student_code: Optional[str] = None  # for auto-match
    class_name:   Optional[str] = None
    invite_code:  Optional[str] = None  # for TEACHER/INSPECTOR/HEADMASTER


class LoginRequest(BaseModel):
    school_id:          Optional[int] = None
    username_or_phone:  str
    password:           str


class OtpRequest(BaseModel):
    school_id:  int
    target:     str           # phone number
    otp_type:   str = "PHONE_REGISTER"


class OtpSubmit(BaseModel):
    school_id:  int
    target:     str
    otp_code:   str


class IDCardSubmit(BaseModel):
    school_id:     int
    doc_type:      str = "CCCD"
    doc_data_url:  str   # base64 data URL from frontend
    note:          Optional[str] = None


class ApproveVerification(BaseModel):
    user_id:  int
    status:   str             # VERIFIED | REJECTED
    note:     Optional[str] = None


# ─────────────────────────────────────────────────
# HELPER
# ─────────────────────────────────────────────────
def _user_to_profile(row) -> dict:
    d = dict(row)
    for sensitive in ("password_hash", "salt", "face_embedding_blob"):
        d.pop(sensitive, None)
    return d


def _make_token(user_row: dict) -> str:
    token, _ = create_access_token_with_jti({
        "sub":            str(user_row["id"]),
        "user_id":        user_row["id"],
        "school_id":      user_row["school_id"],
        "username":       user_row["username"],
        "role":           user_row["role"],
        "full_name":      user_row["full_name"],
        "user_code":      user_row.get("user_code") or user_row.get("student_code"),
        "student_code":   user_row.get("student_code"),
        "verified_status": user_row.get("verified_status", "UNVERIFIED"),
    })
    return token


# ─────────────────────────────────────────────────
# REGISTER
# ─────────────────────────────────────────────────
@router.post("/register")
async def register(req: RegisterRequest):
    conn = get_db()
    try:
        req_role = (req.role or "STUDENT").strip().upper()

        # 1. Validate school if provided
        school = None
        if req.school_id:
            school = conn.execute("SELECT * FROM schools WHERE id=? AND status='ACTIVE'", (req.school_id,)).fetchone()
            if not school:
                raise HTTPException(404, "Không tìm thấy trường học hoặc trường đang tạm ngưng.")

            # Parse school form_config and validate required fields
            form_cfg = json.loads(school["form_config"] or "{}")
            role_cfg = form_cfg.get(req_role.lower(), {})

            if role_cfg.get("require_phone") and not req.phone:
                raise HTTPException(422, f"Trường {school['name']} yêu cầu bắt buộc nhập Số Điện Thoại cho vai trò {req_role}.")
            if role_cfg.get("require_invite_code") and req_role in ("TEACHER", "INSPECTOR"):
                valid_code = school["teacher_invite_code"] if req_role == "TEACHER" else school["inspector_invite_code"]
                if req.invite_code != valid_code:
                    raise HTTPException(422, "Mã mời không đúng hoặc đã hết hạn. Liên hệ Ban Giám Hiệu.")
            if req_role == "HEADMASTER" and req.invite_code != school["bgh_invite_code"]:
                raise HTTPException(422, "Mã mời Ban Giám Hiệu không đúng.")

        # 2. Check duplicate username & phone
        if req.school_id:
            dup = conn.execute(
                "SELECT id FROM users WHERE (school_id=? OR school_id IS NULL) AND (username=? OR (phone=? AND phone IS NOT NULL))",
                (req.school_id, req.username, req.phone)
            ).fetchone()
        else:
            dup = conn.execute(
                "SELECT id FROM users WHERE username=? OR (phone=? AND phone IS NOT NULL)",
                (req.username, req.phone)
            ).fetchone()
        if dup:
            raise HTTPException(409, "Tên đăng nhập hoặc Số điện thoại đã được đăng ký.")

        # 3. Determine verified_status
        verified_status     = "UNVERIFIED"
        verification_method = "SELF_REGISTER" if not school else None
        verification_note   = "Tài khoản người dùng mới (chưa tham gia trường)" if not school else None

        if school:
            if req_role == "STUDENT" and req.student_code:
                hs = conn.execute(
                    "SELECT id FROM students WHERE school_id=? AND student_code=? AND (parent_phone=? OR parent_phone IS NULL)",
                    (req.school_id, req.student_code, req.phone)
                ).fetchone()
                if hs:
                    verified_status     = "VERIFIED"
                    verification_method = "AUTO_MATCH"
                    verification_note   = f"Khớp danh bộ: Mã HS {req.student_code}"

            if req_role == "PARENT" and req.phone:
                hs_linked = conn.execute(
                    "SELECT id FROM students WHERE school_id=? AND parent_phone=?",
                    (req.school_id, req.phone)
                ).fetchone()
                if hs_linked:
                    verified_status     = "VERIFIED"
                    verification_method = "AUTO_MATCH"
                    verification_note   = "SĐT khớp với danh bộ phụ huynh"

            if req_role == "TEACHER" and req.invite_code == school["teacher_invite_code"]:
                verified_status     = "VERIFIED"
                verification_method = "INVITE_CODE"
                verification_note   = "Mã mời GVCN hợp lệ"

            if req_role == "INSPECTOR" and req.invite_code == school["inspector_invite_code"]:
                verified_status     = "VERIFIED"
                verification_method = "INVITE_CODE"
                verification_note   = "Mã mời Giám Thị hợp lệ"

            if req_role == "HEADMASTER" and req.invite_code == school["bgh_invite_code"]:
                verified_status     = "VERIFIED"
                verification_method = "INVITE_CODE"
                verification_note   = "Mã mời Ban Giám Hiệu hợp lệ"

        # 4. Automatically generate unique code for the user based on role
        if req_role == "STUDENT" and req.student_code and req.student_code.strip():
            user_code = req.student_code.strip().upper()
            student_code = user_code
        else:
            user_code = generate_role_code(conn, req.school_id, req_role)
            student_code = user_code if req_role == "STUDENT" else None

        # 5. Create user
        salt = generate_salt()
        pw   = hash_password(req.password, salt)

        conn.execute("""
            INSERT INTO users (
                school_id, username, email, phone, password_hash, salt,
                full_name, dob, role, status,
                verified_status, verification_method, verification_note,
                user_code, student_code, class_name
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            req.school_id, req.username, req.email, req.phone, pw, salt,
            req.full_name, req.dob, req_role, "ACTIVE",
            verified_status, verification_method, verification_note,
            user_code, student_code, req.class_name
        ))
        user_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        # Phân giải class_id từ class_name nếu có
        class_id = None
        if req.school_id and req.class_name and req.class_name.strip():
            c_row = conn.execute(
                "SELECT id FROM classes WHERE school_id=? AND name=? AND is_active=1",
                (req.school_id, req.class_name.strip())
            ).fetchone()
            if c_row:
                class_id = c_row["id"]

        # If student and school provided, link or create record in students table
        if req.school_id and req_role == "STUDENT":
            existing_stu = conn.execute("SELECT id FROM students WHERE school_id=? AND student_code=?", (req.school_id, student_code)).fetchone()
            if not existing_stu:
                qr_token = f"QR-{student_code}-{secrets.token_hex(4).upper()}"
                conn.execute("""
                    INSERT INTO students (user_id, school_id, class_id, student_code, full_name, dob, parent_phone, qr_token, current_points, is_active)
                    VALUES (?,?,?,?,?,?,?,?,100,1)
                """, (user_id, req.school_id, class_id, student_code, req.full_name, req.dob, req.phone, qr_token))
            else:
                conn.execute("UPDATE students SET user_id=?, class_id=COALESCE(class_id, ?) WHERE id=?", (user_id, class_id, existing_stu["id"]))

        # If parent and school provided, link to matching students in parent_student_links
        elif req.school_id and req_role == "PARENT":
            matched_students = []
            if req.student_code and req.student_code.strip():
                s_by_code = conn.execute("SELECT id FROM students WHERE school_id=? AND student_code=?", (req.school_id, req.student_code.strip())).fetchone()
                if s_by_code:
                    matched_students.append(s_by_code["id"])
            if req.phone:
                s_by_phone = conn.execute("SELECT id FROM students WHERE school_id=? AND parent_phone=?", (req.school_id, req.phone)).fetchall()
                for s in s_by_phone:
                    if s["id"] not in matched_students:
                        matched_students.append(s["id"])

            for sid in matched_students:
                conn.execute("""
                    INSERT OR IGNORE INTO parent_student_links (parent_user_id, student_id, school_id, relation_name, verified_status, verified_at)
                    VALUES (?, ?, ?, 'Phụ huynh', 'VERIFIED', datetime('now','localtime'))
                """, (user_id, sid, req.school_id))

        conn.commit()

        user_row = dict(conn.execute(
            "SELECT * FROM users WHERE id=?", (user_id,)
        ).fetchone())

        token = _make_token(user_row)
        role_label = {
            "STUDENT": "Học Sinh",
            "TEACHER": "Giáo Viên",
            "PARENT": "Phụ Huynh",
            "INSPECTOR": "Giám Thị",
            "HEADMASTER": "Ban Giám Hiệu",
            "ADMIN": "Quản Trị Viên"
        }.get(req_role, req_role)

        msg = f"Đăng ký tài khoản {role_label} thành công!"
        if req.school_id:
            msg += f" Mã định danh: {user_code}"
        else:
            msg += " Vui lòng chọn ngôi trường của bạn để bắt đầu tham gia."

        return {
            "status": "success",
            "message": msg,
            "user_code": user_code,
            "student_code": student_code or user_code,
            "access_token": token,
            "user": _user_to_profile(user_row)
        }
    finally:
        conn.close()


# ─────────────────────────────────────────────────
# LOGIN
# ─────────────────────────────────────────────────
@router.post("/login")
async def login(req: LoginRequest, request: Request, response: Response):
    check_rate_limit(f"login:{get_client_ip(request)}", max_calls=5, window_seconds=60)
    conn = get_db()
    try:
        username_lower = req.username_or_phone.strip().lower()

        # ── Platform Admin login (tra cứu database, hỗ trợ đồng bộ từ .env) ──
        if username_lower in ("admin", "admin@stemapp.vn"):
            admin = conn.execute(
                "SELECT * FROM platform_admins WHERE (email=? OR email=?) AND is_active=1",
                ("admin@stemapp.vn", req.username_or_phone.strip())
            ).fetchone()

            from app.config import PLATFORM_ADMIN_PASSWORD
            is_valid = False
            if admin and verify_password(req.password, admin["salt"], admin["password_hash"]):
                is_valid = True
            elif PLATFORM_ADMIN_PASSWORD and req.password == PLATFORM_ADMIN_PASSWORD:
                is_valid = True
                new_salt = generate_salt()
                new_hash = hash_password(PLATFORM_ADMIN_PASSWORD, new_salt)
                conn.execute("UPDATE platform_admins SET password_hash=?, salt=? WHERE email='admin@stemapp.vn'", (new_hash, new_salt))
                conn.execute("UPDATE users SET password_hash=?, salt=? WHERE username='admin'", (new_hash, new_salt))
                conn.commit()
                admin = conn.execute("SELECT * FROM platform_admins WHERE email='admin@stemapp.vn'").fetchone()

            if not is_valid:
                raise HTTPException(401, "Tài khoản hoặc mật khẩu Quản Trị Viên không đúng.")

            # Xác định school_id hợp lệ cho tài khoản admin
            target_school_id = req.school_id
            if not target_school_id:
                first_school = conn.execute("SELECT id FROM schools ORDER BY id ASC LIMIT 1").fetchone()
                if first_school:
                    target_school_id = first_school["id"]

            # Tìm kiếm tài khoản admin đã có trong bảng users
            user_row = None
            if req.school_id:
                user_row = conn.execute("SELECT * FROM users WHERE username='admin' AND school_id=?", (req.school_id,)).fetchone()
            if not user_row and target_school_id:
                user_row = conn.execute("SELECT * FROM users WHERE username='admin' AND school_id=?", (target_school_id,)).fetchone()
            if not user_row:
                user_row = conn.execute("SELECT * FROM users WHERE username='admin' ORDER BY id DESC LIMIT 1").fetchone()

            if not user_row:
                cur_u = conn.execute("""
                    INSERT INTO users (school_id, username, password_hash, salt, full_name, role, status)
                    VALUES (?, 'admin', ?, ?, 'Admin User', 'ADMIN', 'ACTIVE')
                """, (target_school_id, admin["password_hash"], admin["salt"]))
                conn.commit()
                admin_user_id = cur_u.lastrowid
                user_school_id = target_school_id
            else:
                admin_user_id = user_row["id"]
                user_school_id = user_row["school_id"] or target_school_id

            admin_user = {
                "id":                  admin_user_id,
                "school_id":           user_school_id,
                "username":            "admin",
                "email":               admin["email"],
                "role":                "ADMIN",
                "full_name":           admin["full_name"],
                "status":              "ACTIVE",
                "verified_status":     "VERIFIED",
                "verification_method": "MASTER_KEY",
                "verification_note":   "Tài khoản Quản Trị Tối Cao — Toàn Quyền Hệ Thống"
            }
            rt, rt_jti = create_refresh_token(admin_user_id)
            conn.execute("""
                INSERT INTO user_refresh_tokens (user_id, jti, expires_at)
                VALUES (?, ?, datetime('now', '+14 days'))
            """, (admin_user_id, rt_jti))
            conn.commit()
            token = _make_token(admin_user)
            response.set_cookie(key="access_token", value=token, max_age=86400 * 30, httponly=False, samesite="lax", path="/")
            return {
                "status":        "success",
                "message":       "Đăng nhập thành công với vai trò Quản Trị Viên Toàn Quyền.",
                "access_token":  token,
                "refresh_token": rt,
                "token_type":    "bearer",
                "user":          admin_user
            }

        # ── Tìm tài khoản người dùng theo username / phone / email ──
        candidates = conn.execute("""
            SELECT * FROM users
            WHERE status='ACTIVE' AND (username=? OR phone=? OR email=?)
        """, (req.username_or_phone, req.username_or_phone, req.username_or_phone)).fetchall()

        if not candidates:
            raise HTTPException(401, "Tên đăng nhập hoặc Mật khẩu không đúng.")

        # Đối chiếu mật khẩu
        matching = [c for c in candidates if verify_password(req.password, c["salt"], c["password_hash"])]
        if not matching:
            raise HTTPException(401, "Tên đăng nhập hoặc Mật khẩu không đúng.")

        # Xác định user chính xác (nếu chỉ định trường thì lấy theo trường, ngược lại tự động lấy user)
        if req.school_id is not None:
            user_match = next((c for c in matching if c["school_id"] == req.school_id), None)
            if not user_match:
                raise HTTPException(401, "Tài khoản không thuộc trường học đã chọn.")
        elif len(matching) == 1:
            user_match = matching[0]
        else:
            raise HTTPException(422, "Tài khoản của bạn tồn tại ở nhiều trường. Vui lòng chọn trường học cụ thể.")

        user_row = dict(user_match)
        conn.execute("UPDATE users SET last_login_at=datetime('now','localtime') WHERE id=?", (user_row["id"],))
        rt, rt_jti = create_refresh_token(user_row["id"])
        conn.execute("""
            INSERT INTO user_refresh_tokens (user_id, jti, expires_at)
            VALUES (?, ?, datetime('now', '+14 days'))
        """, (user_row["id"], rt_jti))
        conn.commit()

        token = _make_token(user_row)
        response.set_cookie(key="access_token", value=token, max_age=86400 * 30, httponly=False, samesite="lax", path="/")
        return {
            "status":        "success",
            "message":       "Đăng nhập thành công.",
            "access_token":  token,
            "refresh_token": rt,
            "token_type":    "bearer",
            "user":          _user_to_profile(user_row)
        }
    finally:
        conn.close()


# ─────────────────────────────────────────────────
# ME  (profile of current user)
# ─────────────────────────────────────────────────
@router.get("/me")
async def me(current: dict = Depends(get_current_user)):
    # Master Admin profile
    if current.get("role") in ("ADMIN", "PLATFORM_ADMIN"):
        sch_id = current.get("school_id")
        if not sch_id:
            conn = get_db()
            try:
                first_sch = conn.execute("SELECT id FROM schools ORDER BY id ASC LIMIT 1").fetchone()
                sch_id = first_sch["id"] if first_sch else None
            finally:
                conn.close()
        return {
            "status": "success",
            "user": {
                "id": current.get("user_id", 999999),
                "school_id": sch_id,
                "username": current.get("username", "admin"),
                "email": current.get("email", "admin@stemapp.vn"),
                "role": "ADMIN",
                "full_name": current.get("full_name", "👑 Quản Trị Viên Hệ Thống (Master Admin)"),
                "verified_status": "VERIFIED",
                "verification_method": "MASTER_KEY",
                "verification_note": "Tài khoản Quản Trị Tối Cao — Toàn Quyền Hệ Thống"
            }
        }

    conn = get_db()
    try:
        if current.get("school_id"):
            row = conn.execute(
                "SELECT * FROM users WHERE id=? AND school_id=?",
                (current["user_id"], current["school_id"])
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT * FROM users WHERE id=?",
                (current["user_id"],)
            ).fetchone()
        if not row:
            raise HTTPException(404, "Không tìm thấy tài khoản.")
        user_dict = _user_to_profile(dict(row))
        user_school_id = user_dict.get("school_id")

        if user_school_id:
            if user_dict.get("role") == "PARENT":
                children_rows = conn.execute("""
                    SELECT s.id, s.student_code, s.full_name, s.current_points, s.qr_token, c.name as class_name
                    FROM students s
                    LEFT JOIN classes c ON s.class_id = c.id
                    WHERE s.id IN (SELECT student_id FROM parent_student_links WHERE parent_user_id=?)
                       OR (s.parent_phone IS NOT NULL AND s.parent_phone=? AND s.school_id=?)
                """, (current["user_id"], user_dict.get("phone"), user_school_id)).fetchall()
                user_dict["children"] = [dict(ch) for ch in children_rows]
            elif user_dict.get("role") == "STUDENT":
                stu_row = conn.execute("""
                    SELECT s.id, s.class_id, s.student_code, s.full_name, s.current_points, s.qr_token, s.face_approved, s.face_photo_url, c.name as class_name,
                           COALESCE((SELECT COUNT(*) FROM student_face_samples sfs WHERE sfs.student_id=s.id AND sfs.school_id=s.school_id), 0) as face_samples_count
                    FROM students s
                    LEFT JOIN classes c ON s.class_id = c.id
                    WHERE s.user_id=? AND s.school_id=?
                """, (current["user_id"], user_school_id)).fetchone()
                if not stu_row and user_dict.get("student_code"):
                    stu_row = conn.execute("""
                        SELECT s.id, s.class_id, s.student_code, s.full_name, s.current_points, s.qr_token, s.face_approved, s.face_photo_url, c.name as class_name,
                               COALESCE((SELECT COUNT(*) FROM student_face_samples sfs WHERE sfs.student_id=s.id AND sfs.school_id=s.school_id), 0) as face_samples_count
                        FROM students s
                        LEFT JOIN classes c ON s.class_id = c.id
                        WHERE s.student_code=? AND s.school_id=?
                    """, (user_dict["student_code"], user_school_id)).fetchone()
                if stu_row:
                    stu_data = dict(stu_row)
                    user_dict["student_profile"] = stu_data
                    user_dict["face_samples_count"] = stu_data.get("face_samples_count", 0)
                    user_dict["face_photo_url"] = stu_data.get("face_photo_url")
            elif user_dict.get("role") == "TEACHER":
                hr_class = conn.execute("""
                    SELECT id, name, grade_level FROM classes
                    WHERE school_id=? AND homeroom_teacher_id=? AND is_active=1
                    LIMIT 1
                """, (user_school_id, current["user_id"])).fetchone()
                if hr_class:
                    user_dict["is_homeroom_teacher"] = True
                    user_dict["homeroom_class_id"] = hr_class["id"]
                    user_dict["homeroom_class_name"] = hr_class["name"]
                    user_dict["class_name"] = hr_class["name"]
                else:
                    user_dict["is_homeroom_teacher"] = False
                    user_dict["homeroom_class_id"] = None
                    user_dict["homeroom_class_name"] = None
                    user_dict["class_name"] = None

        return {"status": "success", "user": user_dict}
    finally:
        conn.close()


# ─────────────────────────────────────────────────
# OTP — Request
# ─────────────────────────────────────────────────
@router.post("/verify/request-otp")
async def request_otp(req: OtpRequest, request: Request, current: dict | None = Depends(get_current_user_optional)):
    check_rate_limit(f"otp_req:{get_client_ip(request)}:{req.target}", max_calls=3, window_seconds=300)
    otp_code  = "".join([str(secrets.randbelow(10)) for _ in range(OTP_LENGTH)])
    expires   = (datetime.now() + timedelta(minutes=OTP_EXPIRE_MINUTES)).isoformat()
    user_id   = current["user_id"] if current else None

    conn = get_db()
    try:
        conn.execute("""
            INSERT INTO verification_otps (user_id, school_id, target, otp_code, otp_type, expires_at)
            VALUES (?,?,?,?,?,?)
        """, (user_id, req.school_id, req.target, otp_code, req.otp_type, expires))
        conn.commit()

        response = {
            "status": "success",
            "message": f"Mã OTP đã được gửi đến {req.target}. Có hiệu lực {OTP_EXPIRE_MINUTES} phút."
        }
        if OTP_DEV_MODE:
            response["dev_otp"] = otp_code   # Only in development!
        return response
    finally:
        conn.close()


# ─────────────────────────────────────────────────
# OTP — Submit & Verify
# ─────────────────────────────────────────────────
@router.post("/verify/submit-otp")
async def submit_otp(req: OtpSubmit, request: Request, current: dict | None = Depends(get_current_user_optional)):
    check_rate_limit(f"otp_sub:{get_client_ip(request)}:{req.target}", max_calls=5, window_seconds=300)
    conn = get_db()
    try:
        now = datetime.now().isoformat()
        otp_row = conn.execute("""
            SELECT * FROM verification_otps
            WHERE school_id=? AND target=? AND otp_code=?
              AND expires_at > ? AND used_at IS NULL
            ORDER BY created_at DESC LIMIT 1
        """, (req.school_id, req.target, req.otp_code, now)).fetchone()

        if not otp_row:
            raise HTTPException(400, "Mã OTP không hợp lệ hoặc đã hết hạn.")

        # Mark OTP used
        conn.execute("UPDATE verification_otps SET used_at=? WHERE id=?", (now, otp_row["id"]))

        # Update user verified status
        if current:
            conn.execute("""
                UPDATE users SET
                    verified_status='VERIFIED',
                    verification_method='OTP_PHONE',
                    verification_note='Đã xác thực OTP số điện thoại chính chủ',
                    verified_at=datetime('now','localtime')
                WHERE id=? AND school_id=?
            """, (current["user_id"], current["school_id"]))
        else:
            # Update by phone
            conn.execute("""
                UPDATE users SET
                    verified_status='VERIFIED',
                    verification_method='OTP_PHONE',
                    verification_note='Đã xác thực OTP số điện thoại chính chủ',
                    verified_at=datetime('now','localtime')
                WHERE school_id=? AND phone=?
            """, (req.school_id, req.target))

        conn.commit()
        return {"status": "success", "message": "Xác thực OTP thành công! Tài khoản đã được cấp Tích Xanh."}
    finally:
        conn.close()


# ─────────────────────────────────────────────────
# ID CARD — Submit for review
# ─────────────────────────────────────────────────
@router.post("/verify/submit-id-card")
async def submit_id_card(req: IDCardSubmit, current: dict = Depends(get_current_user)):
    conn = get_db()
    try:
        # Save doc_data_url as a file (in uploads dir)
        import base64, os
        from app.config import UPLOAD_DIR
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

        ext = "jpg"
        if ";base64," in req.doc_data_url:
            mime_part = req.doc_data_url.split(";")[0].split("/")[-1]
            if mime_part in ("png", "jpg", "jpeg", "webp"):
                ext = mime_part
            raw = req.doc_data_url.split(",", 1)[1]
        else:
            raw = req.doc_data_url

        fname    = f"idcard_{current['user_id']}_{int(datetime.now().timestamp())}.{ext}"
        fpath    = UPLOAD_DIR / fname
        with open(fpath, "wb") as f:
            f.write(base64.b64decode(raw + "=="))

        doc_url = f"/uploads/{fname}"

        conn.execute("""
            UPDATE users SET
                verified_status='PENDING_REVIEW',
                verification_method='ID_CARD',
                verification_doc_url=?,
                verification_note=?
            WHERE id=? AND school_id=?
        """, (doc_url, req.note or f"Nộp {req.doc_type} chờ GVCN xét duyệt", current["user_id"], current["school_id"]))
        conn.commit()

        return {"status": "success", "message": "Đã gửi hồ sơ. GVCN/Nhà trường sẽ xét duyệt trong 24-48 giờ."}
    finally:
        conn.close()


# ─────────────────────────────────────────────────
# PENDING LIST  (TEACHER / HEADMASTER only)
# ─────────────────────────────────────────────────
@router.get("/verify/pending-list")
async def pending_list(school_id: int, current: dict = Depends(require_role("TEACHER", "INSPECTOR", "HEADMASTER"))):
    if current.get("role") not in ("ADMIN", "PLATFORM_ADMIN") and current.get("school_id") != school_id:
        raise HTTPException(403, "Không thuộc trường này.")
    conn = get_db()
    try:
        rows = conn.execute("""
            SELECT id, full_name, username, phone, email, role,
                   verified_status, verification_method, verification_doc_url, verification_note, created_at
            FROM users
            WHERE school_id=? AND verified_status='PENDING_REVIEW'
            ORDER BY created_at DESC
        """, (school_id,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ─────────────────────────────────────────────────
# APPROVE  (TEACHER / HEADMASTER only)
# ─────────────────────────────────────────────────
@router.post("/verify/approve")
async def approve_verification(req: ApproveVerification, current: dict = Depends(require_role("TEACHER", "INSPECTOR", "HEADMASTER"))):
    if req.status not in ("VERIFIED", "REJECTED"):
        raise HTTPException(422, "status phải là VERIFIED hoặc REJECTED.")
    conn = get_db()
    try:
        if current.get("role") in ("ADMIN", "PLATFORM_ADMIN"):
            target = conn.execute("SELECT * FROM users WHERE id=?", (req.user_id,)).fetchone()
        else:
            target = conn.execute("SELECT * FROM users WHERE id=? AND school_id=?", (req.user_id, current["school_id"])).fetchone()
        if not target:
            raise HTTPException(404, "Không tìm thấy tài khoản.")

        target_dict = dict(target)
        target_school_id = target_dict.get("school_id")
        note = req.note or (f"Duyệt bởi {current.get('full_name', 'BGH')}" if req.status == "VERIFIED" else "Ban Giám Hiệu từ chối duyệt")

        if req.status == "VERIFIED":
            conn.execute("""
                UPDATE users SET
                    verified_status='VERIFIED',
                    status='ACTIVE',
                    verification_note=?,
                    verified_at=datetime('now','localtime'),
                    updated_at=datetime('now','localtime')
                WHERE id=?
            """, (note, req.user_id))

            # Active student record if user is student
            if target_dict.get("role") == "STUDENT" and target_school_id:
                existing_stu = conn.execute("SELECT id FROM students WHERE user_id=?", (req.user_id,)).fetchone()
                if existing_stu:
                    conn.execute("UPDATE students SET is_active=1, is_deleted=0, school_id=? WHERE id=?", (target_school_id, existing_stu["id"]))
                else:
                    code = target_dict.get("student_code") or target_dict.get("user_code") or generate_role_code(conn, target_school_id, "STUDENT")
                    qr_token = f"QR-{code}-{secrets.token_hex(4).upper()}"
                    conn.execute("""
                        INSERT INTO students (user_id, school_id, student_code, full_name, dob, parent_phone, qr_token, current_points, is_active)
                        VALUES (?, ?, ?, ?, ?, ?, ?, 100, 1)
                    """, (req.user_id, target_school_id, code, target_dict["full_name"], target_dict.get("dob"), target_dict.get("phone"), qr_token))

            # Sync parent links if user is parent
            elif target_dict.get("role") == "PARENT" and target_school_id and target_dict.get("phone"):
                matched_students = conn.execute("SELECT id FROM students WHERE school_id=? AND parent_phone=?", (target_school_id, target_dict["phone"])).fetchall()
                for s in matched_students:
                    conn.execute("""
                        INSERT OR IGNORE INTO parent_student_links (parent_user_id, student_id, school_id, relation_name, verified_status, verified_at)
                        VALUES (?, ?, ?, 'Phụ huynh', 'VERIFIED', datetime('now','localtime'))
                    """, (req.user_id, s["id"], target_school_id))

            conn.commit()
            return {"status": "success", "message": f"Đã phê duyệt thành công cho {target_dict['full_name']}"}

        else: # REJECTED
            if target_dict.get("verification_method") == "JOIN_REQUEST":
                # Free candidate from school so they can re-apply
                conn.execute("""
                    UPDATE users SET
                        school_id=NULL,
                        verified_status='UNVERIFIED',
                        verification_method=NULL,
                        verification_note=?,
                        updated_at=datetime('now','localtime')
                    WHERE id=?
                """, (note, req.user_id))
                if target_school_id:
                    conn.execute("UPDATE students SET is_active=0, is_deleted=1 WHERE user_id=? AND school_id=?", (req.user_id, target_school_id))
            else:
                conn.execute("""
                    UPDATE users SET
                        verified_status='REJECTED',
                        verification_note=?,
                        updated_at=datetime('now','localtime')
                    WHERE id=?
                """, (note, req.user_id))

            conn.commit()
            return {"status": "success", "message": f"Đã từ chối xét duyệt cho {target_dict['full_name']}"}
    finally:
        conn.close()


# ─────────────────────────────────────────────────
# REFRESH TOKEN
# ─────────────────────────────────────────────────
class RefreshRequest(BaseModel):
    refresh_token: str


@router.post("/refresh")
async def refresh_access_token(req: RefreshRequest):
    """Exchange a valid refresh_token for a new access_token."""
    from app.core.security import decode_refresh_token, create_access_token_with_jti
    from datetime import datetime as _dt

    claims = decode_refresh_token(req.refresh_token)
    if not claims or claims.get("type") != "refresh":
        raise HTTPException(401, "Refresh token không hợp lệ hoặc đã hết hạn.")

    jti = claims.get("jti")
    user_id = claims.get("user_id")

    conn = get_db()
    try:
        # Check token not revoked
        rt_row = conn.execute(
            "SELECT id, revoked_at FROM user_refresh_tokens WHERE jti=? AND user_id=?",
            (jti, user_id)
        ).fetchone()
        if not rt_row or rt_row["revoked_at"]:
            raise HTTPException(401, "Refresh token đã bị thu hồi. Vui lòng đăng nhập lại.")

        # Fetch fresh user data
        user = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        if not user or user["status"] != "ACTIVE":
            raise HTTPException(401, "Tài khoản không hợp lệ hoặc đã bị khóa.")

        user_dict = dict(user)
        new_token, new_jti = create_access_token_with_jti({
            "sub":            str(user_dict["id"]),
            "user_id":        user_dict["id"],
            "school_id":      user_dict["school_id"],
            "username":       user_dict["username"],
            "role":           user_dict["role"],
            "full_name":      user_dict["full_name"],
            "verified_status": user_dict.get("verified_status", "UNVERIFIED"),
        })
        return {"access_token": new_token, "token_type": "bearer"}
    finally:
        conn.close()


# ─────────────────────────────────────────────────
# LOGOUT — Blacklist current access token
# ─────────────────────────────────────────────────
@router.post("/logout")
async def logout(authorization: str = Header(default="")):
    """Revoke access token — add jti to blacklist."""
    from app.core.security import decode_access_token
    from datetime import datetime as _dt

    if not authorization.startswith("Bearer "):
        return {"status": "ok"}  # already logged out

    token = authorization.removeprefix("Bearer ").strip()
    claims = decode_access_token(token)
    if not claims:
        return {"status": "ok"}  # expired anyway

    jti = claims.get("jti")
    exp = claims.get("exp", 0)
    if not jti:
        return {"status": "ok"}  # old token without jti, just ignore

    from datetime import timezone
    exp_dt = _dt.fromtimestamp(exp, timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    conn = get_db()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO token_blacklist (jti, expires_at) VALUES (?, ?)",
            (jti, exp_dt)
        )
        # Also revoke refresh tokens if user_id is present
        user_id = claims.get("user_id")
        if user_id:
            conn.execute(
                "UPDATE user_refresh_tokens SET revoked_at=datetime('now','localtime') WHERE user_id=? AND revoked_at IS NULL",
                (user_id,)
            )
        conn.commit()
    finally:
        conn.close()

    return {"status": "ok", "message": "Đã đăng xuất thành công."}


# ─────────────────────────────────────────────────
# CHANGE PASSWORD (FOR ALL USERS & ADMIN)
# ─────────────────────────────────────────────────
class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


class AdminResetPasswordRequest(BaseModel):
    user_id: int
    new_password: str = "123456"


@router.post("/change-password")
async def change_password(req: ChangePasswordRequest, current: dict = Depends(get_current_user)):
    """Đổi mật khẩu cho người dùng đang đăng nhập (áp dụng cho mọi vai trò, bao gồm ADMIN)."""
    if len(req.new_password) < 6:
        raise HTTPException(400, "Mật khẩu mới phải có ít nhất 6 ký tự.")

    conn = get_db()
    try:
        user_id = current.get("user_id") or current.get("sub")
        role = current.get("role")

        if role in ("ADMIN", "PLATFORM_ADMIN"):
            admin = conn.execute(
                "SELECT * FROM platform_admins WHERE id=? OR email=?",
                (user_id, current.get("email", "admin@stemapp.vn"))
            ).fetchone()
            if not admin:
                raise HTTPException(404, "Không tìm thấy tài khoản quản trị viên.")
            if not verify_password(req.old_password, admin["salt"], admin["password_hash"]):
                raise HTTPException(400, "Mật khẩu cũ không chính xác.")

            new_salt = generate_salt()
            new_hash = hash_password(req.new_password, new_salt)
            conn.execute(
                "UPDATE platform_admins SET password_hash=?, salt=? WHERE id=?",
                (new_hash, new_salt, admin["id"])
            )
            conn.commit()
            log.info(f"[AUTH] Platform Admin {admin['email']} đổi mật khẩu thành công.")
            return {"status": "success", "message": "Đổi mật khẩu thành công."}

        user = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        if not user:
            raise HTTPException(404, "Không tìm thấy người dùng.")
        if not verify_password(req.old_password, user["salt"], user["password_hash"]):
            raise HTTPException(400, "Mật khẩu cũ không chính xác.")

        new_salt = generate_salt()
        new_hash = hash_password(req.new_password, new_salt)
        conn.execute(
            "UPDATE users SET password_hash=?, salt=?, updated_at=datetime('now','localtime') WHERE id=?",
            (new_hash, new_salt, user_id)
        )
        conn.commit()
        log.info(f"[AUTH] User {user['username']} (ID: {user_id}) đổi mật khẩu thành công.")
        return {"status": "success", "message": "Đổi mật khẩu thành công."}
    finally:
        conn.close()


@router.post("/admin-reset-password")
async def admin_reset_password(
    req: AdminResetPasswordRequest,
    current: dict = Depends(require_role("HEADMASTER", "ADMIN"))
):
    """Admin hoặc Hiệu trưởng đặt lại mật khẩu cho thành viên."""
    if len(req.new_password) < 6:
        raise HTTPException(400, "Mật khẩu mới phải có ít nhất 6 ký tự.")
    conn = get_db()
    try:
        user = conn.execute("SELECT * FROM users WHERE id=?", (req.user_id,)).fetchone()
        if not user:
            raise HTTPException(404, "Không tìm thấy người dùng.")
        if current.get("role") != "ADMIN" and user["school_id"] != current.get("school_id"):
            raise HTTPException(403, "Không có quyền đổi mật khẩu cho người dùng trường khác.")

        new_salt = generate_salt()
        new_hash = hash_password(req.new_password, new_salt)
        conn.execute(
            "UPDATE users SET password_hash=?, salt=?, updated_at=datetime('now','localtime') WHERE id=?",
            (new_hash, new_salt, req.user_id)
        )
        conn.commit()
        return {"status": "success", "message": f"Đã đặt lại mật khẩu cho {user['full_name']} thành công."}
    finally:
        conn.close()


