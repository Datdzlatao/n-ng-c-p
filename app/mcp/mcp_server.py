import asyncio
import json
import logging
from datetime import date
from typing import Optional

from mcp.server.fastmcp import FastMCP
from app.config import get_settings
from app.db.repositories.env_logs import EnvLogsRepository
from app.db.repositories.inventory import InventoryRepository
from app.db.repositories.schedules import SchedulesRepository
from app.db.repositories.alerts import AlertsRepository
from app.db.repositories.pens import PensRepository
from app.db.repositories.devices import DevicesRepository
from app.db.repositories.animals import AnimalsRepository
from app.db.repositories.crops import CropsRepository
from app.db.repositories.feed_logs import FeedLogsRepository
from app.api.websocket_manager import ws_manager

logger = logging.getLogger("smart_manager.mcp")

settings = get_settings()

# Initialize FastMCP Server
mcp = FastMCP(
    name=settings.MCP_SERVER_NAME,
    instructions="MCP Server cho Hệ Thống Quản Lý Đa Chuồng Trại Nông Nghiệp Thông Minh & IoT Tích Hợp AI Agent.",
)

# Initialize Repositories
env_repo = EnvLogsRepository()
inventory_repo = InventoryRepository()
schedules_repo = SchedulesRepository()
alerts_repo = AlertsRepository()
pens_repo = PensRepository()
devices_repo = DevicesRepository()
animals_repo = AnimalsRepository()
crops_repo = CropsRepository()
feed_repo = FeedLogsRepository()


def _notify_websocket_safe(event: str, data: dict):
    """Safely broadcast WebSocket event across sync or async execution contexts."""
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(ws_manager.broadcast(event=event, data=data))
    except RuntimeError:
        try:
            asyncio.run(ws_manager.broadcast(event=event, data=data))
        except Exception as e:
            logger.warning(f"Could not broadcast via WebSocket: {e}")


# ====================================================================
# MCP RESOURCES (ĐỌC NGỮ CẢNH HỆ THỐNG TRANG TRẠI)
# ====================================================================

@mcp.resource("resource://farm/overview")
def get_farm_overview() -> str:
    """
    MCP Resource: Thống kê tổng quan toàn trang trại (danh sách chuồng, thiết bị, vật nuôi, cây trồng).
    """
    try:
        pens = pens_repo.list_all()
        devices = devices_repo.list_all()
        animals = animals_repo.list_all()
        crops = crops_repo.list_all()
        sick_animals = animals_repo.get_sick_or_attention_animals()

        overview = {
            "total_pens": len(pens),
            "total_devices": len(devices),
            "devices_active": len([d for d in devices if d.get("is_active")]),
            "total_animals": len(animals),
            "sick_or_attention_animals": len(sick_animals),
            "total_crops": len(crops),
            "pens": [
                {
                    "id": p.get("id"),
                    "name": p.get("name"),
                    "type": p.get("type"),
                    "animals_count": len(animals_repo.list_by_pen(p.get("id"))),
                    "devices_count": len(devices_repo.list_by_pen(p.get("id"))),
                }
                for p in pens
            ],
        }
        return json.dumps(overview, ensure_ascii=False, default=str, indent=2)
    except Exception as e:
        logger.error(f"Error reading farm overview resource: {e}")
        return f"Lỗi đọc farm overview: {str(e)}"


@mcp.resource("resource://pens/list")
def get_pens_list() -> str:
    """
    MCP Resource: Danh sách đầy đủ tất cả các chuồng trại kèm thống kê chi tiết theo chuồng.
    """
    try:
        pens = pens_repo.list_all()
        pens_detailed = []
        for p in pens:
            pid = str(p.get("id"))
            animals = animals_repo.list_by_pen(pid)
            devices = devices_repo.list_by_pen(pid)
            latest_env = env_repo.get_latest_logs(limit=1, pen_id=pid)
            pens_detailed.append({
                "pen_id": pid,
                "name": p.get("name"),
                "type": p.get("type"),
                "animals": [{"id": a.get("id"), "species": a.get("species"), "status": a.get("status")} for a in animals],
                "devices": [{"id": d.get("id"), "name": d.get("name"), "is_active": d.get("is_active")} for d in devices],
                "telemetry": latest_env[0] if latest_env else None,
            })
        return json.dumps(pens_detailed, ensure_ascii=False, default=str, indent=2)
    except Exception as e:
        return f"Lỗi lấy danh sách chuồng: {str(e)}"


