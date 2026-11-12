"""
backend/tests/test_cleanup_service.py — Unit tests for 8-day rolling retention cleanup service
"""
import os
import time
from datetime import datetime, timedelta
from pathlib import Path

from app.config import UPLOAD_DIR
from app.database import get_db
from app.services.cleanup_service import cleanup_old_attendance_data, get_storage_stats


def test_cleanup_old_attendance_data():
    """Kiểm tra dọn dẹp ảnh cũ hơn 8 ngày: ảnh cũ bị xóa, ảnh mới giữ nguyên."""
    conn = get_db()
    ts = int(time.time() * 1000)

    # 1. Tạo thư mục con trong uploads
    proof_dir = UPLOAD_DIR / "test_proofs"
    proof_dir.mkdir(parents=True, exist_ok=True)

    old_file = proof_dir / f"old_proof_{ts}.jpg"
    old_file.write_bytes(b"OLD_IMAGE_DATA_1234567890")

    new_file = proof_dir / f"new_proof_{ts}.jpg"
    new_file.write_bytes(b"NEW_IMAGE_DATA_1234567890")

    # Mốc thời gian: 10 ngày trước vs hôm nay
    today_str = datetime.now().strftime("%Y-%m-%d")
    old_date_str = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")

    # Tạo học sinh test nếu chưa có
    cur = conn.execute("""
        INSERT OR IGNORE INTO students (school_id, student_code, full_name, is_active)
        VALUES (1, 'TEST_CLEANUP_STUDENT', 'Học Sinh Test Cleanup', 1)
    """)
    conn.commit()
    student = conn.execute("SELECT id FROM students WHERE school_id=1 AND student_code='TEST_CLEANUP_STUDENT'").fetchone()
    student_id = student["id"]
    conn.execute("DELETE FROM attendance_logs WHERE student_id=?", (student_id,))
    conn.commit()

    # Thêm 1 bản ghi cũ (10 ngày trước) và 1 bản ghi mới (hôm nay)
    conn.execute("""
        INSERT INTO attendance_logs (student_id, school_id, timestamp, date_only, status, proof_image_url)
        VALUES (?, 1, ?, ?, 'ON_TIME', ?)
    """, (student_id, old_date_str + "T06:50:00", old_date_str, f"/uploads/test_proofs/{old_file.name}"))

    conn.execute("""
        INSERT INTO attendance_logs (student_id, school_id, timestamp, date_only, status, proof_image_url)
        VALUES (?, 1, ?, ?, 'ON_TIME', ?)
    """, (student_id, today_str + "T06:55:00", today_str, f"/uploads/test_proofs/{new_file.name}"))
    conn.commit()
    conn.close()

    # Xác minh cả 2 file vật lý tồn tại trước khi dọn dẹp
    assert old_file.exists()
    assert new_file.exists()

    # 2. Chạy dọn dẹp với retention 8 ngày (mặc định)
    result = cleanup_old_attendance_data(retention_days=8, delete_records=False)

    assert result["status"] == "success"
    assert result["deleted_photos"] >= 1
    assert result["freed_bytes"] > 0

    # 3. Kiểm tra kết quả:
    # - File cũ (10 ngày trước) phải bị xóa khỏi ổ đĩa
    assert not old_file.exists()
    # - File mới (hôm nay) phải còn nguyên vẹn
    assert new_file.exists()

    # - Database: bản ghi cũ bị xóa link ảnh (proof_image_url = NULL), bản ghi mới giữ nguyên
    conn = get_db()
    old_log = conn.execute(
        "SELECT proof_image_url FROM attendance_logs WHERE student_id=? AND date_only=?",
        (student_id, old_date_str)
    ).fetchone()
    assert old_log["proof_image_url"] is None

    new_log = conn.execute(
        "SELECT proof_image_url FROM attendance_logs WHERE student_id=? AND date_only=?",
        (student_id, today_str)
    ).fetchone()
    assert new_log["proof_image_url"] is not None
    conn.close()

    # Dọn dẹp file test mới
    if new_file.exists():
        new_file.unlink()


def test_storage_stats_and_platform_api(client, admin_token):
    """Kiểm tra API thống kê dung lượng và API kích hoạt dọn dẹp thủ công."""
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Gọi API xem thống kê storage
    res_stats = client.get("/api/v1/platform/maintenance/storage-stats", headers=headers)
    assert res_stats.status_code == 200
    data = res_stats.json()
    assert "total_size_mb" in data
    assert "retention_policy_days" in data
    assert data["retention_policy_days"] == 8

    # 2. Gọi API kích hoạt dọn dẹp
    res_cleanup = client.post(
        "/api/v1/platform/maintenance/cleanup",
        json={"retention_days": 8, "delete_records": False},
        headers=headers
    )
    assert res_cleanup.status_code == 200
    cleanup_res = res_cleanup.json()
    assert cleanup_res["status"] == "success"
    assert "freed_mb" in cleanup_res
