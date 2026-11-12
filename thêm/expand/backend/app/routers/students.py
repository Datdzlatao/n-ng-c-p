"""
app/routers/students.py — Student management & Apple FaceID Guided Enrollment
Scoped to /api/v1/s/{school_id}/students/
"""
import os, re, base64, shutil, secrets, logging
from pathlib import Path
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import Optional, List

from app.database import get_db
from app.config import UPLOAD_DIR, MAX_UPLOAD_MB
from app.core.deps import get_current_user, require_role
from app.core.code_generator import generate_role_code

router = APIRouter(prefix="/api/v1/s/{school_id}/students", tags=["Students"])
log    = logging.getLogger("stem.students")


class CreateStudent(BaseModel):
    full_name:    str
    student_code: Optional[str] = None   # Auto-generated if omitted
    dob:          Optional[str] = None
    gender:       Optional[str] = None
    class_id:     Optional[int] = None
    parent_phone: Optional[str] = None
    parent_name:  Optional[str] = None

class FaceEnrollPayload(BaseModel):
    front_image_b64: str                # Required: Frontal face image (DataURL or raw base64)
    left_image_b64:  Optional[str] = None  # Angle 1: Left turn
    right_image_b64: Optional[str] = None  # Angle 2: Right turn
    tilt_image_b64:  Optional[str] = None  # Angle 3: Tilt up / smile

class UpdateFaceApproval(BaseModel):
    status: str   # APPROVED | REJECTED
    note:   Optional[str] = None

class AssignParentRequest(BaseModel):
    parent_identifier: str  # Phone or Username or Email
    relation_name:     Optional[str] = "Phụ huynh"


def _check_scope(school_id: int, current: dict):
    if current.get("role") in ("ADMIN", "PLATFORM_ADMIN"):
        return
    if current.get("school_id") != school_id:
        raise HTTPException(403, "Không thuộc trường này.")


def _save_b64_image(b64_str: str, target_path: Path):
    if not b64_str:
        return

    resolved_root = UPLOAD_DIR.resolve()
    resolved_target = target_path.resolve()
    if not resolved_target.is_relative_to(resolved_root):
        raise HTTPException(400, "Đường dẫn tệp không an toàn.")

    if "," in b64_str:
        b64_str = b64_str.split(",", 1)[1]
    try:
        data = base64.b64decode(b64_str)
    except Exception:
        raise HTTPException(422, "Dữ liệu ảnh base64 không hợp lệ.")

    if len(data) > MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(413, f"Ảnh vượt quá kích thước cho phép ({MAX_UPLOAD_MB}MB).")

    # Magic byte check: JPEG, PNG, WEBP
    if not (data.startswith(b"\xff\xd8\xff") or data.startswith(b"\x89PNG\r\n\x1a\n") or data.startswith(b"RIFF")):
        raise HTTPException(422, "Định dạng ảnh không được hỗ trợ (chỉ nhận JPEG, PNG, WEBP).")

    target_path.parent.mkdir(parents=True, exist_ok=True)
    with open(target_path, "wb") as f:
        f.write(data)


