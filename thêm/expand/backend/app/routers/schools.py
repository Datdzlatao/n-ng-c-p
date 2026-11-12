"""
app/routers/schools.py — School (Server) management
GET  /api/v1/schools              — List / search all schools
GET  /api/v1/schools/{id}         — Get school info + form_config (public)
POST /api/v1/schools              — Create a new school server
PUT  /api/v1/schools/{id}/config/rules   — Update school rules
PUT  /api/v1/schools/{id}/config/form    — Update join form requirements
PUT  /api/v1/schools/{id}/config/codes   — Rotate invite codes
GET  /api/v1/schools/{id}/stats          — School-level stats dashboard
"""
import json, secrets, logging
from fastapi import APIRouter, HTTPException, Depends, Query, UploadFile, File
from pydantic import BaseModel
from typing import Optional

from app.database import get_db
from app.core.deps import get_current_user, require_role
from app.core.security import generate_salt, hash_password, create_access_token
from app.core.code_generator import generate_role_code
from app.routers.auth import _make_token, _user_to_profile

router = APIRouter(prefix="/api/v1/schools", tags=["Schools"])
log    = logging.getLogger("stem.schools")


# ─────────────────────────────────────────────────
# PYDANTIC MODELS
# ─────────────────────────────────────────────────
class CreateSchool(BaseModel):
    school_code:    str          # slug: thpt-nguyen-hue
    name:           str
    short_name:     Optional[str] = None
    address:        Optional[str] = None
    province_city:  Optional[str] = None
    academic_year:  str = "2025-2026"
    # Initial headmaster credentials
    headmaster_username: str
    headmaster_password: str
    headmaster_name:     str
    headmaster_phone:    Optional[str] = None
    headmaster_email:    Optional[str] = None


class UpdateRulesConfig(BaseModel):
    # Cấu hình chung & Fallback tương thích ngược
    checkin_from:             Optional[str] = "06:00"
    checkin_on_time_until:    Optional[str] = "07:15"
    checkin_late_until:       Optional[str] = "07:30"
    checkout_from:            Optional[str] = "17:00"
    uniform_check:            bool = True
    min_points_warning:       int  = 80
    late_deduct_points:       int  = 2
    absent_deduct_points:     int  = 5
    violation_deduct_points:  int  = 3

    # Buổi Sáng (Morning)
    morning_enabled:          bool = True
    morning_name:             str  = "Chính khóa buổi sáng"
    morning_from:             str  = "06:00"
    morning_on_time:          str  = "07:15"
    morning_late_until:       str  = "07:30"
    morning_checkout:         str  = "11:30"
    morning_uniform_check:    bool = True
    morning_late_deduct:      int  = 2
    morning_notify_parent:    bool = True
    morning_auth_mode:        str  = "ALL"

    # Buổi Chiều (Afternoon)
    afternoon_enabled:        bool = True
    afternoon_name:           str  = "Buổi 2 / Ngoại khóa"
    afternoon_from:           str  = "12:30"
    afternoon_on_time:        str  = "13:15"
    afternoon_late_until:     str  = "13:30"
    afternoon_checkout:       str  = "17:00"
    afternoon_uniform_check:  bool = True
    afternoon_late_deduct:    int  = 2
    afternoon_notify_parent:  bool = True
    afternoon_auth_mode:      str  = "ALL"

    # Buổi Tối (Evening / Nội trú / Tự học)
    evening_enabled:          bool = False
    evening_name:             str  = "Tự học / Nội trú"
    evening_from:             str  = "18:00"
    evening_on_time:          str  = "18:45"
    evening_late_until:       str  = "19:15"
    evening_checkout:         str  = "21:30"
    evening_uniform_check:    bool = False
    evening_late_deduct:      int  = 1
    evening_notify_parent:    bool = True
    evening_auth_mode:        str  = "ALL"


class UpdateFormConfig(BaseModel):
    student_require_student_code: bool = True
    student_require_phone:        bool = True
    student_require_face_photo:   bool = True
    student_require_dob:          bool = True
    parent_require_phone:         bool = True
    parent_require_student_link:  bool = True
    teacher_require_invite_code:  bool = True


