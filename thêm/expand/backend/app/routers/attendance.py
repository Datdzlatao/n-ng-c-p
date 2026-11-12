"""
app/routers/attendance.py — Attendance logs
GET  /api/v1/s/{school_id}/attendance          — List logs (TEACHER/INSPECTOR/HEADMASTER)
GET  /api/v1/s/{school_id}/attendance/today    — Today summary
POST /api/v1/s/{school_id}/attendance/sync     — Camera station push (edge sync)
GET  /api/v1/s/{school_id}/attendance/student/{student_id} — Student's own history
"""
import logging
import json
import base64
import time
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Query, Header, BackgroundTasks, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional

from app.database import get_db
from app.config import UPLOAD_DIR
from app.core.deps import get_current_user, require_role
from app.services.notification_service import notify_parent_attendance
from app.core.rate_limit import check_rate_limit, get_client_ip
from app.routers.websocket import broadcast_to_school

router = APIRouter(prefix="/api/v1/s/{school_id}/attendance", tags=["Attendance"])
log    = logging.getLogger("stem.attendance")



class AttendanceSync(BaseModel):
    """Payload sent by Raspberry Pi / edge camera station."""
    station_secret_key: str
    student_qr_token:   Optional[str] = None
    student_code:       Optional[str] = None
    student_id:         Optional[int] = None
    timestamp:          Optional[str] = None          # ISO datetime
    direction:          Optional[str] = "IN"          # IN | OUT | BIDIRECTIONAL
    check_type:         str = "FACE_AI"               # FACE_AI | QR_SCAN | MANUAL
    status:             str = "ON_TIME"               # ON_TIME | LATE | ABSENT
    uniform_status:     str = "UNKNOWN"
    spoof_status:       str = "SKIPPED"
    confidence_score:   float = 0.0
    proof_image_url:    Optional[str] = None
    proof_image_base64: Optional[str] = None          # Direct snapshot base64
    violation_reason:   Optional[str] = None          # Mo ta vi pham / loi neu co


def _check_scope(school_id: int, current: dict):
    if current.get("role") in ("ADMIN", "PLATFORM_ADMIN"):
        return
    if current.get("school_id") != school_id:
        raise HTTPException(403, "Không thuộc trường này.")


@router.get("")
async def list_attendance(
    school_id: int,
    date:           Optional[str] = Query(None, description="YYYY-MM-DD"),
    date_from:      Optional[str] = Query(None, description="YYYY-MM-DD"),
    date_to:        Optional[str] = Query(None, description="YYYY-MM-DD"),
    time_from:      Optional[str] = Query(None, description="HH:MM"),
    time_to:        Optional[str] = Query(None, description="HH:MM"),
    time_mode:      Optional[str] = Query("daily", description="daily | continuous"),
    direction:      Optional[str] = Query(None, description="IN | OUT"),
    status:         Optional[str] = Query(None),
    uniform_status: Optional[str] = Query(None),
    class_id:       Optional[int] = Query(None),
    student_id:     Optional[int] = Query(None),
    limit:          int = Query(50000, ge=1, le=200000),
    current:        dict = Depends(require_role("TEACHER", "INSPECTOR", "HEADMASTER"))
):
    _check_scope(school_id, current)
    conn = get_db()
    try:
        sql = """
            SELECT a.*, s.full_name, s.student_code, s.face_photo_url, c.name as class_name,
                   cs.name as camera_name, cs.location as camera_location
            FROM attendance_logs a
            JOIN students s ON a.student_id = s.id
            LEFT JOIN classes c ON s.class_id = c.id
            LEFT JOIN camera_stations cs ON a.camera_station_id = cs.id
            WHERE a.school_id=?
        """
        params = [school_id]
        if date:
            sql += " AND a.date_only=?"
            params.append(date)
        else:
            if date_from:
                sql += " AND a.date_only >= ?"
                params.append(date_from)
            if date_to:
                sql += " AND a.date_only <= ?"
                params.append(date_to)

        if time_mode == "continuous" and date_from and date_to:
            tf = f"{time_from or '00:00'}:00"
            tt = f"{time_to or '23:59'}:59"
            sql += " AND replace(a.timestamp, ' ', 'T') >= ? AND replace(a.timestamp, ' ', 'T') <= ?"
            params += [f"{date_from}T{tf}", f"{date_to}T{tt}"]
        else:
            if time_from:
                sql += " AND strftime('%H:%M', replace(a.timestamp, ' ', 'T')) >= ?"
                params.append(time_from)
            if time_to:
                sql += " AND strftime('%H:%M', replace(a.timestamp, ' ', 'T')) <= ?"
                params.append(time_to)

        if direction:
            sql += " AND UPPER(COALESCE(a.direction, 'IN')) = ?"
            params.append(direction.upper())
        if status:
            sql += " AND a.status=?"
            params.append(status)
        if uniform_status:
            sql += " AND a.uniform_status=?"
            params.append(uniform_status)
        if class_id:
            sql += " AND s.class_id=?"
            params.append(class_id)
        if student_id:
            sql += " AND a.student_id=?"
            params.append(student_id)

        # TEACHER scope: nếu là GVCN và không chỉ định class_id -> ưu tiên lớp chủ nhiệm
        if current["role"] == "TEACHER":
            teacher_uid = current.get("user_id") or current.get("id")
            hr_row = conn.execute("""
                SELECT id FROM classes
                WHERE school_id=? AND is_active=1
                  AND (homeroom_teacher_id=? OR homeroom_teacher_id=(SELECT id FROM users WHERE school_id=? AND username=?))
                LIMIT 1
            """, (school_id, teacher_uid, school_id, current["username"])).fetchone()
            if hr_row and not class_id:
                sql += " AND s.class_id=?"
                params.append(hr_row["id"])

        sql += " ORDER BY a.timestamp DESC LIMIT ?"
        params.append(limit)
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


