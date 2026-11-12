import logging
from typing import Any, Optional
from datetime import datetime, timezone, date
from app.db.supabase_client import get_supabase_client

logger = logging.getLogger("smart_manager.repo.staff")

# Initial staff fallback list
_STAFF_FALLBACK = [
    {
        "id": "NV01",
        "name": "Nguyễn Văn An",
        "role": "Quản lý trang trại",
        "pen_id": "123",
        "phone": "0901234567",
        "avatar_url": None,
        "created_at": "2026-08-01T08:00:00Z",
    },
    {
        "id": "NV02",
        "name": "Trần Thị Bình",
        "role": "Bác sĩ thú y",
        "pen_id": "PEN-ISO-01",
        "phone": "0912345678",
        "avatar_url": None,
        "created_at": "2026-08-05T08:00:00Z",
    },
    {
        "id": "NV03",
        "name": "Lê Hoàng Long",
        "role": "Kỹ thuật viên IoT",
        "pen_id": "PEN-A02",
        "phone": "0923456789",
        "avatar_url": None,
        "created_at": "2026-08-10T08:00:00Z",
    },
    {
        "id": "NV04",
        "name": "Phạm Văn Cường",
        "role": "Kỹ sư nông học",
        "pen_id": "PEN-B01",
        "phone": "0934567890",
        "avatar_url": None,
        "created_at": "2026-08-15T08:00:00Z",
    },
]

# In-memory attendance logs fallback
_ATTENDANCE_FALLBACK = [
    {
        "id": 1,
        "staff_id": "NV01",
        "staff_name": "Nguyễn Văn An",
        "pen_id": "123",
        "status": "present",
        "confidence": 0.96,
        "is_real": True,
        "note": "Điểm danh ca sáng qua Face AI",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
]


class StaffRepository:
    """Repository handling database operations for `staff` and `staff_attendance` tables."""

    def __init__(self):
        self._staff_table = "staff"
        self._attendance_table = "staff_attendance"

    @property
    def client(self):
        return get_supabase_client()

    def list_all(self, pen_id: Optional[str] = None) -> list[dict[str, Any]]:
        """List all staff, optionally filtered by pen_id."""
        try:
            query = self.client.table(self._staff_table).select("*")
            if pen_id:
                query = query.eq("pen_id", str(pen_id).strip())
            response = query.order("id").execute()
            if response.data:
                return response.data
        except Exception as e:
            logger.warning(f"Error fetching staff from Supabase: {e}. Using fallback.")

        if pen_id:
            return [s for s in _STAFF_FALLBACK if s.get("pen_id") == pen_id]
        return list(_STAFF_FALLBACK)

    def get_by_id(self, staff_id: str) -> Optional[dict[str, Any]]:
        """Get staff member by staff_id."""
        clean_id = staff_id.strip()
        try:
            response = self.client.table(self._staff_table).select("*").eq("id", clean_id).execute()
            if response.data:
                return response.data[0]
        except Exception as e:
            logger.warning(f"Error getting staff {clean_id}: {e}")

        for s in _STAFF_FALLBACK:
            if s.get("id") == clean_id:
                return s
        return None

    def create_staff(
        self,
        staff_id: str,
        name: str,
        role: str = "Kỹ thuật viên",
        pen_id: str = "123",
        phone: Optional[str] = None,
        avatar_url: Optional[str] = None,
    ) -> dict[str, Any]:
        """Register a new staff member."""
        clean_id = staff_id.strip()
        data = {
            "id": clean_id,
            "name": name.strip(),
            "role": role.strip(),
            "pen_id": pen_id.strip() if pen_id else "123",
            "phone": phone,
            "avatar_url": avatar_url,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        try:
            response = self.client.table(self._staff_table).upsert(data).execute()
            if response.data:
                return response.data[0]
        except Exception as e:
            logger.warning(f"Error creating staff in Supabase: {e}. Storing in fallback.")

        # Update fallback
        for idx, s in enumerate(_STAFF_FALLBACK):
            if s["id"] == clean_id:
                _STAFF_FALLBACK[idx] = data
                return data
        _STAFF_FALLBACK.append(data)
        return data

    def log_attendance(
        self,
        staff_id: str,
        staff_name: str,
        pen_id: Optional[str] = "123",
        status: str = "present",
        confidence: float = 1.0,
        is_real: bool = True,
        note: str = "",
    ) -> dict[str, Any]:
        """Record attendance check-in for a staff member."""
        clean_id = staff_id.strip()
        record = {
            "staff_id": clean_id,
            "staff_name": staff_name.strip(),
            "pen_id": pen_id.strip() if pen_id else "123",
            "status": status,
            "confidence": float(confidence),
            "is_real": bool(is_real),
            "note": note,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        try:
            response = self.client.table(self._attendance_table).insert(record).execute()
            if response.data:
                return response.data[0]
        except Exception as e:
            logger.warning(f"Error logging attendance in Supabase: {e}. Storing in fallback.")

        record["id"] = len(_ATTENDANCE_FALLBACK) + 1
        _ATTENDANCE_FALLBACK.insert(0, record)
        return record

    def get_today_attendance(self, pen_id: Optional[str] = None) -> list[dict[str, Any]]:
        """Get all attendance logs recorded today."""
        today_date = date.today().isoformat()
        try:
            query = self.client.table(self._attendance_table).select("*").gte("created_at", f"{today_date}T00:00:00")
            if pen_id:
                query = query.eq("pen_id", str(pen_id).strip())
            response = query.order("created_at", desc=True).execute()
            if response.data is not None:
                return response.data
        except Exception as e:
            logger.warning(f"Error fetching today's attendance: {e}")

        today_logs = []
        for log in _ATTENDANCE_FALLBACK:
            log_time = str(log.get("created_at", ""))
            if log_time.startswith(today_date):
                if not pen_id or log.get("pen_id") == pen_id:
                    today_logs.append(log)
        return today_logs

    def get_attendance_history(self, staff_id: Optional[str] = None, limit: int = 20) -> list[dict[str, Any]]:
        """Retrieve recent attendance history."""
        try:
            query = self.client.table(self._attendance_table).select("*")
            if staff_id:
                query = query.eq("staff_id", staff_id.strip())
            response = query.order("created_at", desc=True).limit(limit).execute()
            if response.data:
                return response.data
        except Exception as e:
            logger.warning(f"Error fetching attendance history: {e}")

        history = [l for l in _ATTENDANCE_FALLBACK if not staff_id or l.get("staff_id") == staff_id]
        return history[:limit]