# ─────────────────────────────────────────────────
# LIST / SEARCH SCHOOLS  (public)
# ─────────────────────────────────────────────────
@router.get("")
async def list_schools(q: Optional[str] = Query(None), province: Optional[str] = Query(None)):
    conn = get_db()
    try:
        sql    = "SELECT id, school_code, name, short_name, logo_url, address, province_city, academic_year, status FROM schools WHERE status='ACTIVE'"
        params = []
        if q:
            sql += " AND (name LIKE ? OR school_code LIKE ? OR short_name LIKE ?)"
            like = f"%{q}%"
            params += [like, like, like]
        if province:
            sql += " AND province_city LIKE ?"
            params.append(f"%{province}%")
        sql += " ORDER BY name"
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ─────────────────────────────────────────────────
# GET SINGLE SCHOOL  (public — for join flow)
# ─────────────────────────────────────────────────
@router.get("/{school_id}")
async def get_school(school_id: int):
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT id, school_code, name, short_name, logo_url, address, province_city, academic_year, status, rules_config, form_config FROM schools WHERE id=? AND status='ACTIVE'",
            (school_id,)
        ).fetchone()
        if not row:
            raise HTTPException(404, "Không tìm thấy trường học.")
        d = dict(row)
        d["rules_config"] = json.loads(d.get("rules_config") or "{}")
        d["form_config"]  = json.loads(d.get("form_config") or "{}")
        return d
    finally:
        conn.close()


# ─────────────────────────────────────────────────
# CREATE SCHOOL — "NGÔI TRƯỜNG CỦA TÔI" (ADMIN / HEADMASTER ONLY)
# ─────────────────────────────────────────────────
@router.post("")
async def create_school(req: CreateSchool, current: dict = Depends(require_role("ADMIN", "HEADMASTER"))):
    """
    Chỉ dành cho Admin Tối Cao hoặc Hiệu Trưởng được cấp quyền khởi tạo "Ngôi Trường Của Tôi".
    """
    conn = get_db()
    try:
        # Check duplicate school_code
        dup = conn.execute("SELECT id FROM schools WHERE school_code=?", (req.school_code,)).fetchone()
        if dup:
            raise HTTPException(409, f"Mã trường '{req.school_code}' đã tồn tại. Vui lòng chọn mã khác.")

        default_rules = json.dumps({
            "checkin_from": "06:00",
            "checkin_on_time_until": "07:15",
            "checkin_late_until": "07:30",
            "uniform_check": True,
            "min_points_warning": 80,
            "late_deduct_points": 2,
            "absent_deduct_points": 5,
            "violation_deduct_points": 3
        })
        default_form = json.dumps({
            "student": {
                "require_student_code": True,
                "require_phone":        True,
                "require_face_photo":   True,
                "require_dob":          True
            },
            "parent": {
                "require_phone":         True,
                "require_student_link":  True
            },
            "teacher": {
                "require_invite_code": True
            }
        })

        # Generate invite codes
        teacher_code   = f"GV_{req.school_code.upper().replace('-','_')}_{secrets.token_hex(4).upper()}"
        inspector_code = f"GT_{req.school_code.upper().replace('-','_')}_{secrets.token_hex(4).upper()}"
        bgh_code       = f"BGH_{req.school_code.upper().replace('-','_')}_{secrets.token_hex(4).upper()}"

        conn.execute("""
            INSERT INTO schools (
                school_code, name, short_name, address, province_city,
                academic_year, status, rules_config, form_config,
                teacher_invite_code, inspector_invite_code, bgh_invite_code
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            req.school_code, req.name, req.short_name, req.address, req.province_city,
            req.academic_year, "ACTIVE", default_rules, default_form,
            teacher_code, inspector_code, bgh_code
        ))
        school_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        # Create headmaster user
        salt = generate_salt()
        pw   = hash_password(req.headmaster_password, salt)
        conn.execute("""
            INSERT INTO users (
                school_id, username, email, phone, password_hash, salt,
                full_name, role, status, verified_status, verification_method, verification_note
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            school_id, req.headmaster_username, req.headmaster_email, req.headmaster_phone,
            pw, salt, req.headmaster_name,
            "HEADMASTER", "ACTIVE", "VERIFIED", "SCHOOL_FOUNDER",
            "Tài khoản Hiệu Trưởng khởi tạo trường"
        ))
        headmaster_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        # Link school owner
        conn.execute("UPDATE schools SET owner_user_id=? WHERE id=?", (headmaster_id, school_id))
        conn.commit()

        headmaster_row = dict(conn.execute("SELECT * FROM users WHERE id=?", (headmaster_id,)).fetchone())
        token = create_access_token({
            "sub": str(headmaster_id), "user_id": headmaster_id,
            "school_id": school_id, "username": req.headmaster_username,
            "role": "HEADMASTER", "full_name": req.headmaster_name,
            "verified_status": "VERIFIED"
        })

        return {
            "status": "success",
            "message": f"Đã tạo thành công 'Ngôi Trường Của Tôi': {req.name}!",
            "school": {
                "id": school_id,
                "school_code": req.school_code,
                "name": req.name,
                "province_city": req.province_city
            },
            "school_id": school_id,
            "school_code": req.school_code,
            "invite_codes": {
                "teacher":   teacher_code,
                "inspector": inspector_code,
                "bgh":       bgh_code
            },
            "access_token": token,
            "headmaster": {"id": headmaster_id, "username": req.headmaster_username, "full_name": req.headmaster_name}
        }
    finally:
        conn.close()


