"""
tests/test_honor_board.py — Test Flame Streaks & Honor Board API
"""
import pytest
from app.database import get_db
from app.routers.honor import get_flame_tier, _calculate_streak

def test_flame_tier_mapping():
    # 0 ngày: Chưa có lửa
    t0 = get_flame_tier(0)
    assert t0["tier"] == "NONE"

    # 1 ngày: Lửa Mầm
    t1 = get_flame_tier(1)
    assert t1["tier"] == "BLUE"
    assert t1["days_left"] == 2

    # 3 ngày: Lửa Xanh Lá (Green)
    t3 = get_flame_tier(3)
    assert t3["tier"] == "GREEN"
    assert t3["color"] == "green"
    assert t3["next_target"] == 7

    # 7 ngày: Lửa Cam (Orange)
    t7 = get_flame_tier(7)
    assert t7["tier"] == "ORANGE"
    assert t7["color"] == "orange"
    assert t7["next_target"] == 14

    # 14 ngày: Lửa Đỏ (Red)
    t14 = get_flame_tier(14)
    assert t14["tier"] == "RED"
    assert t14["color"] == "red"
    assert t14["next_target"] == 30

    # 30 ngày: Lửa Tím (Purple)
    t30 = get_flame_tier(30)
    assert t30["tier"] == "PURPLE"
    assert t30["color"] == "purple"
    assert t30["next_target"] is None


def test_honor_board_api(client):
    res = client.get("/api/v1/s/1/honor")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "streak_leaders" in data["data"]
    assert "points_leaders" in data["data"]
    assert "class_rankings" in data["data"]


def test_whole_day_validity_streak():
    """
    Kiểm tra tiêu chuẩn nguyên cả 1 ngày hợp lệ:
    - Ngày 2026-09-01: Đúng giờ, không vi phạm -> Hợp lệ.
    - Ngày 2026-09-02: Đúng giờ, nhưng có 1 log vi phạm đồng phục -> CẢ NGÀY BỊ HUỶ.
    - Ngày 2026-09-03: Đúng giờ, không vi phạm -> Hợp lệ (chuỗi là 1, không được nối với ngày 1).
    """
    conn = get_db()
    try:
        stu_id = 9999
        school_id = 1
        conn.execute("INSERT OR IGNORE INTO students (id, school_id, student_code, full_name, is_active) VALUES (?, ?, 'TEST_9999', 'Test Student', 1)", (stu_id, school_id))
        conn.execute("DELETE FROM attendance_logs WHERE student_id=?", (stu_id,))

        # Ngày 1: Hợp lệ
        conn.execute("""
            INSERT INTO attendance_logs (student_id, school_id, timestamp, date_only, status, uniform_status)
            VALUES (?, ?, '2026-09-01 07:00:00', '2026-09-01', 'ON_TIME', 'OK')
        """, (stu_id, school_id))

        # Ngày 2: Sáng đúng giờ nhưng tiết 2 vi phạm đồng phục
        conn.execute("""
            INSERT INTO attendance_logs (student_id, school_id, timestamp, date_only, status, uniform_status)
            VALUES (?, ?, '2026-09-02 07:00:00', '2026-09-02', 'ON_TIME', 'OK')
        """, (stu_id, school_id))
        conn.execute("""
            INSERT INTO attendance_logs (student_id, school_id, timestamp, date_only, status, uniform_status)
            VALUES (?, ?, '2026-09-02 08:30:00', '2026-09-02', 'ON_TIME', 'VIOLATION')
        """, (stu_id, school_id))

        # Ngày 3: Hợp lệ
        conn.execute("""
            INSERT INTO attendance_logs (student_id, school_id, timestamp, date_only, status, uniform_status)
            VALUES (?, ?, '2026-09-03 07:00:00', '2026-09-03', 'ON_TIME', 'OK')
        """, (stu_id, school_id))
        conn.commit()

        streak = _calculate_streak(conn, stu_id, school_id)
        # Chuỗi dừng lại ở ngày 2 (vi phạm), nên streak hiện tại chỉ là 1 ngày (ngày 3)!
        assert streak == 1

        # Dọn dẹp
        conn.execute("DELETE FROM attendance_logs WHERE student_id=?", (stu_id,))
        conn.execute("DELETE FROM students WHERE id=?", (stu_id,))
        conn.commit()
    finally:
        conn.close()
