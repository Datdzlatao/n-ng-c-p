import logging
from typing import Any
from datetime import datetime, timezone
from app.db.supabase_client import get_supabase_client

logger = logging.getLogger("smart_manager.repo.feed_logs")

_FEED_LOGS_FALLBACK = []


class FeedLogsRepository:
    """Repository handling database operations for `feed_logs`."""

    def __init__(self):
        self._table = "feed_logs"

    @property
    def client(self):
        return get_supabase_client()

    def list_all(self, limit: int = 20) -> list[dict[str, Any]]:
        """List recent feeding logs."""
        try:
            res = self.client.table(self._table).select("*").order("created_at", desc=True).limit(limit).execute()
            if res.data:
                return res.data
        except Exception as e:
            logger.warning(f"Error fetching feed logs from Supabase: {e}")
        return _FEED_LOGS_FALLBACK[-limit:]

    def log_feeding(self, pen_id: str, food_name: str, amount: float) -> dict[str, Any]:
        """Record feeding in feed_logs."""
        entry = {
            "pen_id": pen_id.strip(),
            "food_name": food_name.strip(),
            "amount": float(amount),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        try:
            res = self.client.table(self._table).insert(entry).execute()
            if res.data:
                return res.data[0]
        except Exception as e:
            logger.warning(f"Error inserting feed log into Supabase: {e}")

        _FEED_LOGS_FALLBACK.append(entry)
        return entry