@mcp.resource("resource://env/latest")
def get_latest_env_logs() -> str:
    """
    MCP Resource: Lấy các bản ghi cảm biến môi trường mới nhất trên toàn trại.
    """
    try:
        logs = env_repo.get_latest_logs(limit=10)
        if not logs:
            return "Chưa có dữ liệu cảm biến môi trường nào trong hệ thống."
        return json.dumps(logs, ensure_ascii=False, default=str, indent=2)
    except Exception as e:
        logger.error(f"Error fetching env logs resource: {e}")
        return f"Lỗi khi đọc resource://env/latest: {str(e)}"


@mcp.resource("resource://inventory/low-stock")
def get_low_stock_inventory() -> str:
    """
    MCP Resource: Lấy danh sách thức ăn, thuốc, vật tư chạm hoặc thấp hơn ngưỡng tối thiểu.
    """
    try:
        low_stock = inventory_repo.get_low_stock()
        if not low_stock:
            return "Tất cả vật tư trong kho đều đang ở mức an toàn (không có mặt hàng nào thiếu hụt)."
        return json.dumps(low_stock, ensure_ascii=False, default=str, indent=2)
    except Exception as e:
        logger.error(f"Error fetching low stock resource: {e}")
        return f"Lỗi khi đọc resource://inventory/low-stock: {str(e)}"


@mcp.resource("resource://animals/attention")
def get_animals_attention() -> str:
    """
    MCP Resource: Danh sách vật nuôi cần chăm sóc đặc biệt (ốm, sốt, bỏ ăn) kèm chuồng hiện tại.
    """
    try:
        sick = animals_repo.get_sick_or_attention_animals()
        if not sick:
            return "Tất cả vật nuôi trong trang trại đều khỏe mạnh bình thường."
        return json.dumps(sick, ensure_ascii=False, default=str, indent=2)
    except Exception as e:
        return f"Lỗi đọc danh sách vật nuôi: {str(e)}"


@mcp.resource("resource://crops/harvest")
def get_crops_harvest() -> str:
    """
    MCP Resource: Danh sách cây trồng / vụ mùa sắp đến hạn thu hoạch trong 7 ngày tới.
    """
    try:
        upcoming = crops_repo.get_upcoming_harvests(within_days=7)
        if not upcoming:
            return "Không có cây trồng nào cần thu hoạch trong 7 ngày tới."
        return json.dumps(upcoming, ensure_ascii=False, default=str, indent=2)
    except Exception as e:
        return f"Lỗi đọc thông tin cây trồng: {str(e)}"


# ====================================================================
# MCP TOOLS (CÁNH TAY THỰC THI CHO AI AGENT)
# ====================================================================

@mcp.tool()
def transfer_animal_pen(
    animal_id: str,
    target_pen_id: str,
    reason: str = "",
) -> str:
    """
    Chuyển đổi cá thể vật nuôi từ chuồng hiện tại sang chuồng khác (ví dụ: chuyển sang chuồng cách ly y tế, chuồng xuất chuồng, hoặc đổi khu).

    Args:
        animal_id: Mã định danh cá thể vật nuôi (ví dụ: 'HEO-101', 'HEO-102')
        target_pen_id: Mã chuồng mới chuyển đến (ví dụ: 'PEN-ISO-01', 'PEN-A02', '123')
        reason: Lý do điều chuyển chuồng (ví dụ: 'Cách ly điều trị sốt', 'Tách đàn nuôi thịt')
    """
    try:
        target_clean = target_pen_id.strip()
        animal_clean = animal_id.strip()

        # Kiểm tra chuồng đích, nếu chưa có thì tự động tạo
        pen = pens_repo.get_by_id(target_clean)
        if not pen:
            pens_repo.create_pen(pen_id=target_clean, name=f"Chuồng {target_clean}")

        res = animals_repo.transfer_pen(
            animal_id=animal_clean,
            target_pen_id=target_clean,
            reason=reason,
        )

        _notify_websocket_safe("animal_transfer", res)
        return (
            f"🚚 ĐÃ CHUYỂN CHUỒNG THÀNH CÔNG: Vật nuôi '{animal_clean}' từ [{res.get('old_pen_id')}] "
            f"sang [{target_clean}]. Lý do: {reason or 'Điều chuyển chuồng trại'}."
        )
    except Exception as e:
        logger.error(f"Error in transfer_animal_pen: {e}")
        return f"❌ Lỗi khi chuyển chuồng: {str(e)}"