# ─────────────────────────────────────────────────
# UPDATE RULES CONFIG  (HEADMASTER only)
# ─────────────────────────────────────────────────
@router.put("/{school_id}/config/rules")
async def update_rules(school_id: int, cfg: UpdateRulesConfig, current: dict = Depends(require_role("HEADMASTER"))):
    if current.get("role") not in ("ADMIN", "PLATFORM_ADMIN") and current.get("school_id") != school_id:
        raise HTTPException(403, "Không thuộc trường này.")
    
    rules_dict = cfg.dict()
    # Tự động đồng bộ các trường legacy với ca sáng & chiều để đảm bảo tương thích ngược tuyệt đối
    if rules_dict.get("morning_from"):
        rules_dict["checkin_from"] = rules_dict["morning_from"]
    if rules_dict.get("morning_on_time"):
        rules_dict["checkin_on_time_until"] = rules_dict["morning_on_time"]
    if rules_dict.get("morning_late_until"):
        rules_dict["checkin_late_until"] = rules_dict["morning_late_until"]
    if rules_dict.get("afternoon_checkout"):
        rules_dict["checkout_from"] = rules_dict["afternoon_checkout"]

    conn = get_db()
    try:
        conn.execute(
            "UPDATE schools SET rules_config=?, updated_at=datetime('now','localtime') WHERE id=?",
            (json.dumps(rules_dict, ensure_ascii=False), school_id)
        )
        conn.commit()

        # Phát sóng sự kiện WebSocket thông báo cấu hình đã đồng bộ thời gian thực
        try:
            from app.routers.websocket import broadcast_to_school
            import asyncio
            asyncio.create_task(broadcast_to_school(school_id, {
                "type": "RULES_CONFIG_UPDATED",
                "rules": rules_dict,
                "message": "Quy định giờ học (Sáng · Chiều · Tối) và nề nếp đã được cập nhật thành công."
            }))
        except Exception:
            pass

        return {
            "status": "success",
            "message": "Đã cập nhật quy định trường (Sáng - Chiều - Tối) & đồng bộ tức thì!",
            "rules": rules_dict
        }
    finally:
        conn.close()


