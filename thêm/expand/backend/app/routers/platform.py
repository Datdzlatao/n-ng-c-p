"""
backend/app/routers/platform.py — Platform Super Admin API
Manage all schools, global stats, platform admin auth.
"""
import logging
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional

from app.database import get_db
from app.core.security import verify_password, hash_password, generate_salt, create_access_token_with_jti, create_refresh_token
from app.core.deps import get_current_user

router = APIRouter(prefix="/api/v1/platform", tags=["Platform Admin"])
log    = logging.getLogger("stem.platform")


class PlatformLogin(BaseModel):
    username_or_email: str
    password:          str


class UpdateSchoolStatus(BaseModel):
    status: str   # ACTIVE | SUSPENDED | PENDING


def require_platform_admin(current: dict = Depends(get_current_user)):
    if current.get("role") not in ("PLATFORM_ADMIN", "ADMIN"):
        raise HTTPException(403, "Yêu cầu quyền Quản Trị Hệ Thống (Platform Super Admin).")
    return current


@router.post("/login")
async def platform_login(req: PlatformLogin):
    """Super Admin login — xác thực qua database platform_admins (không hardcode password)."""
    conn = get_db()
    try:
        # Tra cứu trong bảng platform_admins theo email
        admin = conn.execute(
            "SELECT * FROM platform_admins WHERE (email=? OR email=?) AND is_active=1",
            (req.username_or_email.strip(), "admin@stemapp.vn" if req.username_or_email.strip().lower() == "admin" else req.username_or_email.strip())
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
            log.warning(f"[Platform] Đăng nhập thất bại cho: {req.username_or_email!r}")
            raise HTTPException(401, "Tài khoản hoặc mật khẩu Quản Trị Viên không đúng.")

        admin_id    = admin["id"]
        admin_email = admin["email"]
        admin_name  = admin["full_name"]

        token, jti = create_access_token_with_jti({
            "sub":            str(admin_id),
            "user_id":        admin_id,
            "school_id":      1,
            "username":       "admin",
            "email":          admin_email,
            "role":           "ADMIN",
            "full_name":      admin_name,
            "verified_status": "VERIFIED"
        })
        rt, rt_jti = create_refresh_token(admin_id)
        conn.execute("""
            INSERT INTO user_refresh_tokens (user_id, jti, expires_at)
            VALUES (?, ?, datetime('now', '+14 days'))
        """, (admin_id, rt_jti))
        conn.commit()
        log.info(f"[Platform] Đăng nhập thành công: {admin_email}")

        return {
            "status":        "success",
            "message":       "Đăng nhập Quản Trị Hệ Thống thành công.",
            "access_token":  token,
            "refresh_token": rt,
            "token_type":    "bearer",
            "admin": {
                "id":        admin_id,
                "email":     admin_email,
                "full_name": admin_name,
                "role":      "ADMIN"
            }
        }
    finally:
        conn.close()


@router.get("/stats")
async def platform_stats(current: dict = Depends(require_platform_admin)):
    """Global system-wide stats across all schools."""
    conn = get_db()
    try:
        total_schools    = conn.execute("SELECT COUNT(*) FROM schools").fetchone()[0]
        active_schools   = conn.execute("SELECT COUNT(*) FROM schools WHERE status='ACTIVE'").fetchone()[0]
        total_users      = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        total_students   = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
        total_teachers   = conn.execute("SELECT COUNT(*) FROM users WHERE role='TEACHER'").fetchone()[0]
        total_cameras    = conn.execute("SELECT COUNT(*) FROM camera_stations").fetchone()[0]
        today_attendance = conn.execute("SELECT COUNT(*) FROM attendance_logs WHERE date_only=date('now','localtime')").fetchone()[0]

        return {
            "total_schools":    total_schools,
            "active_schools":   active_schools,
            "total_users":      total_users,
            "total_students":   total_students,
            "total_teachers":   total_teachers,
            "total_cameras":    total_cameras,
            "today_attendance": today_attendance,
        }
    finally:
        conn.close()


@router.get("/schools")
async def platform_list_schools(current: dict = Depends(require_platform_admin)):
    """List all schools with detailed metrics for admin."""
    conn = get_db()
    try:
        rows = conn.execute("""
            SELECT s.*,
                   (SELECT COUNT(*) FROM students stu WHERE stu.school_id=s.id AND stu.is_active=1) as student_count,
                   (SELECT COUNT(*) FROM users u WHERE u.school_id=s.id AND u.role='TEACHER') as teacher_count,
                   (SELECT COUNT(*) FROM classes c WHERE c.school_id=s.id AND c.is_active=1) as class_count,
                   (SELECT COUNT(*) FROM camera_stations cs WHERE cs.school_id=s.id) as camera_count,
                   (SELECT full_name FROM users u WHERE u.id=s.owner_user_id) as owner_name
            FROM schools s
            ORDER BY s.id ASC
        """).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


@router.put("/schools/{school_id}/status")
async def platform_update_school_status(school_id: int, req: UpdateSchoolStatus, current: dict = Depends(require_platform_admin)):
    """Activate or suspend a school server."""
    if req.status not in ("ACTIVE", "SUSPENDED", "PENDING"):
        raise HTTPException(422, "Status không hợp lệ.")
    conn = get_db()
    try:
        conn.execute("UPDATE schools SET status=?, updated_at=datetime('now','localtime') WHERE id=?", (req.status, school_id))
        conn.commit()
        return {"status": "success", "message": f"Đã cập nhật trạng thái trường thành {req.status}"}
    finally:
        conn.close()


@router.delete("/schools/{school_id}")
async def platform_delete_school(school_id: int, current: dict = Depends(require_platform_admin)):
    """Permanently delete a school and all associated data."""
    conn = get_db()
    try:
        school = conn.execute("SELECT name FROM schools WHERE id=?", (school_id,)).fetchone()
        if not school:
            raise HTTPException(404, "Không tìm thấy trường học.")
        
        school_name = school["name"]
        
        # Disable foreign keys temporarily and delete in proper dependency order
        conn.execute("PRAGMA foreign_keys=OFF")
        
        # 1. Social & Community
        conn.execute("DELETE FROM post_comments WHERE school_id=? OR post_id IN (SELECT id FROM posts WHERE school_id=?)", (school_id, school_id))
        conn.execute("DELETE FROM post_likes WHERE post_id IN (SELECT id FROM posts WHERE school_id=?)", (school_id,))
        conn.execute("DELETE FROM posts WHERE school_id=?", (school_id,))
        
        # 2. Security & Face AI
        conn.execute("DELETE FROM security_alerts WHERE school_id=?", (school_id,))
        conn.execute("DELETE FROM student_face_samples WHERE school_id=?", (school_id,))
        conn.execute("DELETE FROM biometric_consent_records WHERE school_id=?", (school_id,))
        
        # 3. Attendance & Disputes
        conn.execute("DELETE FROM disputes WHERE school_id=?", (school_id,))
        conn.execute("DELETE FROM attendance_logs WHERE school_id=?", (school_id,))
        conn.execute("DELETE FROM leave_requests WHERE school_id=?", (school_id,))
        conn.execute("DELETE FROM discipline_scores WHERE school_id=?", (school_id,))
        
        # 4. Infrastructure & Links
        conn.execute("DELETE FROM camera_stations WHERE school_id=?", (school_id,))
        conn.execute("DELETE FROM parent_student_links WHERE school_id=?", (school_id,))
        conn.execute("DELETE FROM verification_otps WHERE school_id=?", (school_id,))
        conn.execute("DELETE FROM students WHERE school_id=?", (school_id,))
        conn.execute("DELETE FROM classes WHERE school_id=?", (school_id,))
        
        # 5. Tokens & Users (Bảo vệ tài khoản Master Admin / Platform Admin không bị xóa mất phiên đăng nhập)
        conn.execute("""
            DELETE FROM user_refresh_tokens 
            WHERE user_id IN (SELECT id FROM users WHERE school_id=? AND role NOT IN ('PLATFORM_ADMIN', 'ADMIN'))
        """, (school_id,))
        conn.execute("UPDATE users SET school_id=NULL WHERE school_id=? AND role IN ('PLATFORM_ADMIN', 'ADMIN')", (school_id,))
        conn.execute("DELETE FROM users WHERE school_id=? AND role NOT IN ('PLATFORM_ADMIN', 'ADMIN')", (school_id,))
        
        # 6. Delete School itself
        conn.execute("DELETE FROM schools WHERE id=?", (school_id,))
        conn.commit()
        conn.execute("PRAGMA foreign_keys=ON")
        
        return {
            "status": "success",
            "message": f"Đã xóa vĩnh viễn trường '{school_name}' (ID #{school_id}) và toàn bộ dữ liệu liên quan thành công!"
        }
    finally:
        conn.close()


@router.post("/reset-demo-data")
async def platform_reset_demo_data(current: dict = Depends(require_platform_admin)):
    """Clear all demo schools & sample data for a 100% fresh clean system."""
    conn = get_db()
    try:
        conn.execute("PRAGMA foreign_keys=OFF")
        conn.execute("DELETE FROM post_comments")
        conn.execute("DELETE FROM post_likes")
        conn.execute("DELETE FROM posts")
        conn.execute("DELETE FROM security_alerts")
        conn.execute("DELETE FROM student_face_samples")
        conn.execute("DELETE FROM biometric_consent_records")
        conn.execute("DELETE FROM disputes")
        conn.execute("DELETE FROM attendance_logs")
        conn.execute("DELETE FROM leave_requests")
        conn.execute("DELETE FROM discipline_scores")
        conn.execute("DELETE FROM camera_stations")
        conn.execute("DELETE FROM parent_student_links")
        conn.execute("DELETE FROM verification_otps")
        conn.execute("DELETE FROM students")
        conn.execute("DELETE FROM classes")
        conn.execute("DELETE FROM user_refresh_tokens WHERE user_id IN (SELECT id FROM users WHERE role NOT IN ('PLATFORM_ADMIN', 'ADMIN'))")
        conn.execute("UPDATE users SET school_id=NULL WHERE role IN ('PLATFORM_ADMIN', 'ADMIN')")
        conn.execute("DELETE FROM users WHERE role NOT IN ('PLATFORM_ADMIN', 'ADMIN')")
        conn.execute("DELETE FROM schools")
        conn.commit()
        conn.execute("PRAGMA foreign_keys=ON")
        return {
            "status": "success",
            "message": "Đã dọn sạch toàn bộ trường demo! Hệ thống hiện đã sẵn sàng 100% để bạn tạo trường thực tế."
        }
    finally:
        conn.close()


@router.get("/maintenance/storage-stats")
async def platform_storage_stats(current: dict = Depends(require_platform_admin)):
    """Thống kê dung lượng thư mục uploads và tình trạng dữ liệu ảnh điểm danh."""
    from app.services.cleanup_service import get_storage_stats
    return get_storage_stats()


class ManualCleanupRequest(BaseModel):
    retention_days: Optional[int] = None
    delete_records: Optional[bool] = None


@router.post("/maintenance/cleanup")
async def platform_manual_cleanup(
    req: Optional[ManualCleanupRequest] = None,
    current: dict = Depends(require_platform_admin)
):
    """Kích hoạt dọn dẹp thủ công dữ liệu điểm danh và ảnh camera cũ hơn N ngày (mặc định 8 ngày)."""
    from app.services.cleanup_service import cleanup_old_attendance_data
    days = req.retention_days if req else None
    del_records = req.delete_records if req else None
    result = cleanup_old_attendance_data(retention_days=days, delete_records=del_records)
    return result
