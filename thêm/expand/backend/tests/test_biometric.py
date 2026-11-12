"""
tests/test_biometric.py — Multi-Angle Biometric Auto-Capture (160° eKYC) Tests
"""
import uuid
import base64

# Small valid 1x1 jpeg base64 for testing
TINY_JPEG_B64 = "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAP//////////////////////////////////////////////////////////////////////////////////////wgALCAABAAEBAREA/8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABPxA="

def test_biometric_session_init(client):
    res = client.post("/api/v1/auth/biometric/session-init", json={
        "school_id": 1,
        "student_code": "HS-BIO-001"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "session_id" in data
    assert data["required_sweep_angle"] in ("BIOMETRIC_SWEEP", "160_DEGREES", "BIOMETRIC_SWEEP_5_POSES")
    assert len(data["angle_targets"]) in (5, 6)

def test_upload_biometric_samples_requires_auth(client):
    res = client.post("/api/v1/auth/biometric/upload-samples", json={"school_id": 1})
    assert res.status_code == 401

def test_upload_biometric_samples_requires_consent(client, auth_header):
    res = client.post("/api/v1/auth/biometric/upload-samples", headers=auth_header, json={
        "school_id": 1,
        "student_code": "HS-BIO-NOCONSENT",
        "consent": {"accepted": False, "purpose": "FACE_ATTENDANCE"},
        "samples": [
            {
                "sample_index": 0,
                "angle_type": "CENTER",
                "yaw_angle": 0.0,
                "pitch_angle": 0.0,
                "image_base64": TINY_JPEG_B64,
                "quality_score": 0.95
            }
        ]
    })
    assert res.status_code == 422

def test_upload_biometric_samples_success(client, auth_header):
    code = f"HS-BIO-{uuid.uuid4().hex[:6]}"

    # Send multi-angle samples covering the 160° sweep
    samples_payload = [
        {"sample_index": 0, "angle_type": "FAR_LEFT",  "yaw_angle": -60.0, "pitch_angle": 0.0, "image_base64": TINY_JPEG_B64, "quality_score": 0.92},
        {"sample_index": 1, "angle_type": "MID_LEFT",  "yaw_angle": -30.0, "pitch_angle": 0.0, "image_base64": TINY_JPEG_B64, "quality_score": 0.94},
        {"sample_index": 2, "angle_type": "CENTER",    "yaw_angle":   0.0, "pitch_angle": 0.0, "image_base64": TINY_JPEG_B64, "quality_score": 0.98},
        {"sample_index": 3, "angle_type": "MID_RIGHT", "yaw_angle":  30.0, "pitch_angle": 0.0, "image_base64": TINY_JPEG_B64, "quality_score": 0.93},
        {"sample_index": 4, "angle_type": "FAR_RIGHT", "yaw_angle":  60.0, "pitch_angle": 0.0, "image_base64": TINY_JPEG_B64, "quality_score": 0.91},
        {"sample_index": 5, "angle_type": "TILT",      "yaw_angle":   0.0, "pitch_angle": 15.0, "image_base64": TINY_JPEG_B64, "quality_score": 0.95},
    ]

    res = client.post("/api/v1/auth/biometric/upload-samples", headers=auth_header, json={
        "school_id": 1,
        "student_code": code,
        "consent": {
            "accepted": True,
            "consent_version": "1.0",
            "purpose": "FACE_ATTENDANCE"
        },
        "samples": samples_payload
    })
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["samples_count"] == 6
    assert data["face_photo_url"] is not None
    student_id = data["student_id"]

    # Verify samples endpoint returns all 6 records (C-6 requires authentication)
    samples_res = client.get(f"/api/v1/s/1/students/{student_id}/samples", headers=auth_header)
    assert samples_res.status_code == 200
    samples_list = samples_res.json()
    assert len(samples_list) == 6
    assert any(s["angle_type"] == "FAR_LEFT" for s in samples_list)
    assert any(s["angle_type"] == "FAR_RIGHT" for s in samples_list)
    assert any(s["angle_type"] == "CENTER" for s in samples_list)


def test_upload_biometric_samples_verifies_user_account(client, auth_header):
    # Test that authenticated user uploading biometric face scan receives VERIFIED status
    res = client.post("/api/v1/auth/biometric/upload-samples", headers=auth_header, json={
        "school_id": 1,
        "student_code": "HS-TEST-VERIFY",
        "consent": {
            "accepted": True,
            "consent_version": "1.0",
            "purpose": "FACE_ATTENDANCE"
        },
        "samples": [
            {
                "sample_index": 0,
                "angle_type": "CENTER",
                "yaw_angle": 0.0,
                "pitch_angle": 0.0,
                "image_base64": TINY_JPEG_B64,
                "quality_score": 0.95
            }
        ]
    })
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["verified_status"] == "VERIFIED"

    # Check /auth/me returns VERIFIED
    me_res = client.get("/api/v1/auth/me", headers=auth_header)
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert me_data["user"]["verified_status"] == "VERIFIED"
    assert me_data["user"]["verification_method"] in ("FACE_SCAN", "MASTER_KEY")