# ─────────────────────────────────────────────────
# UPDATE FORM CONFIG  (HEADMASTER only)
# ─────────────────────────────────────────────────
@router.put("/{school_id}/config/form")
async def update_form_config(school_id: int, cfg: UpdateFormConfig, current: dict = Depends(require_role("HEADMASTER"))):
    if current.get("role") not in ("ADMIN", "PLATFORM_ADMIN") and current.get("school_id") != school_id:
        raise HTTPException(403, "Không thuộc trường này.")
    conn = get_db()
    try:
        form_dict = {
            "student": {
                "require_student_code": cfg.student_require_student_code,
                "require_phone":        cfg.student_require_phone,
                "require_face_photo":   cfg.student_require_face_photo,
                "require_dob":          cfg.student_require_dob
            },
            "parent": {
                "require_phone":        cfg.parent_require_phone,
                "require_student_link": cfg.parent_require_student_link
            },
            "teacher": {
                "require_invite_code":  cfg.teacher_require_invite_code
            }
        }
        conn.execute(
            "UPDATE schools SET form_config=?, updated_at=datetime('now','localtime') WHERE id=?",
            (json.dumps(form_dict), school_id)
        )
        conn.commit()
        return {"status": "success", "message": "Đã cập nhật cấu hình form đăng ký.", "form_config": form_dict}
    finally:
        conn.close()


# ─────────────────────────────────────────────────
# ROTATE INVITE CODES  (HEADMASTER only)
# ─────────────────────────────────────────────────
@router.put("/{school_id}/config/codes")
async def rotate_invite_codes(school_id: int, current: dict = Depends(require_role("HEADMASTER"))):
    if current.get("role") not in ("ADMIN", "PLATFORM_ADMIN") and current.get("school_id") != school_id:
        raise HTTPException(403, "Không thuộc trường này.")
    conn = get_db()
    try:
        school = conn.execute("SELECT school_code FROM schools WHERE id=?", (school_id,)).fetchone()
        code = school["school_code"].upper().replace("-", "_")
        new_teacher   = f"GV_{code}_{secrets.token_hex(4).upper()}"
        new_inspector = f"GT_{code}_{secrets.token_hex(4).upper()}"
        new_bgh       = f"BGH_{code}_{secrets.token_hex(4).upper()}"
        conn.execute("""
            UPDATE schools SET
                teacher_invite_code=?, inspector_invite_code=?, bgh_invite_code=?,
                updated_at=datetime('now','localtime')
            WHERE id=?
        """, (new_teacher, new_inspector, new_bgh, school_id))
        conn.commit()
        return {
            "status": "success",
            "message": "Đã tạo mã mời mới. Thông báo ngay cho GVCN & Giám Thị.",
            "invite_codes": {"teacher": new_teacher, "inspector": new_inspector, "bgh": new_bgh}
        }
    finally:
        conn.close()


# ─────────────────────────────────────────────────
# SCHOOL STATS  (HEADMASTER / INSPECTOR / TEACHER)
# ─────────────────────────────────────────────────
@router.get("/{school_id}/stats")
async def school_stats(school_id: int, current: dict = Depends(require_role("HEADMASTER", "INSPECTOR", "TEACHER"))):
    if current.get("role") not in ("ADMIN", "PLATFORM_ADMIN") and current.get("school_id") != school_id:
        raise HTTPException(403, "Không thuộc trường này.")
    conn = get_db()
    try:
        total_students = conn.execute("SELECT COUNT(*) FROM students WHERE school_id=? AND is_active=1", (school_id,)).fetchone()[0]
        total_teachers = conn.execute("SELECT COUNT(*) FROM users WHERE school_id=? AND role='TEACHER' AND status='ACTIVE'", (school_id,)).fetchone()[0]
        total_classes  = conn.execute("SELECT COUNT(*) FROM classes WHERE school_id=? AND is_active=1", (school_id,)).fetchone()[0]
        pending_verify = conn.execute("SELECT COUNT(*) FROM users WHERE school_id=? AND verified_status='PENDING_REVIEW'", (school_id,)).fetchone()[0]
        pending_disputes = conn.execute("SELECT COUNT(*) FROM disputes WHERE school_id=? AND status='PENDING'", (school_id,)).fetchone()[0]
        pending_leaves = conn.execute("SELECT COUNT(*) FROM leave_requests WHERE school_id=? AND status='PENDING'", (school_id,)).fetchone()[0]
        today_attendance = conn.execute(
            "SELECT COUNT(*) FROM attendance_logs WHERE school_id=? AND date_only=date('now','localtime')", (school_id,)
        ).fetchone()[0]
        return {
            "total_students": total_students,
            "total_teachers": total_teachers,
            "total_classes":  total_classes,
            "pending_verifications": pending_verify,
            "pending_join_requests": pending_verify,
            "pending_disputes":   pending_disputes,
            "pending_leaves":     pending_leaves,
            "today_attendance":   today_attendance,
        }
    finally:
        conn.close()


