"""
tests/test_teacher_role.py — Unit & Integration tests for TEACHER role features
"""
import pytest
from app.database import get_db
from app.core.security import generate_salt, hash_password, create_access_token

@pytest.fixture(scope="module")
def teacher_setup():
    """Seed test teachers and classes in school 1 once for the module."""
    conn = get_db()
    salt = generate_salt()
    pw = hash_password("Teacher@123!", salt)

    try:
        # Clean up existing test data in reverse FK dependency order
        conn.execute("DELETE FROM attendance_logs WHERE student_id IN (SELECT id FROM students WHERE student_code IN ('HS-TCH-001', 'HS-TCH-002'))")
        conn.execute("DELETE FROM students WHERE student_code IN ('HS-TCH-001', 'HS-TCH-002')")
        conn.execute("DELETE FROM classes WHERE name IN ('10A1-TEST', '10A2-TEST', '10A3-TEST')")
        conn.execute("DELETE FROM users WHERE username IN ('teacher_a', 'teacher_b', 'teacher_c')")

        # 1. Create Teacher A (GVCN 10A1), Teacher B (GVCN 10A2), Teacher C (Chưa phân công)
        cur_a = conn.execute("""
            INSERT INTO users (school_id, username, password_hash, salt, full_name, role, status)
            VALUES (1, 'teacher_a', ?, ?, 'Cô Nguyễn Thị Hoa', 'TEACHER', 'ACTIVE')
        """, (pw, salt))
        teacher_a_id = cur_a.lastrowid

        cur_b = conn.execute("""
            INSERT INTO users (school_id, username, password_hash, salt, full_name, role, status)
            VALUES (1, 'teacher_b', ?, ?, 'Thầy Trần Văn Nam', 'TEACHER', 'ACTIVE')
        """, (pw, salt))
        teacher_b_id = cur_b.lastrowid

        cur_c = conn.execute("""
            INSERT INTO users (school_id, username, password_hash, salt, full_name, role, status)
            VALUES (1, 'teacher_c', ?, ?, 'Thầy Lê Văn Cường', 'TEACHER', 'ACTIVE')
        """, (pw, salt))
        teacher_c_id = cur_c.lastrowid

        # 2. Create Classes
        cur_c1 = conn.execute("""
            INSERT INTO classes (school_id, name, grade_level, homeroom_teacher_id, academic_year, is_active)
            VALUES (1, '10A1-TEST', 10, ?, '2025-2026', 1)
        """, (teacher_a_id,))
        class_1_id = cur_c1.lastrowid

        cur_c2 = conn.execute("""
            INSERT INTO classes (school_id, name, grade_level, homeroom_teacher_id, academic_year, is_active)
            VALUES (1, '10A2-TEST', 10, ?, '2025-2026', 1)
        """, (teacher_b_id,))
        class_2_id = cur_c2.lastrowid

        # 3. Create Students in Class 1
        cur_s1 = conn.execute("""
            INSERT INTO students (school_id, class_id, student_code, full_name, parent_phone, is_active, is_deleted)
            VALUES (1, ?, 'HS-TCH-001', 'Lê Văn An', '0988111222', 1, 0)
        """, (class_1_id,))
        s1_id = cur_s1.lastrowid

        cur_s2 = conn.execute("""
            INSERT INTO students (school_id, class_id, student_code, full_name, parent_phone, is_active, is_deleted)
            VALUES (1, ?, 'HS-TCH-002', 'Trần Thị Bình', '0988333444', 1, 0)
        """, (class_1_id,))
        s2_id = cur_s2.lastrowid

        conn.commit()
    finally:
        conn.close()

    token_a = create_access_token({
        "sub": str(teacher_a_id),
        "user_id": teacher_a_id,
        "school_id": 1,
        "role": "TEACHER",
        "username": "teacher_a",
        "full_name": "Cô Nguyễn Thị Hoa"
    })

    token_b = create_access_token({
        "sub": str(teacher_b_id),
        "user_id": teacher_b_id,
        "school_id": 1,
        "role": "TEACHER",
        "username": "teacher_b",
        "full_name": "Thầy Trần Văn Nam"
    })

    token_c = create_access_token({
        "sub": str(teacher_c_id),
        "user_id": teacher_c_id,
        "school_id": 1,
        "role": "TEACHER",
        "username": "teacher_c",
        "full_name": "Thầy Lê Văn Cường"
    })

    hm_token = create_access_token({
        "sub": "1",
        "user_id": 1,
        "school_id": 1,
        "role": "HEADMASTER",
        "username": "hieutruong",
        "full_name": "Thầy Hiệu Trưởng"
    })

    return {
        "teacher_a_token": token_a,
        "teacher_b_token": token_b,
        "teacher_c_token": token_c,
        "teacher_c_id": teacher_c_id,
        "hm_token": hm_token,
        "class_1_id": class_1_id,
        "class_2_id": class_2_id,
        "student_1_id": s1_id,
        "student_2_id": s2_id,
    }