@mcp.tool()
def get_pen_status(pen_id: str) -> str:
    """
    Tra cứu chi tiết một chuồng bất kỳ: Chỉ số cảm biến (nhiệt độ, độ ẩm, mùi), thiết bị IoT và danh sách vật nuôi hiện có.

    Args:
        pen_id: Mã chuồng cần tra cứu (ví dụ: '123', 'PEN-A02', 'PEN-ISO-01', 'PEN-B01')
    """
    clean_pen = pen_id.strip()
    pen = pens_repo.get_by_id(clean_pen)
    if not pen:
        return f"❌ Không tìm thấy chuồng có mã '{clean_pen}' trong hệ thống."

    animals = animals_repo.list_by_pen(clean_pen)
    devices = devices_repo.list_by_pen(clean_pen)
    latest_env = env_repo.get_latest_logs(limit=1, pen_id=clean_pen)

    status_data = {
        "pen_id": clean_pen,
        "name": pen.get("name"),
        "type": pen.get("type"),
        "latest_sensor": latest_env[0] if latest_env else "Chưa có dữ liệu cảm biến",
        "total_animals": len(animals),
        "animals": [{"id": a.get("id"), "species": a.get("species"), "status": a.get("status"), "weight": a.get("weight")} for a in animals],
        "devices": [{"id": d.get("id"), "name": d.get("name"), "is_active": d.get("is_active")} for d in devices],
    }
    return json.dumps(status_data, ensure_ascii=False, default=str, indent=2)


@mcp.tool()
def manage_pen(
    action: str,
    pen_id: str,
    name: str = "",
    pen_type: str = "livestock",
) -> str:
    """
    Quản lý chuồng trại: Thêm chuồng mới hoặc cập nhật thông tin chuồng.

    Args:
        action: 'create' hoặc 'update'
        pen_id: Mã chuồng (ví dụ: 'PEN-A03', 'PEN-ISO-02')
        name: Tên gọi chuồng (ví dụ: 'Chuồng Heo Nái A3')
        pen_type: Phân loại: 'livestock' (gia súc), 'crops' (trồng trọt), 'greenhouse' (nhà màng)
    """
    action_clean = action.strip().lower()
    clean_id = pen_id.strip()

    try:
        if action_clean in ["create", "add"]:
            created = pens_repo.create_pen(pen_id=clean_id, name=name or f"Chuồng {clean_id}", pen_type=pen_type)
            _notify_websocket_safe("pen_update", {"action": "create", "pen": created})
            return f"✅ Đã tạo mới thành công chuồng [{clean_id}] - '{created.get('name')}' (Loại: {pen_type})."
        else:
            return f"❌ Hành động '{action}' không hỗ trợ. Vui lòng chọn 'create'."
    except Exception as e:
        return f"❌ Lỗi quản lý chuồng: {str(e)}"


@mcp.tool()
def control_device(
    action: str,
    device_name: str = "",
    pen_id: str = "123",
    device_id: str = "",
) -> str:
    """
    Điều khiển thiết bị IoT tại chuồng trại bất kỳ (bật/tắt quạt thông gió, đèn sưởi, máy phun sương).

    Args:
        action: 'turn_on' (bật), 'turn_off' (tắt), hoặc 'toggle'
        device_name: Tên thiết bị (ví dụ: 'quạt', 'bóng đèn', 'phun sương', 'nước')
        pen_id: Mã chuồng lắp đặt thiết bị (ví dụ: '123', 'PEN-A02', 'PEN-ISO-01')
        device_id: Mã định danh thiết bị nếu biết chính xác
    """
    action_clean = action.strip().lower()
    is_active = True if action_clean in ["turn_on", "on", "bat", "bật", "mo", "mở"] else False

    try:
        updated = devices_repo.set_device_state(
            device_id=device_id if device_id else None,
            pen_id=pen_id if pen_id else "123",
            device_name=device_name if device_name else None,
            is_active=is_active,
        )
        status_text = "ĐÃ BẬT 🟢" if is_active else "ĐÃ TẮT 🔴"
        _notify_websocket_safe("device_update", updated)
        return f"✅ {status_text} thiết bị '{updated.get('name')}' (ID: {updated.get('id')}) tại chuồng {pen_id}."
    except Exception as e:
        logger.error(f"Error in control_device: {e}")
        return f"❌ Lỗi khi điều khiển thiết bị: {str(e)}"