@router.get("")
async def list_students(
    school_id: int,
    class_id:  Optional[int] = Query(None),
    q:         Optional[str]  = Query(None),
    current:   dict = Depends(require_role("TEACHER", "INSPECTOR", "HEADMASTER", "ADMIN"))
):
    _check_scope(school_id, current)
    conn = get_db()
    try:
        sql    = """
            SELECT s.*, c.name as class_name,
                   COALESCE((SELECT COUNT(*) FROM student_face_samples sfs WHERE sfs.student_id=s.id AND sfs.school_id=s.school_id), 0) as face_samples_count
            FROM students s
            LEFT JOIN classes c ON s.class_id=c.id
            WHERE s.school_id=? AND s.is_active=1 AND s.is_deleted=0
        """
        params = [school_id]
        if class_id:
            sql += " AND s.class_id=?"
            params.append(class_id)
        if q:
            sql += " AND (s.full_name LIKE ? OR s.student_code LIKE ?)"
            like = f"%{q}%"
            params += [like, like]
        if current.get("role") == "TEACHER":
            teacher_uid = current.get("user_id") or current.get("id")
            hr_row = conn.execute("""
                SELECT id FROM classes
                WHERE school_id=? AND is_active=1
                  AND (homeroom_teacher_id=? OR homeroom_teacher_id=(SELECT id FROM users WHERE school_id=? AND username=?))
                LIMIT 1
            """, (school_id, teacher_uid, school_id, current["username"])).fetchone()
            if hr_row and not class_id:
                # Nếu là GVCN và không chọn lớp cụ thể -> ưu tiên hiển thị học sinh lớp chủ nhiệm
                sql += " AND s.class_id=?"
                params.append(hr_row["id"])
        sql += " ORDER BY s.student_code ASC, s.full_name ASC"
        rows = conn.execute(sql, params).fetchall()

        # Map linked parents for each student
        links = conn.execute("""
            SELECT psl.student_id, psl.relation_name, psl.verified_status,
                   u.id as parent_user_id, u.full_name as parent_full_name,
                   u.username as parent_username, u.phone as parent_phone
            FROM parent_student_links psl
            JOIN users u ON psl.parent_user_id = u.id
            WHERE psl.school_id=?
        """, (school_id,)).fetchall()
        parents_map = {}
        for l in links:
            sid = l["student_id"]
            if sid not in parents_map:
                parents_map[sid] = []
            parents_map[sid].append(dict(l))

        result = []
        for r in rows:
            d = dict(r)
            d.pop("face_embedding_blob", None)
            d["linked_parents"] = parents_map.get(d["id"], [])
            result.append(d)
        return result
    finally:
        conn.close()


@router.get("/by-code/{student_code}")
async def get_student_by_code(school_id: int, student_code: str, current: dict = Depends(get_current_user)):
    """Lookup entire student profile, QR card, face photo, and attendance history by Student Code."""
    _check_scope(school_id, current)
    conn = get_db()
    try:
        row = conn.execute("""
            SELECT s.*, c.name as class_name,
                   COALESCE((SELECT COUNT(*) FROM student_face_samples sfs WHERE sfs.student_id=s.id AND sfs.school_id=s.school_id), 0) as face_samples_count
            FROM students s
            LEFT JOIN classes c ON s.class_id=c.id
            WHERE s.student_code=? AND s.school_id=? AND s.is_deleted=0
        """, (student_code, school_id)).fetchone()
        if not row:
            raise HTTPException(404, f"Không tìm thấy học sinh có mã '{student_code}'.")
        d = dict(row)
        d.pop("face_embedding_blob", None)
        if not d.get("parent_invite_code"):
            invite_code = f"PH-{secrets.token_hex(3).upper()}"
            conn.execute("UPDATE students SET parent_invite_code=? WHERE id=?", (invite_code, d["id"]))
            conn.commit()
            d["parent_invite_code"] = invite_code

        # Linked parents
        p_rows = conn.execute("""
            SELECT psl.relation_name, psl.verified_status,
                   u.id as parent_user_id, u.full_name as parent_full_name,
                   u.username as parent_username, u.phone as parent_phone
            FROM parent_student_links psl
            JOIN users u ON psl.parent_user_id = u.id
            WHERE psl.student_id=? AND psl.school_id=?
        """, (d["id"], school_id)).fetchall()
        d["linked_parents"] = [dict(p) for p in p_rows]
        
        # Fetch recent 10 attendance records
        att_rows = conn.execute(
            """SELECT timestamp, date_only, check_type, status, uniform_status, spoof_status, proof_image_url 
               FROM attendance_logs WHERE student_id=? ORDER BY timestamp DESC LIMIT 10""",
            (d["id"],)
        ).fetchall()
        d["recent_attendance"] = [dict(a) for a in att_rows]

        return d
    finally:
        conn.close()