@router.get("/today")
async def today_summary(
    school_id: int,
    date:      Optional[str] = Query(None, description="YYYY-MM-DD"),
    current:   dict = Depends(require_role("TEACHER", "INSPECTOR", "HEADMASTER"))
):
    _check_scope(school_id, current)
    conn = get_db()
    try:
        target_date = date or datetime.now().strftime("%Y-%m-%d")
        rows  = conn.execute("""
            SELECT a.status, COUNT(*) as cnt
            FROM attendance_logs a
            WHERE a.school_id=? AND a.date_only=?
            GROUP BY a.status
        """, (school_id, target_date)).fetchall()
        result = {"date": target_date, "ON_TIME": 0, "LATE": 0, "ABSENT": 0, "EXCUSED": 0, "total_in": 0, "total_out": 0, "total_scans": 0, "total_strangers": 0}
        for r in rows:
            if r["status"] in result:
                result[r["status"]] = r["cnt"]

        # Thống kê phân loại theo log Vào (IN) và log Ra (OUT)
        in_out_rows = conn.execute("""
            SELECT UPPER(COALESCE(a.direction, 'IN')) as dir, COUNT(*) as cnt
            FROM attendance_logs a
            WHERE a.school_id=? AND a.date_only=?
            GROUP BY UPPER(COALESCE(a.direction, 'IN'))
        """, (school_id, target_date)).fetchall()
        for r in in_out_rows:
            if r["dir"] == "IN":
                result["total_in"] = r["cnt"]
            elif r["dir"] == "OUT":
                result["total_out"] = r["cnt"]

        # Tổng số lượt quét và cảnh báo an ninh thực tế trong ngày
        result["total_scans"] = conn.execute(
            "SELECT COUNT(*) FROM attendance_logs WHERE school_id=? AND date_only=?",
            (school_id, target_date)
        ).fetchone()[0]

        result["total_strangers"] = conn.execute(
            "SELECT COUNT(*) FROM security_alerts WHERE school_id=? AND date_only=?",
            (school_id, target_date)
        ).fetchone()[0]

        # Tổng số học sinh đang hoạt động
        total_active = conn.execute(
            "SELECT COUNT(*) FROM students WHERE school_id=? AND is_active=1 AND is_deleted=0",
            (school_id,)
        ).fetchone()[0]

        recorded_students = sum(v for k, v in result.items() if k in ("ON_TIME", "LATE", "EXCUSED"))
        if result["ABSENT"] == 0 and total_active > recorded_students:
            result["ABSENT"] = total_active - recorded_students

        result["total"] = total_active if total_active > 0 else recorded_students
        result["present"] = result["ON_TIME"] + result["LATE"]
        return result
    finally:
        conn.close()