@mcp.tool()
def log_feeding(
    pen_id: str,
    food_name: str,
    amount: float,
) -> str:
    """
    Ghi nhận cho vật nuôi ăn tại chuồng được chỉ định và tự động trừ số lượng tồn kho tương ứng trong bảng inventory.

    Args:
        pen_id: Mã chuồng được cho ăn (ví dụ: '123', 'PEN-A02', 'PEN-ISO-01')
        food_name: Tên loại thức ăn (ví dụ: 'Cám Con Cò Siêu Tăng Trọng')
        amount: Số lượng thức ăn cho ăn (kg)
    """
    if amount <= 0:
        return "❌ Lượng thức ăn cho ăn phải lớn hơn 0."

    try:
        updated_stock = inventory_repo.adjust_quantity(
            item_name=food_name,
            delta_quantity=-abs(amount),
            pen_id=pen_id,
            note=f"Xuất cho chuồng {pen_id} ăn",
        )

        feed_log = feed_repo.log_feeding(pen_id=pen_id, food_name=food_name, amount=amount)

        _notify_websocket_safe("feed_update", {"feed_log": feed_log, "inventory": updated_stock})

        warning = ""
        if float(updated_stock.get("quantity", 0)) <= float(updated_stock.get("min_threshold", 5.0)):
            warning = f" ⚠️ CẢNH BÁO: Thức ăn '{food_name}' đã chạm/dưới ngưỡng an toàn ({updated_stock.get('quantity')} {updated_stock.get('unit')} còn lại)!"

        return f"✅ Đã ghi nhận cho chuồng {pen_id} ăn {amount} kg '{food_name}'. Tồn kho còn lại: {updated_stock.get('quantity')} {updated_stock.get('unit')}.{warning}"

    except ValueError as ve:
        return f"❌ Lỗi cho ăn: {str(ve)}"
    except Exception as e:
        logger.error(f"Error in log_feeding: {e}")
        return f"❌ Lỗi hệ thống khi ghi nhận cho ăn: {str(e)}"


@mcp.tool()
def update_animal_health(
    animal_id: str,
    status: str,
    note: str = "",
    health_type: str = "Disease",
) -> str:
    """
    Cập nhật tình trạng sức khỏe cho cá thể vật nuôi (Khỏe, Sốt, Bệnh, Cách ly) và lưu nhật ký y tế.

    Args:
        animal_id: Mã định danh cá thể (ví dụ: 'HEO-101', 'HEO-102', 'HEO-201')
        status: Trạng thái sức khỏe mới ('Khoe', 'Sot nhe', 'Bo an', 'Cach ly', ...)
        note: Ghi chú triệu chứng hoặc hướng điều trị
        health_type: Phân loại nhật ký ('Routine', 'Disease', 'Vaccine')
    """
    try:
        res = animals_repo.update_health_status(
            animal_id=animal_id,
            status=status,
            note=note,
            health_type=health_type,
        )
        _notify_websocket_safe("animal_update", res)
        return f"✅ Đã cập nhật sức khỏe vật nuôi '{animal_id}' sang trạng thái: [{status}]. Ghi chú y tế: {note or 'Không có'}."
    except Exception as e:
        logger.error(f"Error in update_animal_health: {e}")
        return f"❌ Lỗi khi cập nhật sức khỏe: {str(e)}"


