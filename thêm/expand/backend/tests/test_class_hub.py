"""
tests/test_class_hub.py — Test Class Hub & Discussions for Student Role
"""
import secrets, pytest
from app.database import get_db
from app.core.security import generate_salt, hash_password

@pytest.fixture
def student_auth(client):
    """Tạo học sinh thử nghiệm với username ngẫu nhiên để tránh xung đột khóa"""
    suffix = secrets.token_hex(4)
    username = f"stu_{suffix}"
    invite_code = f"INV_{suffix.upper()}"
    class_id = 900 + secrets.randbelow(900)

    conn = get_db()
    try:
        salt = generate_salt()
        pw = hash_password("StudentPass@123", salt)

        # Đảm bảo trường 1 tồn tại
        conn.execute("INSERT OR IGNORE INTO schools (id, school_code, name, status) VALUES (1, 'thpt-test', 'THPT Test', 'ACTIVE')")

        # Tạo lớp học ngẫu nhiên
        conn.execute("""
            INSERT OR REPLACE INTO classes (id, school_id, name, grade_level, invite_code, is_active)
            VALUES (?, 1, '10A_TEST', 10, ?, 1)
        """, (class_id, invite_code))

        # Tạo tài khoản học sinh
        conn.execute("""
            INSERT INTO users (school_id, username, password_hash, salt, full_name, role, status)
            VALUES (1, ?, ?, ?, 'Nguyen Van A', 'STUDENT', 'ACTIVE')
        """, (username, pw, salt))
        conn.commit()
    finally:
        conn.close()

    res = client.post("/api/v1/auth/login", json={
        "username_or_phone": username,
        "password": "StudentPass@123"
    })
    assert res.status_code == 200, res.text
    token = res.json()["access_token"]
    return {
        "headers": {"Authorization": f"Bearer {token}"},
        "class_id": class_id,
        "invite_code": invite_code
    }


def test_my_class_flow(client, student_auth):
    headers = student_auth["headers"]
    class_id = student_auth["class_id"]
    invite_code = student_auth["invite_code"]

    # 1. Trước khi join lớp: has_class = False
    res = client.get("/api/v1/s/1/classes/my-class", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["has_class"] is False

    # 2. Join lớp với mã mời sai -> 404
    res_fail = client.post("/api/v1/s/1/classes/join", json={"invite_code": "WRONG_CODE_999"}, headers=headers)
    assert res_fail.status_code == 404

    # 3. Join lớp với mã mời đúng -> 200
    res_join = client.post("/api/v1/s/1/classes/join", json={"invite_code": invite_code}, headers=headers)
    assert res_join.status_code == 200
    assert res_join.json()["status"] == "success"
    assert res_join.json()["class_id"] == class_id

    # 4. Sau khi join: has_class = True, có đầy đủ metadata
    res_after = client.get("/api/v1/s/1/classes/my-class", headers=headers)
    assert res_after.status_code == 200
    after_data = res_after.json()
    assert after_data["has_class"] is True
    assert after_data["class"]["name"] == "10A_TEST"
    assert len(after_data["classmates"]) >= 1


def test_class_discussion_and_comments(client, student_auth):
    headers = student_auth["headers"]
    class_id = student_auth["class_id"]
    invite_code = student_auth["invite_code"]

    # 1. Đảm bảo học sinh đã vào lớp
    client.post("/api/v1/s/1/classes/join", json={"invite_code": invite_code}, headers=headers)

    # 2. Học sinh đăng bài thảo luận trong lớp
    res_post = client.post("/api/v1/posts", json={
        "school_id": 1,
        "class_id": class_id,
        "content": "Cho em hỏi về đề tài STEM năng lượng mặt trời tuần này?",
        "category": "QNA"
    }, headers=headers)
    assert res_post.status_code == 200
    post_data = res_post.json()["data"]
    post_id = post_data["id"]
    assert post_data["category"] == "QNA"
    assert post_data["classId"] == class_id

    # 3. Lấy danh sách thảo luận của lớp
    res_list = client.get(f"/api/v1/posts?school_id=1&class_id={class_id}", headers=headers)
    assert res_list.status_code == 200
    posts = res_list.json()["data"]
    assert any(p["id"] == post_id for p in posts)

    # 4. Thêm bình luận vào bài viết
    res_comment = client.post(f"/api/v1/posts/{post_id}/comments", json={
        "content": "Mình cũng đang làm phần mạch cảm biến ánh sáng này!"
    }, headers=headers)
    assert res_comment.status_code == 200
    comment_data = res_comment.json()["data"]
    assert comment_data["content"] == "Mình cũng đang làm phần mạch cảm biến ánh sáng này!"

    # 5. Lấy danh sách bình luận
    res_c_list = client.get(f"/api/v1/posts/{post_id}/comments", headers=headers)
    assert res_c_list.status_code == 200
    comments = res_c_list.json()["data"]
    assert len(comments) >= 1
    assert comments[0]["content"] == "Mình cũng đang làm phần mạch cảm biến ánh sáng này!"


def test_student_parent_invite_code_and_class_metadata(client, student_auth):
    headers = student_auth["headers"]
    class_id = student_auth["class_id"]
    invite_code = student_auth["invite_code"]

    # 1. Join class
    res_join = client.post("/api/v1/s/1/classes/join", json={"invite_code": invite_code}, headers=headers)
    assert res_join.status_code == 200

    # 2. Check student parent invite code endpoint returns class metadata
    res_code = client.get("/api/v1/s/1/students/me/parent-invite-code", headers=headers)
    assert res_code.status_code == 200
    data = res_code.json()
    assert data["status"] == "success"
    assert data["parent_invite_code"].startswith("PH-")
    assert data["class_name"] == "10A_TEST"
    assert data["grade_level"] == 10

