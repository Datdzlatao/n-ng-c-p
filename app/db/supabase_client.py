import logging
from typing import Optional
from supabase import Client, create_client
from app.config import get_settings

logger = logging.getLogger("smart_manager.supabase")

_supabase_client: Optional[Client] = None


def get_supabase_client() -> Client:
    """
    Get or initialize a singleton instance of the Supabase Client.
    Raises RuntimeError if credentials are not configured.
    """
    global _supabase_client
    if _supabase_client is not None:
        return _supabase_client

    settings = get_settings()

    if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
        raise RuntimeError(
            "Supabase credentials are missing! Please define SUPABASE_URL and SUPABASE_KEY in your .env file."
        )

    try:
        _supabase_client = create_client(
            supabase_url=settings.SUPABASE_URL,
            supabase_key=settings.SUPABASE_KEY,
        )
        logger.info("Supabase client initialized successfully with URL: %s", settings.SUPABASE_URL)
        return _supabase_client
    except Exception as e:
        logger.error("Failed to initialize Supabase client: %s", str(e))
        raise RuntimeError(f"Could not connect to Supabase: {str(e)}") from e


def test_supabase_connection() -> dict:
    """
    Test Supabase connection by executing lightweight queries across core farm tables.
    """
    settings = get_settings()
    if not settings.is_supabase_configured:
        return {
            "connected": False,
            "details": "SUPABASE_URL hoặc SUPABASE_KEY chưa được cấu hình trong .env",
            "tables": {},
        }

    try:
        client = get_supabase_client()
        tables_status = {}

        core_tables = ["pens", "env_logs", "devices", "animals", "inventory", "crops", "alerts", "schedules"]
        for table in core_tables:
            try:
                res = client.table(table).select("count", count="exact").limit(1).execute()
                tables_status[table] = {
                    "exists": True,
                    "count": res.count if hasattr(res, "count") else len(res.data),
                }
            except Exception as table_err:
                tables_status[table] = {
                    "exists": False,
                    "error": str(table_err),
                }

        connected_tables = [t for t, s in tables_status.items() if s.get("exists")]
        return {
            "connected": True,
            "connected_tables_count": len(connected_tables),
            "total_tables": len(core_tables),
            "details": f"Kết nối Supabase thành công! ({len(connected_tables)}/{len(core_tables)} bảng hoạt động).",
            "tables": tables_status,
        }
    except Exception as e:
        return {
            "connected": False,
            "details": f"Lỗi kết nối Supabase: {str(e)}",
            "tables": {},
        }
