import logging
from typing import Any, Optional
from datetime import date, datetime, timezone
from app.db.supabase_client import get_supabase_client

logger = logging.getLogger("smart_manager.repo.schedules")

_SCHEDULES_FALLBACK: list[dict[str, Any]] = [
    {
        "id": 1,
        "pen_id": "123",
        "task_name": "Kiểm tra nhiệt độ & bật thông gió chuồng Heo",
        "target_date": date.today().isoformat(),
        "status": "pending",
        "note": "Ưu tiên ca sáng",
        "created_at": datetime.now(timezone.utc).isoformat(),
    },
    {
        "id": 2,
        "pen_id": "123",
        "task_name": "Tiêm vắc xin phòng dịch cho lứa heo 102",
        "target_date": date.today().isoformat(),
        "status": "pending",
        "note": "Theo dõi phản ứng sau tiêm",
        "created_at": datetime.now(timezone.utc).isoformat(),
    },
]


class SchedulesRepository:
    """Repository handling database operations for the `schedules` table."""

    def __init__(self):
        self._table = "schedules"

    @property
    def client(self):
        return get_supabase_client()

    def list_all(self) -> list[dict[str, Any]]:
        """List all schedules."""
        try:
            response = self.client.table(self._table).select("*").order("target_date").execute()
            if response.data and len(response.data) > 0:
                return response.data
        except Exception as e:
            logger.debug(f"Schedules table not available on Supabase ({e}), using in-memory store.")
        return _SCHEDULES_FALLBACK

    def get_pending_schedules(self, target_date: Optional[str] = None) -> list[dict[str, Any]]:
        """Fetch pending schedules, optionally for a specific date."""
        try:
            query = self.client.table(self._table).select("*").eq("status", "pending")
            if target_date:
                query = query.eq("target_date", target_date)
            response = query.order("target_date").execute()
            if response.data and len(response.data) > 0:
                return response.data
        except Exception:
            pass

        results = [s for s in _SCHEDULES_FALLBACK if s.get("status") == "pending"]
        if target_date:
            results = [s for s in results if s.get("target_date") == target_date]
        return results

    def create_schedule(
        self,
        task_name: str,
        target_date: str,
        pen_id: Optional[str] = None,
        note: str = "",
        status: str = "pending",
    ) -> dict[str, Any]:
        """Create a new schedule task."""
        payload = {
            "task_name": task_name.strip(),
            "target_date": target_date.strip(),
            "pen_id": pen_id,
            "status": status,
            "note": note.strip() if note else "",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        try:
            response = self.client.table(self._table).insert(payload).execute()
            if response.data:
                return response.data[0]
        except Exception as e:
            logger.debug(f"Could not insert schedule into Supabase ({e}), saving to in-memory store.")

        payload["id"] = len(_SCHEDULES_FALLBACK) + 1
        _SCHEDULES_FALLBACK.append(payload)
        return payload

    def update_schedule(
        self,
        task_name: str,
        status: Optional[str] = None,
        target_date: Optional[str] = None,
        note: Optional[str] = None,
    ) -> dict[str, Any]:
        """Update a schedule by task_name."""
        clean_name = task_name.strip().lower()
        target = None
        for s in _SCHEDULES_FALLBACK:
            if clean_name in s.get("task_name", "").lower():
                target = s
                break

        if not target:
            target = {
                "id": len(_SCHEDULES_FALLBACK) + 1,
                "task_name": task_name,
                "target_date": target_date or date.today().isoformat(),
                "status": status or "done",
                "note": note or "",
            }
            _SCHEDULES_FALLBACK.append(target)

        if status:
            target["status"] = status
        if target_date:
            target["target_date"] = target_date
        if note:
            target["note"] = note

        try:
            updates = {}
            if status: updates["status"] = status
            if target_date: updates["target_date"] = target_date
            if note: updates["note"] = note
            self.client.table(self._table).update(updates).ilike("task_name", f"%{clean_name}%").execute()
        except Exception:
            pass

        return target
