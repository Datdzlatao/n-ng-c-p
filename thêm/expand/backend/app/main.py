"""
backend/app/main.py — FastAPI REST API Entry Point
Frontend web chạy RIÊNG BIỆT trên port khác hoặc serve bởi Nginx.
Backend CHỈ xử lý: /api/v1/*, /ws/*, /uploads/*, /health, /docs
"""
import logging, time
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

from app.config import (
    APP_TITLE, APP_VERSION, APP_DESCRIPTION, APP_DEBUG,
    CORS_ORIGINS, UPLOAD_DIR
)
from app.database import init_db, cleanup_expired_tokens
from app.services.cleanup_service import start_cleanup_scheduler, stop_cleanup_scheduler
from app.routers import auth, schools, students, attendance, disputes, leaves, classes, cameras, websocket, platform, health, compliance, biometric, notifications, posts, honor, parents, users

# ── Logging ──────────────────────────────────────
logging.basicConfig(
    level=logging.DEBUG if APP_DEBUG else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger("stem")


# ── Lifespan (FastAPI modern startup / shutdown) ───
@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("=" * 60)
    log.info(f"  {APP_TITLE} v{APP_VERSION}  [BACKEND ONLY]")
    log.info("  Frontend: http://localhost:5173  (run separately)")
    log.info("=" * 60)
    init_db()
    cleanup_expired_tokens()
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    start_cleanup_scheduler()
    log.info("[App] Backend API ready.")
    yield
    stop_cleanup_scheduler()
    log.info("[App] Backend shutdown complete.")


# ── FastAPI App ───────────────────────────────────
app = FastAPI(
    title=APP_TITLE,
    version=APP_VERSION,
    description=APP_DESCRIPTION,
    docs_url="/docs" if APP_DEBUG else None,
    redoc_url="/redoc" if APP_DEBUG else None,
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────
has_wildcard = "*" in CORS_ORIGINS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o for o in CORS_ORIGINS if o != "*"] if has_wildcard else CORS_ORIGINS,
    allow_origin_regex=(
        r"https?://(localhost|127\.0\.0\.1|0\.0\.0\.0|"
        r"10\.\d{1,3}\.\d{1,3}\.\d{1,3}|"
        r"192\.168\.\d{1,3}\.\d{1,3}|"
        r"172\.(1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}|"
        r".*\.trycloudflare\.com|.*\.ts\.net|.*edusams\.io\.vn)(:\d+)?$"
    ) if (has_wildcard or APP_DEBUG) else None,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Process-Time-ms"],
)

# ── Security & Timing Middleware ─────────────────
@app.middleware("http")
async def security_and_timing_middleware(request: Request, call_next):
    start    = time.time()
    response = await call_next(request)
    response.headers["X-Process-Time-ms"] = f"{(time.time()-start)*1000:.1f}"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    return response

# ── API Routers ───────────────────────────────────
app.include_router(platform.router)
app.include_router(auth.router)
app.include_router(schools.router)
app.include_router(students.router)
app.include_router(attendance.router)
app.include_router(disputes.router)
app.include_router(leaves.router)
app.include_router(classes.router)
app.include_router(cameras.router)
app.include_router(websocket.router)
app.include_router(health.router)
app.include_router(compliance.router)
app.include_router(biometric.router)
app.include_router(notifications.router)
app.include_router(posts.router)
app.include_router(honor.router)
app.include_router(parents.router)
app.include_router(users.router)

# ── Uploads (user-generated files only) ──────────
if UPLOAD_DIR.exists():
    app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

from starlette.responses import FileResponse

# ── Frontend Web Static Files (All-in-One Serving) ──
FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend-web"
DIST_DIR = FRONTEND_DIR / "dist"
APP_DIR = FRONTEND_DIR / "app"
ASSETS_DIR = FRONTEND_DIR / "assets"

# 1. Mount Dashboard Quản Trị Chuyên Sâu (/app/index.html)
if APP_DIR.exists():
    app.mount("/app", StaticFiles(directory=str(APP_DIR), html=True), name="dashboard_app")

# 2. Mount Assets Dùng Chung (CSS, JS, Biometric Face Scanner, Models & Bundles)
if ASSETS_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(ASSETS_DIR)), name="shared_assets")

SERVE_DIR = DIST_DIR if (DIST_DIR.exists() and (DIST_DIR / "index.html").exists()) else FRONTEND_DIR

@app.get("/")
@app.get("/index.html")
async def root(request: Request):
    if request.url.path == "/index.html" and (SERVE_DIR / "index.html").exists():
        return FileResponse(SERVE_DIR / "index.html")
    accept = request.headers.get("accept", "")
    if "text/html" in accept and (SERVE_DIR / "index.html").exists():
        return FileResponse(SERVE_DIR / "index.html")
    return {
        "service": APP_TITLE,
        "version": APP_VERSION,
        "status": "running",
        "docs": "/docs",
    }

# 3. Mount Trang Chủ Web SPA
if SERVE_DIR.exists():
    app.mount("/", StaticFiles(directory=str(SERVE_DIR), html=True), name="frontend")

