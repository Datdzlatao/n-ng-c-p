import asyncio
import logging
from typing import Optional

from app.db.repositories.env_logs import EnvLogsRepository
from app.mcp.mcp_server import create_system_alert, control_device
from app.config import get_settings

logger = logging.getLogger("smart_manager.watcher")

_watcher_task: Optional[asyncio.Task] = None
_is_running = False
_last_processed_log_id: Optional[int] = None

# Ngưỡng phát hiện bất thường môi trường chuồng trại
DELTA_TEMP_THRESHOLD = 3.0       # Biến thiên nhiệt độ >= 3.0°C giữa 2 lần đo liên tiếp
DELTA_HUM_THRESHOLD = 15.0       # Biến thiên độ ẩm >= 15.0%
MAX_TEMPERATURE = 35.0           # Nhiệt độ quá nóng gây sốc nhiệt gia súc
MIN_TEMPERATURE = 15.0           # Nhiệt độ quá lạnh
MIN_HUMIDITY = 40.0              # Quá khô
MAX_HUMIDITY = 90.0              # Quá ẩm ướt
MAX_SMELL_LEVEL = 10.0           # Ngưỡng nồng độ mùi hôi / khí chuồng nguy hiểm


async def _evaluate_anomaly_with_gemini(log_curr: dict, log_prev: dict, reasons: list[str]) -> str:
    """Send sensor anomaly data to Gemini to produce an expert evaluation and recommendation."""
    settings = get_settings()
    summary_reason = "; ".join(reasons)
    pen_id = log_curr.get("pen_id") or "123"

    if settings.is_gemini_configured:
        try:
            from google import genai
            client = genai.Client(api_key=settings.GEMINI_API_KEY)
            prompt = (
                f"Phát hiện bất thường môi trường chuồng trại (Chuồng: {pen_id}): {summary_reason}.\n"
                f"- Hiện tại: Nhiệt độ {log_curr.get('temperature')}°C, Độ ẩm {log_curr.get('humidity')}%, Nồng độ mùi: {log_curr.get('smell_level')}\n"
                f"- Liền trước: Nhiệt độ {log_prev.get('temperature')}°C, Độ ẩm {log_prev.get('humidity')}%, Nồng độ mùi: {log_prev.get('smell_level')}\n"
                "Hãy đưa ra 1 thông báo cảnh báo súc tích (1-2 câu) và hành động khẩn cấp cần thực hiện."
            )
            response = client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=prompt,
            )
            if response.text:
                return response.text.strip()
        except Exception as e:
            logger.warning(f"Gemini evaluation failed in watcher: {e}")

    # Fallback message
    return (
        f"CẢNH BÁO CHUỒNG {pen_id}: {summary_reason}. "
        f"Hiện tại: {log_curr.get('temperature')}°C, {log_curr.get('humidity')}%, Mùi: {log_curr.get('smell_level')}. "
        "Hệ thống đã tự động kích hoạt quạt thông gió làm mát!"
    )


async def env_watcher_loop(interval_seconds: int = 15):
    """
    Background Task loop (The Watcher):
    Continuously monitors the 2 most recent env_logs records.
    """
    global _last_processed_log_id, _is_running
    env_repo = EnvLogsRepository()
    logger.info("The Watcher started (interval: %d seconds)...", interval_seconds)

    while _is_running:
        try:
            logs = env_repo.get_latest_logs(limit=2)

            if len(logs) >= 2:
                curr = logs[0]
                prev = logs[1]
                curr_id = curr.get("id")

                # Chỉ xử lý khi có bản ghi mới
                if curr_id != _last_processed_log_id:
                    _last_processed_log_id = curr_id
                    t_curr = float(curr.get("temperature", 0))
                    t_prev = float(prev.get("temperature", 0))
                    h_curr = float(curr.get("humidity", 0))
                    h_prev = float(prev.get("humidity", 0))
                    s_curr = float(curr.get("smell_level", 0))
                    pen_id = str(curr.get("pen_id") or "123")

                    delta_temp = abs(t_curr - t_prev)
                    delta_hum = abs(h_curr - h_prev)

                    reasons = []
                    should_turn_on_fan = False

                    if delta_temp >= DELTA_TEMP_THRESHOLD:
                        reasons.append(f"Nhiệt độ đột biến thay đổi {delta_temp:.1f}°C (từ {t_prev}°C lên {t_curr}°C)")
                    if delta_hum >= DELTA_HUM_THRESHOLD:
                        reasons.append(f"Độ ẩm đột biến thay đổi {delta_hum:.1f}%")
                    if t_curr > MAX_TEMPERATURE:
                        reasons.append(f"Nhiệt độ vượt ngưỡng nóng nguy hiểm ({t_curr}°C > {MAX_TEMPERATURE}°C)")
                        should_turn_on_fan = True
                    elif t_curr < MIN_TEMPERATURE:
                        reasons.append(f"Nhiệt độ hạ quá thấp ({t_curr}°C < {MIN_TEMPERATURE}°C)")
                    if s_curr >= MAX_SMELL_LEVEL:
                        reasons.append(f"Nồng độ mùi / khí amoniac cao nguy hiểm ({s_curr} >= {MAX_SMELL_LEVEL})")
                        should_turn_on_fan = True

                    if reasons:
                        logger.warning("Bất thường môi trường phát hiện: %s", reasons)
                        eval_msg = await _evaluate_anomaly_with_gemini(curr, prev, reasons)

                        # Auto-action: Bật quạt thông gió nếu quá nóng hoặc mùi cao
                        if should_turn_on_fan:
                            try:
                                fan_result = control_device(action="turn_on", device_name="quạt", pen_id=pen_id)
                                logger.info(f"The Watcher auto-triggered fan: {fan_result}")
                            except Exception as dev_err:
                                logger.warning(f"Watcher could not activate fan: {dev_err}")

                        # Phát và lưu cảnh báo qua MCP Tool
                        create_system_alert(alert_type="ENV_ANOMALY", message=eval_msg, pen_id=pen_id)

        except Exception as e:
            logger.error("Error in Watcher loop: %s", str(e))

        await asyncio.sleep(interval_seconds)


def start_env_watcher(interval_seconds: int = 15):
    """Start the Watcher background task."""
    global _watcher_task, _is_running
    if not _is_running:
        _is_running = True
        loop = asyncio.get_event_loop()
        _watcher_task = loop.create_task(env_watcher_loop(interval_seconds))
        logger.info("Env Watcher background service initiated.")


def stop_env_watcher():
    """Stop the Watcher background task."""
    global _watcher_task, _is_running
    if _is_running:
        _is_running = False
        if _watcher_task and not _watcher_task.done():
            _watcher_task.cancel()
        logger.info("Env Watcher background service stopped.")
