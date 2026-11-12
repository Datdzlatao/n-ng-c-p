import logging
from typing import Any, Optional
from datetime import datetime, timezone
from app.db.supabase_client import get_supabase_client

logger = logging.getLogger("smart_manager.repo.pens")

# Danh sách đa dạng các chuồng trại / khu vực nuôi trồng
_PENS_FALLBACK = [
    {"id": "123", "name": "Chuồng Heo Thịt Khu A1", "type": "livestock", "created_at": "2026-08-01T00:00:00Z"},
    {"id": "PEN-A02", "name": "Chuồng Heo Thịt Khu A2", "type": "livestock", "created_at": "2026-08-15T00:00:00Z"},
    {"id": "PEN-ISO-01", "name": "Khu Cách Ly Y Tế / Heo Bệnh", "type": "livestock", "created_at": "2026-09-01T00:00:00Z"},
    {"id": "PEN-B01", "name": "Khu Nhà Màng Dưa Lưới B1", "type": "crops", "created_at": "2026-09-10T00:00:00Z"},
    {"id": "PEN-B02", "name": "Khu Nhà Màng Cà Chua Cherry B2", "type": "crops", "created_at": "2026-10-01T00:00:00Z"},
]


class PensRepository:
    """Repository handling database operations for the `pens` table."""

    def __init__(self):
        self._table = "pens"

    @property
    def client(self):
        return get_supabase_client()

    def list_all(self, user_id: Optional[str] = None) -> list[dict[str, Any]]:
        """List all pens, optionally isolated by user_id."""
        try:
            query = self.client.table(self._table).select("*")
            if user_id:
                query = query.eq("user_id", str(user_id).strip())
            response = query.order("id").execute()
            if response.data is not None:
                if user_id:
                    return response.data
                # If no user_id filter, merge with fallback for general overview
                existing_ids = {str(p.get("id")).strip() for p in response.data}
                combined = list(response.data)
                for fb in _PENS_FALLBACK:
                    if fb["id"] not in existing_ids:
                        combined.append(fb)
                return combined
        except Exception as e:
            logger.warning(f"Error fetching pens from Supabase: {e}. Using fallback.")
        return [fb for fb in _PENS_FALLBACK if not user_id or fb.get("user_id") == user_id]

    def get_by_id(self, pen_id: str) -> Optional[dict[str, Any]]:
        """Get pen by ID."""
        clean_id = pen_id.strip()
        try:
            response = self.client.table(self._table).select("*").eq("id", clean_id).limit(1).execute()
            if response.data and len(response.data) > 0:
                return response.data[0]
        except Exception as e:
            logger.warning(f"Error getting pen {clean_id}: {e}")

        for p in self.list_all():
            if str(p.get("id")).strip().lower() == clean_id.lower():
                return p
        return None

    def create_pen(
        self, pen_id: str, name: str, pen_type: str = "livestock", user_id: Optional[str] = None
    ) -> dict[str, Any]:
        """Create a new pen assigned to a specific user_id."""
        clean_id = pen_id.strip()
        existing = self.get_by_id(clean_id)
        if existing:
            return existing

        item = {
            "id": clean_id,
            "name": name.strip(),
            "type": pen_type.strip(),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        if user_id:
            item["user_id"] = str(user_id).strip()

        try:
            response = self.client.table(self._table).insert(item).execute()
            if response.data:
                return response.data[0]
        except Exception as e:
            logger.warning(f"Error creating pen in Supabase: {e}. Storing in fallback.")

        _PENS_FALLBACK.append(item)
        return item
