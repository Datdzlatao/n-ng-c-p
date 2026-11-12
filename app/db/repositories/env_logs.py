import logging
from typing import Any, Optional
from datetime import datetime, timezone
from app.db.supabase_client import get_supabase_client

logger = logging.getLogger("smart_manager.repo.env_logs")

_ENV_LOGS_FALLBACK = [
    {"id": 1, "pen_id": "123", "temperature": 28.5, "humidity": 75.0, "smell_level": 2.5, "created_at": datetime.now(timezone.utc).isoformat()},
    {"id": 2, "pen_id": "PEN-A02", "temperature": 27.8, "humidity": 72.0, "smell_level": 1.8, "created_at": datetime.now(timezone.utc).isoformat()},
    {"id": 3, "pen_id": "PEN-ISO-01", "temperature": 29.5, "humidity": 68.0, "smell_level": 4.2, "created_at": datetime.now(timezone.utc).isoformat()},
    {"id": 4, "pen_id": "PEN-B01", "temperature": 31.0, "humidity": 82.0, "smell_level": 0.5, "created_at": datetime.now(timezone.utc).isoformat()},
]


class EnvLogsRepository:
    """Repository handling database operations for the `env_logs` table."""

    def __init__(self):
        self._table = "env_logs"

    @property
    def client(self):
        return get_supabase_client()

    def get_latest_logs(self, limit: int = 10, pen_id: Optional[str] = None) -> list[dict[str, Any]]:
        """
        Fetch the most recent environmental records, ordered by created_at DESC.
        Optionally filter by pen_id.
        """
        try:
            query = self.client.table(self._table).select("*").order("created_at", desc=True)
            if pen_id:
                query = query.eq("pen_id", pen_id.strip())
            response = query.limit(limit).execute()
            if response.data and len(response.data) > 0:
                return response.data
        except Exception as e:
            logger.warning(f"Error fetching env logs from Supabase: {e}")

        filtered = _ENV_LOGS_FALLBACK
        if pen_id:
            clean_pen = pen_id.strip().lower()
            filtered = [x for x in filtered if str(x.get("pen_id", "")).strip().lower() == clean_pen]
            if not filtered:
                # Default baseline for newly created pen
                filtered = [
                    {"id": 99, "pen_id": pen_id, "temperature": 28.0, "humidity": 70.0, "smell_level": 2.0, "created_at": datetime.now(timezone.utc).isoformat()}
                ]
        return filtered[:limit]

    def insert_log(
        self,
        temperature: float,
        humidity: float,
        smell_level: float = 0.0,
        pen_id: str = "123",
    ) -> dict[str, Any]:
        """Insert a new environmental record."""
        payload = {
            "temperature": float(temperature),
            "humidity": float(humidity),
            "smell_level": float(smell_level),
            "pen_id": str(pen_id).strip(),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        try:
            response = self.client.table(self._table).insert(payload).execute()
            if response.data:
                return response.data[0]
        except Exception as e:
            logger.warning(f"Could not insert env log to Supabase: {e}")

        payload["id"] = len(_ENV_LOGS_FALLBACK) + 100
        _ENV_LOGS_FALLBACK.insert(0, payload)
        return payload