def test_get_my_homeroom_as_teacher(client, teacher_setup):
    headers = {"Authorization": f"Bearer {teacher_setup['teacher_a_token']}"}
    res = client.get("/api/v1/s/1/classes/my-homeroom", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["has_class"] is True
    assert data["class"]["name"] == "10A1-TEST"
    assert data["stats"]["total_students"] >= 2
    assert "attendance_rate" in data["stats"]
    assert "pending_leaves_count" in data["stats"]


def test_get_roster_today_as_teacher(client, teacher_setup):
    headers = {"Authorization": f"Bearer {teacher_setup['teacher_a_token']}"}
    cid = teacher_setup["class_1_id"]
    res = client.get(f"/api/v1/s/1/classes/{cid}/roster-today", headers=headers)
    assert res.status_code == 200
    roster = res.json()
    assert len(roster) >= 2
    names = [s["full_name"] for s in roster]
    assert "Lê Văn An" in names
    assert "Trần Thị Bình" in names


def test_classroom_roll_call_as_teacher(client, teacher_setup):
    headers = {"Authorization": f"Bearer {teacher_setup['teacher_a_token']}"}
    cid = teacher_setup["class_1_id"]
    s1 = teacher_setup["student_1_id"]
    s2 = teacher_setup["student_2_id"]

    res = client.post(f"/api/v1/s/1/classes/{cid}/roll-call", headers=headers, json={
        "items": [
            {"student_id": s1, "status": "ON_TIME", "uniform_status": "OK"},
            {"student_id": s2, "status": "LATE", "uniform_status": "VIOLATION", "note": "Đi trễ 10 phút"}
        ]
    })
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["updated_count"] == 2

    # Verify that roster-today reflects the update
    res_roster = client.get(f"/api/v1/s/1/classes/{cid}/roster-today", headers=headers)
    assert res_roster.status_code == 200
    roster = res_roster.json()
    s1_item = next(item for item in roster if item["student_id"] == s1)
    s2_item = next(item for item in roster if item["student_id"] == s2)
    assert s1_item["status"] == "ON_TIME"
    assert s2_item["status"] == "LATE"
    assert s2_item["uniform_status"] == "VIOLATION"


def test_teacher_forbidden_from_other_class(client, teacher_setup):
    """Teacher A cannot view or roll-call Teacher B's class."""
    headers_a = {"Authorization": f"Bearer {teacher_setup['teacher_a_token']}"}
    cid_2 = teacher_setup["class_2_id"]

    # Teacher A trying to access Class 2
    res_get = client.get(f"/api/v1/s/1/classes/{cid_2}/roster-today", headers=headers_a)
    assert res_get.status_code == 403

    res_post = client.post(f"/api/v1/s/1/classes/{cid_2}/roll-call", headers=headers_a, json={
        "items": [{"student_id": 999, "status": "ON_TIME"}]
    })
    assert res_post.status_code == 403


def test_notify_absent_parents(client, teacher_setup):
    headers = {"Authorization": f"Bearer {teacher_setup['teacher_a_token']}"}
    cid = teacher_setup["class_1_id"]

    # Mark student 1 ON_TIME, student 2 ABSENT
    s1 = teacher_setup["student_1_id"]
    s2 = teacher_setup["student_2_id"]
    client.post(f"/api/v1/s/1/classes/{cid}/roll-call", headers=headers, json={
        "items": [
            {"student_id": s1, "status": "ON_TIME"},
            {"student_id": s2, "status": "ABSENT"}
        ]
    })

    res = client.post(f"/api/v1/s/1/classes/{cid}/notify-absent-parents", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["notified_count"] == 1
    assert data["notified_parents"][0]["student_id"] == s2
    assert data["notified_parents"][0]["parent_phone"] == "0988333444"


def test_unassigned_teacher_homeroom(client, teacher_setup):
    """Giáo viên chưa được bổ nhiệm làm GVCN sẽ có has_class=False và is_homeroom=False."""
    headers_c = {"Authorization": f"Bearer {teacher_setup['teacher_c_token']}"}
    res = client.get("/api/v1/s/1/classes/my-homeroom", headers=headers_c)
    assert res.status_code == 200
    data = res.json()
    assert data["has_class"] is False
    assert data["is_homeroom"] is False
    assert "chưa được Ban Giám Hiệu bổ nhiệm" in data["message"]


def test_unassigned_teacher_auth_me(client, teacher_setup):
    """GET /auth/me phản ánh đúng trạng thái chưa là GVCN."""
    headers_c = {"Authorization": f"Bearer {teacher_setup['teacher_c_token']}"}
    res = client.get("/api/v1/auth/me", headers=headers_c)
    assert res.status_code == 200
    user = res.json()["user"]
    assert user["role"] == "TEACHER"
    assert user["is_homeroom_teacher"] is False
    assert user["homeroom_class_id"] is None
    assert user["class_name"] is None


def test_headmaster_assign_and_unassign_homeroom_teacher(client, teacher_setup):
    """Hiệu trưởng tạo lớp không gán GVCN -> Bổ nhiệm GVCN -> Hủy bổ nhiệm GVCN sạch sẽ."""
    hm_headers = {"Authorization": f"Bearer {teacher_setup['hm_token']}"}
    teacher_c_id = teacher_setup["teacher_c_id"]

    # 1. Tạo lớp mới không phân công GVCN
    res_create = client.post("/api/v1/s/1/classes", headers=hm_headers, json={
        "name": "10A3-TEST",
        "grade_level": 10,
        "homeroom_teacher_id": None
    })
    assert res_create.status_code == 200
    
    # Lấy class_id vừa tạo
    res_list = client.get("/api/v1/s/1/classes", headers=hm_headers)
    cls3 = next(c for c in res_list.json() if c["name"] == "10A3-TEST")
    cid3 = cls3["id"]
    assert cls3["homeroom_teacher_id"] is None
    assert cls3["teacher_name"] is None

    # 2. Hiệu trưởng bổ nhiệm Teacher C làm GVCN
    res_asg = client.put(f"/api/v1/s/1/classes/{cid3}/assign-teacher", headers=hm_headers, json={
        "teacher_id": teacher_c_id
    })
    assert res_asg.status_code == 200
    assert res_asg.json()["teacher_id"] == teacher_c_id

    # Teacher C giờ đã là GVCN lớp 10A3-TEST
    headers_c = {"Authorization": f"Bearer {teacher_setup['teacher_c_token']}"}
    res_me = client.get("/api/v1/auth/me", headers=headers_c)
    assert res_me.json()["user"]["is_homeroom_teacher"] is True
    assert res_me.json()["user"]["homeroom_class_name"] == "10A3-TEST"

    # 3. Hiệu trưởng hủy bổ nhiệm GVCN cho lớp này (teacher_id = None)
    res_unasg = client.put(f"/api/v1/s/1/classes/{cid3}/assign-teacher", headers=hm_headers, json={
        "teacher_id": None
    })
    assert res_unasg.status_code == 200
    assert res_unasg.json()["teacher_id"] is None

    # Kiểm tra Teacher C đã được giải phóng khỏi lớp chủ nhiệm
    res_me_after = client.get("/api/v1/auth/me", headers=headers_c)
    assert res_me_after.json()["user"]["is_homeroom_teacher"] is False
    assert res_me_after.json()["user"]["homeroom_class_name"] is None
    assert res_me_after.json()["user"]["class_name"] is None


def test_unassigned_teacher_can_view_students(client, teacher_setup):
    """Giáo viên chưa có lớp chủ nhiệm vẫn có thể xem danh sách học sinh trường thay vì bị rỗng."""
    headers_c = {"Authorization": f"Bearer {teacher_setup['teacher_c_token']}"}
    res = client.get("/api/v1/s/1/students", headers=headers_c)
    assert res.status_code == 200
    students = res.json()
    assert len(students) >= 2
