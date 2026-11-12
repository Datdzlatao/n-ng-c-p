"""
tests/test_camera_occlusion.py — Test Camera Occlusion / Tampering Alert (>=60%)
"""
import pytest
from app.database import get_db
from app.core.security import generate_salt, hash_password


@pytest.fixture
def admin_auth(client):
    """Tạo tài khoản Hiệu trưởng / Admin để test nhận cảnh báo che khuất"""
    conn = get_db()
    try:
        salt = generate_salt()
        pw = hash_password("AdminPass@123", salt)
        conn.execute("INSERT OR IGNORE INTO schools (id, school_code, name, status) VALUES (1, 'thpt-test', 'THPT Test', 'ACTIVE')")
        conn.execute("""
            INSERT OR REPLACE INTO camera_stations (id, school_id, camera_num, name, location, stream_type, stream_url, secret_key, status)
            VALUES (1, 1, 1, 'Camera Cổng Chính', 'Cổng Số 1', 'WEBCAM', '0', 'test-secret-cam-1', 'ONLINE')
        """)
        conn.execute("""
            INSERT OR REPLACE INTO users (id, school_id, username, password_hash, salt, full_name, role, status)
            VALUES (9991, 1, 'headmaster_occ_test', ?, ?, 'Thầy Hiệu Trưởng', 'HEADMASTER', 'ACTIVE')
        """, (pw, salt))
        conn.execute("""
            INSERT OR REPLACE INTO users (id, school_id, username, password_hash, salt, full_name, role, status)
            VALUES (9992, 1, 'inspector_occ_test', ?, ?, 'Thầy Giám Thị', 'INSPECTOR', 'ACTIVE')
        """, (pw, salt))
        conn.commit()
    finally:
        conn.close()

    res_hm = client.post("/api/v1/auth/login", json={"username_or_phone": "headmaster_occ_test", "password": "AdminPass@123"})
    assert res_hm.status_code == 200
    token_hm = res_hm.json()["access_token"]

    res_ins = client.post("/api/v1/auth/login", json={"username_or_phone": "inspector_occ_test", "password": "AdminPass@123"})
    assert res_ins.status_code == 200
    token_ins = res_ins.json()["access_token"]

    return {
        "hm_headers": {"Authorization": f"Bearer {token_hm}"},
        "ins_headers": {"Authorization": f"Bearer {token_ins}"}
    }


def test_camera_occlusion_alert_flow(client, admin_auth):
    hm_headers = admin_auth["hm_headers"]
    ins_headers = admin_auth["ins_headers"]

    # 1. Edge gửi cảnh báo camera 1 bị che khuất 68%
    alert_payload = {
        "secret_key": "test-secret-cam-1",
        "occlusion_percent": 68.5,
        "details": "Vật cản che 68% khung hình camera"
    }
    res = client.post("/api/v1/s/1/cameras/1/occlusion-alert", json=alert_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["occlusion_percent"] == 68.5

    # 2. Kiểm tra Hiệu trưởng nhận được thông báo trong feed
    res_notif_hm = client.get("/api/v1/notifications", headers=hm_headers)
    assert res_notif_hm.status_code == 200
    notifs_hm = res_notif_hm.json()["data"]
    occ_notif_hm = [n for n in notifs_hm if "Camera Bị Che Khuất" in n["title"]]
    assert len(occ_notif_hm) >= 1
    assert "Camera Cổng Chính" in occ_notif_hm[0]["content"]

    # 3. Kiểm tra Giám thị cũng nhận được thông báo trong feed
    res_notif_ins = client.get("/api/v1/notifications", headers=ins_headers)
    assert res_notif_ins.status_code == 200
    notifs_ins = res_notif_ins.json()["data"]
    occ_notif_ins = [n for n in notifs_ins if "Camera Bị Che Khuất" in n["title"]]
    assert len(occ_notif_ins) >= 1
    assert "Camera Cổng Chính" in occ_notif_ins[0]["content"]


def test_test_occlusion_alert_endpoint(client, admin_auth):
    hm_headers = admin_auth["hm_headers"]
    # Kiểm thử endpoint test của Hiệu trưởng / Giám thị
    res = client.post("/api/v1/s/1/cameras/1/test-occlusion-alert", headers=hm_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["occlusion_percent"] == 75.0


def test_toggle_occlusion_check_and_bypass(client, admin_auth):
    hm_headers = admin_auth["hm_headers"]

    # 1. Tắt tính năng cảnh báo che khuất trên camera 1
    res_toggle_off = client.post("/api/v1/s/1/cameras/1/toggle-occlusion", json={"enabled": False}, headers=hm_headers)
    assert res_toggle_off.status_code == 200
    assert res_toggle_off.json()["occlusion_check"] is False

    # 2. Gửi cảnh báo che khuất -> Server phải bỏ qua (status == ignored)
    alert_payload = {
        "secret_key": "test-secret-cam-1",
        "occlusion_percent": 80.0,
        "details": "Che camera khi tính năng đang tắt"
    }
    res_alert = client.post("/api/v1/s/1/cameras/1/occlusion-alert", json=alert_payload)
    assert res_alert.status_code == 200
    assert res_alert.json()["status"] == "ignored"

    # 3. Bật lại tính năng cảnh báo che khuất
    res_toggle_on = client.post("/api/v1/s/1/cameras/1/toggle-occlusion", json={"enabled": True}, headers=hm_headers)
    assert res_toggle_on.status_code == 200
    assert res_toggle_on.json()["occlusion_check"] is True

    # 4. Gửi lại cảnh báo -> Server tiếp nhận thành công
    res_alert2 = client.post("/api/v1/s/1/cameras/1/occlusion-alert", json=alert_payload)
    assert res_alert2.status_code == 200
    assert res_alert2.json()["status"] == "success"