@router.get("/{student_id}")
async def get_student(school_id: int, student_id: int, current: dict = Depends(get_current_user)):
    _check_scope(school_id, current)
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT s.*, c.name as class_name FROM students s LEFT JOIN classes c ON s.class_id=c.id WHERE s.id=? AND s.school_id=? AND s.is_deleted=0",
            (student_id, school_id)
        ).fetchone()
        if not row:
            raise HTTPException(404, "Không tìm thấy học sinh.")
        d = dict(row)
        d.pop("face_embedding_blob", None)

        p_rows = conn.execute("""
            SELECT psl.relation_name, psl.verified_status,
                   u.id as parent_user_id, u.full_name as parent_full_name,
                   u.username as parent_username, u.phone as parent_phone
            FROM parent_student_links psl
            JOIN users u ON psl.parent_user_id = u.id
            WHERE psl.student_id=? AND psl.school_id=?
        """, (d["id"], school_id)).fetchall()
        d["linked_parents"] = [dict(p) for p in p_rows]

        return d
    finally:
        conn.close()


@router.post("")
async def create_student(school_id: int, req: CreateStudent, current: dict = Depends(require_role("TEACHER", "HEADMASTER", "ADMIN"))):
    _check_scope(school_id, current)
    conn = get_db()
    try:
        # Auto-generate student code if not provided (e.g. HS01-0001)
        if not req.student_code or not req.student_code.strip():
            student_code = generate_role_code(conn, school_id, "STUDENT")
        else:
            student_code = req.student_code.strip().upper()

        dup = conn.execute("SELECT id FROM students WHERE school_id=? AND student_code=?", (school_id, student_code)).fetchone()
        if dup:
            raise HTTPException(409, f"Mã học sinh '{student_code}' đã tồn tại trong trường.")

        qr_token = f"QR-{student_code}-{secrets.token_hex(4).upper()}"
        parent_invite_code = f"PH-{secrets.token_hex(3).upper()}"
        conn.execute("""
            INSERT INTO students (school_id, class_id, student_code, full_name, dob, gender,
                                  parent_phone, parent_name, qr_token, parent_invite_code, current_points, is_active)
            VALUES (?,?,?,?,?,?,?,?,?,?,100,1)
        """, (
            school_id, req.class_id, student_code, req.full_name.strip(), req.dob, req.gender,
            req.parent_phone, req.parent_name, qr_token, parent_invite_code
        ))
        conn.commit()
        student_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        return {
            "status": "success",
            "message": f"Đã cấp mã học sinh '{student_code}' cho {req.full_name}.",
            "student_id": student_id,
            "student_code": student_code,
            "parent_invite_code": parent_invite_code,
            "qr_token": qr_token
        }
    finally:
        conn.close()


