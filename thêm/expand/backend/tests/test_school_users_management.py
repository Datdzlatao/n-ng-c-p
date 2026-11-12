"""
tests/test_school_users_management.py — Kiểm tra tính năng phân quyền & sửa thông tin người dùng của Hiệu trưởng
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import get_db
from app.core.security import generate_salt, hash_password, create_access_token

client = TestClient(app)


@pytest.fixture(scope="module")
def seed_school_users():
    """Tạo dữ liệu thử nghiệm trường #1 và #2 kèm các tài khoản Hiệu trưởng, Giáo viên, Giám thị, Phụ huynh, Học sinh."""
    conn = get_db()
    try:
        salt = generate_salt()
        pw = hash_password("Password123!", salt)

        # Trường 1
        conn.execute("""
            INSERT OR REPLACE INTO schools (id, school_code, name, province_city, status)
            VALUES (1, 'thpt-test-1', 'Trường THPT Test 1', 'Hà Nội', 'ACTIVE')
        """)
        # Trường 2 (để test cross-school)
        conn.execute("""
            INSERT OR REPLACE INTO schools (id, school_code, name, province_city, status)
            VALUES (2, 'thpt-test-2', 'Trường THPT Test 2', 'Hồ Chí Minh', 'ACTIVE')
        """)

        # Xóa dữ liệu test cũ nếu có theo thứ tự tránh lỗi khóa ngoại
        conn.execute("DELETE FROM students WHERE student_code='HS01-0001' OR school_id IN (1, 2) AND full_name LIKE 'Em Học Sinh%'")
        conn.execute("DELETE FROM users WHERE username LIKE 'test_%'")

        # User Hiệu trưởng trường 1
        conn.execute("""
            INSERT INTO users (school_id, username, email, phone, password_hash, salt, full_name, role, status, user_code)
            VALUES (1, 'test_principal1', 'principal1@test.edu.vn', '0988000001', ?, ?, 'Thầy Hiệu Trưởng 1', 'HEADMASTER', 'ACTIVE', 'HT01-0001')
        """, (pw, salt))
        principal1_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        # User Hiệu phó (cũng role HEADMASTER trường 1)
        conn.execute("""
            INSERT INTO users (school_id, username, email, phone, password_hash, salt, full_name, role, status, user_code)
            VALUES (1, 'test_principal2', 'principal2@test.edu.vn', '0988000002', ?, ?, 'Cô Phó Hiệu Trưởng', 'HEADMASTER', 'ACTIVE', 'HT01-0002')
        """, (pw, salt))
        principal2_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        # User Giáo viên trường 1
        conn.execute("""
            INSERT INTO users (school_id, username, email, phone, password_hash, salt, full_name, role, status, user_code)
            VALUES (1, 'test_teacher1', 'teacher1@test.edu.vn', '0988000003', ?, ?, 'Thầy Giáo Viên', 'TEACHER', 'ACTIVE', 'GV01-0001')
        """, (pw, salt))
        teacher1_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        # User Học sinh trường 1
        conn.execute("""
            INSERT INTO users (school_id, username, email, phone, password_hash, salt, full_name, role, status, student_code)
            VALUES (1, 'test_student1', 'student1@test.edu.vn', '0988000004', ?, ?, 'Em Học Sinh', 'STUDENT', 'ACTIVE', 'HS01-0001')
        """, (pw, salt))
        student1_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        # Bản ghi trong bảng students tương ứng
        conn.execute("""
            INSERT OR REPLACE INTO students (id, user_id, school_id, student_code, full_name, is_active)
            VALUES (9999, ?, 1, 'HS01-0001', 'Em Học Sinh', 1)
        """, (student1_id,))

        # User ở trường 2
        conn.execute("""
            INSERT INTO users (school_id, username, email, phone, password_hash, salt, full_name, role, status, user_code)
            VALUES (2, 'test_other_sch_user', 'other@test.edu.vn', '0988000099', ?, ?, 'Người Dùng Trường Khác', 'TEACHER', 'ACTIVE', 'GV02-0001')
        """, (pw, salt))
        other_user_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        conn.commit()
    finally:
        conn.close()

    # Tạo JWT Tokens
    principal_token = create_access_token({
        "sub": str(principal1_id),
        "user_id": principal1_id,
        "school_id": 1,
        "role": "HEADMASTER",
        "full_name": "Thầy Hiệu Trưởng 1",
    })

    teacher_token = create_access_token({
        "sub": str(teacher1_id),
        "user_id": teacher1_id,
        "school_id": 1,
        "role": "TEACHER",
        "full_name": "Thầy Giáo Viên",
    })

    yield {
        "principal_id": principal1_id,
        "principal2_id": principal2_id,
        "teacher_id": teacher1_id,
        "student_id": student1_id,
        "other_user_id": other_user_id,
        "principal_token": principal_token,
        "teacher_token": teacher_token,
    }

    # Teardown: dọn dẹp sạch dữ liệu test sau khi chạy xong
    conn_clean = get_db()
    try:
        conn_clean.execute("PRAGMA foreign_keys = OFF")
        conn_clean.execute("DELETE FROM students WHERE id = 9999")
        conn_clean.execute("DELETE FROM users WHERE username LIKE 'test_%'")
        conn_clean.execute("DELETE FROM schools WHERE id = 2")
        conn_clean.commit()
    finally:
        conn_clean.close()


