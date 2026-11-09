import logging
from typing import Any, Optional
from datetime import date, timedelta
from app.db.supabase_client import get_supabase_client

logger = logging.getLogger("smart_manager.repo.crops")

_CROPS_FALLBACK = [
    {
        "id": 1,
        "pen_id": "PEN-B01",
        "name": "Dưa Lưới Fuji F1",
        "quantity": 500,
        "plant_date": (date.today() - timedelta(days=65)).isoformat(),
        "harvest_date": (date.today() + timedelta(days=5)).isoformat(),
        "status": "Ripening",
    }
]


class CropsRepository:
    """Repository handling database operations for `crops`."""

    def __init__(self):
        self._table = "crops"

    @property
    def client(self):
        return get_supabase_client()

    def list_all(self) -> list[dict[str, Any]]:
        """List all crops."""
        try:
            res = self.client.table(self._table).select("*").execute()
            if res.data and len(res.data) > 0:
                return res.data
        except Exception as e:
            logger.warning(f"Error fetching crops from Supabase: {e}")
        return _CROPS_FALLBACK

    def get_upcoming_harvests(self, within_days: int = 7) -> list[dict[str, Any]]:
        """Get crops ready for harvest within the next N days."""
        all_crops = self.list_all()
        today = date.today()
        upcoming = []
        for c in all_crops:
            h_date_str = c.get("harvest_date")
            if h_date_str:
                try:
                    h_date = date.fromisoformat(str(h_date_str)[:10])
                    delta = (h_date - today).days
                    if 0 <= delta <= within_days:
                        c_copy = dict(c)
                        c_copy["days_remaining"] = delta
                        upcoming.append(c_copy)
                except Exception:
                    pass
        return upcoming