@router.post("/{student_id}/face-enroll")
async def enroll_student_faceid(
    school_id: int,
    student_id: int,
    payload: FaceEnrollPayload,
    current: dict = Depends(get_current_user)
):
    """
    Apple FaceID-style Guided Autocapture:
    Saves multi-angle pictures under the student's unique Student Code (<student_code>.jpg)
    Stores both on Backend and Edge camera directories for instant recognition.
    """
    _check_scope(school_id, current)
    conn = get_db()
    try:
        student = conn.execute("SELECT * FROM students WHERE id=? AND school_id=?", (student_id, school_id)).fetchone()
        if not student:
            raise HTTPException(404, "Không tìm thấy học sinh.")
        
        student_code = re.sub(r"[^a-zA-Z0-9_-]", "", student["student_code"])
        if not student_code:
            raise HTTPException(400, "Mã học sinh không hợp lệ.")
        
        # 1. Save Primary Frontal Face image as <student_code>.jpg
        face_filename = f"{student_code}.jpg"
        backend_face_path = UPLOAD_DIR / "faces" / face_filename
        _save_b64_image(payload.front_image_b64, backend_face_path)

        # 2. Copy to Edge faces directory if running on the same host
        from app.config import BASE_DIR
        edge_face_dir = BASE_DIR.parent / "edge" / "data" / "faces"
        has_edge = edge_face_dir.parent.exists()
        if has_edge:
            edge_face_dir.mkdir(parents=True, exist_ok=True)
            try:
                shutil.copy2(str(backend_face_path), str(edge_face_dir / face_filename))
            except Exception as e:
                log.warning(f"Could not copy face photo to edge dir: {e}")

        # 3. Save and copy multi-angle frames (left, right, tilt) for deep multi-angle recognition
        if payload.left_image_b64:
            left_backend = UPLOAD_DIR / "faces" / f"{student_code}_left.jpg"
            _save_b64_image(payload.left_image_b64, left_backend)
            if has_edge:
                try:
                    shutil.copy2(str(left_backend), str(edge_face_dir / f"{student_code}_left.jpg"))
                except Exception as e:
                    log.warning(f"Could not copy left face to edge dir: {e}")

        if payload.right_image_b64:
            right_backend = UPLOAD_DIR / "faces" / f"{student_code}_right.jpg"
            _save_b64_image(payload.right_image_b64, right_backend)
            if has_edge:
                try:
                    shutil.copy2(str(right_backend), str(edge_face_dir / f"{student_code}_right.jpg"))
                except Exception as e:
                    log.warning(f"Could not copy right face to edge dir: {e}")

        if payload.tilt_image_b64:
            tilt_backend = UPLOAD_DIR / "faces" / f"{student_code}_tilt.jpg"
            _save_b64_image(payload.tilt_image_b64, tilt_backend)
            if has_edge:
                try:
                    shutil.copy2(str(tilt_backend), str(edge_face_dir / f"{student_code}_tilt.jpg"))
                except Exception as e:
                    log.warning(f"Could not copy tilt face to edge dir: {e}")

        # Xóa cache vector đặc trưng cũ trên Edge để trạm camera tự động nạp lại embeddings đa góc mới nhất
        if has_edge and edge_face_dir.exists():
            cache_npz = edge_face_dir.parent / "faces_embeddings.npz"
            if cache_npz.exists():
                try:
                    cache_npz.unlink()
                except Exception:
                    pass
            edge_face_dir.touch(exist_ok=True)

        face_url = f"/uploads/faces/{face_filename}"
        conn.execute(
            "UPDATE students SET face_photo_url=?, face_approved='APPROVED', updated_at=datetime('now','localtime') WHERE id=?",
            (face_url, student_id)
        )
        conn.commit()

        return {
            "status": "success",
            "message": f"FaceID của học sinh '{student['full_name']}' ({student_code}) đã thu thập và lưu trữ thành công!",
            "student_code": student_code,
            "face_photo_url": face_url,
            "face_approved": "APPROVED",
            "files_saved": [
                f"/uploads/faces/{face_filename}",
                f"edge/data/faces/{face_filename}"
            ]
        }
    finally:
        conn.close()


@router.put("/{student_id}/face-approval")
async def update_face_approval(
    school_id: int,
    student_id: int,
    req: UpdateFaceApproval,
    current: dict = Depends(require_role("TEACHER", "HEADMASTER", "ADMIN"))
):
    _check_scope(school_id, current)
    conn = get_db()
    try:
        conn.execute(
            "UPDATE students SET face_approved=?, updated_at=datetime('now','localtime') WHERE id=? AND school_id=?",
            (req.status, student_id, school_id)
        )
        conn.commit()
        return {"status": "success", "message": f"Đã cập nhật trạng thái ảnh: {req.status}"}
    finally:
        conn.close()