# ─────────────────────────────────────────────────
# AI RULE PARSER (GEMINI POWERED - TEXT & 50MB FILE)
# ─────────────────────────────────────────────────
class ParseRuleTextRequest(BaseModel):
    raw_text: str

@router.post("/{school_id}/ai-rules/parse")
async def parse_school_rules_ai(school_id: int, req: ParseRuleTextRequest, current: dict = Depends(require_role("HEADMASTER"))):
    """Use Gemini AI to parse natural language rules into structured violation rules."""
    if current.get("role") not in ("ADMIN", "PLATFORM_ADMIN") and current.get("school_id") != school_id:
        raise HTTPException(403, "Không thuộc trường này.")
    if not req.raw_text.strip():
        raise HTTPException(422, "Văn bản nội quy không được để trống.")
    
    from app.services.rule_parser_service import parse_rules_with_gemini
    parsed_rules = parse_rules_with_gemini(req.raw_text)
    
    conn = get_db()
    try:
        conn.execute(
            "UPDATE schools SET rules_config=?, updated_at=datetime('now','localtime') WHERE id=?",
            (json.dumps(parsed_rules), school_id)
        )
        conn.commit()
        return {
            "status": "success",
            "message": "AI Gemini đã phân tích và cập nhật thành công bộ lọc lỗi camera!",
            "rules_profile": parsed_rules
        }
    finally:
        conn.close()


@router.post("/{school_id}/ai-rules/upload-file")
async def upload_school_rules_file(
    school_id: int,
    file: UploadFile = File(...),
    current: dict = Depends(require_role("HEADMASTER"))
):
    """Upload PDF / DOCX / TXT school rule handbook (up to 50MB) -> Extract text -> Gemini AI parse -> Sync to Pi."""
    if current.get("role") not in ("ADMIN", "PLATFORM_ADMIN") and current.get("school_id") != school_id:
        raise HTTPException(403, "Không thuộc trường này.")
    
    # Read file content (up to 50MB)
    content = await file.read()
    if len(content) > 50 * 1024 * 1024:
        raise HTTPException(413, "Dung lượng file vượt quá giới hạn 50MB.")
    
    from app.services.rule_parser_service import extract_text_from_file_bytes, parse_rules_with_gemini
    try:
        extracted_text = extract_text_from_file_bytes(content, file.filename or "rules.txt")
    except ValueError as ve:
        raise HTTPException(422, str(ve))
    except Exception as e:
        raise HTTPException(500, f"Lỗi đọc file: {e}")

    parsed_rules = parse_rules_with_gemini(extracted_text)
    
    conn = get_db()
    try:
        conn.execute(
            "UPDATE schools SET rules_config=?, updated_at=datetime('now','localtime') WHERE id=?",
            (json.dumps(parsed_rules), school_id)
        )
        conn.commit()
        return {
            "status": "success",
            "message": f"AI đã đọc thành công file '{file.filename}' ({len(content)/(1024*1024):.2f}MB) và cập nhật bộ lọc lỗi camera!",
            "file_name": file.filename,
            "file_size_mb": round(len(content)/(1024*1024), 2),
            "rules_profile": parsed_rules
        }
    finally:
        conn.close()


@router.get("/{school_id}/ai-rules/profile")
async def get_school_rules_profile(school_id: int):
    """Public / Edge endpoint: Raspberry Pi downloads the active rule profile for this school."""
    conn = get_db()
    try:
        school = conn.execute("SELECT id, name, school_code, rules_config, updated_at FROM schools WHERE id=?", (school_id,)).fetchone()
        if not school:
            raise HTTPException(404, "Không tìm thấy trường học.")
        
        rules = json.loads(school["rules_config"] or "{}")
        return {
            "school_id": school["id"],
            "school_name": school["name"],
            "school_code": school["school_code"],
            "rules": rules,
            "last_updated": school["updated_at"]
        }
    finally:
        conn.close()


