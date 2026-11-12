#!/usr/bin/env python3
"""
Full Verification Script for Staff & Face Attendance Workflow Integration
Tests:
1. Staff Repository CRUD & Attendance Logging
2. FaceVisionService Client & Diagnostics
3. FastMCP Resources & Tools for Staff Management
4. AI Agent Intent Resolution & Tool Calling for Staff Operations
5. FastAPI REST Endpoints via TestClient
6. APScheduler Daily Morning Briefing Staff Integration
"""

import sys
import json
import asyncio
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from starlette.testclient import TestClient

print("=" * 80)
print("👤 SMART FARM STAFF & FACE ATTENDANCE WORKFLOW - FULL VERIFICATION TEST")
print("=" * 80)


async def test_staff_workflow():
    # -------------------------------------------------------------
    # 1. TEST STAFF REPOSITORY
    # -------------------------------------------------------------
    print("\n[STEP 1] Testing Staff Repository...")
    from app.db.repositories.staff import StaffRepository

    repo = StaffRepository()
    all_staff = repo.list_all()
    print(f"  ✅ Initial Staff count: {len(all_staff)} ({[s['id'] for s in all_staff]})")
    assert len(all_staff) >= 4, "Should have initial staff members"

    # Register new staff
    created = repo.create_staff(
        staff_id="NV99",
        name="Nguyễn Văn Test",
        role="Thực tập sinh",
        pen_id="PEN-B01",
        phone="0999888777",
    )
    print(f"  ✅ Created new staff: {created['id']} - {created['name']} ({created['role']})")
    assert repo.get_by_id("NV99") is not None

    # Log attendance
    att_log = repo.log_attendance(
        staff_id="NV99",
        staff_name="Nguyễn Văn Test",
        pen_id="PEN-B01",
        status="present",
        confidence=0.97,
        is_real=True,
        note="Điểm danh thử nghiệm",
    )
    print(f"  ✅ Logged attendance for NV99: status={att_log['status']}, confidence={att_log['confidence']}")

    today_logs = repo.get_today_attendance()
    print(f"  ✅ Today's attendance logs count: {len(today_logs)}")
    assert len(today_logs) >= 1

    # -------------------------------------------------------------
    # 2. TEST FACE VISION SERVICE
    # -------------------------------------------------------------
    print("\n[STEP 2] Testing FaceVisionService Client...")
    from app.services.face_service import face_service

    health = face_service.check_health()
    print(f"  ✅ Vision Service Health Check: {health}")
    assert "online" in health

    # -------------------------------------------------------------
    # 3. TEST FASTMCP RESOURCES & TOOLS
    # -------------------------------------------------------------
    print("\n[STEP 3] Testing FastMCP Server (Staff Resources & Tools)...")
    from app.mcp.mcp_server import (
        mcp,
        get_today_staff_attendance,
        get_all_staff_resource,
        get_staff_list,
        check_in_staff_face,
        get_today_attendance_summary,
    )

    tools = [t.name for t in mcp._tool_manager.list_tools()]
    print(f"  ✅ FastMCP registered tools: {tools}")
    assert "get_staff_list" in tools
    assert "check_in_staff_face" in tools
    assert "get_today_attendance_summary" in tools

    # Test Resource
    staff_res_str = get_today_staff_attendance()
    print(f"  ✅ Resource 'resource://staff/today' output length: {len(staff_res_str)} chars")

    # Test Tools
    staff_list_str = get_staff_list()
    print(f"  ✅ Tool 'get_staff_list' returned {len(json.loads(staff_list_str))} staff")

    checkin_res = check_in_staff_face(staff_id="NV02", pen_id="PEN-ISO-01", note="Vào ca khu cách ly")
    print(f"  ✅ Tool 'check_in_staff_face' result: {checkin_res}")
    assert "THÀNH CÔNG" in checkin_res

    summary_str = get_today_attendance_summary()
    summary_data = json.loads(summary_str)
    print(f"  ✅ Tool 'get_today_attendance_summary': present={summary_data['present_count']}, absent={summary_data['absent_count']}")

    # -------------------------------------------------------------
    # 4. TEST AI AGENT NLP & MCP TOOL CALLING
    # -------------------------------------------------------------
    print("\n[STEP 4] Testing Smart Farm AI Agent with Staff Queries...")
    from app.services.agent_service import agent_service

    # Staff checkin via NLP
    agent_res = await agent_service.chat("Điểm danh cho nhân viên NV03 tại chuồng A2")
    print(f"  ✅ Agent NLP Check-in Reply:\n    {agent_res['reply']}")
    assert len(agent_res['tool_calls']) > 0 or "NV03" in agent_res['reply'] or "thành công" in agent_res['reply'].lower()

    # Staff list query via NLP
    agent_res2 = await agent_service.chat("Danh sách nhân sự trang trại có những ai")
    print(f"  ✅ Agent NLP Staff List Reply:\n    {agent_res2['reply']}")

    # -------------------------------------------------------------
    # 5. TEST FASTAPI REST ENDPOINTS
    # -------------------------------------------------------------
    print("\n[STEP 5] Testing FastAPI REST Endpoints via TestClient...")
    from app.main import app

    client = TestClient(app)

    # List staff
    r_list = client.get("/api/staff")
    assert r_list.status_code == 200
    print(f"  ✅ GET /api/staff -> 200 OK ({len(r_list.json())} staff)")

    # Checkin endpoint
    r_checkin = client.post("/api/staff/checkin", json={
        "staff_id": "NV01",
        "pen_id": "123",
        "note": "Điểm danh qua TestClient"
    })
    assert r_checkin.status_code == 200
    print(f"  ✅ POST /api/staff/checkin -> 200 OK ({r_checkin.json()['message']})")

    # Attendance logs
    r_att = client.get("/api/staff/attendance")
    assert r_att.status_code == 200
    print(f"  ✅ GET /api/staff/attendance -> 200 OK ({len(r_att.json())} records)")

    # Vision status
    r_vis = client.get("/api/staff/vision-status")
    assert r_vis.status_code == 200
    print(f"  ✅ GET /api/staff/vision-status -> 200 OK ({r_vis.json()})")

    # Dedicated Full-Body Uniform Inspection Endpoint
    import base64
    with open("standalone_ai_engine/test_sample.jpg", "rb") as f:
        sample_b64 = base64.b64encode(f.read()).decode("utf-8")
    r_uni = client.post("/api/uniform/scan", json={
        "image_base64": sample_b64,
        "weekday": 1,
        "return_annotated": True
    })
    assert r_uni.status_code == 200
    uni_data = r_uni.json()
    assert uni_data.get("person_detected") is True
    print(f"  ✅ POST /api/uniform/scan -> 200 OK (Uniform: {uni_data['uniform']['status']} - {uni_data['uniform']['message']})")

    # Real-Time Live AI Scan Endpoint (/api/staff/live-scan)
    with open("standalone_ai_engine/known_faces/HS01_Nguyen_Van_A_camera.jpg", "rb") as f:
        known_face_b64 = base64.b64encode(f.read()).decode("utf-8")
    r_live = client.post("/api/staff/live-scan", json={
        "image_base64": known_face_b64,
        "pen_id": "PEN-A01",
        "check_type": "check_in",
        "weekday": -1,
        "auto_checkin": True
    })
    assert r_live.status_code == 200
    live_data = r_live.json()
    assert live_data.get("status") == "success"
    print(f"  ✅ POST /api/staff/live-scan -> 200 OK (Live FaceID: {len(live_data['faces'])} faces, Checked In: {live_data['checked_in']})")

    # -------------------------------------------------------------
    # 6. TEST SCHEDULER BRIEFING WITH STAFF INTEGRATION
    # -------------------------------------------------------------
    print("\n[STEP 6] Testing Morning Briefing with Staff Attendance...")
    from app.background.scheduler import run_morning_briefing

    briefing = await run_morning_briefing()
    print(f"  ✅ Morning Briefing Payload: staff_present_count={briefing.get('staff_present_count')}")
    print(f"  ✅ Briefing Content:\n{briefing.get('content')}")
    assert "staff_present_count" in briefing

    print("\n" + "=" * 80)
    print("🎉 ALL 6 VERIFICATION STEPS PASSED SUCCESSFULLY!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_staff_workflow())