@router.delete("/{student_id}")
async def delete_student(
    school_id: int,
    student_id: int,
    current: dict = Depends(require_role("HEADMASTER", "ADMIN"))
):
    """Xóa mềm học sinh (soft delete) — học sinh không còn hiển thị nhưng dữ liệu vẫn được lưu."""
    _check_scope(school_id, current)
    conn = get_db()
    try:
        student = conn.execute(
            "SELECT id, full_name FROM students WHERE id=? AND school_id=? AND is_deleted=0",
            (student_id, school_id)
        ).fetchone()
        if not student:
            raise HTTPException(404, "Không tìm thấy học sinh.")

        conn.execute(
            "UPDATE students SET is_deleted=1, deleted_at=datetime('now','localtime') WHERE id=?",
            (student_id,)
        )
        conn.commit()
        log.info(f"[STUDENTS] Soft-deleted student #{student_id} ({student['full_name']}) at school #{school_id}")
        return {"status": "success", "message": f"Đã xóa học sinh '{student['full_name']}' khỏi hệ thống."}
    finally:
        conn.close()


@router.post("/{student_id}/assign-parent")
async def assign_parent_to_student(
    school_id: int,
    student_id: int,
    req: AssignParentRequest,
    current: dict = Depends(require_role("TEACHER", "HEADMASTER", "ADMIN"))
):
    """
    Nhà trường (BGH hoặc GVCN) chủ động gán tài khoản phụ huynh cho học sinh.
    Tìm kiếm tài khoản theo Số điện thoại, Tên đăng nhập hoặc Email.
    """
    _check_scope(school_id, current)
    conn = get_db()
    try:
        student = conn.execute(
            "SELECT * FROM students WHERE id=? AND school_id=? AND is_deleted=0",
            (student_id, school_id)
        ).fetchone()
        if not student:
            raise HTTPException(404, "Không tìm thấy học sinh.")

        # If current is TEACHER, verify homeroom teacher
        if current.get("role") == "TEACHER":
            teacher_uid = current.get("user_id") or current.get("id")
            hr_row = conn.execute("""
                SELECT id FROM classes
                WHERE school_id=? AND id=? AND is_active=1
                  AND (homeroom_teacher_id=? OR homeroom_teacher_id=(SELECT id FROM users WHERE school_id=? AND username=?))
            """, (school_id, student["class_id"], teacher_uid, school_id, current["username"])).fetchone()
            if not hr_row:
                raise HTTPException(403, "Chỉ Giáo Viên Chủ Nhiệm của lớp hoặc Ban Giám Hiệu mới có thể gán phụ huynh cho học sinh này.")

        ident = req.parent_identifier.strip()
        if not ident:
            raise HTTPException(400, "Vui lòng nhập Số điện thoại, Username hoặc Email của phụ huynh.")

        # Find user with role PARENT
        parent = conn.execute("""
            SELECT * FROM users
            WHERE role='PARENT' AND (phone=? OR username=? OR email=?)
        """, (ident, ident, ident)).fetchone()

        if not parent:
            other_role = conn.execute("""
                SELECT role FROM users WHERE phone=? OR username=? OR email=?
            """, (ident, ident, ident)).fetchone()
            if other_role:
                raise HTTPException(400, f"Tài khoản '{ident}' có vai trò {other_role['role']}, không phải vai trò Phụ Huynh (PARENT).")
            raise HTTPException(404, f"Không tìm thấy tài khoản Phụ huynh nào với thông tin '{ident}'. Vui lòng hướng dẫn phụ huynh đăng ký tài khoản trước.")

        rel_name = (req.relation_name or "Phụ huynh").strip()
        conn.execute("""
            INSERT INTO parent_student_links (parent_user_id, student_id, school_id, relation_name, verified_status, verified_at)
            VALUES (?, ?, ?, ?, 'VERIFIED', datetime('now','localtime'))
            ON CONFLICT(parent_user_id, student_id) DO UPDATE SET
                school_id = excluded.school_id,
                relation_name = excluded.relation_name,
                verified_status = 'VERIFIED',
                verified_at = datetime('now','localtime')
        """, (parent["id"], student_id, school_id, rel_name))

        if not parent["school_id"]:
            conn.execute("UPDATE users SET school_id=? WHERE id=?", (school_id, parent["id"]))

        conn.execute("""
            UPDATE students SET
                parent_phone = COALESCE(parent_phone, ?),
                parent_name  = COALESCE(parent_name, ?),
                updated_at   = datetime('now','localtime')
            WHERE id=?
        """, (parent["phone"], parent["full_name"], student_id))

        conn.commit()
        log.info(f"[STUDENTS] Assigned parent #{parent['id']} ({parent['full_name']}) to student #{student_id} by {current['username']}")

        return {
            "status": "success",
            "message": f"Đã liên kết thành công tài khoản phụ huynh '{parent['full_name']}' với học sinh '{student['full_name']}'.",
            "parent": {
                "id": parent["id"],
                "full_name": parent["full_name"],
                "username": parent["username"],
                "phone": parent["phone"],
                "relation_name": rel_name
            }
        }
    finally:
        conn.close()


