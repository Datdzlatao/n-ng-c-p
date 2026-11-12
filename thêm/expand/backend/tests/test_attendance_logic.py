"""
tests/test_attendance_logic.py — Comprehensive tests for attendance rules,
dispute resolution, leave approval refunds, mark-absent-today, and camera sync.
"""
import json
import time
from datetime import datetime, timedelta
from app.database import get_db


def test_camera_roster_sync(client, auth_header):
    """
    Trạm camera AI có thể tải danh sách học sinh theo trường bằng secret_key,
    chỉ lấy học sinh của trường đó và từ chối khi secret_key sai.
    """
    conn = get_db()
    ts = int(time.time() * 1000)
    code1 = f"SYNC-1-{ts}"
    code2 = f"SYNC-2-{ts}"
    code_other = f"SYNC-OTHER-{ts}"

    try:
        secret = f"cam_sync_secret_{ts}"
        cur = conn.execute("""
            INSERT INTO camera_stations (school_id, name, secret_key, stream_type, status)
            VALUES (1, 'Trạm Cổng 1 Test', ?, 'WEBCAM', 'ONLINE')
        """, (secret,))
        cam_id = cur.lastrowid

        # Tạo 2 học sinh ở trường 1, 1 học sinh ở trường 2
        conn.execute("""
            INSERT INTO students (school_id, student_code, full_name, is_active)
            VALUES (1, ?, 'Nguyễn Test Đồng Bộ 1', 1)
        """, (code1,))
        conn.execute("""
            INSERT INTO students (school_id, student_code, full_name, is_active)
            VALUES (1, ?, 'Trần Test Đồng Bộ 2', 1)
        """, (code2,))
        # Trường khác
        conn.execute("""
            INSERT OR IGNORE INTO schools (id, school_code, name, status)
            VALUES (2, 'school-2-test', 'Trường 2', 'ACTIVE')
        """)
        conn.execute("""
            INSERT INTO students (school_id, student_code, full_name, is_active)
            VALUES (2, ?, 'Lê Trường Khác', 1)
        """, (code_other,))
        conn.commit()
    finally:
        conn.close()

    # 1. Gọi sai secret_key -> 403
    res_wrong = client.get(f"/api/v1/s/1/cameras/{cam_id}/students?secret_key=WRONG_KEY")
    assert res_wrong.status_code == 403

    # 2. Gọi đúng secret_key -> 200, danh sách học sinh trường 1
    res = client.get(f"/api/v1/s/1/cameras/{cam_id}/students?secret_key={secret}")
    assert res.status_code == 200
    students = res.json()
    assert isinstance(students, list)
    codes = [s["student_code"] for s in students]
    assert code1 in codes
    assert code2 in codes
    assert code_other not in codes