def test_list_school_users(seed_school_users):
    """Hiệu trưởng xem danh sách thành viên trong trường."""
    data = seed_school_users
    headers = {"Authorization": f"Bearer {data['principal_token']}"}

    res = client.get("/api/v1/s/1/users", headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "success"
    assert body["total"] >= 4

    users = body["users"]
    teacher_row = next((u for u in users if u["id"] == data["teacher_id"]), None)
    assert teacher_row is not None
    assert teacher_row["is_subordinate"] is True
    assert teacher_row["can_edit"] is True

    principal2_row = next((u for u in users if u["id"] == data["principal2_id"]), None)
    assert principal2_row is not None
    assert principal2_row["is_subordinate"] is False
    assert principal2_row["can_edit"] is False


def test_update_subordinate_user_success(seed_school_users):
    """Hiệu trưởng chủ động cập nhật SĐT, email, họ tên của giáo viên cấp dưới thành công."""
    data = seed_school_users
    headers = {"Authorization": f"Bearer {data['principal_token']}"}

    payload = {
        "full_name": "Thầy Giáo Viên Cập Nhật",
        "phone": "0919999888",
        "email": "teacher.updated@test.edu.vn",
        "gender": "Nam",
        "dob": "1990-01-15",
    }
    res = client.put(f"/api/v1/s/1/users/{data['teacher_id']}", json=payload, headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "success"
    assert body["user"]["full_name"] == "Thầy Giáo Viên Cập Nhật"
    assert body["user"]["phone"] == "0919999888"
    assert body["user"]["email"] == "teacher.updated@test.edu.vn"

    # Kiểm tra lại qua GET
    detail = client.get(f"/api/v1/s/1/users/{data['teacher_id']}", headers=headers).json()
    assert detail["user"]["phone"] == "0919999888"
    assert detail["user"]["email"] == "teacher.updated@test.edu.vn"


def test_update_student_syncs_students_table(seed_school_users):
    """Cập nhật thông tin tài khoản học sinh tự động đồng bộ sang bảng students."""
    data = seed_school_users
    headers = {"Authorization": f"Bearer {data['principal_token']}"}

    payload = {
        "full_name": "Em Học Sinh Giỏi",
        "phone": "0977112233",
        "dob": "2008-09-02",
        "gender": "Nữ",
    }
    res = client.put(f"/api/v1/s/1/users/{data['student_id']}", json=payload, headers=headers)
    assert res.status_code == 200

    conn = get_db()
    stu = conn.execute("SELECT full_name, dob, gender FROM students WHERE user_id=?", (data["student_id"],)).fetchone()
    conn.close()
    assert stu["full_name"] == "Em Học Sinh Giỏi"
    assert stu["dob"] == "2008-09-02"
    assert stu["gender"] == "Nữ"


def test_principal_cannot_edit_peer_headmaster(seed_school_users):
    """Hiệu trưởng KHÔNG ĐƯỢC PHÉP sửa tài khoản Hiệu trưởng / BGH khác (403 Forbidden)."""
    data = seed_school_users
    headers = {"Authorization": f"Bearer {data['principal_token']}"}

    payload = {"full_name": "Thay Đổi Tên BGH Khác"}
    res = client.put(f"/api/v1/s/1/users/{data['principal2_id']}", json=payload, headers=headers)
    assert res.status_code == 403
    assert "vai trò cấp dưới" in res.json()["detail"]


def test_principal_cannot_promote_to_headmaster(seed_school_users):
    """Hiệu trưởng KHÔNG ĐƯỢC nâng quyền giáo viên lên HEADMASTER qua endpoint này (403 Forbidden)."""
    data = seed_school_users
    headers = {"Authorization": f"Bearer {data['principal_token']}"}

    payload = {"role": "HEADMASTER"}
    res = client.put(f"/api/v1/s/1/users/{data['teacher_id']}", json=payload, headers=headers)
    assert res.status_code == 403
    assert "chỉ có thể phân vai trò thuộc cấp dưới" in res.json()["detail"]


def test_duplicate_phone_rejected(seed_school_users):
    """Nếu số điện thoại bị trùng với tài khoản khác trong cùng trường -> Báo lỗi 409 Conflict."""
    data = seed_school_users
    headers = {"Authorization": f"Bearer {data['principal_token']}"}

    # Thử đổi SĐT giáo viên thành SĐT của Hiệu trưởng 1 (0988000001)
    payload = {"phone": "0988000001"}
    res = client.put(f"/api/v1/s/1/users/{data['teacher_id']}", json=payload, headers=headers)
    assert res.status_code == 409
    assert "đã được đăng ký" in res.json()["detail"]


def test_cross_school_access_blocked(seed_school_users):
    """Hiệu trưởng trường 1 KHÔNG THỂ truy cập hoặc sửa user trường 2 (403 Forbidden)."""
    data = seed_school_users
    headers = {"Authorization": f"Bearer {data['principal_token']}"}

    res = client.get(f"/api/v1/s/2/users", headers=headers)
    assert res.status_code == 403

    payload = {"full_name": "Hacker"}
    res2 = client.put(f"/api/v1/s/1/users/{data['other_user_id']}", json=payload, headers=headers)
    assert res2.status_code == 404  # Không tìm thấy user này trong trường 1


def test_principal_reset_subordinate_password(seed_school_users):
    """Hiệu trưởng chủ động đặt lại mật khẩu cho thành viên cấp dưới."""
    data = seed_school_users
    headers = {"Authorization": f"Bearer {data['principal_token']}"}

    res = client.post(
        f"/api/v1/s/1/users/{data['teacher_id']}/reset-password",
        json={"new_password": "NewSecretPass2026!"},
        headers=headers
    )
    assert res.status_code == 200
    assert res.json()["status"] == "success"

    # Thử đăng nhập bằng mật khẩu mới
    login_res = client.post("/api/v1/auth/login", json={
        "school_id": 1,
        "username_or_phone": "test_teacher1",
        "password": "NewSecretPass2026!"
    })
    assert login_res.status_code == 200
    assert "access_token" in login_res.json()


def test_principal_toggle_user_status(seed_school_users):
    """Hiệu trưởng tạm khóa và mở khóa tài khoản cấp dưới."""
    data = seed_school_users
    headers = {"Authorization": f"Bearer {data['principal_token']}"}

    # Khóa
    res1 = client.post(
        f"/api/v1/s/1/users/{data['teacher_id']}/toggle-status",
        json={"status": "SUSPENDED"},
        headers=headers
    )
    assert res1.status_code == 200
    assert res1.json()["new_status"] == "SUSPENDED"

    # Mở khóa
    res2 = client.post(
        f"/api/v1/s/1/users/{data['teacher_id']}/toggle-status",
        json={"status": "ACTIVE"},
        headers=headers
    )
    assert res2.status_code == 200
    assert res2.json()["new_status"] == "ACTIVE"


def test_teacher_cannot_access_user_management(seed_school_users):
    """Giáo viên không có quyền truy cập endpoint quản lý nhân sự của Hiệu trưởng (403 Forbidden)."""
    data = seed_school_users
    headers = {"Authorization": f"Bearer {data['teacher_token']}"}

    res = client.get("/api/v1/s/1/users", headers=headers)
    assert res.status_code == 403
