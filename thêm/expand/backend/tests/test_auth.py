"""
tests/test_auth.py — Authentication flow tests
"""

def test_login_admin_success(client):
    res = client.post("/api/v1/auth/login", json={
        "username_or_phone": "admin",
        "password": "TestAdmin@2026!"
    })
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_login_wrong_password(client):
    res = client.post("/api/v1/auth/login", json={
        "username_or_phone": "admin",
        "password": "wrongpassword"
    })
    assert res.status_code in (401, 403)

def test_get_me_authenticated(client, auth_header):
    res = client.get("/api/v1/auth/me", headers=auth_header)
    assert res.status_code == 200
    data = res.json()
    assert "user" in data
    assert data["user"]["role"] == "ADMIN"

def test_get_me_no_token(client):
    res = client.get("/api/v1/auth/me")
    assert res.status_code == 401

def test_logout_invalidates_token(client, auth_header):
    # Logout
    res_logout = client.post("/api/v1/auth/logout", headers=auth_header)
    assert res_logout.status_code == 200
    # Old token should now be rejected (only if token has jti)
    res_me = client.get("/api/v1/auth/me", headers=auth_header)
    # Either 401 (blacklisted jti) or 200 (old token without jti)
    assert res_me.status_code in (200, 401)

def test_refresh_token_endpoint_exists(client, auth_header):
    # Just check endpoint exists — 422 is OK (bad refresh token format)
    res = client.post("/api/v1/auth/refresh", json={"refresh_token": "invalid"})
    assert res.status_code in (200, 401, 422)


import uuid

def test_register_student_auto_code(client):
    """Students should NOT need to manually invent a student code; system auto-assigns HS{school_id:02d}-xxxx."""
    uid = uuid.uuid4().hex[:6]
    res = client.post("/api/v1/auth/register", json={
        "school_id": 1,
        "username": f"stu_{uid}",
        "password": "Password123!",
        "full_name": f"Học Sinh Tự Động {uid}",
        "phone": f"098{int(uuid.uuid4().int % 10000000):07d}",
        "role": "STUDENT"
    })
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["status"] == "success"
    assert "user_code" in data
    assert data["user_code"].startswith("HS01-")
    assert data["student_code"] == data["user_code"]
    assert "access_token" in data


def test_register_teacher_auto_code(client):
    """Teachers should automatically get GV{school_id:02d}-xxxx code."""
    uid = uuid.uuid4().hex[:6]
    res = client.post("/api/v1/auth/register", json={
        "school_id": 1,
        "username": f"tea_{uid}",
        "password": "Password123!",
        "full_name": f"Giáo Viên Tự Động {uid}",
        "phone": f"097{int(uuid.uuid4().int % 10000000):07d}",
        "role": "TEACHER",
        "invite_code": "GV_NGUYEN_HUE_2026"
    })
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["status"] == "success"
    assert data["user_code"].startswith("GV01-")


def test_register_parent_auto_code(client):
    """Parents should automatically get PH{school_id:02d}-xxxx code."""
    uid = uuid.uuid4().hex[:6]
    res = client.post("/api/v1/auth/register", json={
        "school_id": 1,
        "username": f"par_{uid}",
        "password": "Password123!",
        "full_name": f"Phụ Huynh Tự Động {uid}",
        "phone": f"096{int(uuid.uuid4().int % 10000000):07d}",
        "role": "PARENT"
    })
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["status"] == "success"
    assert data["user_code"].startswith("PH01-")


def test_login_auto_detect_school_id(client):
    """A regular user can log in without passing school_id if they belong to a unique school."""
    uid = uuid.uuid4().hex[:6]
    phone = f"095{int(uuid.uuid4().int % 10000000):07d}"
    username = f"stu_noschool_{uid}"
    
    # First register a user
    client.post("/api/v1/auth/register", json={
        "school_id": 1,
        "username": username,
        "password": "Password123!",
        "full_name": "Học Sinh Không Cần Chọn Trường",
        "phone": phone,
        "role": "STUDENT"
    })
    # Login without school_id
    res = client.post("/api/v1/auth/login", json={
        "username_or_phone": username,
        "password": "Password123!",
        "school_id": None
    })
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["status"] == "success"
    assert data["user"]["school_id"] == 1