@router.delete("/{student_id}/unlink-parent/{parent_user_id}")
async def unlink_parent_from_student(
    school_id: int,
    student_id: int,
    parent_user_id: int,
    current: dict = Depends(require_role("TEACHER", "HEADMASTER", "ADMIN"))
):
    """Gỡ liên kết tài khoản phụ huynh khỏi học sinh."""
    _check_scope(school_id, current)
    conn = get_db()
    try:
        student = conn.execute(
            "SELECT * FROM students WHERE id=? AND school_id=? AND is_deleted=0",
            (student_id, school_id)
        ).fetchone()
        if not student:
            raise HTTPException(404, "Không tìm thấy học sinh.")

        if current.get("role") == "TEACHER":
            teacher_uid = current.get("user_id") or current.get("id")
            hr_row = conn.execute("""
                SELECT id FROM classes
                WHERE school_id=? AND id=? AND is_active=1
                  AND (homeroom_teacher_id=? OR homeroom_teacher_id=(SELECT id FROM users WHERE school_id=? AND username=?))
            """, (school_id, student["class_id"], teacher_uid, school_id, current["username"])).fetchone()
            if not hr_row:
                raise HTTPException(403, "Chỉ Giáo Viên Chủ Nhiệm của lớp hoặc Ban Giám Hiệu mới có thể gỡ phụ huynh của học sinh này.")

        link = conn.execute(
            "SELECT id FROM parent_student_links WHERE parent_user_id=? AND student_id=? AND school_id=?",
            (parent_user_id, student_id, school_id)
        ).fetchone()
        if not link:
            raise HTTPException(404, "Không tìm thấy liên kết giữa tài khoản phụ huynh này và học sinh.")

        parent_user = conn.execute("SELECT phone FROM users WHERE id=?", (parent_user_id,)).fetchone()
        conn.execute("DELETE FROM parent_student_links WHERE id=?", (link["id"],))
        if parent_user and parent_user["phone"]:
            conn.execute("UPDATE students SET parent_phone=NULL WHERE id=? AND parent_phone=?", (student_id, parent_user["phone"]))
        conn.commit()

        log.info(f"[STUDENTS] Unlinked parent #{parent_user_id} from student #{student_id} by {current['username']}")
        return {"status": "success", "message": "Đã gỡ liên kết tài khoản phụ huynh thành công."}
    finally:
        conn.close()


