"""
app/config.py — Centralized Settings
Multi-Tenant STEM Attendance Platform
"""
import os
import logging
from pathlib import Path

log = logging.getLogger("stem.config")

# ── Root Paths ──────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent

# ── Load .env if present ─────────────────────────────────────────
_env_file = BASE_DIR / ".env"
if _env_file.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(_env_file)
    except ImportError:
        with open(_env_file, "r", encoding="utf-8") as _f:
            for _line in _f:
                _line = _line.strip()
                if _line and not _line.startswith("#") and "=" in _line:
                    _k, _v = _line.split("=", 1)
                    _k, _v = _k.strip(), _v.strip()
                    if _k not in os.environ:
                        os.environ[_k] = _v

# ── Application ─────────────────────────────────────────────────
APP_TITLE        = "EduSAMS — Nền Tảng Điểm Danh Trường Học"
APP_VERSION      = "1.0.0"
APP_DESCRIPTION  = "Multi-tenant school attendance platform with AI camera integration"
APP_DEBUG        = os.getenv("DEBUG", "true").lower() == "true"

# ── Database ────────────────────────────────────────────────────
_custom_db = os.getenv("DATABASE_PATH")
DB_PATH = Path(_custom_db) if _custom_db else (BASE_DIR / "data" / "stem_platform.db")

# ── Security ────────────────────────────────────────────────────
_JWT_SECRET_DEFAULT = "REPLACE_WITH_STRONG_SECRET_IN_PROD_use_openssl_rand_hex_32"
JWT_SECRET        = os.getenv("JWT_SECRET", _JWT_SECRET_DEFAULT)
JWT_ALGORITHM     = "HS256"
JWT_EXPIRE_HOURS  = int(os.getenv("JWT_EXPIRE_HOURS", "1"))

# Kiểm tra bảo mật JWT_SECRET ngay lúc import config
if JWT_SECRET == _JWT_SECRET_DEFAULT:
    if not APP_DEBUG:
        # Production: bắt buộc phải đặt JWT_SECRET mạnh
        raise RuntimeError(
            "🚨 BẢO MẬT: JWT_SECRET vẫn là giá trị mặc định không an toàn! "
            "Hãy đặt biến môi trường JWT_SECRET=<chuỗi ngẫu nhiên 32+ bytes> "
            "trước khi chạy server production. "
            "Tạo bằng: openssl rand -hex 32"
        )
    else:
        # Development: cảnh báo rõ ràng
        log.warning(
            "⚠️  [DEV] JWT_SECRET đang dùng giá trị mặc định — KHÔNG AN TOÀN cho production! "
            "Đặt JWT_SECRET trong file .env trước khi deploy."
        )

PBKDF2_ITERATIONS = 100_000
PBKDF2_HASH       = "sha256"

# ── CORS ────────────────────────────────────────────────────────
_default_cors = (
    "http://localhost:5173,http://127.0.0.1:5173,"
    "http://localhost:3000,http://127.0.0.1:3000,"
    "http://localhost:8000,http://127.0.0.1:8000,"
    "https://edusams.io.vn,https://www.edusams.io.vn"
)
_cors_env = os.getenv("CORS_ORIGINS", _default_cors)
CORS_ORIGINS = [orig.strip() for orig in _cors_env.split(",") if orig.strip()]


# ── Uploads & Retention ──────────────────────────────────────────
UPLOAD_DIR             = BASE_DIR / "uploads"
MAX_UPLOAD_MB          = 10
RETENTION_DAYS         = int(os.getenv("RETENTION_DAYS", "8"))
CLEANUP_DELETE_RECORDS = os.getenv("CLEANUP_DELETE_RECORDS", "false").lower() == "true"

# ── OTP ─────────────────────────────────────────────────────────
OTP_EXPIRE_MINUTES = 5
OTP_LENGTH         = 6
OTP_DEV_MODE       = os.getenv("OTP_DEV_MODE", "true").lower() == "true"

# ── Notification ─────────────────────────────────────────────────
ZALO_OA_TOKEN  = os.getenv("ZALO_OA_TOKEN", "")
FCM_SERVER_KEY = os.getenv("FCM_SERVER_KEY", "")

# ── AI & Gemini ──────────────────────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL   = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

# ── Platform Admin ───────────────────────────────────────────────
# SECURITY: PLATFORM_ADMIN_PASSWORD chỉ dùng để seed lần đầu, KHÔNG dùng cho bypass login.
# Xác thực admin phải qua bảng platform_admins + verify_password() PBKDF2 — xem auth.py & platform.py.
PLATFORM_ADMIN_EMAIL    = os.getenv("PLATFORM_ADMIN_EMAIL", "admin@stemapp.vn")
PLATFORM_ADMIN_PASSWORD = os.getenv("PLATFORM_ADMIN_PASSWORD", "")  # Không có default — bắt buộc qua .env

# ── Static Files ────────────────────────────────────────────────
STATIC_DIR = BASE_DIR / "static"

# ── Rate Limiting & Redis ────────────────────────────────────────────────
REDIS_URL               = os.getenv("REDIS_URL", "")
JWT_REFRESH_EXPIRE_DAYS = int(os.getenv("JWT_REFRESH_EXPIRE_DAYS", "14"))
JWT_ACCESS_EXPIRE_MIN   = int(os.getenv("JWT_ACCESS_EXPIRE_MIN", "1440"))  # 24h default

# ── Database Hybrid (SQLite dev / PostgreSQL prod) ────────────────────────
# TODO [ARCHITECTURAL DEBT]: SQLite chỉ hỗ trợ Single Writer.
# Khi nhiều cổng trường đồng thời gửi điểm danh giờ cao điểm, nguy cơ
# "database is locked" rất cao. Cần migrate sang PostgreSQL cho production:
#   DATABASE_URL=postgresql+asyncpg://user:pass@host/db
#
# Bước tạm thời: database.py bật WAL mode (PRAGMA journal_mode=WAL)
# để tăng concurrency đọc/ghi trên SQLite hiện tại.
DATABASE_URL = os.getenv("DATABASE_URL", "")  # empty = SQLite default

if not DATABASE_URL and not APP_DEBUG:
    log.warning(
        "⚠️  [PRODUCTION] DATABASE_URL chưa được cấu hình — đang dùng SQLite. "
        "SQLite không phù hợp cho production multi-tenant. "
        "Hãy chuyển sang PostgreSQL: DATABASE_URL=postgresql+asyncpg://..."
    )

