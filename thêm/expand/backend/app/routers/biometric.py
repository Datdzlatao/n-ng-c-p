"""
app/routers/biometric.py — Multi-Angle Biometric Auto-Capture & Consent Onboarding
Tuân thủ Nghị định 13/2023/NĐ-CP về Bảo Vệ Dữ Liệu Sinh Trắc Học.

POST /api/v1/auth/biometric/session-init    — Khởi tạo phiên quét sinh trắc học
POST /api/v1/auth/biometric/upload-samples — Tiếp nhận gói ảnh sinh trắc học eKYC
GET  /api/v1/s/{school_id}/students/{student_id}/samples — Lấy danh sách mẫu góc mặt
"""
import os
import re
import time
import base64
import shutil
import logging
from pathlib import Path
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel, Field

from app.database import get_db
from app.config import UPLOAD_DIR, MAX_UPLOAD_MB
from app.core.deps import get_current_user, get_current_user_optional, require_role

router = APIRouter(tags=["Biometric"])
log    = logging.getLogger("stem.biometric")


class BiometricSessionInit(BaseModel):
    school_id: int
    student_code: Optional[str] = None
    student_id: Optional[int] = None
    full_name: Optional[str] = None
    consent_agreed: Optional[bool] = None
    parent_consent: Optional[bool] = None
    user_agent: Optional[str] = None


class SampleItem(BaseModel):
    sample_index: int = 0
    angle_type: str = "CENTER"   # CENTER | MID_LEFT | FAR_LEFT | MID_RIGHT | FAR_RIGHT | TILT
    yaw_angle: float = 0.0       # -80° to +80°
    pitch_angle: float = 0.0     # -30° to +30°
    image_base64: Optional[str] = None            # data:image/jpeg;base64,...
    image_data: Optional[str] = None              # fallback field name
    quality_score: float = 1.0


class ConsentData(BaseModel):
    accepted: bool = True
    consent_version: str = "1.0"
    parent_name: Optional[str] = None
    purpose: str = "FACE_ATTENDANCE"


class BiometricUploadRequest(BaseModel):
    school_id: int
    student_code: Optional[str] = None
    student_id: Optional[int] = None
    session_token: Optional[str] = None
    consent: Optional[ConsentData] = None
    samples: List[SampleItem] = Field(default_factory=list)
    verify_account: Optional[bool] = True


@router.post("/api/v1/auth/biometric/session-init")
async def init_biometric_session(req: BiometricSessionInit):
    """
    Khởi tạo phiên chụp sinh trắc học cho học sinh.
    Cung cấp session id và các thông số góc quét yêu cầu.
    """
    conn = get_db()
    try:
        school = conn.execute("SELECT id, name FROM schools WHERE id=?", (req.school_id,)).fetchone()
        if not school:
            raise HTTPException(404, "Không tìm thấy trường học.")

        st_code = req.student_code
        if not st_code and req.student_id:
            stu = conn.execute("SELECT student_code FROM students WHERE id=? AND school_id=?", (req.student_id, req.school_id)).fetchone()
            if stu:
                st_code = stu["student_code"]
            else:
                usr = conn.execute("SELECT student_code, username FROM users WHERE id=? AND school_id=?", (req.student_id, req.school_id)).fetchone()
                if usr:
                    st_code = usr["student_code"] or usr["username"]
        if not st_code:
            st_code = f"HS{req.school_id}-{req.student_id or int(time.time())}"

        session_id = f"BIO-{req.school_id}-{st_code}-{int(time.time())}"
        return {
            "status": "success",
            "session_id": session_id,
            "session_token": session_id,
            "school_id": req.school_id,
            "student_code": st_code,
            "required_sweep_angle": "BIOMETRIC_SWEEP_5_POSES",
            "target_samples_count": 5,
            "angle_targets": [
                {"type": "CENTER",    "name": "Chính Diện", "yaw_range": [-14,  14], "pitch_range": [-18,  18], "required_shots": 1},
                {"type": "LEFT",      "name": "Nghiêng Trái", "yaw_range": [-45, -12], "pitch_range": [-22,  22], "required_shots": 1},
                {"type": "RIGHT",     "name": "Nghiêng Phải", "yaw_range": [ 12,  45], "pitch_range": [-22,  22], "required_shots": 1},
                {"type": "TILT_UP",   "name": "Ngước Lên", "yaw_range": [-22,  22], "pitch_range": [  8,  45], "required_shots": 1},
                {"type": "TILT_DOWN", "name": "Cúi Nhẹ", "yaw_range": [-22,  22], "pitch_range": [-45,  -6], "required_shots": 1}
            ]
        }
    finally:
        conn.close()


