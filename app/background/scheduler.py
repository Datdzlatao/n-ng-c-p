import asyncio
import logging
from datetime import date, datetime, timezone
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.db.repositories.inventory import InventoryRepository
from app.db.repositories.schedules import SchedulesRepository
from app.db.repositories.animals import AnimalsRepository
from app.db.repositories.crops import CropsRepository
from app.api.websocket_manager import ws_manager
from app.config import get_settings

logger = logging.getLogger("smart_manager.scheduler")

_scheduler: Optional[AsyncIOScheduler] = None


async def run_morning_briefing() -> dict:
    """
    Quét lịch trình hôm nay, vật tư cạn, vật nuôi ốm và cây trồng sắp thu hoạch,
    kết hợp Gemini tạo bản tin trang trại buổi sáng và đẩy qua WebSocket.
    """
    logger.info("Executing daily morning briefing job for Smart Farm...")
    settings = get_settings()

    inventory_repo = InventoryRepository()
    schedules_repo = SchedulesRepository()
    animals_repo = AnimalsRepository()
    crops_repo = CropsRepository()

    today_str = date.today().isoformat()
    pending_tasks = []
    low_stocks = []
    sick_animals = []
    harvest_crops = []

    try:
        pending_tasks = schedules_repo.get_pending_schedules(target_date=today_str)
    except Exception as e:
        logger.warning(f"Scheduler could not read schedules: {e}")

    try:
        low_stocks = inventory_repo.get_low_stock()
    except Exception as e:
        logger.warning(f"Scheduler could not read inventory: {e}")

    try:
        sick_animals = animals_repo.get_sick_or_attention_animals()
    except Exception as e:
        logger.warning(f"Scheduler could not read animals: {e}")

    try:
        harvest_crops = crops_repo.get_upcoming_harvests(within_days=7)
    except Exception as e:
        logger.warning(f"Scheduler could not read crops: {e}")

    today_staff = []
    try:
        from app.db.repositories.staff import StaffRepository
        staff_repo = StaffRepository()
        today_staff = staff_repo.get_today_attendance()
    except Exception as e:
        logger.warning(f"Scheduler could not read staff attendance: {e}")

    # Xây dựng nội dung tóm tắt cho Gemini
    tasks_summary = "\n".join([f"- {t.get('task_name')} (Ghi chú: {t.get('note', '')})" for t in pending_tasks]) or "Hôm nay không có lịch trình nào."
    stocks_summary = "\n".join([f"- {i.get('name')}: còn {i.get('quantity')} {i.get('unit')} (Ngưỡng an toàn: {i.get('min_threshold')} {i.get('unit')})" for i in low_stocks]) or "Vật tư & thức ăn đều an toàn."
    animals_summary = "\n".join([f"- {a.get('id')} ({a.get('species')}): Trạng thái [{a.get('status')}], Ăn uống: {a.get('feeding_status')}" for a in sick_animals]) or "Tất cả vật nuôi đều khỏe mạnh."
    crops_summary = "\n".join([f"- {c.get('name')} (Chuồng/Khu {c.get('pen_id')}): Thu hoạch dự kiến sau {c.get('days_remaining')} ngày" for c in harvest_crops]) or "Chưa có cây trồng nào đến kỳ thu hoạch."

    briefing_text = ""

    if settings.is_gemini_configured:
        try:
            from google import genai
            client = genai.Client(api_key=settings.GEMINI_API_KEY)
            prompt = (
                f"Hôm nay là ngày {today_str}.\n"
                f"1. Công việc cần làm hôm nay:\n{tasks_summary}\n\n"
                f"2. Thức ăn / Vật tư đang thiếu:\n{stocks_summary}\n\n"
                f"3. Vật nuôi cần theo dõi sức khỏe:\n{animals_summary}\n\n"
                f"4. Cây trồng sắp thu hoạch:\n{crops_summary}\n\n"
                "Hãy đóng vai Trợ lý Quản lý Trang trại Nông Nghiệp Thông Minh, tổng hợp thành một bản tin chào buổi sáng tràn đầy năng lượng, súc tích (3-5 câu), chỉ rõ việc ưu tiên nhất hôm nay."
            )
            response = client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=prompt,
            )
            if response.text:
                briefing_text = response.text.strip()
        except Exception as e:
            logger.warning(f"Gemini briefing generation failed: {e}")

    if not briefing_text:
        briefing_text = (
            f"🌾 BẢN TIN TRANG TRẠI BUỔI SÁNG ({today_str}):\n"
            f"👤 Nhân sự có mặt: {len(today_staff)} người đã vào ca trực.\n"
            f"📋 Việc hôm nay: {len(pending_tasks)} nhiệm vụ cần làm.\n"
            f"⚠️ Kho thiếu: {len(low_stocks)} mặt hàng chạm ngưỡng.\n"
            f"🩺 Vật nuôi cần chăm sóc: {len(sick_animals)} cá thể.\n"
            f"🍉 Cây sắp thu hoạch: {len(harvest_crops)} vụ mùa."
        )

    briefing_payload = {
        "date": today_str,
        "content": briefing_text,
        "staff_present_count": len(today_staff),
        "tasks_count": len(pending_tasks),
        "low_stock_count": len(low_stocks),
        "sick_animals_count": len(sick_animals),
        "harvest_crops_count": len(harvest_crops),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # Phát sóng qua WebSocket tới tất cả Web/Mobile clients
    await ws_manager.broadcast(event="morning_briefing", data=briefing_payload)
    logger.info("Daily farm morning briefing sent via WebSocket.")
    return briefing_payload


def start_scheduler():
    """Start APScheduler in background."""
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler()
        # Schedule daily at 07:00 AM
        _scheduler.add_job(
            run_morning_briefing,
            trigger=CronTrigger(hour=7, minute=0),
            id="daily_morning_briefing",
            name="Daily Smart Farm Morning Briefing at 07:00",
            replace_existing=True,
        )
        _scheduler.start()
        logger.info("APScheduler initialized for Smart Farm.")


def stop_scheduler():
    """Stop APScheduler."""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("APScheduler stopped.")


async def trigger_daily_briefing() -> dict:
    """Manual trigger endpoint for testing or on-demand briefing."""
    return await run_morning_briefing()
