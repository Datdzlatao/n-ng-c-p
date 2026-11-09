import logging
from typing import Any, Optional
from datetime import datetime, timezone
from app.db.supabase_client import get_supabase_client

logger = logging.getLogger("smart_manager.repo.alerts")

_ALERTS_FALLBACK: list[dict[str, Any]] = [
    {
        "id": 1,
        "pen_id": "123",
        "alert_type": "SYSTEM",
        "message": "Hệ thống Smart Management AI Agent đã sẵn sàng giám sát chuồng trại.",
        "is_read": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
]


class AlertsRepository:
    """Repository handling database operations for the `alerts` table."""

    def __init__(self):
        self._table = "alerts"

    @property
    def client(self):
        return get_supabase_client()

    def get_recent_alerts(self, limit: int = 20) -> list[dict[str, Any]]:
        """Fetch recent alerts ordered by created_at DESC."""
        try:
            response = self.client.table(self._table).select("*").order("created_at", desc=True).limit(limit).execute()
            if response.data and len(response.data) > 0:
                return response.data
        except Exception as e:
            logger.debug(f"Alerts table unavailable on Supabase ({e}), using in-memory store.")

        return list(reversed(_ALERTS_FALLBACK[-limit:]))

    def create_alert(
        self,
        alert_type: str,
        message: str,
        pen_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """Create a new alert record."""
        payload = {
            "alert_type": alert_type.strip(),
            "message": message.strip(),
            "pen_id": pen_id,
            "is_read": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        try:
            response = self.client.table(self._table).insert(payload).execute()
            if response.data:
                return response.data[0]
        except Exception as e:
            logger.debug(f"Could not insert alert into Supabase ({e}), saving to in-memory store.")

        payload["id"] = len(_ALERTS_FALLBACK) + 1
        _ALERTS_FALLBACK.append(payload)
        return payload

    def mark_as_read(self, alert_id: int) -> dict[str, Any]:
        """Mark an alert as read."""
        try:
            response = self.client.table(self._table).update({"is_read": True}).eq("id", alert_id).execute()
            if response.data:
                return response.data[0]
        except Exception:
            pass

        for a in _ALERTS_FALLBACK:
            if a.get("id") == alert_id:
                a["is_read"] = True
                return a
        return {"id": alert_id, "is_read": True}
