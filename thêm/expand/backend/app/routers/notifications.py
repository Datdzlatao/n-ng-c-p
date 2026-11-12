"""
app/routers/notifications.py — User Notifications API
Provides real-time role-based notification feed for Web and Mobile clients.
"""
import logging
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException

from app.database import get_db
from app.core.deps import get_current_user

router = APIRouter(prefix="/api/v1/notifications", tags=["Notifications"])
log    = logging.getLogger("stem.notifications")


@router.get("")
async def get_notifications(current: dict = Depends(get_current_user)):
    """Return contextual in-app notifications matching user role and school."""
    user_id = current.get("user_id")
    school_id = current.get("school_id")
    role = current.get("role", "STUDENT")

    notifications = []
    conn = get_db()
    try:
        now_str = datetime.now().strftime("%H:%M %d/%m/%Y")

        # 1. School Admin / Headmaster / Inspector alerts
        if role in ("HEADMASTER", "ADMIN", "PLATFORM_ADMIN", "INSPECTOR") and school_id:
            pending_reqs = conn.execute(
                "SELECT COUNT(*) FROM users WHERE school_id=? AND verified_status='PENDING_REVIEW'",
                (school_id,)
            ).fetchone()[0]
            if pending_reqs > 0:
                notifications.append({
                    "id": 1,
                    "title": "Yêu cầu gia nhập trường mới",
                    "content": f"Có {pending_reqs} tài khoản đang chờ Ban Giám Hiệu xét duyệt gia nhập trường.",
                    "category": "APPROVALS",
                    "isRead": False,
                    "createdAt": now_str
                })

            pending_disputes = conn.execute(
                "SELECT COUNT(*) FROM disputes WHERE school_id=? AND status='PENDING'",
                (school_id,)
            ).fetchone()[0]
            if pending_disputes > 0:
                notifications.append({
                    "id": 2,
                    "title": "Khiếu nại nề nếp cần xử lý",
                    "content": f"Có {pending_disputes} khiếu nại nề nếp đang chờ đối chiếu và xử lý.",
                    "category": "APPROVALS",
                    "isRead": False,
                    "createdAt": now_str
                })

        # 2. Teacher alerts
        elif role == "TEACHER" and school_id:
            pending_leaves = conn.execute("""
                SELECT COUNT(l.id) FROM leave_requests l
                JOIN students s ON l.student_id = s.id
                JOIN classes c ON s.class_id = c.id
                WHERE l.school_id=? AND l.status='PENDING'
                  AND c.homeroom_teacher_id=?
            """, (school_id, user_id)).fetchone()[0]
            if pending_leaves > 0:
                notifications.append({
                    "id": 3,
                    "title": "Đơn xin nghỉ phép lớp phụ trách",
                    "content": f"Có {pending_leaves} đơn xin nghỉ phép từ phụ huynh/học sinh cần GVCN phê duyệt.",
                    "category": "CLASS_UPDATES",
                    "isRead": False,
                    "createdAt": now_str
                })

        # 3. Cảnh Báo An Ninh Cổng Trường (Phát Hiện Người Lạ & Camera Bị Che Khuất)
        if school_id and role in ("HEADMASTER", "ADMIN", "PLATFORM_ADMIN", "INSPECTOR", "TEACHER"):
            try:
                today_str = datetime.now().strftime("%Y-%m-%d")
                alerts = conn.execute("""
                    SELECT sa.id, sa.alert_type, sa.title, sa.description, sa.direction, sa.proof_image_url, sa.timestamp,
                           COALESCE(cs.name, 'Trạm Camera') as station_name
                    FROM security_alerts sa
                    LEFT JOIN camera_stations cs ON sa.camera_station_id = cs.id
                    WHERE sa.school_id=? AND sa.alert_type IN ('STRANGER', 'CAMERA_OCCLUSION') AND sa.date_only=?
                    ORDER BY sa.id DESC LIMIT 10
                """, (school_id, today_str)).fetchall()

                for a in alerts:
                    a_dict = dict(a)
                    time_part = a_dict.get("timestamp", "").replace("T", " ")[:16]
                    if a_dict.get("alert_type") == "CAMERA_OCCLUSION":
                        notif_title = "🚨 Cảnh Báo: Camera Bị Che Khuất"
                        notif_content = f"{time_part} — {a_dict['description']}"
                    else:
                        dir_tag = "Lượt Ra Về" if a_dict.get("direction") == "OUT" else "Lượt Vào Cổng"
                        notif_title = "🚨 Cảnh Báo An Ninh: Phát Hiện Người Lạ"
                        notif_content = f"{time_part} — Tại {a_dict['station_name']} ({dir_tag}): {a_dict['description']}"

                    notifications.append({
                        "id": f"sec_{a_dict['id']}",
                        "title": notif_title,
                        "content": notif_content,
                        "category": "SECURITY",
                        "proof_image_url": a_dict.get("proof_image_url"),
                        "isRead": False,
                        "createdAt": time_part
                    })
            except Exception as _e:
                log.warning(f"Lỗi truy vấn security_alerts: {_e}")

        # 4. Student / Parent notifications (Đơn xin nghỉ phép, khiếu nại - không spam thông báo ra vào cổng)
        elif role in ("STUDENT", "PARENT") and school_id:
            pass

        return {"status": "success", "data": notifications}
    finally:
        conn.close()


@router.put("/{notification_id}/read")
async def mark_notification_read(notification_id: int, current: dict = Depends(get_current_user)):
    return {"status": "success", "message": f"Đã đánh dấu thông báo #{notification_id} đã đọc."}


@router.put("/read-all")
async def mark_all_notifications_read(current: dict = Depends(get_current_user)):
    return {"status": "success", "message": "Đã đánh dấu tất cả thông báo đã đọc."}
