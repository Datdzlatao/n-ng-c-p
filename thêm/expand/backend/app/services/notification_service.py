"""
app/services/notification_service.py — Async Notification Dispatcher
Chay nhu FastAPI BackgroundTasks — khong block API response.

Ho tro:
  - Zalo ZNS (SMS)
  - Firebase FCM (Push)
  - In-process queue (khong can Redis)
"""
import logging
import asyncio
import urllib.request
import json
from datetime import datetime
from typing import Optional

from app.config import ZALO_OA_TOKEN, FCM_SERVER_KEY

log = logging.getLogger("stem.notification")


async def send_zalo_zns(
    phone: str,
    message: str,
    template_id: str = ""
) -> bool:
    """Gui tin nhan Zalo ZNS toi phu huynh. Tra ve True neu thanh cong."""
    if not ZALO_OA_TOKEN or not phone:
        log.debug(f"[ZNS] Bo qua: token chua cau hinh hoac khong co SDT. phone={phone}")
        return False

    def _do_send():
        try:
            url = "https://business.openapi.zalo.me/message/template"
            payload = json.dumps({
                "phone":       phone.lstrip("0").replace("+84", ""),
                "template_id": template_id,
                "template_data": {"message": message},
            }).encode("utf-8")
            req = urllib.request.Request(url, data=payload, method="POST")
            req.add_header("access_token", ZALO_OA_TOKEN)
            req.add_header("Content-Type", "application/json")
            with urllib.request.urlopen(req, timeout=5) as resp:
                result = json.loads(resp.read())
                return result.get("error", -1) == 0
        except Exception as e:
            log.warning(f"[ZNS] Loi gui tin ZNS toi {phone}: {e}")
            return False

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _do_send)


async def send_fcm_push(
    device_tokens: list,
    title: str,
    body: str,
    data: Optional[dict] = None
) -> bool:
    """Gui Firebase FCM push notification."""
    if not FCM_SERVER_KEY or not device_tokens:
        log.debug("[FCM] Bo qua: FCM_SERVER_KEY chua cau hinh.")
        return False

    def _do_send():
        try:
            url = "https://fcm.googleapis.com/fcm/send"
            payload = json.dumps({
                "registration_ids": device_tokens,
                "notification": {"title": title, "body": body},
                "data": data or {},
            }).encode("utf-8")
            req = urllib.request.Request(url, data=payload, method="POST")
            req.add_header("Authorization", f"key={FCM_SERVER_KEY}")
            req.add_header("Content-Type", "application/json")
            with urllib.request.urlopen(req, timeout=5) as resp:
                result = json.loads(resp.read())
                return result.get("success", 0) > 0
        except Exception as e:
            log.warning(f"[FCM] Loi gui FCM: {e}")
            return False

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _do_send)


async def notify_parent_attendance(
    school_id: int,
    student_name: str,
    parent_phone: str,
    check_time: str,
    status: str = "ON_TIME",
    direction: str = "IN"
) -> None:
    """Gui thong bao diem danh toi phu huynh qua Zalo ZNS."""
    dir_label = "vào cổng trường" if direction.upper() == "IN" else "ra khỏi cổng trường"
    status_text = {"ON_TIME": "đúng giờ", "LATE": "trễ/vi phạm", "ABSENT": "vắng mặt"}.get(status, status)
    message = f"[STEM] Học sinh {student_name} đã {dir_label} lúc {check_time} ({status_text})."
    await send_zalo_zns(parent_phone, message)
    log.info(f"[NOTIFY] Da gui thong bao toi {parent_phone} cho hoc sinh {student_name} ({direction} - {status})")
