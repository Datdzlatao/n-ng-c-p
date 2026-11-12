import uuid

def test_compliance_audit_log(client, auth_header):
    # School #1 audit log
    res = client.get("/api/v1/s/1/compliance/audit-log", headers=auth_header)
    assert res.status_code == 200
    data = res.json()
    assert "total_students" in data
    assert "with_face_data" in data
    assert "consented" in data
    assert "compliance_rate" in data

def test_record_and_get_consent(client, auth_header):
    code = f"HS-CMP-{uuid.uuid4().hex[:6]}"
    # First create a test student in school 1 if not exists
    student_res = client.post("/api/v1/s/1/students", headers=auth_header, json={
        "full_name": "Nguyễn Văn Test Compliance",
        "student_code": code,
        "parent_phone": "0988776655"
    })
    assert student_res.status_code in (200, 201)
    student_id = student_res.json().get("student_id")
    assert student_id is not None

    # Record consent
    consent_res = client.post(f"/api/v1/s/1/compliance/consent/{student_id}", headers=auth_header, json={
        "consent_status": "CONSENTED",
        "purpose": "FACE_ATTENDANCE"
    })
    assert consent_res.status_code == 200
    assert consent_res.json()["status"] == "success"

    # Get consent history
    hist_res = client.get(f"/api/v1/s/1/compliance/consent/{student_id}", headers=auth_header)
    assert hist_res.status_code == 200
    records = hist_res.json()["records"]
    assert len(records) >= 1
    assert records[0]["consent_status"] == "CONSENTED"

def test_right_to_erasure_biometric_data(client, auth_header):
    # Create test student with photo URL
    code = f"HS-ERASE-{uuid.uuid4().hex[:6]}"
    student_res = client.post("/api/v1/s/1/students", headers=auth_header, json={
        "full_name": "Trần Thị Xóa Sinh Trắc",
        "student_code": code,
        "parent_phone": "0911223344"
    })
    student_id = student_res.json().get("student_id")
    assert student_id is not None

    # Erase biometric data (Right to Erasure)
    erase_res = client.delete(f"/api/v1/s/1/compliance/biometric/{student_id}", headers=auth_header)
    assert erase_res.status_code == 200
    assert "Đã xóa toàn bộ dữ liệu sinh trắc học" in erase_res.json()["message"]

    # Student still exists (soft delete not applied, only biometric erased)
    stu_check = client.get(f"/api/v1/s/1/students/{student_id}", headers=auth_header)
    assert stu_check.status_code == 200
    assert stu_check.json().get("face_approved") == "REVOKED"
