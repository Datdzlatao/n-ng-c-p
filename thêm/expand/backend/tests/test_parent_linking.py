"""
tests/test_parent_linking.py — Unit & Integration tests for Parent-Student Linking
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import get_db
from app.core.security import generate_salt, hash_password, create_access_token

client = TestClient(app)

@pytest.fixture(scope="module")
def parent_link_setup():
    """Setup school, students, parents, teacher for parent-linking tests."""
    conn = get_db()
    salt = generate_salt()
    pw = hash_password("Password@123!", salt)

    try:
        # Clean up
        conn.execute("DELETE FROM parent_student_links WHERE school_id = 1")
        conn.execute("DELETE FROM students WHERE student_code IN ('HS-PL-001', 'HS-PL-002', 'HS-PL-003')")
        conn.execute("DELETE FROM classes WHERE name = '10PL-TEST'")
        conn.execute("DELETE FROM users WHERE username IN ('parent_user1', 'parent_user2', 'teacher_pl', 'hm_pl', 'student_user1')")

        # 1. Create Teacher (GVCN)
        cur_t = conn.execute("""
            INSERT INTO users (school_id, username, password_hash, salt, full_name, role, status)
            VALUES (1, 'teacher_pl', ?, ?, 'GVCN Test PL', 'TEACHER', 'ACTIVE')
        """, (pw, salt))
        teacher_id = cur_t.lastrowid

        # 2. Create Headmaster
        cur_hm = conn.execute("""
            INSERT INTO users (school_id, username, password_hash, salt, full_name, role, status)
            VALUES (1, 'hm_pl', ?, ?, 'Hiệu Trưởng PL', 'HEADMASTER', 'ACTIVE')
        """, (pw, salt))
        hm_id = cur_hm.lastrowid

        # 3. Create Class
        cur_c = conn.execute("""
            INSERT INTO classes (school_id, name, grade_level, homeroom_teacher_id, academic_year, is_active)
            VALUES (1, '10PL-TEST', 10, ?, '2025-2026', 1)
        """, (teacher_id,))
        class_id = cur_c.lastrowid

        # 4. Create Students
        # Student 1: has dob & parent_phone
        cur_s1 = conn.execute("""
            INSERT INTO students (school_id, class_id, student_code, full_name, dob, parent_phone, is_active, is_deleted)
            VALUES (1, ?, 'HS-PL-001', 'Nguyễn Văn Con Một', '2010-05-15', '0911222333', 1, 0)
        """, (class_id,))
        s1_id = cur_s1.lastrowid

        # Student 2: has dob, no parent_phone
        cur_s2 = conn.execute("""
            INSERT INTO students (school_id, class_id, student_code, full_name, dob, parent_phone, is_active, is_deleted)
            VALUES (1, ?, 'HS-PL-002', 'Nguyễn Văn Con Hai', '2010-10-20', NULL, 1, 0)
        """, (class_id,))
        s2_id = cur_s2.lastrowid

        # Student 3: no dob, no parent_phone (raw student profile)
        cur_s3 = conn.execute("""
            INSERT INTO students (school_id, class_id, student_code, full_name, dob, parent_phone, is_active, is_deleted)
            VALUES (1, ?, 'HS-PL-003', 'Trần Thị Ba', NULL, NULL, 1, 0)
        """, (class_id,))
        s3_id = cur_s3.lastrowid

        # 5. Create Parent Users
        # Parent 1: phone = 0911222333 (matches Student 1)
        cur_p1 = conn.execute("""
            INSERT INTO users (school_id, username, password_hash, salt, full_name, role, phone, status, verified_status)
            VALUES (1, 'parent_user1', ?, ?, 'Bố Nguyễn Văn Một', 'PARENT', '0911222333', 'ACTIVE', 'VERIFIED')
        """, (pw, salt))
        p1_id = cur_p1.lastrowid

        # Parent 2: phone = 0988777666 (no match initially)
        cur_p2 = conn.execute("""
            INSERT INTO users (school_id, username, password_hash, salt, full_name, role, phone, status, verified_status)
            VALUES (1, 'parent_user2', ?, ?, 'Mẹ Trần Thị Hai', 'PARENT', '0988777666', 'ACTIVE', 'VERIFIED')
        """, (pw, salt))
        p2_id = cur_p2.lastrowid

        # 6. Create Student User for Student 1
        cur_stu_u = conn.execute("""
            INSERT INTO users (school_id, username, password_hash, salt, full_name, role, status, verified_status)
            VALUES (1, 'student_user1', ?, ?, 'Nguyễn Văn Con Một', 'STUDENT', 'ACTIVE', 'VERIFIED')
        """, (pw, salt))
        stu_u_id = cur_stu_u.lastrowid
        conn.execute("UPDATE students SET user_id=? WHERE id=?", (stu_u_id, s1_id))

        conn.commit()

        token_p1 = create_access_token({"user_id": p1_id, "username": "parent_user1", "role": "PARENT", "school_id": 1})
        token_p2 = create_access_token({"user_id": p2_id, "username": "parent_user2", "role": "PARENT", "school_id": 1})
        token_tch = create_access_token({"user_id": teacher_id, "username": "teacher_pl", "role": "TEACHER", "school_id": 1})
        token_hm = create_access_token({"user_id": hm_id, "username": "hm_pl", "role": "HEADMASTER", "school_id": 1})
        token_stu = create_access_token({"user_id": stu_u_id, "username": "student_user1", "role": "STUDENT", "school_id": 1})

        yield {
            "p1_id": p1_id,
            "p2_id": p2_id,
            "s1_id": s1_id,
            "s2_id": s2_id,
            "s3_id": s3_id,
            "stu_u_id": stu_u_id,
            "token_p1": token_p1,
            "token_p2": token_p2,
            "token_tch": token_tch,
            "token_hm": token_hm,
            "token_stu": token_stu,
        }
    finally:
        conn = get_db()
        conn.execute("DELETE FROM parent_student_links WHERE school_id = 1")
        conn.execute("DELETE FROM students WHERE student_code IN ('HS-PL-001', 'HS-PL-002', 'HS-PL-003')")
        conn.execute("DELETE FROM classes WHERE name = '10PL-TEST'")
        conn.execute("DELETE FROM users WHERE username IN ('parent_user1', 'parent_user2', 'teacher_pl', 'hm_pl', 'student_user1')")
        conn.commit()
        conn.close()


def test_parent_link_child_by_phone_auto_match(parent_link_setup):
    """Parent 1 links Student 1: phone matches automatically."""
    setup = parent_link_setup
    headers = {"Authorization": f"Bearer {setup['token_p1']}"}

    res = client.post("/api/v1/s/1/parents/link-child", json={
        "student_code": "HS-PL-001",
        "relation_name": "Bố"
    }, headers=headers)

    assert res.status_code == 200, res.text
    data = res.json()
    assert data["status"] == "success"
    assert data["student"]["student_code"] == "HS-PL-001"


def test_parent_duplicate_link_rejected(parent_link_setup):
    """Linking the same child again should return 400."""
    setup = parent_link_setup
    headers = {"Authorization": f"Bearer {setup['token_p1']}"}

    res = client.post("/api/v1/s/1/parents/link-child", json={
        "student_code": "HS-PL-001"
    }, headers=headers)

    assert res.status_code == 400
    assert "đã được liên kết" in res.json()["detail"]


def test_parent_link_child_by_dob(parent_link_setup):
    """Parent 2 links Student 2: phone does not match, but enters correct DOB."""
    setup = parent_link_setup
    headers = {"Authorization": f"Bearer {setup['token_p2']}"}

    # Wrong DOB first
    res_fail = client.post("/api/v1/s/1/parents/link-child", json={
        "student_code": "HS-PL-002",
        "verify_key": "2010-01-01"
    }, headers=headers)
    assert res_fail.status_code == 400
    assert "không khớp" in res_fail.json()["detail"]

    # Correct DOB (DD/MM/YYYY format test)
    res_ok = client.post("/api/v1/s/1/parents/link-child", json={
        "student_code": "HS-PL-002",
        "verify_key": "20/10/2010",
        "relation_name": "Mẹ"
    }, headers=headers)
    assert res_ok.status_code == 200, res_ok.text
    assert res_ok.json()["status"] == "success"


def test_parent_get_my_children(parent_link_setup):
    """Get my children should return linked students."""
    setup = parent_link_setup
    headers = {"Authorization": f"Bearer {setup['token_p1']}"}

    res = client.get("/api/v1/s/1/parents/my-children", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 1
    codes = [c["student_code"] for c in data]
    assert "HS-PL-001" in codes


def test_parent_unlink_child(parent_link_setup):
    """Parent can unlink a child."""
    setup = parent_link_setup
    headers = {"Authorization": f"Bearer {setup['token_p2']}"}

    res = client.delete(f"/api/v1/s/1/parents/unlink-child/{setup['s2_id']}", headers=headers)
    assert res.status_code == 200
    assert res.json()["status"] == "success"

    # Confirm list is now empty for Parent 2
    res_list = client.get("/api/v1/s/1/parents/my-children", headers=headers)
    assert res_list.status_code == 200
    codes = [c["student_code"] for c in res_list.json()]
    assert "HS-PL-002" not in codes


def test_teacher_assign_parent_to_student(parent_link_setup):
    """GVCN can assign a parent account to their student."""
    setup = parent_link_setup
    headers = {"Authorization": f"Bearer {setup['token_tch']}"}

    # Assign Parent 2 to Student 2
    res = client.post(f"/api/v1/s/1/students/{setup['s2_id']}/assign-parent", json={
        "parent_identifier": "parent_user2",
        "relation_name": "Mẹ"
    }, headers=headers)

    assert res.status_code == 200, res.text
    assert res.json()["status"] == "success"
    assert res.json()["parent"]["username"] == "parent_user2"

    # Verify student profile shows linked parents
    res_stu = client.get(f"/api/v1/s/1/students/{setup['s2_id']}", headers=headers)
    assert res_stu.status_code == 200
    stu_data = res_stu.json()
    assert len(stu_data["linked_parents"]) >= 1
    assert stu_data["linked_parents"][0]["parent_username"] == "parent_user2"


def test_teacher_unlink_parent_from_student(parent_link_setup):
    """GVCN / Headmaster can unlink a parent from student."""
    setup = parent_link_setup
    headers = {"Authorization": f"Bearer {setup['token_hm']}"}

    res = client.delete(f"/api/v1/s/1/students/{setup['s2_id']}/unlink-parent/{setup['p2_id']}", headers=headers)
    assert res.status_code == 200
    assert res.json()["status"] == "success"

    # Verify no linked parents
    res_stu = client.get(f"/api/v1/s/1/students/{setup['s2_id']}", headers=headers)
    assert len(res_stu.json()["linked_parents"]) == 0


def test_student_get_and_rotate_parent_invite_code(parent_link_setup):
    """Học sinh xem và đổi mã mời phụ huynh thành công."""
    setup = parent_link_setup
    headers = {"Authorization": f"Bearer {setup['token_stu']}"}

    # 1. Get invite code
    res = client.get("/api/v1/s/1/students/me/parent-invite-code", headers=headers)
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["status"] == "success"
    code1 = data["parent_invite_code"]
    assert code1.startswith("PH-")

    # 2. Rotate invite code
    res_rot = client.post("/api/v1/s/1/students/me/rotate-parent-invite-code", headers=headers)
    assert res_rot.status_code == 200
    code2 = res_rot.json()["parent_invite_code"]
    assert code2.startswith("PH-")
    assert code1 != code2


def test_parent_link_by_invite_code_1_touch(parent_link_setup):
    """Phụ huynh liên kết 1 chạm bằng Mã Mời Phụ Huynh do học sinh cấp."""
    setup = parent_link_setup
    stu_headers = {"Authorization": f"Bearer {setup['token_stu']}"}
    p_headers = {"Authorization": f"Bearer {setup['token_p2']}"}

    # Lấy mã mời hiện tại của học sinh 1
    res_stu = client.get("/api/v1/s/1/students/me/parent-invite-code", headers=stu_headers)
    invite_code = res_stu.json()["parent_invite_code"]

    # Phụ huynh 2 dùng mã mời này để liên kết 1 chạm
    res_link = client.post("/api/v1/s/1/parents/link-by-invite-code", json={
        "invite_code": invite_code,
        "relation_name": "Mẹ"
    }, headers=p_headers)

    assert res_link.status_code == 200, res_link.text
    data = res_link.json()
    assert data["status"] == "success"
    assert data["student"]["student_code"] == "HS-PL-001"
    assert "Mã mời phụ huynh" in data["match_reason"]


def test_parent_link_by_invalid_invite_code(parent_link_setup):
    """Mã mời phụ huynh không tồn tại bị từ chối 404."""
    setup = parent_link_setup
    headers = {"Authorization": f"Bearer {setup['token_p2']}"}

    res = client.post("/api/v1/s/1/parents/link-by-invite-code", json={
        "invite_code": "PH-INVALID999"
    }, headers=headers)

    assert res.status_code == 404
    assert "không hợp lệ" in res.json()["detail"]


def test_teacher_rotate_student_parent_invite_code(parent_link_setup):
    """GVCN hoặc BGH có thể cấp lại mã mời phụ huynh cho học sinh."""
    setup = parent_link_setup
    headers = {"Authorization": f"Bearer {setup['token_tch']}"}

    res = client.post(f"/api/v1/s/1/students/{setup['s1_id']}/rotate-parent-invite-code", headers=headers)
    assert res.status_code == 200
    assert res.json()["status"] == "success"
    assert res.json()["parent_invite_code"].startswith("PH-")