@router.get("/me/parent-invite-code")
async def get_my_parent_invite_code(school_id: int, current: dict = Depends(require_role("STUDENT"))):
    """
    Học sinh lấy mã mời phụ huynh (Parent Invite Code) của chính mình để gửi cho bố mẹ.
    Bố mẹ chỉ cần nhập mã này là kết nối ngay lập tức!
    """
    _check_scope(school_id, current)
    conn = get_db()
    try:
        user_id = current.get("user_id") or current.get("id")
        student = conn.execute("""
            SELECT s.*, c.name as class_name, c.grade_level, c.invite_code as class_invite_code,
                   u_t.full_name as teacher_name
            FROM students s
            LEFT JOIN classes c ON s.class_id = c.id
            LEFT JOIN users u_t ON c.homeroom_teacher_id = u_t.id
            WHERE s.user_id=? AND s.school_id=? AND s.is_deleted=0
        """, (user_id, school_id)).fetchone()
        if not student:
            raise HTTPException(404, "Không tìm thấy hồ sơ học sinh của tài khoản này.")

        invite_code = student["parent_invite_code"]
        if not invite_code:
            invite_code = f"PH-{secrets.token_hex(3).upper()}"
            conn.execute("UPDATE students SET parent_invite_code=? WHERE id=?", (invite_code, student["id"]))
            conn.commit()

        # Linked parents
        links = conn.execute("""
            SELECT psl.relation_name, psl.verified_status, psl.verified_at,
                   u.id as parent_user_id, u.full_name as parent_full_name,
                   u.phone as parent_phone
            FROM parent_student_links psl
            JOIN users u ON psl.parent_user_id = u.id
            WHERE psl.student_id=? AND psl.school_id=?
        """, (student["id"], school_id)).fetchall()

        return {
            "status": "success",
            "student_id": student["id"],
            "student_code": student["student_code"],
            "full_name": student["full_name"],
            "class_name": student["class_name"] if "class_name" in student.keys() else None,
            "grade_level": student["grade_level"] if "grade_level" in student.keys() else None,
            "teacher_name": student["teacher_name"] if "teacher_name" in student.keys() else None,
            "class_invite_code": student["class_invite_code"] if "class_invite_code" in student.keys() else None,
            "parent_invite_code": invite_code,
            "linked_parents": [dict(l) for l in links]
        }
    finally:
        conn.close()


@router.post("/me/rotate-parent-invite-code")
async def rotate_my_parent_invite_code(school_id: int, current: dict = Depends(require_role("STUDENT"))):
    """Học sinh chủ động đổi mã mời phụ huynh mới (để hủy mã cũ)."""
    _check_scope(school_id, current)
    conn = get_db()
    try:
        user_id = current.get("user_id") or current.get("id")
        student = conn.execute(
            "SELECT id, full_name, student_code FROM students WHERE user_id=? AND school_id=? AND is_deleted=0",
            (user_id, school_id)
        ).fetchone()
        if not student:
            raise HTTPException(404, "Không tìm thấy hồ sơ học sinh.")

        new_code = f"PH-{secrets.token_hex(3).upper()}"
        conn.execute("UPDATE students SET parent_invite_code=?, updated_at=datetime('now','localtime') WHERE id=?", (new_code, student["id"]))
        conn.commit()

        log.info(f"[STUDENTS] Student #{student['id']} ({student['student_code']}) rotated parent invite code to {new_code}")
        return {
            "status": "success",
            "message": "Đã đổi mã mời phụ huynh mới thành công.",
            "parent_invite_code": new_code
        }
    finally:
        conn.close()


@router.post("/{student_id}/rotate-parent-invite-code")
async def rotate_student_parent_invite_code(
    school_id: int,
    student_id: int,
    current: dict = Depends(require_role("TEACHER", "HEADMASTER", "ADMIN"))
):
    """Giáo viên hoặc BGH cấp/đổi lại mã mời phụ huynh cho học sinh."""
    _check_scope(school_id, current)
    conn = get_db()
    try:
        student = conn.execute(
            "SELECT id, full_name, student_code FROM students WHERE id=? AND school_id=? AND is_deleted=0",
            (student_id, school_id)
        ).fetchone()
        if not student:
            raise HTTPException(404, "Không tìm thấy hồ sơ học sinh.")

        new_code = f"PH-{secrets.token_hex(3).upper()}"
        conn.execute("UPDATE students SET parent_invite_code=?, updated_at=datetime('now','localtime') WHERE id=?", (new_code, student_id))
        conn.commit()

        return {
            "status": "success",
            "message": f"Đã cấp mã mời phụ huynh mới cho {student['full_name']}.",
            "parent_invite_code": new_code
        }
    finally:
        conn.close()

