import logging
from typing import Any, Optional
from datetime import datetime, timezone
from app.db.supabase_client import get_supabase_client

logger = logging.getLogger("smart_manager.repo.devices")

_DEVICES_FALLBACK = [
    {"id": "DEV_FAN_01", "pen_id": "123", "name": "Quạt Thông Gió Hút Mùi", "is_active": False, "pin_number": 1},
    {"id": "DEV_MIST_01", "pen_id": "123", "name": "Hệ Thống Phun Sương Làm Mát", "is_active": False, "pin_number": 2},
    {"id": "DEV_LAMP_01", "pen_id": "123", "name": "Đèn Sưởi Hồng Ngoại", "is_active": False, "pin_number": 3},
    {"id": "DEV_FAN_02", "pen_id": "PEN-A02", "name": "Quạt Hút Gió Chuồng A2", "is_active": False, "pin_number": 1},
    {"id": "DEV_UV_01", "pen_id": "PEN-ISO-01", "name": "Đèn Khử Trùng UV Y Tế", "is_active": False, "pin_number": 1},
    {"id": "DEV_MIST_ISO", "pen_id": "PEN-ISO-01", "name": "Máy Phun Thuốc Sát Trùng", "is_active": False, "pin_number": 2},
    {"id": "DEV_VALVE_01", "pen_id": "PEN-B01", "name": "Hệ Thống Tưới Nhỏ Giọt Dưa", "is_active": False, "pin_number": 1},
]


class DevicesRepository:
    """Repository handling database operations for the `devices` table."""

    def __init__(self):
        self._table = "devices"

    @property
    def client(self):
        return get_supabase_client()

    def list_all(self) -> list[dict[str, Any]]:
        """List all devices."""
        try:
            response = self.client.table(self._table).select("*").execute()
            if response.data and len(response.data) > 0:
                existing_ids = {str(d.get("id")).strip().lower() for d in response.data}
                combined = list(response.data)
                for fb in _DEVICES_FALLBACK:
                    if fb["id"].lower() not in existing_ids:
                        combined.append(fb)
                return combined
        except Exception as e:
            logger.warning(f"Error fetching devices from Supabase: {e}")
        return _DEVICES_FALLBACK

    def list_by_pen(self, pen_id: str) -> list[dict[str, Any]]:
        """List devices in a specific pen."""
        clean_pen = pen_id.strip().lower()
        all_devs = self.list_all()
        return [d for d in all_devs if str(d.get("pen_id", "")).strip().lower() == clean_pen]

    def set_device_state(
        self,
        device_id: Optional[str] = None,
        pen_id: Optional[str] = None,
        device_name: Optional[str] = None,
        is_active: bool = True,
    ) -> dict[str, Any]:
        """
        Turn a device ON (True) or OFF (False).
        Matches by device_id, or by pen_id + device_name.
        """
        target = None
        all_devs = self.list_all()

        # 1. Match by device_id
        if device_id:
            for d in all_devs:
                if str(d.get("id")).strip().lower() == str(device_id).strip().lower():
                    target = d
                    break

        # 2. Match by pen_id + device_name
        if not target and pen_id and device_name:
            for d in all_devs:
                if str(d.get("pen_id")).strip().lower() == str(pen_id).strip().lower():
                    if device_name.lower().strip() in str(d.get("name", "")).lower().strip():
                        target = d
                        break

        # 3. Match by device_name alone
        if not target and device_name:
            for d in all_devs:
                if device_name.lower().strip() in str(d.get("name", "")).lower().strip():
                    target = d
                    break

        if not target:
            target = {
                "id": device_id or f"DEV_AUTO_{len(all_devs)+1}",
                "pen_id": pen_id or "123",
                "name": device_name or "Thiết Bị Điều Khiển",
                "is_active": is_active,
                "pin_number": 1,
            }
            _DEVICES_FALLBACK.append(target)

        target["is_active"] = is_active
        target["updated_at"] = datetime.now(timezone.utc).isoformat()

        try:
            target_id = target.get("id")
            self.client.table(self._table).update({"is_active": is_active}).eq("id", target_id).execute()
        except Exception as e:
            logger.warning(f"Could not update device on Supabase: {e}. Updated in local state.")

        return target
