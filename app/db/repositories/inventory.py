import logging
from typing import Any, Optional
from datetime import datetime, timezone
from app.db.supabase_client import get_supabase_client

logger = logging.getLogger("smart_manager.repo.inventory")

_INVENTORY_FALLBACK = [
    {
        "id": 1,
        "name": "Cám Con Cò Siêu Tăng Trọng",
        "category": "Feed",
        "quantity": 85.0,
        "unit": "kg",
        "unit_price": 15000.0,
        "min_threshold": 20.0,
        "location": "Kho Cám A",
    },
    {
        "id": 2,
        "name": "Kháng Sinh Amoxicillin 50%",
        "category": "Medicine",
        "quantity": 3.0,
        "unit": "hộp",
        "unit_price": 120000.0,
        "min_threshold": 5.0,
        "location": "Tủ Thuốc Thú Y",
    },
    {
        "id": 3,
        "name": "Phân Bón NPK Dinh Dưỡng Dưa",
        "category": "Fertilizer",
        "quantity": 15.0,
        "unit": "kg",
        "unit_price": 25000.0,
        "min_threshold": 30.0,
        "location": "Kho Phân Bón",
    },
]


class InventoryRepository:
    """Repository handling database operations for the `inventory` table."""

    def __init__(self):
        self._table = "inventory"
        self._logs_table = "inventory_logs"

    @property
    def client(self):
        return get_supabase_client()

    def list_all(self) -> list[dict[str, Any]]:
        """List all inventory items."""
        try:
            response = self.client.table(self._table).select("*").execute()
            if response.data and len(response.data) > 0:
                return response.data
        except Exception as e:
            logger.warning(f"Error fetching inventory from Supabase: {e}")
        return _INVENTORY_FALLBACK

    def get_by_name(self, item_name: str) -> Optional[dict[str, Any]]:
        """Find an inventory item by name (case-insensitive fuzzy match)."""
        clean_name = item_name.strip().lower()

        # Try Supabase query using 'name' column
        try:
            response = (
                self.client.table(self._table)
                .select("*")
                .ilike("name", f"%{clean_name}%")
                .limit(1)
                .execute()
            )
            if response.data and len(response.data) > 0:
                return response.data[0]
        except Exception as e:
            logger.warning(f"Error querying inventory by name '{item_name}': {e}")

        # Check fallback
        for item in _INVENTORY_FALLBACK:
            if clean_name in item.get("name", "").lower() or clean_name in item.get("item_name", "").lower():
                return item
        return None

    def get_low_stock(self) -> list[dict[str, Any]]:
        """Fetch items where current quantity is less than or equal to min_threshold."""
        items = self.list_all()
        low_stock_items = []
        for item in items:
            qty = float(item.get("quantity", 0))
            thresh = float(item.get("min_threshold", 5.0))
            if qty <= thresh:
                low_stock_items.append(item)
        return low_stock_items

    def create_item(
        self,
        item_name: str,
        quantity: float,
        unit: str = "kg",
        category: str = "Feed",
        min_threshold: float = 5.0,
        unit_price: float = 0.0,
        location: str = "Kho Chính",
    ) -> dict[str, Any]:
        """Create a new item in the inventory."""
        existing = self.get_by_name(item_name)
        if existing:
            raise ValueError(f"Vật tư '{item_name}' đã tồn tại trong kho (ID: {existing['id']}).")

        payload = {
            "name": item_name.strip(),
            "category": category.strip(),
            "quantity": max(0.0, float(quantity)),
            "unit": unit.strip(),
            "unit_price": float(unit_price),
            "min_threshold": max(0.0, float(min_threshold)),
        }

        try:
            response = self.client.table(self._table).insert(payload).execute()
            if response.data:
                return response.data[0]
        except Exception as e:
            logger.warning(f"Could not insert inventory into Supabase: {e}. Storing in fallback.")

        payload["id"] = len(_INVENTORY_FALLBACK) + 1
        _INVENTORY_FALLBACK.append(payload)
        return payload

    def adjust_quantity(
        self,
        item_name: str,
        delta_quantity: float,
        pen_id: Optional[str] = None,
        note: str = "",
    ) -> dict[str, Any]:
        """
        Adjust quantity by adding delta_quantity (positive for import, negative for export).
        Validates inventory stock to prevent negative stock values.
        Logs to inventory_logs if available.
        """
        existing = self.get_by_name(item_name)
        if not existing:
            # Auto-create if importing a new item
            if delta_quantity > 0:
                existing = self.create_item(item_name=item_name, quantity=0.0)
            else:
                raise ValueError(f"Không tìm thấy vật tư '{item_name}' trong kho để xuất.")

        current_qty = float(existing.get("quantity", 0))
        new_qty = current_qty + delta_quantity

        if new_qty < 0:
            raise ValueError(
                f"Tồn kho không đủ! Vật tư '{existing.get('name')}' hiện chỉ còn {current_qty} {existing.get('unit')}, "
                f"không thể xuất {abs(delta_quantity)} {existing.get('unit')}."
            )

        existing["quantity"] = new_qty
        existing["updated_at"] = datetime.now(timezone.utc).isoformat()

        # Update Supabase
        try:
            item_id = existing.get("id")
            self.client.table(self._table).update({"quantity": new_qty}).eq("id", item_id).execute()

            # Record to inventory_logs
            action_type = "IMPORT" if delta_quantity > 0 else "EXPORT"
            self.client.table(self._logs_table).insert({
                "item_name": existing.get("name"),
                "action_type": action_type,
                "amount": abs(delta_quantity),
                "pen_id": pen_id,
                "note": note or f"AI Agent adjust quantity: {delta_quantity}",
            }).execute()
        except Exception as e:
            logger.warning(f"Could not update inventory in Supabase: {e}")

        return existing