@router.post("/api/v1/auth/biometric/upload-samples")
async def upload_biometric_samples(
    req: BiometricUploadRequest,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """
    Tiếp nhận và lưu trữ bộ ảnh sinh trắc học (eKYC).
    Yêu cầu xác thực tài khoản và kiểm tra quyền tương ứng (C-5).
    Kiểm tra kích thước file và định dạng ảnh (H-6).
    Khử độc mã học sinh chống Path Traversal (H-7).
    Ghi nhật ký chấp thuận pháp lý theo Nghị định 13/2023/NĐ-CP.
    """
    # Scope check: user phải thuộc đúng trường trừ Master Admin
    if current_user.get("role") not in ("ADMIN", "PLATFORM_ADMIN"):
        if current_user.get("school_id") != req.school_id:
            raise HTTPException(403, "Bạn không thuộc trường học này.")

    consent = req.consent or ConsentData(accepted=True)
    if not consent.accepted:
        raise HTTPException(422, "Cần chấp thuận cam kết bảo vệ dữ liệu sinh trắc học theo Nghị định 13/2023/NĐ-CP.")

    if not req.samples or len(req.samples) == 0:
        raise HTTPException(422, "Không có mẫu ảnh nào được gửi lên.")

    conn = get_db()
    try:
        # 1. Xác định student_code & student_id và kiểm tra quyền (C-5)
        student_code = req.student_code
        student_id = req.student_id

        # Nếu là học sinh, CHỈ ĐƯỢC upload cho chính bản thân mình
        if current_user.get("role") == "STUDENT":
            stu = conn.execute(
                "SELECT id, student_code FROM students WHERE user_id=? AND school_id=?",
                (current_user["user_id"], req.school_id)
            ).fetchone()
            if not stu:
                raise HTTPException(403, "Không tìm thấy hồ sơ học sinh liên kết với tài khoản này.")
            student_id = stu["id"]
            student_code = stu["student_code"]
        else:
            # Giáo viên / Ban Giám Hiệu / Quản trị viên
            if not student_code and student_id:
                s_row = conn.execute("SELECT student_code FROM students WHERE id=? AND school_id=?", (student_id, req.school_id)).fetchone()
                if s_row:
                    student_code = s_row["student_code"]
                else:
                    u_row = conn.execute("SELECT student_code, username FROM users WHERE id=? AND school_id=?", (student_id, req.school_id)).fetchone()
                    if u_row:
                        student_code = u_row["student_code"] or u_row["username"]

            if not student_code:
                student_code = f"HS{req.school_id}-{student_id or int(time.time())}"

            # Tìm hoặc xác thực học sinh trong bảng students
            student = conn.execute(
                "SELECT id, student_code, full_name FROM students WHERE school_id=? AND student_code=?",
                (req.school_id, student_code)
            ).fetchone()

            if student:
                student_id = student["id"]
            elif not student_id:
                qr_token = f"QR-{student_code}"
                conn.execute("""
                    INSERT INTO students (school_id, student_code, full_name, qr_token, current_points, is_active)
                    VALUES (?, ?, ?, ?, 100, 1)
                """, (req.school_id, student_code, student_code, qr_token))
                conn.commit()
                student_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        # 2. Khử độc mã học sinh chống Path Traversal (H-7)
        clean_code = re.sub(r"[^a-zA-Z0-9_-]", "", student_code)
        if not clean_code:
            raise HTTPException(422, "Mã học sinh chứa ký tự không hợp lệ.")
        student_code = clean_code

        faces_root = (UPLOAD_DIR / "faces").resolve()
        faces_root.mkdir(parents=True, exist_ok=True)
        student_dir = (faces_root / str(req.school_id) / student_code).resolve()
        if not student_dir.is_relative_to(faces_root):
            raise HTTPException(400, "Đường dẫn lưu trữ không an toàn.")
        student_dir.mkdir(parents=True, exist_ok=True)

        # Tự động dọn dẹp các mẫu ảnh cũ và bản ghi cũ trước khi lưu bộ ảnh mới
        for old_sample_file in student_dir.glob("sample_*.jpg"):
            try:
                old_sample_file.unlink()
            except Exception:
                pass
        conn.execute("DELETE FROM student_face_samples WHERE student_id=? AND school_id=?", (student_id, req.school_id))

        # 3. Kiểm tra dung lượng và định dạng ảnh (H-6)
        total_upload_bytes = 0
        MAX_TOTAL_BYTES = MAX_UPLOAD_MB * 1024 * 1024
        MAX_SAMPLE_BYTES = 3 * 1024 * 1024  # 3MB per sample

        saved_samples = []
        best_center_path = None
        best_center_url = None
        best_left_path = None
        best_right_path = None
        best_tilt_up_path = None
        best_tilt_down_path = None
        best_tilt_path = None
        min_yaw_diff = 999.0

        for s in req.samples:
            img_data = s.image_base64 or s.image_data or ""
            if not img_data:
                continue
            if "," in img_data:
                img_data = img_data.split(",", 1)[1]
            try:
                raw_bytes = base64.b64decode(img_data)
            except Exception as e:
                log.warning(f"Lỗi giải mã base64 sample {s.sample_index}: {e}")
                continue

            if len(raw_bytes) > MAX_SAMPLE_BYTES:
                raise HTTPException(413, f"Mẫu ảnh {s.sample_index} vượt quá kích thước cho phép (3MB).")

            total_upload_bytes += len(raw_bytes)
            if total_upload_bytes > MAX_TOTAL_BYTES:
                raise HTTPException(413, f"Tổng dung lượng mẫu ảnh vượt quá giới hạn ({MAX_UPLOAD_MB}MB).")

            # Magic bytes validation: JPEG, PNG, WEBP
            is_valid_image = (
                raw_bytes.startswith(b"\xff\xd8\xff") or
                raw_bytes.startswith(b"\x89PNG\r\n\x1a\n") or
                raw_bytes.startswith(b"RIFF")
            )
            if not is_valid_image:
                log.warning(f"Mẫu ảnh {s.sample_index} không có header ảnh hợp lệ, bỏ qua.")
                continue

            file_name = f"sample_{s.sample_index}_{s.angle_type.lower()}.jpg"
            file_path = student_dir / file_name
            with open(file_path, "wb") as f:
                f.write(raw_bytes)

            img_rel_url = f"/uploads/faces/{req.school_id}/{student_code}/{file_name}"

            conn.execute("""
                INSERT INTO student_face_samples
                    (student_id, school_id, sample_index, angle_type, yaw_angle, pitch_angle, image_url, quality_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (student_id, req.school_id, s.sample_index, s.angle_type, s.yaw_angle, s.pitch_angle, img_rel_url, s.quality_score))

            saved_samples.append({
                "sample_index": s.sample_index,
                "angle_type": s.angle_type,
                "url": img_rel_url
            })

            angle_type_str = s.angle_type.upper()
            if "LEFT" in angle_type_str:
                best_left_path = file_path
            elif "RIGHT" in angle_type_str:
                best_right_path = file_path
            elif "TILT_UP" in angle_type_str or "UP" in angle_type_str:
                best_tilt_up_path = file_path
            elif "TILT_DOWN" in angle_type_str or "DOWN" in angle_type_str:
                best_tilt_down_path = file_path
            elif "TILT" in angle_type_str:
                best_tilt_path = file_path
            elif "CENTER" in angle_type_str or abs(s.yaw_angle) < min_yaw_diff:
                min_yaw_diff = abs(s.yaw_angle)
                best_center_path = file_path
                best_center_url = img_rel_url

        if not saved_samples:
            raise HTTPException(400, "Không có mẫu ảnh hợp lệ nào được lưu.")

        if not best_center_path and saved_samples:
            best_center_path = student_dir / f"sample_{saved_samples[0]['sample_index']}_{saved_samples[0]['angle_type'].lower()}.jpg"
            best_center_url = saved_samples[0]['url']

        # 4. Đồng bộ ảnh avatar chính diện và góc nghiêng vào uploads/faces và edge/data/faces
        if best_center_path and best_center_path.exists():
            (UPLOAD_DIR / "faces").mkdir(parents=True, exist_ok=True)
            avatar_main_path = UPLOAD_DIR / "faces" / f"{student_code}.jpg"
            shutil.copyfile(str(best_center_path), str(avatar_main_path))

            from app.config import BASE_DIR
            edge_faces_dir = BASE_DIR.parent / "edge" / "data" / "faces"
            if edge_faces_dir.parent.exists():
                edge_faces_dir.mkdir(parents=True, exist_ok=True)
                try:
                    shutil.copyfile(str(best_center_path), str(edge_faces_dir / f"{student_code}.jpg"))
                    if best_left_path and best_left_path.exists():
                        shutil.copyfile(str(best_left_path), str(edge_faces_dir / f"{student_code}_left.jpg"))
                        shutil.copyfile(str(best_left_path), str(UPLOAD_DIR / "faces" / f"{student_code}_left.jpg"))
                    if best_right_path and best_right_path.exists():
                        shutil.copyfile(str(best_right_path), str(edge_faces_dir / f"{student_code}_right.jpg"))
                        shutil.copyfile(str(best_right_path), str(UPLOAD_DIR / "faces" / f"{student_code}_right.jpg"))
                    if best_tilt_up_path and best_tilt_up_path.exists():
                        shutil.copyfile(str(best_tilt_up_path), str(edge_faces_dir / f"{student_code}_tilt_up.jpg"))
                        shutil.copyfile(str(best_tilt_up_path), str(UPLOAD_DIR / "faces" / f"{student_code}_tilt_up.jpg"))
                    if best_tilt_down_path and best_tilt_down_path.exists():
                        shutil.copyfile(str(best_tilt_down_path), str(edge_faces_dir / f"{student_code}_tilt_down.jpg"))
                        shutil.copyfile(str(best_tilt_down_path), str(UPLOAD_DIR / "faces" / f"{student_code}_tilt_down.jpg"))
                    if best_tilt_path and best_tilt_path.exists():
                        shutil.copyfile(str(best_tilt_path), str(edge_faces_dir / f"{student_code}_tilt.jpg"))
                        shutil.copyfile(str(best_tilt_path), str(UPLOAD_DIR / "faces" / f"{student_code}_tilt.jpg"))
                    
                    # Xóa cache vector cũ để Edge Station tự động nạp lại embeddings mới
                    cache_npz = edge_faces_dir.parent / "faces_embeddings.npz"
                    if cache_npz.exists():
                        try:
                            cache_npz.unlink()
                        except Exception:
                            pass
                    edge_faces_dir.touch(exist_ok=True)
                except Exception as ex:
                    log.warning(f"Không thể copy ảnh đa góc sang edge: {ex}")

            conn.execute("""
                UPDATE students
                SET face_photo_url=?, face_approved='APPROVED', updated_at=datetime('now','localtime')
                WHERE id=?
            """, (best_center_url, student_id))

        # 5. Cấp Tích Xanh xác minh tài khoản người dùng
        target_uid = current_user.get("user_id") or current_user.get("id")
        if current_user.get("role") != "STUDENT":
            stu_row = conn.execute("SELECT user_id FROM students WHERE id=?", (student_id,)).fetchone()
            if stu_row and stu_row["user_id"]:
                target_uid = stu_row["user_id"]

        if target_uid:
            conn.execute("""
                UPDATE users
                SET verified_status='VERIFIED',
                    verification_method='FACE_SCAN',
                    verification_doc_url=?,
                    verification_note='Xác minh sinh trắc học khuôn mặt FaceID thành công',
                    verified_at=datetime('now','localtime')
                WHERE id=?
            """, (best_center_url or f"/uploads/faces/{student_code}.jpg", target_uid))

        # 6. Ghi nhật ký Consent (Nghị định 13/2023/NĐ-CP)
        client_ip = request.headers.get("X-Forwarded-For", "").split(",")[0].strip() or (
            request.client.host if request.client else "unknown"
        )
        user_agent = request.headers.get("User-Agent", "Unknown")

        conn.execute("""
            INSERT INTO biometric_consent_records
                (student_id, school_id, consent_status, consent_version, purpose, ip_address, user_agent, device_info)
            VALUES (?, ?, 'CONSENTED', ?, ?, ?, ?, 'EKYC_FACEID_SWEEP')
        """, (student_id, req.school_id, consent.consent_version, consent.purpose, client_ip, user_agent))

        conn.commit()

        log.info(f"[BIOMETRIC] Đã lưu thành công {len(saved_samples)} mẫu ảnh cho {student_code} tại trường #{req.school_id}")

        return {
            "status": "success",
            "message": "Đã lưu bộ ảnh sinh trắc học và cấp Tích Xanh xác minh thành công.",
            "student_id": student_id,
            "student_code": student_code,
            "samples_count": len(saved_samples),
            "face_photo_url": best_center_url if best_center_path else None,
            "verified_status": "VERIFIED"
        }
    finally:
        conn.close()


@router.get("/api/v1/s/{school_id}/students/{student_id}/samples")
async def get_student_biometric_samples(
    school_id: int,
    student_id: int,
    current: dict = Depends(get_current_user)
):
    """
    Lấy danh sách tất cả các mẫu góc quét sinh trắc học của học sinh.
    Kiểm tra quyền truy cập nghiêm ngặt theo vai trò (C-6).
    """
    # Scope check
    if current.get("role") not in ("ADMIN", "PLATFORM_ADMIN"):
        if current.get("school_id") != school_id:
            raise HTTPException(403, "Bạn không thuộc trường học này.")

        if current.get("role") == "STUDENT":
            conn_check = get_db()
            try:
                my_stu = conn_check.execute(
                    "SELECT id FROM students WHERE user_id=? AND school_id=?",
                    (current["user_id"], school_id)
                ).fetchone()
                if not my_stu or my_stu["id"] != student_id:
                    raise HTTPException(403, "Bạn chỉ có thể xem dữ liệu sinh trắc học của chính mình.")
            finally:
                conn_check.close()
        elif current.get("role") not in ("TEACHER", "INSPECTOR", "HEADMASTER"):
            raise HTTPException(403, "Bạn không có quyền truy cập dữ liệu sinh trắc học này.")

    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT * FROM student_face_samples WHERE school_id=? AND student_id=? ORDER BY sample_index ASC",
            (school_id, student_id)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