@mcp.tool()
def manage_inventory(
    action: str,
    name: str,
    quantity: float = 0.0,
    unit: str = "kg",
    category: str = "Feed",
) -> str:
    """
    Quản lý kho thức ăn, thuốc thú y, phân bón: Thêm mới, nhập kho, xuất kho hoặc điều chỉnh.
    """
    action_clean = action.strip().lower()
    item_clean = name.strip()

    try:
        if action_clean in ["create", "add"]:
            created = inventory_repo.create_item(
                item_name=item_clean,
                quantity=quantity,
                unit=unit,
                category=category,
            )
            _notify_websocket_safe("inventory_update", {"action": "create", "item": created})
            return f"✅ Đã thêm mới mặt hàng '{item_clean}' ({category}) với số lượng {quantity} {unit}."

        elif action_clean in ["import", "increase", "add_stock"]:
            if quantity <= 0:
                return "❌ Số lượng nhập kho phải lớn hơn 0."
            updated = inventory_repo.adjust_quantity(item_name=item_clean, delta_quantity=abs(quantity))
            _notify_websocket_safe("inventory_update", {"action": "import", "item": updated})
            return f"✅ Đã nhập thêm {quantity} {updated.get('unit')} vào kho cho '{item_clean}'. Tồn kho hiện tại: {updated.get('quantity')} {updated.get('unit')}."

        elif action_clean in ["export", "decrease", "reduce_stock"]:
            if quantity <= 0:
                return "❌ Số lượng xuất kho phải lớn hơn 0."
            updated = inventory_repo.adjust_quantity(item_name=item_clean, delta_quantity=-abs(quantity))
            _notify_websocket_safe("inventory_update", {"action": "export", "item": updated})
            warning = ""
            if float(updated.get("quantity", 0)) <= float(updated.get("min_threshold", 5.0)):
                warning = f" ⚠️ CẢNH BÁO: Mặt hàng này hiện đã chạm/dưới ngưỡng an toàn ({updated.get('quantity')} {updated.get('unit')})!"
            return f"✅ Đã xuất {quantity} {updated.get('unit')} khỏi kho cho '{item_clean}'. Tồn kho còn lại: {updated.get('quantity')} {updated.get('unit')}.{warning}"

        else:
            return f"❌ Hành động '{action}' không hợp lệ. Hãy chọn: 'import', 'export', 'create'."

    except ValueError as ve:
        return f"❌ Lỗi kho: {str(ve)}"
    except Exception as e:
        logger.error(f"Error in manage_inventory: {e}")
        return f"❌ Lỗi hệ thống khi thao tác kho: {str(e)}"


@mcp.tool()
def manage_schedule(
    action: str,
    task_name: str,
    target_date: str = "",
    pen_id: str = "123",
    note: str = "",
) -> str:
    """
    Quản lý lịch trình công việc: Tạo lịch công việc mới hoặc cập nhật hoàn thành theo chuồng.
    """
    action_clean = action.strip().lower()
    task_clean = task_name.strip()

    try:
        final_date = target_date.strip() if target_date.strip() else date.today().isoformat()

        if action_clean in ["create", "add"]:
            created = schedules_repo.create_schedule(
                task_name=task_clean,
                target_date=final_date,
                pen_id=pen_id,
                note=note,
                status="pending",
            )
            _notify_websocket_safe("schedule_update", {"action": "create", "schedule": created})
            return f"✅ Đã lên lịch thành công cho công việc: '{task_clean}' vào ngày {final_date} (Chuồng {pen_id}). Ghi chú: {note or 'Không có'}."

        elif action_clean in ["done", "complete", "finish"]:
            updated = schedules_repo.update_schedule(
                task_name=task_clean,
                status="done",
                note=f"Hoàn thành lúc {date.today().isoformat()} - {note}" if note else None,
            )
            _notify_websocket_safe("schedule_update", {"action": "done", "schedule": updated})
            return f"🎉 Đã cập nhật công việc '{task_clean}' sang trạng thái HOÀN THÀNH."

        else:
            return f"❌ Hành động '{action}' không hợp lệ. Vui lòng chọn 'create' hoặc 'done'."

    except Exception as e:
        logger.error(f"Error in manage_schedule: {e}")
        return f"❌ Lỗi hệ thống khi thao tác lịch trình: {str(e)}"


@mcp.tool()
def create_system_alert(
    alert_type: str,
    message: str,
    pen_id: str = "123",
) -> str:
    """
    Tạo cảnh báo bất thường trong trang trại (môi trường, mùi hôi, sức khỏe vật nuôi, cạn kho) và phát realtime qua WebSocket.
    """
    try:
        created = alerts_repo.create_alert(alert_type=alert_type, message=message, pen_id=pen_id)
        _notify_websocket_safe("alert", created)
        return f"🚨 Đã phát và lưu cảnh báo thành công: [{created.get('alert_type')}] {created.get('message')} (Chuồng: {pen_id})."
    except Exception as e:
        logger.error(f"Error in create_system_alert: {e}")
        return f"❌ Lỗi khi ghi nhận cảnh báo: {str(e)}"


if __name__ == "__main__":
    print(f"🚀 Starting Smart Farm FastMCP Server: {settings.MCP_SERVER_NAME}...")
    mcp.run()