# ─────────────────────────────────────────────────
# JOIN REQUESTS & 1-CLICK APPROVAL (SCHOOL ONBOARDING)
# ─────────────────────────────────────────────────
class JoinRequestAction(BaseModel):
    action: str                        # 'approve' | 'reject'
    rejectNote: Optional[str] = None


@router.post("/{school_id}/join-request")
async def send_join_request(school_id: int, current: dict = Depends(get_current_user)):
    """Candidate submits a request to join a school."""
    conn = get_db()
    try:
        school = conn.execute("SELECT id, name FROM schools WHERE id=? AND status='ACTIVE'", (school_id,)).fetchone()
        if not school:
            raise HTTPException(404, "Không tìm thấy trường học.")
        
        user_id = current["user_id"]
        user = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        if not user:
            raise HTTPException(404, "Không tìm thấy tài khoản người dùng.")

        # If already verified in this school
        if user["school_id"] == school_id and user["verified_status"] == "VERIFIED":
            return {
                "status": "success",
                "success": True,
                "message": f"Bạn đã là thành viên chính thức của {school['name']}.",
                "school_id": school_id,
                "access_token": _make_token(dict(user)),
                "user": _user_to_profile(dict(user))
            }
        
        user_role = user["role"] or "STUDENT"
        school_user_code = generate_role_code(conn, school_id, user_role)

        conn.execute("""
            UPDATE users SET
                school_id=?,
                user_code=?,
                student_code=CASE WHEN role='STUDENT' THEN ? ELSE student_code END,
                verified_status='PENDING_REVIEW',
                verification_method='JOIN_REQUEST',
                verification_note='Yêu cầu gia nhập trường đang chờ BGH xét duyệt',
                updated_at=datetime('now','localtime')
            WHERE id=?
        """, (school_id, school_user_code, school_user_code, user_id))

        if user_role == "STUDENT":
            existing_stu = conn.execute("SELECT id FROM students WHERE user_id=?", (user_id,)).fetchone()
            if not existing_stu:
                qr_token = f"QR-{school_user_code}-{secrets.token_hex(4).upper()}"
                conn.execute("""
                    INSERT INTO students (user_id, school_id, student_code, full_name, dob, parent_phone, qr_token, current_points, is_active)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 100, 0)
                """, (user_id, school_id, school_user_code, user["full_name"], user["dob"], user["phone"], qr_token))
            else:
                conn.execute("UPDATE students SET school_id=?, student_code=?, is_active=0 WHERE id=?", (school_id, school_user_code, existing_stu["id"]))

        conn.commit()

        updated_user = dict(conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone())
        new_token = _make_token(updated_user)

        return {
            "status": "success",
            "success": True,
            "message": f"Đã gửi yêu cầu gia nhập {school['name']} thành công! Đang chờ Ban Giám Hiệu xét duyệt.",
            "school_id": school_id,
            "access_token": new_token,
            "user": _user_to_profile(updated_user)
        }
    finally:
        conn.close()


@router.get("/{school_id}/requests")
async def get_school_join_requests(school_id: int, current: dict = Depends(require_role("HEADMASTER", "ADMIN", "INSPECTOR"))):
    """List pending membership requests for school admin approval."""
    if current.get("role") not in ("ADMIN", "PLATFORM_ADMIN") and current.get("school_id") != school_id:
        raise HTTPException(403, "Không có quyền truy cập trường này.")
    
    conn = get_db()
    try:
        rows = conn.execute("""
            SELECT id, full_name, username, phone, email, role, user_code, student_code,
                   verified_status, verification_method, verification_note, created_at
            FROM users
            WHERE school_id=? AND verified_status='PENDING_REVIEW'
            ORDER BY created_at DESC
        """, (school_id,)).fetchall()

        data = []
        for r in rows:
            d = dict(r)
            data.append({
                "id": d["id"],
                "schoolId": school_id,
                "status": "PENDING",
                "createdAt": d["created_at"],
                "verificationMethod": d.get("verification_method") or "JOIN_REQUEST",
                "verificationNote": d.get("verification_note") or "Chờ xét duyệt gia nhập",
                "user": {
                    "id": d["id"],
                    "fullName": d["full_name"],
                    "username": d["username"],
                    "memberCode": d.get("user_code") or d.get("student_code") or f"ID-{d['id']}",
                    "role": d["role"],
                    "phone": d["phone"],
                    "email": d["email"],
                }
            })
        return {"success": True, "status": "success", "data": data}
    finally:
        conn.close()


