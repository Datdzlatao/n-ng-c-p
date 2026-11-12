"""
tests/test_join_requests.py — End-to-end tests for School Join Requests & 1-Click BGH Approval
"""
import uuid
import pytest
from app.database import get_db
from app.core.security import generate_salt, hash_password, create_access_token_with_jti


@pytest.fixture
def headmaster_header(client):
    """Create and return an authenticated HEADMASTER for school #1."""
    conn = get_db()
    uid = uuid.uuid4().hex[:6]
    username = f"hm_{uid}"
    salt = generate_salt()
    pw = hash_password("Headmaster@2026!", salt)
    
    conn.execute("""
        INSERT INTO users (school_id, username, password_hash, salt, full_name, role, status, verified_status)
        VALUES (1, ?, ?, ?, 'Thầy Hiệu Trưởng Test', 'HEADMASTER', 'ACTIVE', 'VERIFIED')
    """, (username, pw, salt))
    hm_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.commit()
    conn.close()

    token, _ = create_access_token_with_jti({
        "sub": str(hm_id),
        "user_id": hm_id,
        "school_id": 1,
        "username": username,
        "role": "HEADMASTER",
        "full_name": "Thầy Hiệu Trưởng Test",
        "verified_status": "VERIFIED"
    })
    return {"Authorization": f"Bearer {token}"}


def test_join_request_lifecycle_approve(client, headmaster_header):
    """Test candidate registration without school, sending join request, BGH listing, and BGH 1-click approval."""
    uid = uuid.uuid4().hex[:6]
    candidate_username = f"cand_{uid}"
    
    # 1. Register candidate user without school
    reg_res = client.post("/api/v1/auth/register", json={
        "school_id": None,
        "username": candidate_username,
        "password": "CandidatePass123!",
        "full_name": f"Ứng Viên Thử Nghiệm {uid}",
        "phone": f"091{int(uuid.uuid4().int % 10000000):07d}",
        "role": "STUDENT"
    })
    assert reg_res.status_code == 200, reg_res.text
    token = reg_res.json()["access_token"]
    user_data = reg_res.json()["user"]
    candidate_id = user_data["id"]
    cand_header = {"Authorization": f"Bearer {token}"}

    # 2. Candidate checks /me without school_id -> must not crash
    me_res = client.get("/api/v1/auth/me", headers=cand_header)
    assert me_res.status_code == 200
    assert me_res.json()["user"]["username"] == candidate_username
    assert me_res.json()["user"]["school_id"] is None

    # 3. Candidate sends join request to School #1
    join_res = client.post("/api/v1/schools/1/join-request", headers=cand_header, json={})
    assert join_res.status_code == 200
    assert join_res.json()["status"] == "success"
    assert "access_token" in join_res.json()

    # Verify candidate user state in DB
    conn = get_db()
    u = conn.execute("SELECT * FROM users WHERE id=?", (candidate_id,)).fetchone()
    assert u["school_id"] == 1
    assert u["verified_status"] == "PENDING_REVIEW"
    assert u["verification_method"] == "JOIN_REQUEST"

    # Student row must exist but is_active = 0
    stu = conn.execute("SELECT * FROM students WHERE user_id=? AND school_id=1", (candidate_id,)).fetchone()
    assert stu is not None
    assert stu["is_active"] == 0
    conn.close()

    # 4. Headmaster views pending requests
    reqs_res = client.get("/api/v1/schools/1/requests", headers=headmaster_header)
    assert reqs_res.status_code == 200
    pending_list = reqs_res.json()["data"]
    matched = [r for r in pending_list if r["user"]["id"] == candidate_id]
    assert len(matched) == 1
    assert matched[0]["user"]["fullName"] == f"Ứng Viên Thử Nghiệm {uid}"

    # Also stats should count pending join requests
    stats_res = client.get("/api/v1/schools/1/stats", headers=headmaster_header)
    assert stats_res.status_code == 200
    assert stats_res.json()["pending_join_requests"] >= 1

    # 5. Headmaster 1-click approves
    action_res = client.post(f"/api/v1/schools/requests/{candidate_id}/action", headers=headmaster_header, json={
        "action": "approve"
    })
    assert action_res.status_code == 200
    assert action_res.json()["status"] == "success"

    # 6. Verify candidate is now ACTIVE, VERIFIED, and student is_active = 1
    conn = get_db()
    u_after = conn.execute("SELECT * FROM users WHERE id=?", (candidate_id,)).fetchone()
    assert u_after["verified_status"] == "VERIFIED"
    assert u_after["status"] == "ACTIVE"

    stu_after = conn.execute("SELECT * FROM students WHERE user_id=? AND school_id=1", (candidate_id,)).fetchone()
    assert stu_after["is_active"] == 1
    conn.close()


def test_join_request_lifecycle_reject(client, headmaster_header):
    """Test candidate registration, sending join request, and BGH rejection freeing school_id."""
    uid = uuid.uuid4().hex[:6]
    candidate_username = f"cand_rej_{uid}"
    
    reg_res = client.post("/api/v1/auth/register", json={
        "school_id": None,
        "username": candidate_username,
        "password": "CandidatePass123!",
        "full_name": f"Ứng Viên Từ Chối {uid}",
        "phone": f"092{int(uuid.uuid4().int % 10000000):07d}",
        "role": "STUDENT"
    })
    assert reg_res.status_code == 200
    token = reg_res.json()["access_token"]
    candidate_id = reg_res.json()["user"]["id"]
    cand_header = {"Authorization": f"Bearer {token}"}

    # Candidate joins School #1
    join_res = client.post("/api/v1/schools/1/join-request", headers=cand_header, json={})
    assert join_res.status_code == 200

    # Headmaster rejects the request
    action_res = client.post(f"/api/v1/schools/requests/{candidate_id}/action", headers=headmaster_header, json={
        "action": "reject",
        "rejectNote": "Không thuộc danh sách học sinh trúng tuyển"
    })
    assert action_res.status_code == 200

    # Verify user is freed (school_id is NULL, status UNVERIFIED)
    conn = get_db()
    u_after = conn.execute("SELECT * FROM users WHERE id=?", (candidate_id,)).fetchone()
    assert u_after["school_id"] is None
    assert u_after["verified_status"] == "UNVERIFIED"
    conn.close()
