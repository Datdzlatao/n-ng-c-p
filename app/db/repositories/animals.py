import logging
from typing import Any, Optional
from datetime import datetime, timezone
from app.db.supabase_client import get_supabase_client

logger = logging.getLogger("smart_manager.repo.animals")

_ANIMALS_FALLBACK = [
    {
        "id": "HEO-101",
        "pen_id": "123",
        "species": "Heo Siêu Nạc",
        "weight": 65.5,
        "target_weight": 100.0,
        "feeding_status": "Normal",
        "status": "Khoe",
        "created_at": "2026-08-01T00:00:00Z",
    },
    {
        "id": "HEO-102",
        "pen_id": "123",
        "species": "Heo Siêu Nạc",
        "weight": 62.0,
        "target_weight": 100.0,
        "feeding_status": "An it",
        "status": "Sot nhe",
        "created_at": "2026-08-01T00:00:00Z",
    },
    {
        "id": "HEO-201",
        "pen_id": "PEN-A02",
        "species": "Heo Siêu Nạc",
        "weight": 72.0,
        "target_weight": 100.0,
        "feeding_status": "Normal",
        "status": "Khoe",
        "created_at": "2026-08-15T00:00:00Z",
    },
    {
        "id": "HEO-ISO-01",
        "pen_id": "PEN-ISO-01",
        "species": "Heo Lai Rừng",
        "weight": 48.0,
        "target_weight": 80.0,
        "feeding_status": "Normal",
        "status": "Khoe",
        "created_at": "2026-09-01T00:00:00Z",
    },
]

_HEALTH_LOGS_FALLBACK = []


class AnimalsRepository:
    """Repository handling database operations for `animals` and `health_logs`."""

    def __init__(self):
        self._table = "animals"
        self._health_table = "health_logs"

    @property
    def client(self):
        return get_supabase_client()

    def list_all(self) -> list[dict[str, Any]]:
        """List all animals."""
        try:
            res = self.client.table(self._table).select("*").execute()
            if res.data and len(res.data) > 0:
                existing_ids = {str(a.get("id")).strip().lower() for a in res.data}
                combined = list(res.data)
                for fb in _ANIMALS_FALLBACK:
                    if fb["id"].lower() not in existing_ids:
                        combined.append(fb)
                return combined
        except Exception as e:
            logger.warning(f"Error fetching animals from Supabase: {e}")
        return _ANIMALS_FALLBACK

    def list_by_pen(self, pen_id: str) -> list[dict[str, Any]]:
        """List animals residing in a specific pen."""
        clean_pen = pen_id.strip().lower()
        return [a for a in self.list_all() if str(a.get("pen_id", "")).strip().lower() == clean_pen]

    def get_by_id(self, animal_id: str) -> Optional[dict[str, Any]]:
        """Get an animal by ID."""
        clean_id = animal_id.strip().lower()
        try:
            res = self.client.table(self._table).select("*").eq("id", animal_id.strip()).limit(1).execute()
            if res.data and len(res.data) > 0:
                return res.data[0]
        except Exception as e:
            logger.warning(f"Error fetching animal {animal_id}: {e}")

        for a in self.list_all():
            if str(a.get("id")).strip().lower() == clean_id:
                return a
        return None

    def get_sick_or_attention_animals(self) -> list[dict[str, Any]]:
        """Fetch animals that are not healthy ('Khoe') or have abnormal feeding."""
        all_animals = self.list_all()
        return [
            a for a in all_animals
            if a.get("status", "Khoe").lower() not in ["khoe", "healthy", "normal"]
            or a.get("feeding_status", "Normal").lower() in ["an it", "bo an", "kem"]
        ]

    def update_health_status(
        self,
        animal_id: str,
        status: str,
        note: str = "",
        health_type: str = "Disease",
    ) -> dict[str, Any]:
        """Update animal status and insert health log."""
        animal = self.get_by_id(animal_id)
        if not animal:
            animal = {
                "id": animal_id.strip(),
                "pen_id": "123",
                "species": "Gia Súc",
                "weight": 50.0,
                "target_weight": 100.0,
                "feeding_status": "Normal",
                "status": status,
            }
            _ANIMALS_FALLBACK.append(animal)

        animal["status"] = status

        health_entry = {
            "animal_id": animal_id.strip(),
            "type": health_type,
            "title": f"Cập nhật sức khỏe: {status}",
            "note": note,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        _HEALTH_LOGS_FALLBACK.append(health_entry)

        try:
            self.client.table(self._table).update({"status": status}).eq("id", animal_id.strip()).execute()
            self.client.table(self._health_table).insert(health_entry).execute()
        except Exception as e:
            logger.warning(f"Error updating animal health on Supabase: {e}")

        return {"animal": animal, "health_log": health_entry}

    def transfer_pen(
        self,
        animal_id: str,
        target_pen_id: str,
        reason: str = "",
    ) -> dict[str, Any]:
        """
        Transfer an animal from current pen to another pen.
        Updates animals.pen_id and records an audit log.
        """
        clean_animal = animal_id.strip()
        clean_target_pen = target_pen_id.strip()

        animal = self.get_by_id(clean_animal)
        if not animal:
            raise ValueError(f"Không tìm thấy vật nuôi có mã '{animal_id}' trong trang trại.")

        old_pen_id = animal.get("pen_id") or "Chưa xếp chuồng"
        if old_pen_id.lower() == clean_target_pen.lower():
            return {
                "success": True,
                "already_in_pen": True,
                "animal": animal,
                "message": f"Cá thể '{clean_animal}' hiện đã ở sẵn tại chuồng '{clean_target_pen}'.",
            }

        # Update pen_id
        animal["pen_id"] = clean_target_pen

        # Log transfer event
        transfer_note = f"Chuyển từ chuồng '{old_pen_id}' sang chuồng '{clean_target_pen}'. Lý do: {reason or 'Điều chuyển chuồng trại'}"
        health_entry = {
            "animal_id": clean_animal,
            "type": "Transfer",
            "title": f"Đổi chuồng: {old_pen_id} -> {clean_target_pen}",
            "note": transfer_note,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        _HEALTH_LOGS_FALLBACK.append(health_entry)

        # Update Supabase
        try:
            self.client.table(self._table).update({"pen_id": clean_target_pen}).eq("id", clean_animal).execute()
            self.client.table(self._health_table).insert(health_entry).execute()
        except Exception as e:
            logger.warning(f"Error transferring animal on Supabase: {e}")

        return {
            "success": True,
            "animal_id": clean_animal,
            "old_pen_id": old_pen_id,
            "target_pen_id": clean_target_pen,
            "reason": reason,
            "animal": animal,
            "transfer_log": health_entry,
        }