@router.post("/sync")
async def edge_sync(school_id: int, req: AttendanceSync, background_tasks: BackgroundTasks, request: Request):
    """
    Called by Raspberry Pi camera stations. No JWT required — authenticated by station secret key.
    """
    check_rate_limit(f"sync:{get_client_ip(request)}", max_calls=200, window_seconds=60)
    conn = get_db()
    try:
        # Authenticate station
        station = conn.execute(
            "SELECT * FROM camera_stations WHERE school_id=? AND secret_key=?",
            (school_id, req.station_secret_key)
        ).fetchone()
        if not station:
            raise HTTPException(403, "Secret key trạm camera không hợp lệ.")

        # Update station last ping
        conn.execute(
            "UPDATE camera_stations SET status='ONLINE', last_ping_at=datetime('now','localtime') WHERE id=?",
            (station["id"],)
        )

        # Find student
        student = None
        if req.student_id:
            student = conn.execute("SELECT * FROM students WHERE school_id=? AND id=?", (school_id, req.student_id)).fetchone()
        elif req.student_qr_token:
            student = conn.execute("SELECT * FROM students WHERE school_id=? AND qr_token=?", (school_id, req.student_qr_token.strip())).fetchone()
        elif req.student_code:
            code_clean = req.student_code.strip()
            student = conn.execute(
                "SELECT * FROM students WHERE school_id=? AND (LOWER(student_code)=LOWER(?) OR qr_token=?)",
                (school_id, code_clean, code_clean)
            ).fetchone()

        if not student:
            # Kiểm tra nếu là cảnh báo NGƯỜI LẠ (STRANGER / UNKNOWN)
            code_upper = (req.student_code or "").strip().upper()
            is_stranger = (
                code_upper in ("STRANGER", "UNKNOWN", "NGUOI_LA", "NGUOI LA")
                or (req.violation_reason and any(k in req.violation_reason.lower() for k in ("người lạ", "nguoi la", "stranger", "chưa xác định")))
                or req.status in ("STRANGER", "ALERT")
            )
            if is_stranger:
                try:
                    dt = datetime.fromisoformat(req.timestamp) if req.timestamp else datetime.now()
                except Exception:
                    dt = datetime.now()
                date_only = dt.strftime("%Y-%m-%d")
                time_only = dt.strftime("%H:%M")
                iso_timestamp = dt.isoformat()

                station_dir = dict(station).get("direction") or "IN"
                eff_direction = (req.direction or station_dir or "IN").upper()
                if eff_direction not in ("IN", "OUT"):
                    eff_direction = "IN"

                # Lưu ảnh chụp bằng chứng người lạ
                proof_image_url = req.proof_image_url
                if req.proof_image_base64:
                    try:
                        proofs_dir = UPLOAD_DIR / "proofs"
                        proofs_dir.mkdir(parents=True, exist_ok=True)
                        raw_b64 = req.proof_image_base64
                        if "," in raw_b64:
                            raw_b64 = raw_b64.split(",", 1)[1]
                        img_bytes = base64.b64decode(raw_b64)
                        fn = f"stranger_{school_id}_{station['id']}_{date_only}_{int(time.time()*1000)}.jpg"
                        (proofs_dir / fn).write_bytes(img_bytes)
                        proof_image_url = f"/uploads/proofs/{fn}"
                    except Exception as e:
                        log.warning(f"Không thể lưu ảnh người lạ Base64: {e}")

                st_name = dict(station).get("name") or "Cổng trường"
                alert_desc = f"Phát hiện người lạ ({'Lượt ra về' if eff_direction == 'OUT' else 'Lượt vào cổng'}) tại trạm {st_name} lúc {time_only}"
                
                # Chống lặp cảnh báo người lạ liên tục trong 6 giây tại cùng một trạm camera
                recent_alert = conn.execute("""
                    SELECT id, timestamp FROM security_alerts 
                    WHERE school_id=? AND camera_station_id=? AND alert_type='STRANGER' AND date_only=?
                    ORDER BY id DESC LIMIT 1
                """, (school_id, station["id"], date_only)).fetchone()

                should_insert = True
                if recent_alert:
                    try:
                        r_dt = datetime.fromisoformat(recent_alert["timestamp"].replace(" ", "T"))
                        if abs((dt - r_dt).total_seconds()) < 6:
                            should_insert = False
                            if proof_image_url:
                                conn.execute("UPDATE security_alerts SET proof_image_url=? WHERE id=?", (proof_image_url, recent_alert["id"]))
                                conn.commit()
                    except Exception:
                        pass

                if should_insert:
                    conn.execute("""
                        INSERT INTO security_alerts (school_id, camera_station_id, alert_type, title, description, direction, proof_image_url, timestamp, date_only)
                        VALUES (?, ?, 'STRANGER', '🚨 Cảnh Báo Phát Hiện Người Lạ', ?, ?, ?, ?, ?)
                    """, (school_id, station["id"], alert_desc, eff_direction, proof_image_url, iso_timestamp, date_only))
                    conn.commit()

                    # Phát cảnh báo khẩn cấp qua WebSocket cho toàn bộ Giám Thị, BGH, Giáo Viên
                    ws_payload = {
                        "type": "SECURITY_ALERT",
                        "alert_type": "STRANGER",
                        "title": "🚨 CẢNH BÁO AN NINH: PHÁT HIỆN NGƯỜI LẠ",
                        "message": alert_desc,
                        "station_name": st_name,
                        "station_id": station["id"],
                        "direction": eff_direction,
                        "timestamp": iso_timestamp,
                        "proof_image_url": proof_image_url
                    }
                    background_tasks.add_task(broadcast_to_school, school_id, ws_payload)
                    log.warning(f"[SECURITY] 🚨 Cảnh báo phát hiện người lạ tại trường {school_id} - Trạm {st_name} [{eff_direction}]")

                return {
                    "status": "security_alert",
                    "message": f"Đã ghi nhận cảnh báo người lạ tại {st_name}",
                    "direction": eff_direction,
                    "proof_image_url": proof_image_url
                }

            conn.commit()
            return {"status": "not_found", "message": "Không nhận diện được học sinh."}

        # Parse date & time
        try:
            dt = datetime.fromisoformat(req.timestamp) if req.timestamp else datetime.now()
        except Exception:
            dt = datetime.now()
        date_only = dt.strftime("%Y-%m-%d")
        time_only = dt.strftime("%H:%M")
        iso_timestamp = dt.isoformat()

        # Load school rules config — hỗ trợ cả cấu trúc phẳng và cấu trúc lồng AI (H-5)
        school_row = conn.execute("SELECT rules_config FROM schools WHERE id=?", (school_id,)).fetchone()
        rules = json.loads(school_row["rules_config"] or "{}") if school_row else {}
        time_rules = rules.get("time_rules") if isinstance(rules.get("time_rules"), dict) else {}
        uniform_rules = rules.get("uniform_rules") if isinstance(rules.get("uniform_rules"), dict) else {}


        late_deduct = rules.get("late_deduct_points") or time_rules.get("late_deduct_points", 2)
        violation_deduct = rules.get("violation_deduct_points") or uniform_rules.get("shirt", {}).get("violation_deduct_points", 3)
        absent_deduct = rules.get("absent_deduct_points") or time_rules.get("absent_deduct_points", 5)

        # ── PHÂN CHIA & NHẬN DIỆN CA HỌC: BUỔI SÁNG, BUỔI CHIỀU, BUỔI TỐI ──
        # 1. Ca Sáng (Morning)
        m_enabled = rules.get("morning_enabled", True)
        m_from = rules.get("morning_from") or rules.get("checkin_from") or time_rules.get("gate_open", "06:00")
        m_on_time = rules.get("morning_on_time") or rules.get("checkin_on_time_until") or time_rules.get("on_time_deadline", "07:15")
        m_late_cut = rules.get("morning_late_until") or rules.get("checkin_late_until") or time_rules.get("late_cutoff", "07:30")
        m_checkout = rules.get("morning_checkout") or "11:30"

        # 2. Ca Chiều (Afternoon)
        a_enabled = rules.get("afternoon_enabled", True)
        a_from = rules.get("afternoon_from", "12:30")
        a_on_time = rules.get("afternoon_on_time", "13:15")
        a_late_cut = rules.get("afternoon_late_until", "13:30")
        a_checkout = rules.get("afternoon_checkout") or rules.get("checkout_from") or time_rules.get("checkout_start", "17:00")

        # 3. Ca Tối (Evening)
        e_enabled = rules.get("evening_enabled", False)
        e_from = rules.get("evening_from", "18:00")
        e_on_time = rules.get("evening_on_time", "18:45")
        e_late_cut = rules.get("evening_late_until", "19:15")
        e_checkout = rules.get("evening_checkout", "21:30")

        # Xác định ca học dựa theo thời điểm quét time_only
        if time_only < a_from:
            cur_session_code = "MORNING"
            cur_session_name = "buổi sáng"
            cur_enabled = m_enabled
            cur_from = m_from
            cur_on_time = m_on_time
            cur_late_cut = m_late_cut
            cur_checkout = m_checkout
            cur_uniform_check = rules["morning_uniform_check"] if "morning_uniform_check" in rules else rules.get("uniform_check", True)
            cur_late_deduct = rules["morning_late_deduct"] if "morning_late_deduct" in rules else late_deduct
            cur_auth_mode = rules.get("morning_auth_mode", "ALL")
        elif time_only < e_from:
            cur_session_code = "AFTERNOON"
            cur_session_name = "buổi chiều"
            cur_enabled = a_enabled
            cur_from = a_from
            cur_on_time = a_on_time
            cur_late_cut = a_late_cut
            cur_checkout = a_checkout
            cur_uniform_check = rules["afternoon_uniform_check"] if "afternoon_uniform_check" in rules else rules.get("uniform_check", True)
            cur_late_deduct = rules["afternoon_late_deduct"] if "afternoon_late_deduct" in rules else late_deduct
            cur_auth_mode = rules.get("afternoon_auth_mode", "ALL")
        else:
            cur_session_code = "EVENING"
            cur_session_name = "buổi tối"
            cur_enabled = e_enabled
            cur_from = e_from
            cur_on_time = e_on_time
            cur_late_cut = e_late_cut
            cur_checkout = e_checkout
            cur_uniform_check = rules["evening_uniform_check"] if "evening_uniform_check" in rules else rules.get("uniform_check", True)
            cur_late_deduct = rules["evening_late_deduct"] if "evening_late_deduct" in rules else late_deduct
            cur_auth_mode = rules.get("evening_auth_mode", "ALL")

        # ── XÁC ĐỊNH CHIỀU DI CHUYỂN (IN vs OUT) ──
        station_dir = dict(station).get("direction") or "IN"
        eff_direction = (req.direction or station_dir or "IN").upper()
        if eff_direction not in ("IN", "OUT"):
            eff_direction = "IN"

        # ── XỬ LÝ LỖI & VI PHẠM (ĐẢM BẢO HỌC SINH CÓ DỮ LIỆU DB KHÔNG BỊ VẮNG) ──
        effective_status = req.status
        is_late_by_time = (time_only > cur_on_time)
        is_out_of_standard_hours = (time_only < cur_from or time_only > cur_late_cut)

        # Xử lý đồng phục: nếu ca này không yêu cầu đồng phục thì bỏ qua lỗi vi phạm đồng phục
        eff_uniform_status = req.uniform_status
        if not cur_uniform_check and eff_uniform_status == "VIOLATION":
            eff_uniform_status = "OK"

        # Thu thập chi tiết vi phạm / lỗi
        violation_details_list = []
        if req.violation_reason and req.violation_reason.strip():
            violation_details_list.append(req.violation_reason.strip())
        if cur_uniform_check and eff_uniform_status == "VIOLATION" and not any("phục" in v.lower() or "phuc" in v.lower() for v in violation_details_list):
            violation_details_list.append("Vi phạm đồng phục")

        if eff_direction == "IN":
            if not cur_enabled:
                violation_details_list.append(f"Điểm danh ngoài ca học (Chưa bật {cur_session_name})")
            elif is_out_of_standard_hours and not any("ngoài giờ" in v.lower() or "ngoai gio" in v.lower() for v in violation_details_list):
                violation_details_list.append(f"Điểm danh ngoài khung giờ {cur_session_name} ({time_only})")
            elif is_late_by_time and not any("trễ" in v.lower() or "tre" in v.lower() for v in violation_details_list):
                violation_details_list.append(f"Đi trễ {cur_session_name} ({time_only} > {cur_on_time})")
        elif eff_direction == "OUT":
            if time_only < cur_checkout and not any("sớm" in v.lower() or "som" in v.lower() for v in violation_details_list):
                violation_details_list.append(f"Ra cổng trước giờ tan học {cur_session_name} ({time_only} < {cur_checkout})")

        if req.spoof_status == "FAILED":
            violation_details_list.append("Cảnh báo nghi vấn sinh trắc học")

        violation_details = "; ".join(violation_details_list) if violation_details_list else None

        # Chuẩn hóa effective_status cho check-in
        if eff_direction == "IN":
            if effective_status in ("ABSENT", "WARN", "VIOLATION", "ERROR"):
                effective_status = "LATE"
            elif effective_status == "ON_TIME" and (is_late_by_time or is_out_of_standard_hours):
                effective_status = "LATE"
        else:
            if effective_status in ("ABSENT", "WARN", "VIOLATION", "ERROR"):
                effective_status = "ON_TIME"

        # ── XỬ LÝ ẢNH CHỤP MINH CHỨNG TỪ CAMERA TRỰC TIẾP (PROOF IMAGE) ──
        proof_image_url = req.proof_image_url
        if req.proof_image_base64:
            try:
                proofs_dir = UPLOAD_DIR / "proofs"
                proofs_dir.mkdir(parents=True, exist_ok=True)
                raw_b64 = req.proof_image_base64
                if "," in raw_b64:
                    raw_b64 = raw_b64.split(",", 1)[1]
                img_bytes = base64.b64decode(raw_b64)
                prefix = "violation" if violation_details else "attendance"
                fn = f"{prefix}_{school_id}_{student['id']}_{date_only}_{int(time.time()*1000)}.jpg"
                (proofs_dir / fn).write_bytes(img_bytes)
                proof_image_url = f"/uploads/proofs/{fn}"
            except Exception as e:
                log.warning(f"Không thể lưu ảnh chụp camera Base64: {e}")

        # KHÔNG fallback ảnh avatar hồ sơ: Ảnh minh chứng phải là ảnh chụp thực tế từ camera tại thời điểm quét!

        # ── CHỐNG QUÉT LẶP (DEBOUNCE TRONG VÒNG 3 GIÂY CÙNG CHIỀU) ──
        recent = conn.execute("""
            SELECT id, timestamp, status, uniform_status, proof_image_url, violation_details, direction
            FROM attendance_logs
            WHERE student_id=? AND date_only=? AND UPPER(COALESCE(direction, 'IN'))=?
            ORDER BY id DESC LIMIT 1
        """, (student["id"], date_only, eff_direction)).fetchone()

        if recent:
            try:
                recent_dt = datetime.fromisoformat(recent["timestamp"].replace(" ", "T"))
                diff_seconds = abs((dt - recent_dt).total_seconds())
            except Exception:
                diff_seconds = 9999
            if diff_seconds < 3:
                update_fields = []
                update_params = []
                if proof_image_url:
                    update_fields.append("proof_image_url=COALESCE(?, proof_image_url)")
                    update_params.append(proof_image_url)
                if violation_details:
                    update_fields.append("violation_details=COALESCE(?, violation_details)")
                    update_params.append(violation_details)
                if eff_uniform_status == "VIOLATION" and recent["uniform_status"] != "VIOLATION":
                    update_fields.append("uniform_status=?")
                    update_params.append("VIOLATION")
                    conn.execute("UPDATE students SET current_points = MAX(0, current_points - ?) WHERE id=?", (violation_deduct, student["id"]))
                if update_fields:
                    update_params.append(recent["id"])
                    conn.execute(f"UPDATE attendance_logs SET {', '.join(update_fields)} WHERE id=?", tuple(update_params))
                    conn.commit()
                return {
                    "status": "already_checked_in",
                    "message": f"Học sinh {student['full_name']} vừa ghi nhận {'đến trường' if eff_direction == 'IN' else 'ra về'} lúc {recent['timestamp'][-8:]}.",
                    "student_name": student["full_name"],
                    "student_code": student["student_code"],
                    "check_status": recent["status"],
                    "direction": eff_direction,
                    "is_present": True,
                    "proof_image_url": proof_image_url or recent["proof_image_url"],
                    "violation_details": violation_details or recent["violation_details"]
                }

        deduct = 0
        # ── NẾU LÀ CHECK-IN VÀ TRƯỚC ĐÓ BỊ ĐÁNH DẤU ABSENT -> XÓA VẮNG & CẬP NHẬT THÀNH CÓ MẶT ──
        absent_log = None
        if eff_direction == "IN":
            absent_log = conn.execute("""
                SELECT id FROM attendance_logs WHERE student_id=? AND date_only=? AND status='ABSENT'
                ORDER BY id DESC LIMIT 1
            """, (student["id"], date_only)).fetchone()

        if absent_log:
            # Hoàn lại điểm phạt vắng
            conn.execute(
                "UPDATE students SET current_points = MIN(100, current_points + ?) WHERE id=?",
                (absent_deduct, student["id"])
            )
            if effective_status == "LATE":
                deduct += cur_late_deduct
            if eff_uniform_status == "VIOLATION":
                deduct += violation_deduct
            if deduct > 0:
                conn.execute("UPDATE students SET current_points = MAX(0, current_points - ?) WHERE id=?", (deduct, student["id"]))

            conn.execute("""
                UPDATE attendance_logs SET
                    camera_station_id=?,
                    timestamp=?,
                    direction=?,
                    check_type=?,
                    status=?,
                    uniform_status=?,
                    spoof_status=?,
                    confidence_score=?,
                    proof_image_url=COALESCE(?, proof_image_url),
                    violation_details=?
                WHERE id=?
            """, (
                station["id"], iso_timestamp, eff_direction, req.check_type, effective_status,
                eff_uniform_status, req.spoof_status, req.confidence_score,
                proof_image_url, violation_details, absent_log["id"]
            ))
            conn.commit()
            log.info(f"Học sinh {student['student_code']} đã chuyển từ ABSENT sang {effective_status} (IN scan).")
        else:
            # Tạo bản ghi log mới (IN hoặc OUT)
            if eff_direction == "IN":
                if effective_status == "LATE":
                    deduct += cur_late_deduct
                if eff_uniform_status == "VIOLATION":
                    deduct += violation_deduct

            conn.execute("""
                INSERT INTO attendance_logs (
                    student_id, camera_station_id, school_id,
                    timestamp, date_only, direction, check_type, status,
                    uniform_status, spoof_status, confidence_score, proof_image_url,
                    violation_details
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                student["id"], station["id"], school_id,
                iso_timestamp, date_only, eff_direction, req.check_type, effective_status,
                eff_uniform_status, req.spoof_status, req.confidence_score, proof_image_url,
                violation_details
            ))

            if deduct > 0:
                conn.execute("UPDATE students SET current_points = MAX(0, current_points - ?) WHERE id=?", (deduct, student["id"]))

            conn.commit()

        # Lấy tên lớp học của học sinh để hiển thị thông báo đầy đủ
        class_name = ""
        if student["class_id"]:
            c_row = conn.execute("SELECT name FROM classes WHERE id=?", (student["class_id"],)).fetchone()
            if c_row:
                class_name = c_row["name"]

        # ── Broadcast realtime lên WebSocket dashboard ──
        ws_payload = {
            "type":              "ATTENDANCE_LOG",
            "school_id":         school_id,
            "student_id":        student["id"],
            "student_name":      student["full_name"],
            "student_code":      student["student_code"],
            "class_name":        class_name,
            "direction":         eff_direction,
            "status":            effective_status,
            "check_type":        req.check_type,
            "uniform_status":    req.uniform_status,
            "confidence":        req.confidence_score,
            "timestamp":         iso_timestamp,
            "station_id":        station["id"],
            "station_name":      dict(station).get("name", ""),
            "points_deducted":   deduct,
            "proof_image_url":   proof_image_url,
            "violation_details": violation_details,
            "is_present":        True
        }
        background_tasks.add_task(broadcast_to_school, school_id, ws_payload)
        log.info(f"[WS] Broadcast attendance to school {school_id}: {student['full_name']} [{eff_direction}] → {effective_status}")

        # Đã bỏ thông báo đẩy ra/vào cổng để tránh nghẽn mạng/lag hệ thống vào giờ cao điểm
        # Dữ liệu được lưu trữ trực tiếp để phụ huynh & giáo viên chủ động tra cứu trên Sổ Điểm Danh

        dir_desc = "vào trường" if eff_direction == "IN" else "ra về"
        return {
            "status":            "success",
            "message":           f"Ghi nhận {dir_desc}: {student['full_name']}" + (f" (Lỗi: {violation_details})" if violation_details else ""),
            "student_name":      student["full_name"],
            "student_code":      student["student_code"],
            "check_status":      effective_status,
            "uniform_status":    eff_uniform_status,
            "direction":         eff_direction,
            "is_present":        True,
            "violation_details": violation_details,
            "proof_image_url":   proof_image_url,
            "points_deducted":   deduct
        }
    finally:
        conn.close()


@router.get("/reconciliation")
async def get_attendance_reconciliation(
    school_id: int,
    date:      Optional[str] = Query(None, description="YYYY-MM-DD"),
    class_id:  Optional[int] = Query(None),
    search:    Optional[str] = Query(None),
    current:   dict = Depends(require_role("TEACHER", "INSPECTOR", "HEADMASTER", "ADMIN"))
):
    """
    Đối chiếu dữ liệu điểm danh log Vào (Check-In) và log Ra (Check-Out) của từng học sinh:
    - Ghép cặp tự động (In-Out Pairing) và tính thời gian ở lại trường (session duration).
    - Phân loại trạng thái hiện diện:
        * IN_CAMPUS: Đang ở trường (Check-in, chưa check-out).
        * DEPARTED: Đã ra về (Check-out hợp lệ cuối ngày).
        * EARLY_EXIT: Ra về sớm (Check-out trước giờ tan trường).
        * ABSENT: Vắng mặt (Không có log vào / có quyết định vắng).
        * EXCUSED: Nghỉ học có phép.
        * OUT_WITHOUT_IN: Bất thường (Có log ra nhưng không có log vào).
    """
    _check_scope(school_id, current)
    conn = get_db()
    try:
        query_date = date or datetime.now().strftime("%Y-%m-%d")

        # Teacher homeroom scope
        if current["role"] == "TEACHER" and not class_id:
            teacher_uid = current.get("user_id") or current.get("id")
            hr_row = conn.execute("""
                SELECT id FROM classes
                WHERE school_id=? AND is_active=1
                  AND (homeroom_teacher_id=? OR homeroom_teacher_id=(SELECT id FROM users WHERE school_id=? AND username=?))
                LIMIT 1
            """, (school_id, teacher_uid, school_id, current["username"])).fetchone()
            if hr_row:
                class_id = hr_row["id"]

        # 1. Danh sách học sinh
        student_sql = """
            SELECT s.id, s.student_code, s.full_name, s.class_id, c.name as class_name,
                   s.face_photo_url, s.current_points, s.parent_phone
            FROM students s
            LEFT JOIN classes c ON s.class_id = c.id
            WHERE s.school_id=? AND s.is_active=1 AND s.is_deleted=0
        """
        student_params = [school_id]
        if class_id:
            student_sql += " AND s.class_id=?"
            student_params.append(class_id)
        if search and search.strip():
            s_term = f"%{search.strip()}%"
            student_sql += " AND (s.full_name LIKE ? OR s.student_code LIKE ?)"
            student_params.extend([s_term, s_term])

        student_sql += " ORDER BY c.name ASC, s.full_name ASC"
        students = [dict(r) for r in conn.execute(student_sql, student_params).fetchall()]

        # 2. Toàn bộ logs trong ngày của trường
        logs = conn.execute("""
            SELECT a.*, cs.name as camera_name, cs.location as camera_location
            FROM attendance_logs a
            LEFT JOIN camera_stations cs ON a.camera_station_id = cs.id
            WHERE a.school_id=? AND a.date_only=?
            ORDER BY a.timestamp ASC
        """, (school_id, query_date)).fetchall()

        # 3. Đơn xin nghỉ phép hợp lệ
        leaves = conn.execute("""
            SELECT student_id, reason FROM leave_requests
            WHERE school_id=? AND status IN ('APPROVE', 'APPROVED') AND ? BETWEEN start_date AND end_date
        """, (school_id, query_date)).fetchall()
        leave_map = {l["student_id"]: l["reason"] for l in leaves}

        # Nhóm logs theo student_id
        student_logs_map = {}
        for l in logs:
            sid = l["student_id"]
            if sid not in student_logs_map:
                student_logs_map[sid] = []
            student_logs_map[sid].append(dict(l))

        def _parse_ts(ts_str):
            if not ts_str:
                return None
            try:
                return datetime.fromisoformat(ts_str.replace(" ", "T"))
            except Exception:
                try:
                    return datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
                except Exception:
                    return None

        records = []
        counts = {
            "total_students": len(students),
            "in_campus": 0,
            "departed": 0,
            "early_exit": 0,
            "absent": 0,
            "excused": 0,
            "anomaly": 0
        }

        for s in students:
            st_logs = student_logs_map.get(s["id"], [])
            
            in_logs = [l for l in st_logs if (l.get("direction") or "IN").upper() == "IN" and l.get("status") != "ABSENT"]
            out_logs = [l for l in st_logs if (l.get("direction") or "IN").upper() == "OUT"]
            is_excused = (s["id"] in leave_map)

            first_in = in_logs[0] if in_logs else None
            last_out = out_logs[-1] if out_logs else None

            # Thời lượng ở trường (phút)
            duration_minutes = 0
            duration_formatted = "--"
            if first_in and last_out:
                dt_in = _parse_ts(first_in["timestamp"])
                dt_out = _parse_ts(last_out["timestamp"])
                if dt_in and dt_out:
                    duration_minutes = max(0, int((dt_out - dt_in).total_seconds() / 60))
                    duration_formatted = f"{duration_minutes // 60}h {duration_minutes % 60:02d}m"
            elif first_in and not last_out:
                dt_in = _parse_ts(first_in["timestamp"])
                if dt_in:
                    now = datetime.now() if query_date == datetime.now().strftime("%Y-%m-%d") else dt_in
                    duration_minutes = max(0, int((now - dt_in).total_seconds() / 60))
                    duration_formatted = f"{duration_minutes // 60}h {duration_minutes % 60:02d}m (đang ở trường)"

            # Xác định presence_status
            if len(in_logs) == 0 and len(out_logs) == 0:
                if is_excused:
                    presence_status = "EXCUSED"
                    counts["excused"] += 1
                else:
                    presence_status = "ABSENT"
                    counts["absent"] += 1
            elif len(in_logs) > 0 and len(out_logs) == 0:
                presence_status = "IN_CAMPUS"
                counts["in_campus"] += 1
            elif len(in_logs) == 0 and len(out_logs) > 0:
                presence_status = "OUT_WITHOUT_IN"
                counts["anomaly"] += 1
            else:
                # Cả vào và ra đều có
                last_in_ts = in_logs[-1]["timestamp"]
                last_out_ts = out_logs[-1]["timestamp"]
                if last_in_ts > last_out_ts:
                    presence_status = "IN_CAMPUS"
                    counts["in_campus"] += 1
                else:
                    # Đã ra cổng -> xét xem ra sớm hay đúng giờ
                    out_time = last_out["timestamp"].replace("T", " ").split(" ")[-1][:5]
                    if out_time < "16:00":
                        presence_status = "EARLY_EXIT"
                        counts["early_exit"] += 1
                    else:
                        presence_status = "DEPARTED"
                        counts["departed"] += 1

            is_anomaly = (presence_status in ("OUT_WITHOUT_IN", "EARLY_EXIT"))
            anomaly_note = ""
            if presence_status == "OUT_WITHOUT_IN":
                anomaly_note = "Phát hiện ra cổng nhưng không có log vào buổi sáng"
            elif presence_status == "EARLY_EXIT":
                anomaly_note = f"Ra về sớm ({last_out['timestamp'].replace('T', ' ').split(' ')[-1][:5]} < 16:00)"

            records.append({
                "student_id": s["id"],
                "student_code": s["student_code"],
                "full_name": s["full_name"],
                "class_id": s["class_id"],
                "class_name": s["class_name"] or "Chưa phân lớp",
                "face_photo_url": s["face_photo_url"],
                "presence_status": presence_status,
                "first_in": {
                    "time": first_in["timestamp"].replace("T", " ").split(" ")[-1][:8],
                    "timestamp": first_in["timestamp"],
                    "camera_name": first_in["camera_name"] or "Cổng trường",
                    "status": first_in["status"],
                    "uniform_status": first_in["uniform_status"],
                    "proof_image_url": first_in["proof_image_url"],
                    "violation_details": first_in["violation_details"]
                } if first_in else None,
                "last_out": {
                    "time": last_out["timestamp"].replace("T", " ").split(" ")[-1][:8],
                    "timestamp": last_out["timestamp"],
                    "camera_name": last_out["camera_name"] or "Cổng trường",
                    "proof_image_url": last_out["proof_image_url"],
                    "violation_details": last_out["violation_details"]
                } if last_out else None,
                "total_in_count": len(in_logs),
                "total_out_count": len(out_logs),
                "duration_minutes": duration_minutes,
                "duration_formatted": duration_formatted,
                "is_anomaly": is_anomaly,
                "anomaly_note": anomaly_note,
                "all_logs": [
                    {
                        "id": l["id"],
                        "direction": (l.get("direction") or "IN").upper(),
                        "timestamp": l["timestamp"],
                        "time": l["timestamp"].replace("T", " ").split(" ")[-1][:8],
                        "camera_name": l["camera_name"] or "Cổng trường",
                        "status": l["status"],
                        "uniform_status": l.get("uniform_status"),
                        "proof_image_url": l.get("proof_image_url"),
                        "violation_details": l["violation_details"]
                    } for l in st_logs
                ]
            })

        return {
            "date": query_date,
            "class_id": class_id,
            "stats": counts,
            "records": records
        }
    finally:
        conn.close()


@router.get("/security-alerts")
async def list_security_alerts(
    school_id: int,
    date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    direction: Optional[str] = Query(None, description="IN | OUT"),
    limit: int = Query(5000, ge=1, le=50000),
    current: dict = Depends(require_role("TEACHER", "INSPECTOR", "HEADMASTER"))
):
    """Lấy danh sách cảnh báo an ninh & ảnh chụp người lạ theo ngày tại các cổng trường."""
    _check_scope(school_id, current)
    conn = get_db()
    try:
        sql = """
            SELECT sa.id, sa.school_id, sa.camera_station_id, sa.alert_type,
                   sa.title, sa.description, sa.direction, sa.proof_image_url,
                   sa.timestamp, sa.date_only, sa.status, sa.created_at,
                   COALESCE(cs.name, 'Cổng trường') AS camera_name,
                   COALESCE(cs.location, 'Camera AI') AS camera_location
            FROM security_alerts sa
            LEFT JOIN camera_stations cs ON sa.camera_station_id = cs.id
            WHERE sa.school_id = ?
        """
        params = [school_id]
        if date:
            sql += " AND sa.date_only = ?"
            params.append(date)
        if direction:
            sql += " AND UPPER(COALESCE(sa.direction, 'IN')) = ?"
            params.append(direction.upper())

        sql += " ORDER BY sa.id DESC LIMIT ?"
        params.append(limit)

        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()



@router.get("/student/{student_id}")
async def student_attendance(school_id: int, student_id: int, current: dict = Depends(get_current_user)):
    _check_scope(school_id, current)
    conn = get_db()
    try:
        # Student can only see own records
        if current["role"] == "STUDENT":
            me = conn.execute("SELECT id FROM students WHERE user_id=? AND school_id=?", (current["user_id"], school_id)).fetchone()
            if not me or me["id"] != student_id:
                raise HTTPException(403, "Bạn chỉ có thể xem lịch sử của mình.")
        elif current["role"] == "PARENT":
            link = conn.execute(
                "SELECT id FROM parent_student_links WHERE parent_user_id=? AND student_id=? AND school_id=?",
                (current["user_id"], student_id, school_id)
            ).fetchone()
            if not link:
                # Fallback đối chiếu SĐT
                stu = conn.execute("""
                    SELECT id FROM students
                    WHERE id=? AND school_id=? AND parent_phone=(SELECT phone FROM users WHERE id=?)
                """, (student_id, school_id, current["user_id"])).fetchone()
                if not stu:
                    raise HTTPException(403, "Bạn chỉ có thể xem lịch sử điểm danh của con mình.")

        rows = conn.execute("""
            SELECT * FROM attendance_logs WHERE student_id=? AND school_id=?
            ORDER BY timestamp DESC LIMIT 60
        """, (student_id, school_id)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


@router.post("/mark-absent-today")
async def mark_absent_today(
    school_id: int,
    current: dict = Depends(require_role("TEACHER", "INSPECTOR", "HEADMASTER", "ADMIN"))
):
    """
    Quét danh sách toàn trường sau giờ đóng cổng:
    - Nếu học sinh có đơn nghỉ phép APPROVED hợp lệ hôm nay -> Đánh dấu EXCUSED.
    - Nếu học sinh không có đơn nghỉ phép -> Đánh dấu ABSENT và trừ điểm chuyên cần.
    """
    _check_scope(school_id, current)
    conn = get_db()
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Tìm các học sinh hoạt động chưa có bản ghi điểm danh hôm nay
        unrecorded = conn.execute("""
            SELECT s.id, s.full_name, s.current_points
            FROM students s
            WHERE s.school_id=? AND s.is_active=1 AND s.is_deleted=0
              AND s.id NOT IN (
                  SELECT student_id FROM attendance_logs WHERE school_id=? AND date_only=?
              )
        """, (school_id, school_id, today)).fetchall()

        marked_absent = 0
        marked_excused = 0

        # Lấy quy định trừ điểm vắng
        school_row = conn.execute("SELECT rules_config FROM schools WHERE id=?", (school_id,)).fetchone()
        rules = json.loads(school_row["rules_config"] or "{}") if school_row else {}
        time_rules = rules.get("time_rules") if isinstance(rules.get("time_rules"), dict) else {}
        absent_deduct = rules.get("absent_deduct_points") or time_rules.get("absent_deduct_points", 5)

        for stu in unrecorded:
            # Kiểm tra đơn nghỉ phép đã duyệt
            leave = conn.execute("""
                SELECT id FROM leave_requests
                WHERE student_id=? AND school_id=? AND status IN ('APPROVE', 'APPROVED') AND ? BETWEEN start_date AND end_date
            """, (stu["id"], school_id, today)).fetchone()

            if leave:
                status_val = "EXCUSED"
                marked_excused += 1
                deduct = 0
            else:
                status_val = "ABSENT"
                marked_absent += 1
                deduct = absent_deduct

            conn.execute("""
                INSERT INTO attendance_logs (
                    student_id, school_id, timestamp, date_only, check_type, status,
                    uniform_status, spoof_status, confidence_score
                ) VALUES (?, ?, datetime('now','localtime'), ?, 'MANUAL', ?, 'UNKNOWN', 'SKIPPED', 1.0)
            """, (stu["id"], school_id, today, status_val))

            if deduct > 0:
                conn.execute("UPDATE students SET current_points = MAX(0, current_points - ?) WHERE id=?", (deduct, stu["id"]))

        conn.commit()
        return {
            "status": "success",
            "message": f"Chốt chuyên cần hôm nay thành công: {marked_absent} vắng không phép, {marked_excused} nghỉ có phép.",
            "marked_absent": marked_absent,
            "marked_excused": marked_excused,
            "total_processed": len(unrecorded)
        }
    finally:
        conn.close()


@router.get("/export-csv")
async def export_attendance_csv(
    school_id: int,
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    time_from: Optional[str] = Query(None),
    time_to: Optional[str] = Query(None),
    time_mode: Optional[str] = Query("daily"),
    class_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    uniform_status: Optional[str] = Query(None),
    date: Optional[str] = Query(None),
    current: dict = Depends(require_role("TEACHER", "INSPECTOR", "HEADMASTER", "ADMIN"))
):
    """Xuất báo cáo chuyên cần CSV phục vụ thống kê & tải về."""
    _check_scope(school_id, current)
    if date and not date_from and not date_to:
        date_from = date
        date_to = date
    from app.services.report_service import generate_attendance_csv
    csv_rel = await generate_attendance_csv(
        school_id=school_id,
        date_from=date_from,
        date_to=date_to,
        time_from=time_from,
        time_to=time_to,
        time_mode=time_mode,
        class_id=class_id,
        status=status,
        uniform_status=uniform_status
    )
    filename = csv_rel.split("/")[-1]
    filepath = UPLOAD_DIR / "reports" / filename
    return FileResponse(
        path=str(filepath),
        media_type="text/csv; charset=utf-8",
        filename=filename,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