def test_independent_penalty_deductions(client):
    """
    Trừ điểm độc lập cho cả đi trễ và vi phạm trang phục (không bị ghi đè hay bỏ sót).
    """
    ts = int(time.time() * 1000)
    secret = f"cam_penalty_{ts}"
    student_code = f"STU-PEN-{ts}"
    today_str = datetime.now().strftime("%Y-%m-%d")

    conn = get_db()
    try:
        # Cấu hình trừ điểm: trễ trừ 3, sai đồng phục trừ 4
        rules = {
            "checkin_from": "05:00",
            "checkin_on_time_until": "07:15",
            "checkin_late_until": "19:00",
            "late_deduct_points": 3,
            "violation_deduct_points": 4
        }
        conn.execute("UPDATE schools SET rules_config=? WHERE id=1", (json.dumps(rules),))

        conn.execute("""
            INSERT INTO camera_stations (school_id, name, secret_key, stream_type, status)
            VALUES (1, 'Trạm Test Phạt', ?, 'WEBCAM', 'ONLINE')
        """, (secret,))

        conn.execute("""
            INSERT INTO students (school_id, student_code, full_name, current_points, is_active)
            VALUES (1, ?, 'Học Sinh Trễ Và Sai Phục', 100, 1)
        """, (student_code,))
        conn.commit()
    finally:
        conn.close()

    # Gửi điểm danh: LATE + VIOLATION lúc 07:30
    res = client.post("/api/v1/s/1/attendance/sync", json={
        "station_secret_key": secret,
        "student_code": student_code,
        "timestamp": f"{today_str}T07:30:00",
        "check_type": "FACE_AI",
        "status": "LATE",
        "uniform_status": "VIOLATION"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    # Điểm trừ phải là 3 (late) + 4 (uniform) = 7
    assert data["points_deducted"] == 7

    conn = get_db()
    try:
        stu = conn.execute("SELECT current_points FROM students WHERE student_code=?", (student_code,)).fetchone()
        assert stu["current_points"] == 93  # 100 - 7 = 93
    finally:
        conn.close()


def test_dispute_approval_refunds_points(client, auth_header):
    """
    Khi GVCN/Admin chấp nhận khiếu nại (APPROVE):
    - Nhật ký đổi sang EXCUSED
    - Điểm nề nếp bị trừ được hoàn trả lại cho học sinh.
    """
    ts = int(time.time() * 1000)
    student_code = f"STU-DISP-{ts}"
    today_str = datetime.now().strftime("%Y-%m-%d")

    conn = get_db()
    try:
        conn.execute("""
            INSERT INTO students (school_id, student_code, full_name, current_points, is_active)
            VALUES (1, ?, 'Học Sinh Khiếu Nại', 93, 1)
        """, (student_code,))
        stu_id = conn.execute("SELECT id FROM students WHERE student_code=?", (student_code,)).fetchone()["id"]

        cur_att = conn.execute("""
            INSERT INTO attendance_logs (
                student_id, school_id, timestamp, date_only, check_type,
                status, uniform_status, is_disputed
            ) VALUES (?, 1, ?, ?, 'FACE_AI', 'LATE', 'VIOLATION', 1)
        """, (stu_id, f"{today_str}T07:35:00", today_str))
        log_id = cur_att.lastrowid

        cur_disp = conn.execute("""
            INSERT INTO disputes (attendance_log_id, student_id, school_id, reason, level, status)
            VALUES (?, ?, 1, 'Em mặc áo khoác che đồng phục', 'LEVEL_1_TEACHER', 'PENDING')
        """, (log_id, stu_id))
        dispute_id = cur_disp.lastrowid
        conn.commit()
    finally:
        conn.close()

    # Admin duyệt khiếu nại
    res = client.put(f"/api/v1/s/1/disputes/{dispute_id}/resolve", json={
        "action": "APPROVE",
        "resolution_note": "Đã xác minh lại ảnh camera, chấp nhận giải trình."
    }, headers=auth_header)
    assert res.status_code == 200

    conn = get_db()
    try:
        stu = conn.execute("SELECT current_points FROM students WHERE id=?", (stu_id,)).fetchone()
        # Đã hoàn lại 3 (late) + 4 (violation) = 7 -> 93 + 7 = 100
        assert stu["current_points"] == 100

        att = conn.execute("SELECT status, is_disputed FROM attendance_logs WHERE id=?", (log_id,)).fetchone()
        assert att["status"] == "EXCUSED"
        assert att["is_disputed"] == 0
    finally:
        conn.close()


def test_leave_request_validation_and_refund(client, auth_header):
    """
    Kiểm tra:
    1. Validation: start_date > end_date -> 422
    2. Duyệt đơn xin phép sau khi đã bị tính vắng -> tự động hoàn trả điểm và chuyển trạng thái log sang EXCUSED.
    """
    ts = int(time.time() * 1000)
    student_code = f"STU-LEAVE-{ts}"
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    conn = get_db()
    try:
        conn.execute("""
            INSERT INTO students (school_id, student_code, full_name, current_points, is_active)
            VALUES (1, ?, 'Học Sinh Xin Phép Nghỉ', 95, 1)
        """, (student_code,))
        stu_id = conn.execute("SELECT id FROM students WHERE student_code=?", (student_code,)).fetchone()["id"]

        conn.execute("""
            INSERT INTO attendance_logs (student_id, school_id, timestamp, date_only, check_type, status)
            VALUES (?, 1, ?, ?, 'MANUAL', 'ABSENT')
        """, (stu_id, f"{yesterday}T07:00:00", yesterday))
        conn.commit()
    finally:
        conn.close()

    # 1. Thử gửi đơn có ngày bắt đầu > ngày kết thúc
    res_invalid = client.post("/api/v1/s/1/leaves", json={
        "student_id": stu_id,
        "start_date": "2026-09-10",
        "end_date": "2026-09-08",
        "reason": "Nghỉ ốm"
    }, headers=auth_header)
    assert res_invalid.status_code == 422

    # 2. Gửi đơn hợp lệ bao trọn ngày hôm qua
    res_valid = client.post("/api/v1/s/1/leaves", json={
        "student_id": stu_id,
        "start_date": yesterday,
        "end_date": yesterday,
        "reason": "Đi khám bệnh theo lịch của viện"
    }, headers=auth_header)
    assert res_valid.status_code == 200

    conn = get_db()
    try:
        leave = conn.execute("SELECT id FROM leave_requests WHERE student_id=? ORDER BY id DESC LIMIT 1", (stu_id,)).fetchone()
        leave_id = leave["id"]
    finally:
        conn.close()

    # 3. Phê duyệt đơn xin phép -> hoàn lại 5 điểm vắng
    res_app = client.put(f"/api/v1/s/1/leaves/{leave_id}/approve", json={"action": "APPROVE"}, headers=auth_header)
    assert res_app.status_code == 200

    conn = get_db()
    try:
        stu = conn.execute("SELECT current_points FROM students WHERE id=?", (stu_id,)).fetchone()
        assert stu["current_points"] == 100  # 95 + 5 = 100

        log = conn.execute("SELECT status FROM attendance_logs WHERE student_id=? AND date_only=?", (stu_id, yesterday)).fetchone()
        assert log["status"] == "EXCUSED"
    finally:
        conn.close()


def test_mark_absent_today(client, auth_header):
    """
    Chốt vắng cuối ngày:
    - Học sinh có đơn xin phép APPROVED -> ghi nhận EXCUSED (không trừ điểm)
    - Học sinh không phép -> ghi nhận ABSENT và trừ điểm chuyên cần.
    - Chạy lại không bị nhân đôi (skip những học sinh đã có log).
    """
    today_str = datetime.now().strftime("%Y-%m-%d")
    ts = int(time.time() * 1000)
    code_a = f"ABS-A-{ts}"
    code_b = f"ABS-B-{ts}"

    conn = get_db()
    try:
        # Học sinh A: có đơn phép APPROVED
        conn.execute("""
            INSERT INTO students (school_id, student_code, full_name, current_points, is_active)
            VALUES (1, ?, 'Học Sinh A Có Phép', 100, 1)
        """, (code_a,))
        conn.execute("""
            INSERT INTO students (school_id, student_code, full_name, current_points, is_active)
            VALUES (1, ?, 'Học Sinh B Không Phép', 100, 1)
        """, (code_b,))
        stu_a_id = conn.execute("SELECT id FROM students WHERE student_code=?", (code_a,)).fetchone()["id"]
        stu_b_id = conn.execute("SELECT id FROM students WHERE student_code=?", (code_b,)).fetchone()["id"]

        # Tạo đơn nghỉ phép APPROVED cho học sinh A
        conn.execute("""
            INSERT INTO leave_requests (student_id, school_id, start_date, end_date, reason, status)
            VALUES (?, 1, ?, ?, 'Đã có phép duyệt trước', 'APPROVE')
        """, (stu_a_id, today_str, today_str))

        conn.commit()
    finally:
        conn.close()

    # Gọi API chốt vắng
    res = client.post("/api/v1/s/1/attendance/mark-absent-today", headers=auth_header)
    assert res.status_code == 200
    res_data = res.json()
    assert res_data["status"] == "success"

    conn = get_db()
    try:
        log_a = conn.execute("SELECT status FROM attendance_logs WHERE student_id=? AND date_only=?", (stu_a_id, today_str)).fetchone()
        assert log_a is not None
        assert log_a["status"] == "EXCUSED"

        stu_a = conn.execute("SELECT current_points FROM students WHERE id=?", (stu_a_id,)).fetchone()
        assert stu_a["current_points"] == 100  # Không bị trừ điểm

        log_b = conn.execute("SELECT status FROM attendance_logs WHERE student_id=? AND date_only=?", (stu_b_id, today_str)).fetchone()
        assert log_b is not None
        assert log_b["status"] == "ABSENT"

        stu_b = conn.execute("SELECT current_points FROM students WHERE id=?", (stu_b_id,)).fetchone()
        assert stu_b["current_points"] < 100  # Bị trừ điểm vắng

        # Gọi lần 2: Đã được ghi nhận nên không bị thêm bản ghi trùng lặp
        res_second = client.post("/api/v1/s/1/attendance/mark-absent-today", headers=auth_header)
        assert res_second.status_code == 200
        assert res_second.json()["marked_absent"] == 0
        assert res_second.json()["marked_excused"] == 0
    finally:
        conn.close()


def test_export_attendance_csv(client, auth_header):
    """
    Xuất báo cáo điểm danh CSV thành công, trả về đúng Content-Type và dữ liệu UTF-8.
    """
    today_str = datetime.now().strftime("%Y-%m-%d")
    res = client.get(f"/api/v1/s/1/attendance/export-csv?date={today_str}", headers=auth_header)
    assert res.status_code == 200
    assert "text/csv" in res.headers["content-type"]
    assert "attachment;" in res.headers.get("content-disposition", "")
    content = res.content.decode("utf-8-sig")
    assert "Ngay,Thoi Gian,Ma HS,Ho Ten,Lop,Trang Thai" in content or "Ngày,Thời Gian,Mã HS,Họ Và Tên,Lớp,Trạng Thái" in content


def test_violation_with_db_student_counts_as_present_and_saves_photo(client):
    """
    Khi học sinh dính lỗi (trễ ngoài giờ, sai trang phục, gửi status ABSENT/WARN),
    nếu học sinh có trong DB thì hệ thống VẪN TÍNH ĐÃ ĐIỂM DANH (CÓ MẶT/TRỄ),
    chụp lại ảnh lỗi và lưu lý do vi phạm, KHÔNG CÒN BỊ TÍNH VẮNG NỮA.
    """
    import base64
    ts = int(time.time() * 1000)
    secret = f"cam_vio_pres_{ts}"
    student_code = f"STU-VIO-{ts}"
    today_str = datetime.now().strftime("%Y-%m-%d")

    # 1 pixel transparent PNG in base64
    tiny_png_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="

    conn = get_db()
    try:
        conn.execute("""
            INSERT INTO camera_stations (school_id, name, secret_key, stream_type, status)
            VALUES (1, 'Trạm Test Lỗi Vẫn Có Mặt', ?, 'WEBCAM', 'ONLINE')
        """, (secret,))

        conn.execute("""
            INSERT INTO students (school_id, student_code, full_name, current_points, is_active)
            VALUES (1, ?, 'Học Sinh Dính Lỗi Vẫn Có Mặt', 100, 1)
        """, (student_code,))
        conn.commit()
    finally:
        conn.close()

    # Gửi điểm danh: đến muộn ngoài giờ lúc 20:30 (ngoài khung giờ 19:00), status gửi là WARN/ABSENT, có ảnh lỗi base64
    res = client.post("/api/v1/s/1/attendance/sync", json={
        "station_secret_key": secret,
        "student_code": student_code,
        "timestamp": f"{today_str}T20:30:00",
        "check_type": "FACE_AI",
        "status": "WARN",
        "uniform_status": "VIOLATION",
        "violation_reason": "Chưa quét thẻ & Sai trang phục",
        "proof_image_base64": tiny_png_b64
    })
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    # Học sinh phải được ghi nhận là ĐÃ ĐIỂM DANH, CÓ MẶT (status là LATE, không phải ABSENT)
    assert data["check_status"] == "LATE"
    assert data["is_present"] is True
    assert "proof_image_url" in data and data["proof_image_url"].startswith("/uploads/proofs/")

    # Kiểm tra trong database
    conn = get_db()
    try:
        log = conn.execute("""
            SELECT a.status, a.uniform_status, a.proof_image_url, a.violation_details
            FROM attendance_logs a
            JOIN students s ON a.student_id = s.id
            WHERE s.student_code=? AND a.date_only=?
        """, (student_code, today_str)).fetchone()

        assert log is not None
        assert log["status"] == "LATE"   # Có mặt (không phải ABSENT)
        assert log["uniform_status"] == "VIOLATION"
        assert log["proof_image_url"] is not None
        assert "Chưa quét thẻ" in log["violation_details"]
    finally:
        conn.close()


def test_student_previously_absent_updated_to_present_when_scanned_with_error(client, auth_header):
    """
    Nếu học sinh trước đó đã bị chốt ABSENT (vắng), khi học sinh xuất hiện trước camera
    (kể cả dính lỗi vi phạm), hệ thống cập nhật xóa vắng -> tính có mặt, hoàn điểm phạt vắng.
    """
    ts = int(time.time() * 1000)
    secret = f"cam_revert_{ts}"
    student_code = f"STU-REV-{ts}"
    today_str = datetime.now().strftime("%Y-%m-%d")

    conn = get_db()
    try:
        conn.execute("""
            INSERT INTO camera_stations (school_id, name, secret_key, stream_type, status)
            VALUES (1, 'Trạm Revert Vắng', ?, 'WEBCAM', 'ONLINE')
        """, (secret,))

        cur = conn.execute("""
            INSERT INTO students (school_id, student_code, full_name, current_points, is_active)
            VALUES (1, ?, 'Học Sinh Đổi Từ Vắng Sang Có Mặt', 95, 1)
        """, (student_code,))
        stu_id = cur.lastrowid

        # Giả lập học sinh đã bị chốt vắng trước đó
        conn.execute("""
            INSERT INTO attendance_logs (
                student_id, school_id, timestamp, date_only, check_type, status
            ) VALUES (?, 1, ?, ?, 'MANUAL', 'ABSENT')
        """, (stu_id, f"{today_str}T07:30:00", today_str))
        conn.commit()
    finally:
        conn.close()

    # Học sinh đến muộn và bị bắt lỗi
    res = client.post("/api/v1/s/1/attendance/sync", json={
        "station_secret_key": secret,
        "student_code": student_code,
        "timestamp": f"{today_str}T08:15:00",
        "check_type": "FACE_AI",
        "status": "LATE",
        "violation_reason": "Đi trễ có lỗi nhận diện"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["check_status"] == "LATE"

    # Kiểm tra database: Bản ghi đã chuyển từ ABSENT sang LATE
    conn = get_db()
    try:
        log = conn.execute("SELECT status, violation_details FROM attendance_logs WHERE student_id=? AND date_only=?", (stu_id, today_str)).fetchone()
        assert log["status"] == "LATE"
        assert "Đi trễ" in log["violation_details"]
    finally:
        conn.close()


def test_multi_session_attendance_rules(client, auth_header):
    """Kiểm tra phân định chính xác ca Sáng, Chiều, Tối và cập nhật quy định ngay lập tức."""
    ts = int(time.time() * 1000)
    secret = f"cam_sessions_{ts}"
    student_code = f"STU-SESS-{ts}"
    student_code_pm = f"STU-PM-{ts}"
    today_str = datetime.now().strftime("%Y-%m-%d")

    conn = get_db()
    try:
        rules = {
            "morning_enabled": True,
            "morning_name": "Chính khóa buổi sáng",
            "morning_from": "06:00",
            "morning_on_time": "07:15",
            "morning_late_until": "07:30",
            "morning_checkout": "11:30",
            "morning_uniform_check": True,
            "morning_late_deduct": 3,

            "afternoon_enabled": True,
            "afternoon_name": "Buổi chiều",
            "afternoon_from": "12:30",
            "afternoon_on_time": "13:15",
            "afternoon_late_until": "13:30",
            "afternoon_checkout": "17:00",
            "afternoon_uniform_check": True,
            "afternoon_late_deduct": 2,

            "evening_enabled": True,
            "evening_name": "Tự học buổi tối",
            "evening_from": "18:00",
            "evening_on_time": "18:45",
            "evening_late_until": "19:15",
            "evening_checkout": "21:30",
            "evening_uniform_check": False,
            "evening_late_deduct": 1,

            "late_deduct_points": 2,
            "violation_deduct_points": 3
        }
        conn.execute("UPDATE schools SET rules_config=? WHERE id=1", (json.dumps(rules),))
        conn.execute("""
            INSERT INTO camera_stations (school_id, name, secret_key, stream_type, status)
            VALUES (1, 'Trạm Đa Ca', ?, 'WEBCAM', 'ONLINE')
        """, (secret,))
        conn.execute("""
            INSERT INTO students (school_id, student_code, full_name, current_points, is_active)
            VALUES (1, ?, 'Học Sinh Đa Ca', 100, 1)
        """, (student_code,))
        conn.execute("""
            INSERT INTO students (school_id, student_code, full_name, current_points, is_active)
            VALUES (1, ?, 'Học Sinh Ca Tối', 100, 1)
        """, (student_code_pm,))
        conn.commit()
    finally:
        conn.close()

    # 1. Quét vào ca Chiều lúc 13:20 (Muộn hơn 13:15)
    res_afternoon = client.post("/api/v1/s/1/attendance/sync", json={
        "station_secret_key": secret,
        "student_code": student_code,
        "timestamp": f"{today_str}T13:20:00",
        "check_type": "FACE_AI",
        "direction": "IN"
    })
    assert res_afternoon.status_code == 200
    data_a = res_afternoon.json()
    assert data_a["check_status"] == "LATE"
    assert "buổi chiều" in (data_a.get("violation_details") or "").lower()

    # 2. Quét ra ca Chiều lúc 16:45 (Trước 17:00 -> Về sớm)
    res_checkout = client.post("/api/v1/s/1/attendance/sync", json={
        "station_secret_key": secret,
        "student_code": student_code,
        "timestamp": f"{today_str}T16:45:00",
        "check_type": "FACE_AI",
        "direction": "OUT"
    })
    assert res_checkout.status_code == 200
    data_out = res_checkout.json()
    assert "tan học buổi chiều" in (data_out.get("violation_details") or "").lower()

    # 3. Quét ca Tối lúc 19:00: Trễ (19:00 > 18:45) nhưng đồng phục gửi VIOLATION
    # Do evening_uniform_check = False, vi phạm đồng phục tự động đổi thành OK,
    # chỉ bị trừ 1 điểm trễ (theo evening_late_deduct = 1) thay vì bị trừ đồng phục!
    res_evening = client.post("/api/v1/s/1/attendance/sync", json={
        "station_secret_key": secret,
        "student_code": student_code_pm,
        "timestamp": f"{today_str}T19:00:00",
        "check_type": "FACE_AI",
        "direction": "IN",
        "status": "LATE",
        "uniform_status": "VIOLATION"
    })
    assert res_evening.status_code == 200
    data_e = res_evening.json()
    assert data_e["check_status"] == "LATE"
    assert data_e["uniform_status"] == "OK"  # Đã chuyển thành OK vì ca tối không bắt buộc
    assert data_e["points_deducted"] == 1    # Chỉ trừ 1 điểm theo evening_late_deduct

    # 4. Kiểm tra cập nhật cấu hình tức thì qua API PUT /api/v1/schools/1/config/rules
    new_rules = {
        "morning_enabled": True,
        "morning_name": "Sáng VIP",
        "morning_from": "06:00",
        "morning_on_time": "07:00",
        "morning_late_until": "07:30",
        "morning_checkout": "11:30",
        "morning_uniform_check": True,
        "morning_late_deduct": 5,

        "afternoon_enabled": True,
        "afternoon_name": "Chiều",
        "afternoon_from": "12:30",
        "afternoon_on_time": "13:15",
        "afternoon_late_until": "13:30",
        "afternoon_checkout": "17:00",
        "afternoon_uniform_check": True,
        "afternoon_late_deduct": 2,

        "evening_enabled": True,
        "evening_name": "Tối",
        "evening_from": "18:00",
        "evening_on_time": "18:45",
        "evening_late_until": "19:15",
        "evening_checkout": "21:30",
        "evening_uniform_check": True,  # Bật quét đồng phục buổi tối
        "evening_late_deduct": 4,       # Tăng trừ điểm tối lên 4

        "late_deduct_points": 5,
        "violation_deduct_points": 3,
        "uniform_check": True,
        "min_points_warning": 80,
        "absent_deduct_points": 5
    }
    update_res = client.put("/api/v1/schools/1/config/rules", json=new_rules, headers=auth_header)
    assert update_res.status_code == 200

    # Quét lại ca Tối với học sinh mới: bây giờ evening_uniform_check đã được bật, VIOLATION giữ nguyên!
    stu_new = f"STU-NEW-{ts}"
    conn = get_db()
    try:
        conn.execute("INSERT INTO students (school_id, student_code, full_name, current_points, is_active) VALUES (1, ?, 'HS Mới', 100, 1)", (stu_new,))
        conn.commit()
    finally:
        conn.close()

    res_evening2 = client.post("/api/v1/s/1/attendance/sync", json={
        "station_secret_key": secret,
        "student_code": stu_new,
        "timestamp": f"{today_str}T19:00:00",
        "check_type": "FACE_AI",
        "direction": "IN",
        "status": "LATE",
        "uniform_status": "VIOLATION"
    })
    assert res_evening2.status_code == 200
    data_e2 = res_evening2.json()
    assert data_e2["check_status"] == "LATE"
    assert data_e2["uniform_status"] == "VIOLATION"  # Giữ nguyên VIOLATION vì đã bật
    # Trừ: 4 (late) + 3 (uniform) = 7
    assert data_e2["points_deducted"] == 7


