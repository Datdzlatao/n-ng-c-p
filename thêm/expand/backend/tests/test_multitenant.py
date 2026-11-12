"""
tests/test_multitenant.py — Multi-tenant security scope tests
"""

def test_admin_can_list_all_schools(client, auth_header):
    res = client.get("/api/v1/schools", headers=auth_header)
    assert res.status_code == 200
    assert isinstance(res.json(), list)

def test_camera_ping_wrong_secret(client):
    """Camera ping with wrong secret must be rejected."""
    res = client.post("/api/v1/s/1/cameras/1/ping?secret_key=WRONG_SECRET")
    assert res.status_code in (403, 404)  # 403 wrong secret, 404 camera not found

def test_attendance_sync_wrong_secret(client):
    """Attendance sync with wrong secret must be rejected."""
    res = client.post("/api/v1/s/1/attendance/sync", json={
        "station_secret_key": "WRONG_SECRET",
        "student_code": "HS01-0001",
        "timestamp": "2026-09-03T07:00:00",
        "check_type": "FACE_AI",
        "status": "ON_TIME"
    })
    assert res.status_code in (401, 403, 404)

def test_unauthenticated_cannot_access_school_data(client):
    res = client.get("/api/v1/s/1/attendance")
    assert res.status_code == 401
