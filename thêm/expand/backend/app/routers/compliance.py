"""
app/routers/compliance.py — Biometric Consent Management
Tuan thu Nghi dinh 13/2023/ND-CP ve bao ve du lieu sinh trac hoc.

GET    /api/v1/s/{school_id}/compliance/consent/{student_id}   — Lich su chap thuan
POST   /api/v1/s/{school_id}/compliance/consent/{student_id}   — Ghi nhan chap thuan
DELETE /api/v1/s/{school_id}/compliance/biometric/{student_id} — Xoa sinh trac (Right to Erasure)
GET    /api/v1/s/{school_id}/compliance/audit-log              — Bao cao toan truong
"""
import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import Optional

from app.database import get_db
from app.core.deps import get_current_user, require_role

router = APIRouter(prefix="/api/v1/s/{school_id}/compliance", tags=["Compliance"])
log    = logging.getLogger("stem.compliance")


class ConsentRequest(BaseModel):
    consent_status: str = "CONSENTED"  # CONSENTED | REVOKED
    purpose: str = "FACE_ATTENDANCE"
    parent_user_id: Optional[int] = None


def _check_scope(school_id: int, current: dict):
    if current.get("role") not in ("ADMIN", "PLATFORM_ADMIN") and current.get("school_id") != school_id:
        raise HTTPException(403, "Khong thuoc truong nay.")


@router.get("/consent/{student_id}")
async def get_consent_history(
    school_id: int,
    student_id: int,
    current: dict = Depends(require_role("HEADMASTER", "INSPECTOR", "TEACHER", "ADMIN"))
):
    """Tra ve lich su chap thuan sinh trac hoc cua hoc sinh."""
    _check_scope(school_id, current)
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT * FROM biometric_consent_records WHERE student_id=? AND school_id=? ORDER BY created_at DESC",
            (student_id, school_id)
        ).fetchall()
        return {"student_id": student_id, "records": [dict(r) for r in rows]}
    finally:
        conn.close()


@router.post("/consent/{student_id}")
async def record_consent(
    school_id: int,
    student_id: int,
    req: ConsentRequest,
    request: Request,
    current: dict = Depends(get_current_user)
):
    """Ghi nhan chap thuan / thu hoi chap thuan thu thap sinh trac hoc."""
    _check_scope(school_id, current)
    conn = get_db()
    try:
        student = conn.execute(
            "SELECT id FROM students WHERE id=? AND school_id=? AND is_deleted=0",
            (student_id, school_id)
        ).fetchone()
        if not student:
            raise HTTPException(404, "Khong tim thay hoc sinh.")

        ip_addr = request.headers.get("X-Forwarded-For", "").split(",")[0].strip() or (
            request.client.host if request.client else "unknown"
        )

        revoked_at = datetime.now().isoformat() if req.consent_status == "REVOKED" else None

        conn.execute(
            """INSERT INTO biometric_consent_records
                (student_id, school_id, parent_user_id, consent_status, purpose, signed_at, revoked_at, ip_address)
               VALUES (?, ?, ?, ?, ?, datetime('now','localtime'), ?, ?)""",
            (student_id, school_id, req.parent_user_id or current.get("user_id"),
             req.consent_status, req.purpose, revoked_at, ip_addr)
        )
        conn.commit()

        return {
            "status": "success",
            "message": "Da ghi nhan chap thuan." if req.consent_status == "CONSENTED" else "Da thu hoi chap thuan sinh trac hoc."
        }
    finally:
        conn.close()


@router.delete("/biometric/{student_id}")
async def erase_biometric_data(
    school_id: int,
    student_id: int,
    current: dict = Depends(require_role("HEADMASTER", "ADMIN"))
):
    """
    Xoa hoan toan du lieu sinh trac hoc theo quyen duoc lang quen
    (Right to Erasure — Dieu 16, ND 13/2023/ND-CP).
    Xoa: face_embedding_blob, face_photo_url, ghi log thu hoi.
    KHONG xoa hoc sinh khoi he thong.
    """
    _check_scope(school_id, current)
    conn = get_db()
    try:
        student = conn.execute(
            "SELECT id, student_code, face_photo_url FROM students WHERE id=? AND school_id=? AND is_deleted=0",
            (student_id, school_id)
        ).fetchone()
        if not student:
            raise HTTPException(404, "Khong tim thay hoc sinh.")

        # Erase biometric data
        conn.execute(
            "UPDATE students SET face_embedding_blob=NULL, face_photo_url=NULL, face_approved='REVOKED' WHERE id=?",
            (student_id,)
        )

        # Record erasure in consent log
        conn.execute(
            """INSERT INTO biometric_consent_records
                (student_id, school_id, parent_user_id, consent_status, purpose, signed_at, revoked_at, device_info)
               VALUES (?, ?, ?, 'REVOKED', 'FACE_ATTENDANCE',
                       datetime('now','localtime'), datetime('now','localtime'), 'ERASURE_REQUEST')""",
            (student_id, school_id, current.get("user_id"))
        )
        conn.commit()

        log.info(f"[COMPLIANCE] Đã xóa sinh trắc học sinh #{student_id} ({dict(student).get('student_code')}) tại trường #{school_id}")
        return {
            "status": "success",
            "message": f"Đã xóa toàn bộ dữ liệu sinh trắc học của học sinh #{student_id}. Học sinh vẫn tồn tại trong hệ thống."
        }
    finally:
        conn.close()


@router.get("/audit-log")
async def get_audit_log(
    school_id: int,
    current: dict = Depends(require_role("HEADMASTER", "ADMIN"))
):
    """Bao cao tong hop tuan thu sinh trac hoc cua toan truong."""
    _check_scope(school_id, current)
    conn = get_db()
    try:
        total_students = conn.execute(
            "SELECT COUNT(*) FROM students WHERE school_id=? AND is_deleted=0", (school_id,)
        ).fetchone()[0]
        with_face = conn.execute(
            "SELECT COUNT(*) FROM students WHERE school_id=? AND is_deleted=0 AND face_embedding_blob IS NOT NULL",
            (school_id,)
        ).fetchone()[0]
        consented = conn.execute(
            "SELECT COUNT(DISTINCT student_id) FROM biometric_consent_records WHERE school_id=? AND consent_status='CONSENTED'",
            (school_id,)
        ).fetchone()[0]
        revoked = conn.execute(
            "SELECT COUNT(DISTINCT student_id) FROM biometric_consent_records WHERE school_id=? AND consent_status='REVOKED'",
            (school_id,)
        ).fetchone()[0]
        return {
            "school_id": school_id,
            "total_students": total_students,
            "with_face_data": with_face,
            "consented": consented,
            "revoked_or_erased": revoked,
            "compliance_rate": f"{consented/max(with_face,1)*100:.1f}%"
        }
    finally:
        conn.close()
