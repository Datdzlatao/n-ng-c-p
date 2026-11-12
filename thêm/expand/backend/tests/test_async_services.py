"""
tests/test_async_services.py — Notification and Report Service tests
"""
import pytest
import os
from app.services.notification_service import send_zalo_zns, send_fcm_push, notify_parent_attendance
from app.services.report_service import generate_attendance_csv

@pytest.mark.anyio
async def test_notification_service_handles_unconfigured_gracefully():
    # When tokens not configured, should return False without raising exceptions
    res_zns = await send_zalo_zns("0987654321", "Test message")
    assert res_zns is False

    res_fcm = await send_fcm_push(["fake_device_token"], "Title", "Body")
    assert res_fcm is False

    # notify_parent_attendance should not raise
    await notify_parent_attendance(school_id=1, student_name="Test Student", parent_phone="0987654321", check_time="07:05")

@pytest.mark.anyio
async def test_generate_attendance_csv():
    # Should generate CSV file and return valid file path
    csv_url = await generate_attendance_csv(school_id=1)
    assert csv_url.startswith("/uploads/reports/")
    assert csv_url.endswith(".csv")
