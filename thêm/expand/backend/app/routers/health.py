"""
app/routers/health.py — Liveness & Readiness Probes
GET /health/live   → 200 luôn (process còn sống)
GET /health/ready  → 200 nếu DB OK, 503 nếu không
"""
import time
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from app.database import get_db
from app.config import APP_VERSION

router = APIRouter(prefix="/health", tags=["Health"])

_start_time = time.time()


@router.get("/live")
async def liveness():
    """Kubernetes/Docker liveness probe — always 200 if process is running."""
    return {"status": "alive", "version": APP_VERSION, "uptime_seconds": round(time.time() - _start_time)}


@router.get("/ready")
async def readiness():
    """Readiness probe — checks DB connectivity."""
    checks = {}
    overall_ok = True

    # SQLite DB check
    try:
        conn = get_db()
        conn.execute("SELECT 1").fetchone()
        conn.close()
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {e}"
        overall_ok = False

    # Redis check (optional — only if REDIS_URL is set)
    try:
        from app.config import REDIS_URL
        if REDIS_URL:
            import socket
            from urllib.parse import urlparse
            parsed = urlparse(REDIS_URL)
            host = parsed.hostname or "localhost"
            port = parsed.port or 6379
            s = socket.create_connection((host, port), timeout=1)
            s.close()
            checks["redis"] = "ok"
        else:
            checks["redis"] = "not_configured"
    except Exception as e:
        checks["redis"] = f"error: {e}"
        # Redis failure is non-fatal if not configured

    status_code = 200 if overall_ok else 503
    return JSONResponse(
        status_code=status_code,
        content={"status": "ready" if overall_ok else "not_ready", "checks": checks}
    )