@router.post("/requests/{user_id}/action")
async def handle_join_request_action(
    user_id: int,
    req: JoinRequestAction,
    current: dict = Depends(require_role("HEADMASTER", "ADMIN", "INSPECTOR"))
):
    """1-Click Approve / Reject membership request without mandatory reason."""
    if req.action not in ("approve", "reject"):
        raise HTTPException(422, "Action phải là 'approve' hoặc 'reject'.")
    
    conn = get_db()
    try:
        target = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        if not target:
            raise HTTPException(404, "Không tìm thấy tài khoản cần duyệt.")
        
        target_dict = dict(target)
        target_school_id = target_dict.get("school_id")

        if current.get("role") not in ("ADMIN", "PLATFORM_ADMIN") and target_school_id != current.get("school_id"):
            raise HTTPException(403, "Tài khoản không thuộc thẩm quyền quản trị của trường này.")
        
        if req.action == "approve":
            new_status = "VERIFIED"
            note = f"Chấp thuận bởi {current.get('full_name', 'Ban Giám Hiệu')}"

            conn.execute("""
                UPDATE users SET
                    verified_status=?,
                    status='ACTIVE',
                    verification_note=?,
                    verified_at=datetime('now','localtime'),
                    updated_at=datetime('now','localtime')
                WHERE id=?
            """, (new_status, note, user_id))

            # Active student record if user is student
            if target_dict.get("role") == "STUDENT" and target_school_id:
                existing_stu = conn.execute("SELECT id FROM students WHERE user_id=?", (user_id,)).fetchone()
                if existing_stu:
                    conn.execute("UPDATE students SET is_active=1, is_deleted=0, school_id=? WHERE id=?", (target_school_id, existing_stu["id"]))
                else:
                    code = target_dict.get("student_code") or target_dict.get("user_code") or generate_role_code(conn, target_school_id, "STUDENT")
                    qr_token = f"QR-{code}-{secrets.token_hex(4).upper()}"
                    conn.execute("""
                        INSERT INTO students (user_id, school_id, student_code, full_name, dob, parent_phone, qr_token, current_points, is_active)
                        VALUES (?, ?, ?, ?, ?, ?, ?, 100, 1)
                    """, (user_id, target_school_id, code, target_dict["full_name"], target_dict.get("dob"), target_dict.get("phone"), qr_token))

            # Sync parent links if user is parent
            elif target_dict.get("role") == "PARENT" and target_school_id and target_dict.get("phone"):
                matched_students = conn.execute("SELECT id FROM students WHERE school_id=? AND parent_phone=?", (target_school_id, target_dict["phone"])).fetchall()
                for s in matched_students:
                    conn.execute("""
                        INSERT OR IGNORE INTO parent_student_links (parent_user_id, student_id, school_id, relation_name, verified_status, verified_at)
                        VALUES (?, ?, ?, 'Phụ huynh', 'VERIFIED', datetime('now','localtime'))
                    """, (user_id, s["id"], target_school_id))

            conn.commit()
            return {
                "success": True,
                "status": "success",
                "message": f"Đã chấp thuận yêu cầu gia nhập của {target_dict['full_name']}!"
            }

        else: # reject
            note = req.rejectNote or "Ban Giám Hiệu từ chối yêu cầu gia nhập"
            conn.execute("""
                UPDATE users SET
                    school_id=NULL,
                    verified_status='UNVERIFIED',
                    verification_method=NULL,
                    verification_note=?,
                    updated_at=datetime('now','localtime')
                WHERE id=?
            """, (note, user_id))

            if target_school_id:
                conn.execute("UPDATE students SET is_active=0, is_deleted=1 WHERE user_id=? AND school_id=?", (user_id, target_school_id))

            conn.commit()
            return {
                "success": True,
                "status": "success",
                "message": f"Đã từ chối yêu cầu gia nhập của {target_dict['full_name']}."
            }
    finally:
        conn.close()


