"""
=============================================================================
  CLOUD_SERVER.PY — Điểm Danh & Quản Lý Nề Nếp STEM Pro v5.2
  FastAPI + Uvicorn + WebSocket Real-time Broadcast + Multi-Tenant RBAC
=============================================================================

Kiến trúc & Phân quyền 5 vai trò (Update 5):
  ┌───────────────────────────────────────────────────────────────────────┐
  │ 1. Hiệu Trưởng / BGH (School Super Admin):                            │
  │    - Cấu hình trường, niên khóa, quy chế nề nếp, trạm Camera AI.      │
  │    - Ký duyệt bảng thi đua tuần/tháng, xuất báo cáo Sở/Phòng GD&ĐT.   │
  │ 2. Giáo Viên Chủ Nhiệm (GVCN - Class Manager):                        │
  │    - Quản lý lớp, duyệt học sinh & ảnh AI 1-chạm.                     │
  │    - Xử lý khiếu nại Cấp 1 (đối soát ảnh camera gốc), duyệt nghỉ phép.│
  │ 3. Giám Thị / Ban Thi Đua (Inspector & Discipline Board):             │
  │    - Giám sát camera trực tiếp, nhận cảnh báo vi phạm đỏ tức thì.     │
  │    - Xử lý khiếu nại Cấp 2 leo thang, chấm điểm thi đua các lớp.      │
  │ 4. Phụ Huynh (Parent / Guardian - Low-Tech 1-Chạm):                   │
  │    - Thanh tìm kiếm to bản tìm con, chạm thẻ liên kết qua SĐT.        │
  │    - Xem giờ vào cổng, ảnh camera thực tế, nộp đơn phép & khiếu nại.  │
  │ 5. Học Sinh (Student):                                                │
  │    - Điền form, chụp ảnh AI, xem mã QR điện tử, theo dõi tiến trình. │
  └───────────────────────────────────────────────────────────────────────┘

Khởi động:
    python cloud_server.py
    # Hoặc qua Uvicorn:
    uvicorn cloud_server:app --host 0.0.0.0 --port 8000 --reload
=============================================================================
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import re
import shutil
import sqlite3
import time
import traceback
import uuid
from contextlib import asynccontextmanager
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import aiosqlite
import uvicorn
from fastapi import (
    BackgroundTasks,
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

# ──────────────────────────────────────────────────────────────
#  LOGGING SETUP
# ──────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("cloud_server_v5.2")

# ──────────────────────────────────────────────────────────────
#  PATHS & DIRECTORIES
# ──────────────────────────────────────────────────────────────
BASE_DIR       = Path(__file__).resolve().parent
STATIC_DIR     = BASE_DIR / "static"
DATA_DIR       = BASE_DIR / "data"
VIOLATIONS_DIR = DATA_DIR / "violations"
STUFACE_DIR    = DATA_DIR / "stuface"
DB_PATH        = DATA_DIR / "database.db"

DATA_DIR.mkdir(exist_ok=True)
VIOLATIONS_DIR.mkdir(exist_ok=True)
STUFACE_DIR.mkdir(exist_ok=True)
STATIC_DIR.mkdir(exist_ok=True)

# ──────────────────────────────────────────────────────────────
#  CONFIG FROM ENVIRONMENT
# ──────────────────────────────────────────────────────────────
SERVER_HOST      = os.getenv("STEM_HOST",     "0.0.0.0")
SERVER_PORT      = int(os.getenv("STEM_PORT", "8000"))
API_SECRET_KEY   = os.getenv("STEM_API_KEY",  "")
SHEETS_ENABLE    = os.getenv("STEM_SHEETS",   "0") == "1"
CREDENTIALS_FILE = os.getenv("STEM_CREDENTIALS_FILE", "")
SPREADSHEET_ID   = os.getenv("STEM_SPREADSHEET_ID", "1CLE7GcJNAiJe1irURuCWzq9WaSPZJPLaoufW9lXythU")
WS_PING_INTERVAL = int(os.getenv("STEM_WS_PING", "20"))


# ──────────────────────────────────────────────────────────────
#  PYDANTIC SCHEMAS (v5.2)
# ──────────────────────────────────────────────────────────────

class SchoolConfig(BaseModel):
    name:          str = Field(..., description="Tên trường học")
    school_code:   str = Field(..., description="Mã định danh trường")
    academic_year: Optional[str] = "2025-2026"
    rules_config:  Optional[Dict[str, Any]] = None
    form_config:   Optional[Dict[str, Any]] = None


class CameraStationCreate(BaseModel):
    name:        str
    location:    str
    stream_url:  Optional[str] = ""
    secret_key:  Optional[str] = ""
    is_active:   Optional[int] = 1


class ClassCreate(BaseModel):
    name:         str
    grade:        Optional[str] = ""
    teacher_name: Optional[str] = ""
    invite_code:  Optional[str] = ""


class UserRegister(BaseModel):
    username:             str
    password:             str
    full_name:            str
    email:                Optional[str] = None
    phone:                Optional[str] = None
    role:                 str = "STUDENT"  # HEADMASTER, VICE_HEADMASTER, TEACHER, INSPECTOR, STUDENT, PARENT
    student_code:         Optional[str] = None
    class_name:           Optional[str] = None
    invite_code:          Optional[str] = None
    verification_doc_url: Optional[str] = None


class UserLogin(BaseModel):
    username_or_phone: str
    password:          str


class RequestOTP(BaseModel):
    target:   str
    otp_type: Optional[str] = "PHONE_REGISTER"


class SubmitOTP(BaseModel):
    target:   str
    otp_code: str


class SubmitIDCard(BaseModel):
    doc_type:      str = "CCCD"
    doc_data_url:  str
    student_code:  Optional[str] = None
    note:          Optional[str] = None


class ApproveVerification(BaseModel):
    user_id: int
    status:  str = "VERIFIED"  # "VERIFIED" or "REJECTED"
    note:    Optional[str] = None


class ParentLinkRequest(BaseModel):
    ma_hs:        str
    parent_name:  str
    parent_phone: str
    relation:     Optional[str] = "Phụ huynh"


class DisputeCreate(BaseModel):
    attendance_log_id: Optional[int] = None
    ma_hs:             str
    ho_ten:            Optional[str] = ""
    lop:               Optional[str] = ""
    level:             Optional[str] = "LEVEL_1_TEACHER"
    reason:            str
    proof_image_url:   Optional[str] = None
    student_evidence:  Optional[str] = None


class DisputeResolveRequest(BaseModel):
    action:            str  # "APPROVE", "REJECT", "ESCALATE"
    resolution_note:   Optional[str] = ""
    resolver_name:     Optional[str] = "GVCN"
    reimburse_points:  Optional[int] = 5


class LeaveRequestCreate(BaseModel):
    ma_hs:        str
    ho_ten:       Optional[str] = ""
    lop:          Optional[str] = ""
    parent_name:  str
    parent_phone: str
    start_date:   str
    end_date:     Optional[str] = None
    reason:       str


class DisciplineScoreSubmitRequest(BaseModel):
    class_name:       str
    week_number:      int
    month_number:     int
    year:             Optional[int] = 2026
    attendance_score: float = 100.0
    uniform_score:    float = 100.0
    discipline_score: float = 100.0
    bonus_points:     float = 0.0
    inspector_notes:  Optional[str] = ""
    inspector_name:   Optional[str] = "Giám Thị"


class AttendanceEvent(BaseModel):
    ma_hs:             str
    ho_ten:            str
    trang_thai:        str = "Vao"
    thoi_gian:         Optional[str] = None
    lop:               Optional[str] = None
    camera_station_id: Optional[int] = 1
    device_id:         Optional[str] = None
    uniform_status:    Optional[str] = "VALID"
    proof_image_url:   Optional[str] = None

    @field_validator("thoi_gian", mode="before")
    @classmethod
    def default_thoi_gian(cls, v):
        return v or datetime.now().strftime("%d/%m/%Y %H:%M:%S")


class StatsResponse(BaseModel):
    date:             str
    total_students:   int
    present:          int
    absent:           int
    violation_count:  int
    pending_students: int
    pending_disputes: int
    pending_leaves:   int
    attendance_rate:  float
    generated_at:     str


# ──────────────────────────────────────────────────────────────
#  WEBSOCKET BROADCAST MANAGER
# ──────────────────────────────────────────────────────────────

class WebSocketManager:
    """Quản lý các kết nối WebSocket thời gian thực (Giám thị, GVCN, Phụ huynh)."""

    def __init__(self) -> None:
        self._clients: Dict[str, WebSocket] = {}
        self._lock = asyncio.Lock()
        self.total_connected = 0
        self.total_messages  = 0

    async def connect(self, ws: WebSocket) -> str:
        await ws.accept()
        cid = str(uuid.uuid4())[:8]
        async with self._lock:
            self._clients[cid] = ws
            self.total_connected += 1
        log.info(f"[WS] Client {cid} kết nối — Tổng kết nối: {len(self._clients)}")
        await self._send_one(cid, ws, {
            "event": "connected",
            "client_id": cid,
            "server_time": datetime.now().isoformat(),
            "message": "Kết nối WebSocket thành công — Hệ thống STEM Pro v5.2",
        })
        return cid

    async def disconnect(self, cid: str) -> None:
        async with self._lock:
            self._clients.pop(cid, None)
        log.info(f"[WS] Client {cid} ngắt kết nối — Còn lại: {len(self._clients)}")

    async def broadcast(self, payload: Dict[str, Any]) -> int:
        if not self._clients:
            return 0
        text = json.dumps(payload, ensure_ascii=False)
        dead: List[str] = []
        success = 0

        async with self._lock:
            items = list(self._clients.items())

        for cid, ws in items:
            ok = await self._send_one(cid, ws, None, text=text)
            if ok:
                success += 1
            else:
                dead.append(cid)

        if dead:
            async with self._lock:
                for cid in dead:
                    self._clients.pop(cid, None)

        self.total_messages += 1
        return success

    async def _send_one(
        self,
        cid: str,
        ws: WebSocket,
        payload: Optional[Dict],
        text: Optional[str] = None,
    ) -> bool:
        try:
            await ws.send_text(text or json.dumps(payload, ensure_ascii=False))
            return True
        except Exception:
            return False

    @property
    def client_count(self) -> int:
        return len(self._clients)


ws_manager = WebSocketManager()


# ──────────────────────────────────────────────────────────────
#  ASYNC BACKGROUND WORKER (I/O QUEUE)
# ──────────────────────────────────────────────────────────────

class AsyncIOWorker:
    """Xử lý I/O nền (SQLite + Google Sheets) không block event loop."""

    def __init__(self) -> None:
        self._queue:   asyncio.Queue = asyncio.Queue(maxsize=1000)
        self._running: bool          = False
        self._task:    Optional[asyncio.Task] = None
        self._sheet_log: Any = None
        self._sheet_vio: Any = None
        self._sheet_sum: Any = None
        self.processed = 0
        self.failed    = 0
        self.queue_size = 0

    async def start(self) -> None:
        self._running = True
        self._task = asyncio.create_task(self._worker_loop(), name="io_worker")
        log.info("[Worker] Async I/O Worker v5.2 đã khởi động.")
        if SHEETS_ENABLE:
            await asyncio.get_event_loop().run_in_executor(None, self._init_sheets)

    async def stop(self) -> None:
        self._running = False
        if self._task:
            try:
                await asyncio.wait_for(self._queue.join(), timeout=3.0)
            except asyncio.TimeoutError:
                pass
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        log.info("[Worker] Async I/O Worker đã dừng.")

    def _init_sheets(self) -> None:
        if not CREDENTIALS_FILE or not os.path.isfile(CREDENTIALS_FILE):
            return
        try:
            import gspread
            from oauth2client.service_account import ServiceAccountCredentials
            scope  = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
            creds  = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
            client = gspread.authorize(creds)
            ss     = client.open_by_key(SPREADSHEET_ID)
            self._sheet_log = ss.worksheet("Log")
            self._sheet_vio = ss.worksheet("PhamLoi")
            self._sheet_sum = ss.worksheet("TongKet")
            log.info("[Sheets] Đồng bộ Google Sheets đã kết nối.")
        except Exception as e:
            log.error(f"[Sheets] Lỗi kết nối Google Sheets: {e}")

    async def _worker_loop(self) -> None:
        while self._running:
            try:
                task = await asyncio.wait_for(self._queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break

            try:
                t = task.get("type")
                d = task.get("data")
                if t == "LOG_ATTENDANCE":
                    await self._write_attendance(d)
                elif t == "LOG_VIOLATION":
                    await self._write_violation(d)
                elif t == "WRITE_SUMMARY":
                    await self._write_summary(d)
                self.processed += 1
            except Exception as e:
                self.failed += 1
                log.error(f"[Worker] Lỗi xử lý task '{task.get('type')}': {e}")
            finally:
                self._queue.task_done()
                self.queue_size = self._queue.qsize()

    async def _write_attendance(self, data: Dict[str, Any]) -> None:
        thoi_gian  = data.get("thoi_gian", datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
        ma_hs      = data.get("ma_hs", "")
        ho_ten     = data.get("ho_ten", "")
        trang_thai = data.get("trang_thai", "Vao")
        lop        = data.get("lop", "")
        cam_id     = data.get("camera_station_id", 1)
        u_stat     = data.get("uniform_status", "VALID")
        p_url      = data.get("proof_image_url", None)

        async with aiosqlite.connect(str(DB_PATH)) as db:
            await db.execute(
                """
                INSERT INTO offline_log 
                (thoi_gian, ma_hs, ho_ten, lop, camera_station_id, trang_thai, attendance_status, uniform_status, proof_image_url, synced)
                VALUES (?, ?, ?, ?, ?, ?, 'ON_TIME', ?, ?, 1)
                """,
                (thoi_gian, ma_hs, ho_ten, lop, cam_id, trang_thai, u_stat, p_url),
            )
            await db.commit()

        # Google Sheets append nếu có
        if self._sheet_log:
            try:
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self._sheet_log.append_row([thoi_gian, ma_hs, ho_ten, trang_thai], value_input_option="RAW"),
                )
            except Exception:
                pass

    async def _write_violation(self, data: Dict[str, Any]) -> None:
        thoi_gian = data.get("thoi_gian", datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
        ma_hs     = data.get("ma_hs", "")
        ho_ten    = data.get("ho_ten", "")
        mo_ta     = data.get("mo_ta", "")
        lop       = data.get("lop", "")
        ten_file  = data.get("ten_file", "")
        duong_dan = data.get("duong_dan", "")

        async with aiosqlite.connect(str(DB_PATH)) as db:
            await db.execute(
                """
                INSERT INTO offline_violation 
                (thoi_gian, ma_hs, ho_ten, lop, mo_ta, ten_file, duong_dan, synced)
                VALUES (?, ?, ?, ?, ?, ?, ?, 1)
                """,
                (thoi_gian, ma_hs, ho_ten, lop, mo_ta, ten_file, duong_dan),
            )
            # Trừ điểm nề nếp của học sinh
            if ma_hs and not ma_hs.startswith("STRANGER"):
                await db.execute(
                    "UPDATE HocSinh SET current_points = MAX(0, current_points - 5) WHERE ma_hs = ?",
                    (ma_hs,)
                )
            await db.commit()

    async def _write_summary(self, data: Dict[str, Any]) -> None:
        pass

    async def put_task(self, task_type: str, data: Any = None) -> None:
        try:
            self._queue.put_nowait({"type": task_type, "data": data})
        except asyncio.QueueFull:
            log.error(f"[Worker] Queue đầy! Task {task_type} bị bỏ qua.")


io_worker = AsyncIOWorker()


# ──────────────────────────────────────────────────────────────
#  DATABASE HELPERS & LIFESPAN
# ──────────────────────────────────────────────────────────────

async def ensure_schema() -> None:
    """Đảm bảo cơ sở dữ liệu và các bảng Multi-Tenant v5.2 luôn đầy đủ."""
    from init_db import SCHEMA_SQL, INDEX_SQL, seed_default_data, migrate_schema
    conn = sqlite3.connect(str(DB_PATH))
    try:
        cur = conn.cursor()
        cur.executescript(SCHEMA_SQL)
        for sql in INDEX_SQL:
            cur.execute(sql)
        conn.commit()
        migrate_schema(conn)
        seed_default_data(conn)
    finally:
        conn.close()
    log.info("[DB] Cấu trúc Database Multi-Tenant v5.2 đã kiểm tra thành công.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("=" * 60)
    log.info("  STEM CLOUD SERVER v5.2 — Fast, Multi-Tenant, Low-Tech UX")
    log.info("=" * 60)
    await ensure_schema()
    await io_worker.start()

    # Periodic ping
    async def periodic_ping():
        while True:
            await asyncio.sleep(WS_PING_INTERVAL)
            if ws_manager.client_count > 0:
                await ws_manager.broadcast({
                    "event": "ping",
                    "server_time": datetime.now().isoformat(),
                    "clients": ws_manager.client_count,
                })

    asyncio.create_task(periodic_ping(), name="ws_ping")
    yield
    await io_worker.stop()


# ──────────────────────────────────────────────────────────────
#  FASTAPI APPLICATION
# ──────────────────────────────────────────────────────────────

app = FastAPI(
    title        = "Hệ Thống Điểm Danh STEM Pro v5.2",
    description  = "Cloud Server hỗ trợ Đa Trường Học (Multi-Tenant), Phân quyền 5 vai trò, UI Desktop Launchpad & Mobile Card Feed.",
    version      = "5.2.0",
    docs_url     = "/docs",
    redoc_url    = "/redoc",
    lifespan     = lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins     = ["*"],
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)

# Mount static directories
if VIOLATIONS_DIR.exists():
    app.mount("/violations", StaticFiles(directory=str(VIOLATIONS_DIR)), name="violations")
if STUFACE_DIR.exists():
    app.mount("/stuface", StaticFiles(directory=str(STUFACE_DIR)), name="stuface")
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


def require_api_key(req: Request):
    if API_SECRET_KEY:
        k = req.headers.get("X-API-Key") or req.query_params.get("api_key")
        if k != API_SECRET_KEY:
            raise HTTPException(status_code=401, detail="Invalid API Key")
    return True


def _clean_ascii(text: str) -> str:
    import unicodedata
    nfkd = unicodedata.normalize('NFKD', text)
    ascii_txt = "".join([c for c in nfkd if not unicodedata.combining(c)])
    return re.sub(r'[^a-zA-Z0-9_]', '', ascii_txt.replace(' ', '_'))


# ──────────────────────────────────────────────────────────────
#  CORE ENDPOINTS: PWA & WEBSOCKET
# ──────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse, tags=["PWA"])
async def serve_index():
    index_file = STATIC_DIR / "index.html"
    if not index_file.exists():
        return HTMLResponse("<h1>Trang web đang được tải...</h1>", status_code=200)
    return FileResponse(str(index_file), media_type="text/html")


@app.websocket("/ws/live")
@app.websocket("/ws/alerts")
async def websocket_live_endpoint(ws: WebSocket):
    cid = await ws_manager.connect(ws)
    try:
        while True:
            data = await ws.receive_text()
            # Echo heartbeat or client commands
            try:
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await ws.send_text(json.dumps({"event": "pong", "time": datetime.now().isoformat()}))
            except Exception:
                pass
    except WebSocketDisconnect:
        await ws_manager.disconnect(cid)
    except Exception:
        await ws_manager.disconnect(cid)


# ──────────────────────────────────────────────────────────────
#  AUTHENTICATION & VERIFIED ACCOUNT HELPERS
# ──────────────────────────────────────────────────────────────
import hashlib
import secrets
import hmac

JWT_SECRET = os.getenv("STEM_JWT_SECRET", "stem_super_secret_signing_key_2026_v5.2")


def hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
    if not salt:
        salt = secrets.token_hex(16)
    pwd_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000).hex()
    return pwd_hash, salt


def verify_password(password: str, salt: str, expected_hash: str) -> bool:
    pwd_hash, _ = hash_password(password, salt)
    return hmac.compare_digest(pwd_hash, expected_hash)


def create_access_token(data: dict, expires_in_seconds: int = 86400 * 7) -> str:
    header = base64.urlsafe_b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode()).decode().rstrip("=")
    payload_data = data.copy()
    payload_data["exp"] = int(time.time()) + expires_in_seconds
    payload_data["iat"] = int(time.time())
    payload = base64.urlsafe_b64encode(json.dumps(payload_data).encode()).decode().rstrip("=")
    signing_input = f"{header}.{payload}".encode()
    signature = hmac.new(JWT_SECRET.encode(), signing_input, hashlib.sha256).digest()
    sig_b64 = base64.urlsafe_b64encode(signature).decode().rstrip("=")
    return f"{header}.{payload}.{sig_b64}"


def decode_access_token(token: str) -> Optional[dict]:
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        header_b64, payload_b64, sig_b64 = parts
        signing_input = f"{header_b64}.{payload_b64}".encode()
        expected_sig = hmac.new(JWT_SECRET.encode(), signing_input, hashlib.sha256).digest()

        rem = len(sig_b64) % 4
        if rem > 0:
            sig_b64 += "=" * (4 - rem)
        actual_sig = base64.urlsafe_b64decode(sig_b64.encode())
        if not hmac.compare_digest(expected_sig, actual_sig):
            return None

        rem_p = len(payload_b64) % 4
        if rem_p > 0:
            payload_b64 += "=" * (4 - rem_p)
        payload = json.loads(base64.urlsafe_b64decode(payload_b64.encode()).decode())
        if payload.get("exp", 0) < time.time():
            return None
        return payload
    except Exception:
        return None


async def get_current_user_optional(req: Request) -> Optional[Dict[str, Any]]:
    auth = req.headers.get("Authorization") or ""
    token = ""
    if auth.startswith("Bearer "):
        token = auth.split(" ")[1]
    elif "token" in req.query_params:
        token = req.query_params["token"]
    if not token:
        return None
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        return None
    user_id = payload["sub"]
    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        row = await (await db.execute("SELECT * FROM users WHERE id = ?", (user_id,))).fetchone()
        if row:
            d = dict(row)
            d.pop("password_hash", None)
            d.pop("salt", None)
            return d
    return None


# ──────────────────────────────────────────────────────────────
#  AUTH & VERIFIED ACCOUNTS ENDPOINTS
# ──────────────────────────────────────────────────────────────

@app.post("/api/v1/auth/register", tags=["Auth & Verification"])
async def auth_register(req_data: UserRegister):
    """Đăng ký tài khoản người dùng thực tế & Tự động xác minh nếu khớp danh bộ."""
    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row

        # 1. Kiểm tra trùng lặp username / email
        existing = await (await db.execute(
            "SELECT id FROM users WHERE username = ? OR (email = ? AND email IS NOT NULL)",
            (req_data.username.strip(), req_data.email.strip() if req_data.email else None)
        )).fetchone()
        if existing:
            raise HTTPException(status_code=400, detail="Tên đăng nhập hoặc Email đã tồn tại trong hệ thống.")

        # 2. Logic Xác minh tài khoản (Verified Status)
        verified_status     = "UNVERIFIED"
        verification_method = "AUTO_MATCH"
        verification_note   = ""
        verified_at         = None
        now_str             = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

        # Phân tích theo vai trò:
        if req_data.role == "STUDENT":
            if req_data.student_code:
                st_row = await (await db.execute("SELECT * FROM HocSinh WHERE ma_hs = ?", (req_data.student_code.strip(),))).fetchone()
                if st_row:
                    verified_status     = "VERIFIED"
                    verification_method = "AUTO_MATCH"
                    verification_note   = f"Tự động xác minh khớp danh bộ học sinh {st_row['ho_ten']} ({st_row['lop']})"
                    verified_at         = now_str
                else:
                    verified_status     = "PENDING_REVIEW"
                    verification_method = "ID_CARD"
                    verification_note   = "Mã học sinh chưa có trong danh bộ, chờ GVCN/Nhà trường duyệt hồ sơ"
            else:
                verified_status = "PENDING_REVIEW"

        elif req_data.role == "PARENT":
            if req_data.student_code:
                st_row = await (await db.execute("SELECT * FROM HocSinh WHERE ma_hs = ?", (req_data.student_code.strip(),))).fetchone()
                if st_row:
                    # Khớp số điện thoại hoặc mã học sinh
                    if req_data.phone and st_row["sdt_phu_huynh"] and req_data.phone.strip() == st_row["sdt_phu_huynh"].strip():
                        verified_status     = "VERIFIED"
                        verification_method = "AUTO_MATCH"
                        verification_note   = f"Tự động xác minh: SĐT khớp 100% hồ sơ phụ huynh em {st_row['ho_ten']}"
                        verified_at         = now_str
                    else:
                        verified_status     = "VERIFIED"
                        verification_method = "AUTO_MATCH"
                        verification_note   = f"Liên kết học sinh {st_row['ho_ten']} ({st_row['lop']})"
                        verified_at         = now_str
            else:
                verified_status = "UNVERIFIED"

        elif req_data.role in ("HEADMASTER", "VICE_HEADMASTER", "INSPECTOR", "TEACHER"):
            # Kiểm tra mã mời đặc quyền (Secret Invite Code)
            if req_data.invite_code and req_data.invite_code.strip().upper() in ("STEM_BGH_2026", "STEM_TEACHER_2026", "INV-10A1", "INV-10A2", "INV-10A3"):
                verified_status     = "VERIFIED"
                verification_method = "HEADMASTER_INVITE"
                verification_note   = f"Xác minh qua mã mời đặc quyền sư phạm {req_data.invite_code}"
                verified_at         = now_str
            else:
                verified_status     = "PENDING_REVIEW"
                verification_method = "HEADMASTER_INVITE"
                verification_note   = "Chờ Hiệu Trưởng / Quản trị viên nhà trường phê duyệt tài khoản giáo viên/cán bộ"

        # 3. Băm mật khẩu an toàn
        pwd_hash, salt = hash_password(req_data.password)

        # 4. Lưu vào CSDL
        cursor = await db.execute(
            """
            INSERT INTO users 
            (school_id, username, email, phone, password_hash, salt, full_name, role, 
             verified_status, verification_method, verification_doc_url, verification_note, verified_at, student_code, class_name)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                1, req_data.username.strip(), req_data.email.strip() if req_data.email else None,
                req_data.phone.strip() if req_data.phone else None, pwd_hash, salt,
                req_data.full_name.strip(), req_data.role, verified_status, verification_method,
                req_data.verification_doc_url, verification_note, verified_at,
                req_data.student_code.strip() if req_data.student_code else None,
                req_data.class_name.strip() if req_data.class_name else None
            )
        )
        user_id = cursor.lastrowid

        # Nếu là phụ huynh và có mã học sinh, tạo luôn liên kết parent_student_links
        if req_data.role == "PARENT" and req_data.student_code:
            await db.execute(
                """
                INSERT INTO parent_student_links (school_id, parent_user_id, parent_name, parent_phone, student_id, verified_status, verified_at)
                VALUES (1, ?, ?, ?, ?, ?, ?)
                """,
                (user_id, req_data.full_name.strip(), req_data.phone or "", req_data.student_code.strip(), verified_status, verified_at)
            )

        await db.commit()

        # 5. Sinh JWT Token đăng nhập tức thì
        token = create_access_token({
            "sub": user_id,
            "username": req_data.username.strip(),
            "role": req_data.role,
            "name": req_data.full_name.strip(),
            "verified_status": verified_status,
        })

        return {
            "status": "success",
            "message": "Đăng ký tài khoản thành công!",
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": user_id,
                "username": req_data.username.strip(),
                "full_name": req_data.full_name.strip(),
                "role": req_data.role,
                "verified_status": verified_status,
                "verification_method": verification_method,
                "verification_note": verification_note,
                "student_code": req_data.student_code,
                "class_name": req_data.class_name,
            }
        }


@app.post("/api/v1/auth/login", tags=["Auth & Verification"])
async def auth_login(req_data: UserLogin):
    """Đăng nhập bằng Tên người dùng / Số điện thoại / Email + Mật khẩu."""
    identifier = req_data.username_or_phone.strip()
    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        user = await (await db.execute(
            "SELECT * FROM users WHERE username = ? OR phone = ? OR email = ?",
            (identifier, identifier, identifier)
        )).fetchone()

        if not user:
            raise HTTPException(status_code=401, detail="Tài khoản không tồn tại hoặc thông tin đăng nhập không chính xác.")

        if not verify_password(req_data.password, user["salt"], user["password_hash"]):
            raise HTTPException(status_code=401, detail="Mật khẩu không chính xác.")

        if user["status"] != "ACTIVE":
            raise HTTPException(status_code=403, detail="Tài khoản của bạn đang bị tạm khóa. Vui lòng liên hệ nhà trường.")

        token = create_access_token({
            "sub": user["id"],
            "username": user["username"],
            "role": user["role"],
            "name": user["full_name"],
            "verified_status": user["verified_status"],
        })

        return {
            "status": "success",
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": user["id"],
                "username": user["username"],
                "email": user["email"],
                "phone": user["phone"],
                "full_name": user["full_name"],
                "role": user["role"],
                "verified_status": user["verified_status"],
                "verification_method": user["verification_method"],
                "verification_note": user["verification_note"],
                "student_code": user["student_code"],
                "class_name": user["class_name"],
            }
        }


@app.get("/api/v1/auth/me", tags=["Auth & Verification"])
async def auth_get_me(req: Request):
    """Lấy thông tin tài khoản hiện tại kèm trạng thái Verified Account."""
    user = await get_current_user_optional(req)
    if not user:
        raise HTTPException(status_code=401, detail="Chưa đăng nhập hoặc phiên làm việc đã hết hạn.")
    return {"status": "success", "user": user}


@app.post("/api/v1/auth/verify/request-otp", tags=["Auth & Verification"])
async def request_verification_otp(req_data: RequestOTP):
    """Yêu cầu gửi mã OTP xác minh số điện thoại hoặc email (SMS/Zalo/Email)."""
    target = req_data.target.strip()
    if not target:
        raise HTTPException(status_code=400, detail="Vui lòng cung cấp số điện thoại hoặc email.")

    # Sinh mã OTP 6 chữ số ngẫu nhiên
    otp_code = f"{secrets.randbelow(900000) + 100000}"
    expires_at = datetime.fromtimestamp(time.time() + 300).strftime("%Y-%m-%d %H:%M:%S")

    async with aiosqlite.connect(str(DB_PATH)) as db:
        await db.execute(
            """
            INSERT INTO verification_otps (target, otp_code, otp_type, expires_at, is_used)
            VALUES (?, ?, ?, ?, 0)
            """,
            (target, otp_code, req_data.otp_type or "PHONE_REGISTER", expires_at)
        )
        await db.commit()

    log.info(f"[OTP] Đã tạo mã OTP {otp_code} cho {target} (Hết hạn: {expires_at})")

    return {
        "status": "success",
        "message": f"Mã xác thực OTP đã được gửi tới {target}.",
        "dev_otp": otp_code,  # Cung cấp cho môi trường test/demo trực tiếp
        "expires_in_seconds": 300
    }


@app.post("/api/v1/auth/verify/submit-otp", tags=["Auth & Verification"])
async def submit_verification_otp(req_data: SubmitOTP, req: Request):
    """Xác thực mã OTP để kích hoạt Huy Hiệu Tích Xanh (VERIFIED)."""
    target = req_data.target.strip()
    code   = req_data.otp_code.strip()

    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        otp_row = await (await db.execute(
            """
            SELECT * FROM verification_otps 
            WHERE target = ? AND otp_code = ? AND is_used = 0 
            ORDER BY id DESC LIMIT 1
            """,
            (target, code)
        )).fetchone()

        if not otp_row:
            raise HTTPException(status_code=400, detail="Mã OTP không chính xác hoặc đã được sử dụng.")

        # Đánh dấu OTP đã dùng
        await db.execute("UPDATE verification_otps SET is_used = 1 WHERE id = ?", (otp_row["id"],))

        now_str = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        user = await get_current_user_optional(req)
        if user:
            await db.execute(
                """
                UPDATE users 
                SET verified_status = 'VERIFIED', verification_method = 'OTP_PHONE', 
                    verification_note = 'Đã xác thực OTP số điện thoại chính chủ', verified_at = ?
                WHERE id = ?
                """,
                (now_str, user["id"])
            )
            # Cập nhật cả bảng liên kết nếu có
            await db.execute(
                "UPDATE parent_student_links SET verified_status = 'VERIFIED', verified_at = ? WHERE parent_user_id = ?",
                (now_str, user["id"])
            )
        await db.commit()

    return {
        "status": "success",
        "message": "Xác thực OTP thành công! Tài khoản của bạn đã đạt chuẩn Verified (Tích Xanh ✅).",
        "verified_status": "VERIFIED"
    }


@app.post("/api/v1/auth/verify/submit-id-card", tags=["Auth & Verification"])
async def submit_id_card_verification(req_data: SubmitIDCard, req: Request):
    """Gửi ảnh Thẻ Căn Cước (CCCD) / Thẻ Học Sinh để xác minh danh tính."""
    user = await get_current_user_optional(req)
    if not user:
        raise HTTPException(status_code=401, detail="Vui lòng đăng nhập để gửi yêu cầu xác minh.")

    doc_url = req_data.doc_data_url
    if doc_url.startswith("data:image"):
        # Lưu file ảnh thực tế
        header, encoded = doc_url.split(",", 1)
        ext = "jpg"
        if "png" in header:
            ext = "png"
        fname = f"id_card_{user['id']}_{int(time.time())}.{ext}"
        fpath = VIOLATIONS_DIR / fname
        with open(fpath, "wb") as f:
            f.write(base64.b64decode(encoded))
        doc_url = f"/violations/{fname}"

    now_str = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    async with aiosqlite.connect(str(DB_PATH)) as db:
        await db.execute(
            """
            UPDATE users 
            SET verified_status = 'PENDING_REVIEW', verification_method = 'ID_CARD', 
                verification_doc_url = ?, verification_note = ?, student_code = COALESCE(?, student_code)
            WHERE id = ?
            """,
            (doc_url, req_data.note or "Đã nộp ảnh giấy tờ CCCD/Thẻ học sinh", req_data.student_code, user["id"])
        )
        await db.commit()

    return {
        "status": "success",
        "message": "Đã gửi thông tin giấy tờ thành công. Hồ sơ đang được GVCN/Nhà trường xét duyệt.",
        "verified_status": "PENDING_REVIEW",
        "doc_url": doc_url
    }


@app.get("/api/v1/auth/verify/pending-list", tags=["Auth & Verification"])
async def get_pending_verifications(req: Request):
    """Danh sách tài khoản đang chờ GVCN hoặc Hiệu Trưởng duyệt danh tính."""
    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        rows = await (await db.execute(
            """
            SELECT id, username, full_name, role, email, phone, verified_status, 
                   verification_method, verification_doc_url, verification_note, student_code, class_name, created_at
            FROM users 
            WHERE verified_status = 'PENDING_REVIEW'
            ORDER BY id DESC
            """
        )).fetchall()
        return [dict(r) for r in rows]


@app.post("/api/v1/auth/verify/approve", tags=["Auth & Verification"])
async def approve_user_verification(req_data: ApproveVerification, req: Request):
    """GVCN hoặc Ban Giám Hiệu phê duyệt/từ chối xác minh tài khoản."""
    now_str = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    new_stat = req_data.status.upper()
    if new_stat not in ("VERIFIED", "REJECTED"):
        raise HTTPException(status_code=400, detail="Trạng thái chỉ có thể là VERIFIED hoặc REJECTED.")

    async with aiosqlite.connect(str(DB_PATH)) as db:
        await db.execute(
            """
            UPDATE users 
            SET verified_status = ?, verification_note = ?, verified_at = ?
            WHERE id = ?
            """,
            (new_stat, req_data.note or "Được GVCN/Quản trị viên phê duyệt", now_str if new_stat == "VERIFIED" else None, req_data.user_id)
        )
        # Đồng bộ bảng liên kết phụ huynh nếu có
        if new_stat == "VERIFIED":
            await db.execute(
                "UPDATE parent_student_links SET verified_status = 'VERIFIED', verified_at = ? WHERE parent_user_id = ?",
                (now_str, req_data.user_id)
            )
        await db.commit()

    return {
        "status": "success",
        "message": f"Đã cập nhật trạng thái tài khoản thành: {new_stat}",
        "user_id": req_data.user_id,
        "verified_status": new_stat
    }


# ──────────────────────────────────────────────────────────────
#  1. QUẢN LÝ TRƯỜNG & TRẠM CAMERA (HIỆU TRƯỞNG / BGH)
# ──────────────────────────────────────────────────────────────

@app.get("/api/v1/schools/info", tags=["School Admin"])
async def get_school_info():
    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        row = await (await db.execute("SELECT * FROM schools WHERE id = 1")).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Không tìm thấy trường")
        return dict(row)


@app.post("/api/v1/schools/config", tags=["School Admin"])
async def update_school_config(config: SchoolConfig):
    async with aiosqlite.connect(str(DB_PATH)) as db:
        await db.execute(
            """
            UPDATE schools 
            SET name = ?, school_code = ?, academic_year = ?, rules_config = ?, form_config = ?
            WHERE id = 1
            """,
            (config.name, config.school_code, config.academic_year, 
             json.dumps(config.rules_config or {}), json.dumps(config.form_config or {}))
        )
        await db.commit()
    return {"status": "success", "message": "Đã cập nhật cấu hình trường thành công"}


@app.get("/api/v1/camera-stations", tags=["Camera Stations"])
async def get_camera_stations():
    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        rows = await (await db.execute("SELECT * FROM camera_stations ORDER BY id ASC")).fetchall()
        return [dict(r) for r in rows]


@app.post("/api/v1/camera-stations", status_code=status.HTTP_201_CREATED, tags=["Camera Stations"])
async def create_camera_station(st: CameraStationCreate):
    key = st.secret_key or f"KEY_{uuid.uuid4().hex[:8].upper()}"
    async with aiosqlite.connect(str(DB_PATH)) as db:
        await db.execute(
            """
            INSERT INTO camera_stations (school_id, name, location, stream_url, secret_key, is_active, status)
            VALUES (1, ?, ?, ?, ?, ?, 'ONLINE')
            """,
            (st.name.strip(), st.location.strip(), st.stream_url.strip(), key, st.is_active)
        )
        await db.commit()
    return {"status": "success", "message": f"Đã thêm trạm camera '{st.name}'", "secret_key": key}


@app.delete("/api/v1/camera-stations/{station_id}", tags=["Camera Stations"])
async def delete_camera_station(station_id: int):
    async with aiosqlite.connect(str(DB_PATH)) as db:
        await db.execute("DELETE FROM camera_stations WHERE id = ?", (station_id,))
        await db.commit()
    return {"status": "success", "message": f"Đã xóa trạm camera ID {station_id}"}


# ──────────────────────────────────────────────────────────────
#  2. PHỤ HUYNH TÌM CON 1-CHẠM (LOW-TECH ONBOARDING PORTAL)
# ──────────────────────────────────────────────────────────────

@app.get("/api/v1/students/search", tags=["Parent Portal"])
async def search_students_for_parents(
    q:     Optional[str] = None,
    lop:   Optional[str] = None,
    grade: Optional[str] = None,
    limit: int = 50,
):
    """Tìm kiếm học sinh theo Tên hoặc Lớp cho phụ huynh (giao diện thẻ to rõ)."""
    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        conds = ["status = 'APPROVED'"]
        params: List[Any] = []

        if lop and lop.strip() and lop != "ALL":
            conds.append("lop = ?")
            params.append(lop.strip())
        elif grade and grade.strip() and grade != "ALL":
            conds.append("lop LIKE ?")
            params.append(f"{grade.strip()}%")

        if q and q.strip():
            conds.append("(ho_ten LIKE ? OR ma_hs LIKE ?)")
            params.extend([f"%{q.strip()}%", f"%{q.strip()}%"])

        where = "WHERE " + " AND ".join(conds)
        query = f"SELECT ma_hs, ho_ten, lop, ngay_sinh, photo_url, current_points FROM HocSinh {where} ORDER BY lop, ho_ten LIMIT ?"
        params.append(limit)

        rows = await (await db.execute(query, params)).fetchall()
        return [dict(r) for r in rows]


@app.post("/api/v1/parent/link", tags=["Parent Portal"])
async def link_parent_to_student(req: ParentLinkRequest):
    """Phụ huynh chạm vào thẻ con và nhập Tên + SĐT để liên kết tức thì."""
    today = datetime.now().strftime("%d/%m/%Y")
    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row

        # 1. Kiểm tra học sinh
        stu = await (await db.execute("SELECT * FROM HocSinh WHERE ma_hs = ?", (req.ma_hs.strip(),))).fetchone()
        if not stu:
            raise HTTPException(status_code=404, detail="Không tìm thấy thông tin học sinh")

        # 2. Cập nhật bảng parent_student_links
        await db.execute(
            """
            INSERT INTO parent_student_links (parent_name, parent_phone, student_id, relation_name, verified_status)
            VALUES (?, ?, ?, ?, 'VERIFIED')
            """,
            (req.parent_name.strip(), req.parent_phone.strip(), req.ma_hs.strip(), req.relation or 'Phụ huynh')
        )
        # Cập nhật thông tin nhanh vào HocSinh
        await db.execute(
            "UPDATE HocSinh SET ten_phu_huynh = ?, sdt_phu_huynh = ? WHERE ma_hs = ?",
            (req.parent_name.strip(), req.parent_phone.strip(), req.ma_hs.strip())
        )
        await db.commit()

        # 3. Lấy trạng thái điểm danh hôm nay
        logs = await (await db.execute(
            "SELECT * FROM offline_log WHERE ma_hs = ? AND thoi_gian LIKE ? ORDER BY id DESC",
            (req.ma_hs.strip(), f"{today}%")
        )).fetchall()

        vios = await (await db.execute(
            "SELECT * FROM offline_violation WHERE ma_hs = ? AND thoi_gian LIKE ? ORDER BY id DESC",
            (req.ma_hs.strip(), f"{today}%")
        )).fetchall()

    latest_log = dict(logs[0]) if logs else None
    return {
        "status": "success",
        "message": f"Đã kết nối thành công với học sinh {stu['ho_ten']} ({stu['ma_hs']})",
        "student": dict(stu),
        "today_attendance": {
            "present": bool(logs and len(logs) % 2 == 1),
            "latest_time": latest_log.get("thoi_gian") if latest_log else None,
            "latest_status": latest_log.get("trang_thai") if latest_log else "Chưa đến trường",
            "proof_image_url": latest_log.get("proof_image_url") if latest_log else None,
            "violations_today": len(vios),
        }
    }


@app.get("/api/v1/parent/student/{ma_hs}/status", tags=["Parent Portal"])
async def get_parent_student_status(ma_hs: str):
    """Lấy dữ liệu thời gian thực của con: giờ vào, ảnh cổng, vi phạm, lịch sử."""
    today = datetime.now().strftime("%d/%m/%Y")
    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        stu = await (await db.execute("SELECT * FROM HocSinh WHERE ma_hs = ?", (ma_hs,))).fetchone()
        if not stu:
            raise HTTPException(status_code=404, detail="Không tìm thấy học sinh")

        logs = await (await db.execute(
            "SELECT * FROM offline_log WHERE ma_hs = ? ORDER BY id DESC LIMIT 20",
            (ma_hs,)
        )).fetchall()

        vios = await (await db.execute(
            "SELECT * FROM offline_violation WHERE ma_hs = ? ORDER BY id DESC LIMIT 10",
            (ma_hs,)
        )).fetchall()

        leaves = await (await db.execute(
            "SELECT * FROM leave_requests WHERE ma_hs = ? ORDER BY id DESC LIMIT 10",
            (ma_hs,)
        )).fetchall()

    today_logs = [l for l in logs if l["thoi_gian"].startswith(today)]
    latest_today = today_logs[0] if today_logs else None

    return {
        "student": dict(stu),
        "today": {
            "is_present": bool(today_logs and len(today_logs) % 2 == 1),
            "arrival_time": latest_today["thoi_gian"] if latest_today else None,
            "status_text": "Đã vào trường an toàn" if (today_logs and len(today_logs) % 2 == 1) else "Chưa điểm danh",
            "proof_image_url": latest_today["proof_image_url"] if latest_today else None,
        },
        "recent_logs": [dict(l) for l in logs],
        "recent_violations": [dict(v) for v in vios],
        "leave_requests": [dict(lr) for lr in leaves],
    }


# ──────────────────────────────────────────────────────────────
#  3. QUẢN LÝ LỚP & HỌC SINH (GIÁO VIÊN CHỦ NHIỆM - GVCN)
# ──────────────────────────────────────────────────────────────

@app.get("/api/v1/classes", tags=["Classes"])
async def get_classes():
    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        query = """
        SELECT c.id, c.name, c.grade, c.teacher_name, c.invite_code, 
               COUNT(h.ma_hs) AS total_students
        FROM classes c
        LEFT JOIN HocSinh h ON c.name = h.lop AND h.status = 'APPROVED'
        GROUP BY c.id, c.name
        ORDER BY c.grade, c.name
        """
        rows = await (await db.execute(query)).fetchall()
        return [dict(r) for r in rows]


@app.post("/api/v1/classes", status_code=status.HTTP_201_CREATED, tags=["Classes"])
async def create_class(c: ClassCreate):
    inv_code = c.invite_code or f"INV-{c.name.upper()}"
    async with aiosqlite.connect(str(DB_PATH)) as db:
        await db.execute(
            "INSERT INTO classes (name, grade, teacher_name, invite_code) VALUES (?, ?, ?, ?)",
            (c.name.strip(), c.grade.strip(), c.teacher_name.strip(), inv_code)
        )
        await db.commit()
    return {"status": "success", "message": f"Đã tạo lớp {c.name}", "invite_code": inv_code}


@app.get("/api/v1/teacher/class-students", tags=["Teacher Portal"])
async def get_class_students_for_teacher(lop: str = "10A1"):
    """Lấy danh sách học sinh của lớp kèm trạng thái ảnh AI và điểm nề nếp."""
    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        rows = await (await db.execute(
            """
            SELECT ma_hs, ho_ten, lop, ngay_sinh, sdt_phu_huynh, ten_phu_huynh, photo_url, status, current_points, tao_luc
            FROM HocSinh 
            WHERE lop = ? 
            ORDER BY status DESC, ho_ten ASC
            """,
            (lop,)
        )).fetchall()
        return [dict(r) for r in rows]


@app.post("/api/v1/students/{ma_hs}/approve", tags=["Teacher Portal"])
async def approve_student_by_teacher(ma_hs: str):
    """GVCN phê duyệt hồ sơ và ảnh AI của học sinh 1-chạm."""
    async with aiosqlite.connect(str(DB_PATH)) as db:
        await db.execute("UPDATE HocSinh SET status = 'APPROVED' WHERE ma_hs = ?", (ma_hs,))
        await db.commit()

    await ws_manager.broadcast({
        "event": "student_approved",
        "data": {"ma_hs": ma_hs}
    })
    return {"status": "success", "message": f"Đã phê duyệt học sinh {ma_hs}"}


@app.post("/api/v1/students/{ma_hs}/reject", tags=["Teacher Portal"])
async def reject_student_by_teacher(ma_hs: str):
    async with aiosqlite.connect(str(DB_PATH)) as db:
        await db.execute("UPDATE HocSinh SET status = 'REJECTED' WHERE ma_hs = ?", (ma_hs,))
        await db.commit()
    return {"status": "success", "message": f"Đã từ chối hồ sơ {ma_hs}"}


@app.get("/api/v1/teacher/class-trends", tags=["Teacher Portal"])
async def get_class_trends(lop: str = "10A1"):
    """Biểu đồ xu hướng nề nếp lớp: Hôm nay, Tuần này, Tháng này, Cả năm."""
    today = datetime.now().strftime("%d/%m/%Y")
    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row

        # Đếm tổng học sinh
        total_r = await (await db.execute("SELECT COUNT(*) AS c FROM HocSinh WHERE lop = ? AND status = 'APPROVED'", (lop,))).fetchone()
        total_stu = total_r["c"] if total_r else 0

        # Lượt có mặt hôm nay
        present_rows = await (await db.execute(
            """
            SELECT l.ma_hs, COUNT(*) AS cnt 
            FROM offline_log l
            JOIN HocSinh h ON l.ma_hs = h.ma_hs
            WHERE h.lop = ? AND l.thoi_gian LIKE ?
            GROUP BY l.ma_hs
            """,
            (lop, f"{today}%")
        )).fetchall()
        present_count = sum(1 for r in present_rows if r["cnt"] % 2 == 1)

        # Vi phạm của lớp
        vio_rows = await (await db.execute(
            """
            SELECT COUNT(*) AS c 
            FROM offline_violation v
            JOIN HocSinh h ON v.ma_hs = h.ma_hs
            WHERE h.lop = ?
            """,
            (lop,)
        )).fetchone()
        total_vios = vio_rows["c"] if vio_rows else 0

        # Xếp hạng điểm số từng học sinh
        rank_rows = await (await db.execute(
            "SELECT ma_hs, ho_ten, current_points FROM HocSinh WHERE lop = ? AND status = 'APPROVED' ORDER BY current_points DESC",
            (lop,)
        )).fetchall()

    return {
        "lop": lop,
        "total_students": total_stu,
        "present_today": present_count,
        "absent_today": max(0, total_stu - present_count),
        "attendance_rate": round(present_count / total_stu * 100, 1) if total_stu else 0,
        "total_violations": total_vios,
        "students_ranking": [dict(r) for r in rank_rows],
        "weekly_trend": [
            {"day": "T2", "rate": 96.5},
            {"day": "T3", "rate": 98.0},
            {"day": "T4", "rate": 95.0},
            {"day": "T5", "rate": 99.0},
            {"day": "T6", "rate": 97.5},
        ]
    }


# ──────────────────────────────────────────────────────────────
#  4. QUY TRÌNH KHIẾU NẠI 2 CẤP (DISPUTES: GVCN -> GIÁM THỊ)
# ──────────────────────────────────────────────────────────────

@app.post("/api/v1/disputes", status_code=status.HTTP_201_CREATED, tags=["Disputes"])
async def create_dispute(d: DisputeCreate):
    """Học sinh / Phụ huynh nộp khiếu nại nề nếp kèm ảnh minh chứng."""
    async with aiosqlite.connect(str(DB_PATH)) as db:
        await db.execute(
            """
            INSERT INTO disputes (attendance_log_id, ma_hs, ho_ten, lop, level, reason, proof_image_url, student_evidence, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'PENDING')
            """,
            (d.attendance_log_id, d.ma_hs, d.ho_ten, d.lop, d.level or 'LEVEL_1_TEACHER', d.reason, d.proof_image_url, d.student_evidence)
        )
        await db.commit()

    await ws_manager.broadcast({
        "event": "new_dispute",
        "data": {"ma_hs": d.ma_hs, "ho_ten": d.ho_ten, "lop": d.lop, "reason": d.reason, "level": d.level}
    })
    return {"status": "success", "message": "Đã gửi khiếu nại thành công đến GVCN"}


@app.get("/api/v1/teacher/disputes", tags=["Teacher Portal"])
async def get_teacher_disputes(lop: Optional[str] = None):
    """GVCN lấy danh sách khiếu nại Cấp 1 của lớp mình."""
    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        conds = ["level = 'LEVEL_1_TEACHER'"]
        params: List[Any] = []
        if lop:
            conds.append("lop = ?")
            params.append(lop)
        where = "WHERE " + " AND ".join(conds)
        rows = await (await db.execute(f"SELECT * FROM disputes {where} ORDER BY id DESC", params)).fetchall()
        return [dict(r) for r in rows]


@app.post("/api/v1/teacher/disputes/{dispute_id}/resolve", tags=["Teacher Portal"])
async def resolve_dispute_by_teacher(dispute_id: int, req: DisputeResolveRequest):
    """GVCN xử lý Cấp 1: Duyệt (+ Hoàn điểm), Từ chối, hoặc Leo thang Cấp 2."""
    now_str = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        disp = await (await db.execute("SELECT * FROM disputes WHERE id = ?", (dispute_id,))).fetchone()
        if not disp:
            raise HTTPException(status_code=404, detail="Không tìm thấy khiếu nại")

        if req.action == "APPROVE":
            new_status = "APPROVED"
            # Hoàn điểm cho học sinh
            await db.execute(
                "UPDATE HocSinh SET current_points = MIN(100, current_points + ?) WHERE ma_hs = ?",
                (req.reimburse_points or 5, disp["ma_hs"])
            )
            await db.execute(
                """
                UPDATE disputes 
                SET status = 'APPROVED', resolution_note = ?, resolver_name = ?, points_reimbursed = ?, resolved_at = ?
                WHERE id = ?
                """,
                (req.resolution_note or 'GVCN đã chấp thuận giải trình.', req.resolver_name, req.reimburse_points or 5, now_str, dispute_id)
            )
        elif req.action == "ESCALATE":
            new_status = "ESCALATED"
            await db.execute(
                """
                UPDATE disputes 
                SET level = 'LEVEL_2_INSPECTOR', status = 'PENDING', resolution_note = ?, resolver_name = ?
                WHERE id = ?
                """,
                (f"GVCN chuyển lên Ban Giám Thị: {req.resolution_note}", req.resolver_name, dispute_id)
            )
        else:
            new_status = "REJECTED"
            await db.execute(
                """
                UPDATE disputes 
                SET status = 'REJECTED', resolution_note = ?, resolver_name = ?, resolved_at = ?
                WHERE id = ?
                """,
                (req.resolution_note or 'Khiếu nại không đủ minh chứng.', req.resolver_name, now_str, dispute_id)
            )
        await db.commit()

    await ws_manager.broadcast({
        "event": "dispute_resolved",
        "data": {"dispute_id": dispute_id, "action": req.action, "status": new_status}
    })
    return {"status": "success", "message": f"Khiếu nại đã được xử lý: {new_status}"}


@app.get("/api/v1/inspector/disputes", tags=["Inspector Portal"])
async def get_inspector_disputes():
    """Giám Thị lấy danh sách khiếu nại Cấp 2 leo thang toàn trường."""
    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        rows = await (await db.execute(
            "SELECT * FROM disputes WHERE level = 'LEVEL_2_INSPECTOR' ORDER BY id DESC"
        )).fetchall()
        return [dict(r) for r in rows]


@app.post("/api/v1/inspector/disputes/{dispute_id}/resolve", tags=["Inspector Portal"])
async def resolve_dispute_by_inspector(dispute_id: int, req: DisputeResolveRequest):
    """Giám Thị phán quyết cuối cùng đối với khiếu nại Cấp 2."""
    now_str = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        disp = await (await db.execute("SELECT * FROM disputes WHERE id = ?", (dispute_id,))).fetchone()
        if not disp:
            raise HTTPException(status_code=404, detail="Không tìm thấy khiếu nại")

        st = "APPROVED" if req.action == "APPROVE" else "REJECTED"
        if req.action == "APPROVE":
            await db.execute(
                "UPDATE HocSinh SET current_points = MIN(100, current_points + ?) WHERE ma_hs = ?",
                (req.reimburse_points or 5, disp["ma_hs"])
            )

        await db.execute(
            """
            UPDATE disputes 
            SET status = ?, resolution_note = ?, resolver_name = ?, points_reimbursed = ?, resolved_at = ?
            WHERE id = ?
            """,
            (st, req.resolution_note or 'Ban Giám Thị đã xác minh.', req.resolver_name or 'Ban Giám Thị', req.reimburse_points if st == "APPROVED" else 0, now_str, dispute_id)
        )
        await db.commit()

    return {"status": "success", "message": f"Giám Thị đã đưa ra phán quyết: {st}"}


# ──────────────────────────────────────────────────────────────
#  5. ĐƠN XIN NGHỈ PHÉP (LEAVE REQUESTS)
# ──────────────────────────────────────────────────────────────

@app.post("/api/v1/leave-requests", status_code=status.HTTP_201_CREATED, tags=["Leave Requests"])
async def create_leave_request(req: LeaveRequestCreate):
    async with aiosqlite.connect(str(DB_PATH)) as db:
        await db.execute(
            """
            INSERT INTO leave_requests (ma_hs, ho_ten, lop, parent_name, parent_phone, start_date, end_date, reason, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'PENDING')
            """,
            (req.ma_hs, req.ho_ten, req.lop, req.parent_name, req.parent_phone, req.start_date, req.end_date, req.reason)
        )
        await db.commit()

    await ws_manager.broadcast({
        "event": "new_leave_request",
        "data": {"ma_hs": req.ma_hs, "ho_ten": req.ho_ten, "lop": req.lop, "parent_name": req.parent_name}
    })
    return {"status": "success", "message": "Đã gửi đơn xin nghỉ phép đến GVCN"}


@app.get("/api/v1/teacher/leave-requests", tags=["Teacher Portal"])
async def get_teacher_leave_requests(lop: Optional[str] = None):
    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        query = "SELECT * FROM leave_requests"
        params = []
        if lop:
            query += " WHERE lop = ?"
            params.append(lop)
        query += " ORDER BY id DESC"
        rows = await (await db.execute(query, params)).fetchall()
        return [dict(r) for r in rows]


@app.post("/api/v1/leave-requests/{req_id}/approve", tags=["Teacher Portal"])
async def approve_leave_request(req_id: int, approved_by: Optional[str] = Form("GVCN")):
    async with aiosqlite.connect(str(DB_PATH)) as db:
        await db.execute(
            "UPDATE leave_requests SET status = 'APPROVED', approved_by = ? WHERE id = ?",
            (approved_by, req_id)
        )
        await db.commit()
    return {"status": "success", "message": "GVCN đã duyệt đơn xin nghỉ phép"}


@app.post("/api/v1/leave-requests/{req_id}/reject", tags=["Teacher Portal"])
async def reject_leave_request(req_id: int, note: Optional[str] = Form("")):
    async with aiosqlite.connect(str(DB_PATH)) as db:
        await db.execute(
            "UPDATE leave_requests SET status = 'REJECTED', note = ? WHERE id = ?",
            (note, req_id)
        )
        await db.commit()
    return {"status": "success", "message": "Đã từ chối đơn xin nghỉ phép"}


# ──────────────────────────────────────────────────────────────
#  6. CHẤM ĐIỂM THI ĐUA CÁC LỚP (GIÁM THỊ CHẤM -> BGH DUYỆT)
# ──────────────────────────────────────────────────────────────

@app.get("/api/v1/inspector/discipline-scores", tags=["Discipline Scores"])
async def get_discipline_scores(week_number: Optional[int] = None):
    wk = week_number or 35
    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        rows = await (await db.execute(
            "SELECT * FROM class_discipline_scores WHERE week_number = ? ORDER BY rank ASC, total_points DESC",
            (wk,)
        )).fetchall()
        return [dict(r) for r in rows]


@app.post("/api/v1/inspector/discipline-scores/submit", tags=["Inspector Portal"])
async def submit_discipline_scores(req: DisciplineScoreSubmitRequest):
    """Giám Thị tổng hợp và trình bảng chấm điểm thi đua lên Hiệu Trưởng."""
    tot = round((req.attendance_score + req.uniform_score + req.discipline_score) / 3 + req.bonus_points, 1)
    async with aiosqlite.connect(str(DB_PATH)) as db:
        await db.execute(
            """
            INSERT OR REPLACE INTO class_discipline_scores 
            (class_name, week_number, month_number, year, attendance_score, uniform_score, discipline_score, bonus_points, total_points, inspector_notes, inspector_name, inspector_status, headmaster_approval)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'SUBMITTED', 'PENDING')
            """,
            (req.class_name, req.week_number, req.month_number, req.year or 2026,
             req.attendance_score, req.uniform_score, req.discipline_score, req.bonus_points, tot, req.inspector_notes, req.inspector_name)
        )
        await db.commit()

    await ws_manager.broadcast({
        "event": "discipline_submitted",
        "data": {"class_name": req.class_name, "week": req.week_number, "total": tot}
    })
    return {"status": "success", "message": f"Đã trình điểm thi đua lớp {req.class_name} lên Hiệu Trưởng"}


@app.post("/api/v1/headmaster/discipline-scores/approve", tags=["Headmaster Portal"])
async def approve_discipline_scores_by_headmaster(week_number: int = Form(...), approved_by: str = Form("Hiệu Trưởng")):
    """Hiệu Trưởng ký duyệt điện tử bảng thi đua toàn trường."""
    now_str = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    async with aiosqlite.connect(str(DB_PATH)) as db:
        await db.execute(
            """
            UPDATE class_discipline_scores 
            SET headmaster_approval = 'APPROVED', approved_by = ?, approved_at = ?
            WHERE week_number = ?
            """,
            (approved_by, now_str, week_number)
        )
        await db.commit()

    await ws_manager.broadcast({
        "event": "discipline_approved",
        "data": {"week_number": week_number, "approved_by": approved_by}
    })
    return {"status": "success", "message": f"Hiệu Trưởng đã ký duyệt Bảng thi đua Tuần {week_number}"}


# ──────────────────────────────────────────────────────────────
#  7. EXECUTIVE ANALYTICS & EXPORT BÁO CÁO TOÀN TRƯỜNG
# ──────────────────────────────────────────────────────────────

@app.get("/api/v1/headmaster/analytics", tags=["Headmaster Portal"])
async def get_headmaster_analytics():
    """Dashboard vĩ mô cho Hiệu Trưởng: chuyên cần toàn trường, bảng thi đua, camera."""
    today = datetime.now().strftime("%d/%m/%Y")
    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row

        # Thống kê học sinh
        total_stu = (await (await db.execute("SELECT COUNT(*) FROM HocSinh WHERE status='APPROVED'")).fetchone())[0]
        pending_stu = (await (await db.execute("SELECT COUNT(*) FROM HocSinh WHERE status='PENDING'")).fetchone())[0]

        # Có mặt hôm nay
        present_rows = await (await db.execute(
            "SELECT ma_hs, COUNT(*) AS cnt FROM offline_log WHERE thoi_gian LIKE ? GROUP BY ma_hs",
            (f"{today}%",)
        )).fetchall()
        present = sum(1 for r in present_rows if r["cnt"] % 2 == 1)

        # Vi phạm & khiếu nại
        vios = (await (await db.execute("SELECT COUNT(*) FROM offline_violation WHERE thoi_gian LIKE ?", (f"{today}%",))).fetchone())[0]
        disp_p = (await (await db.execute("SELECT COUNT(*) FROM disputes WHERE status='PENDING'")).fetchone())[0]

        # Top lớp dẫn đầu
        top_classes = await (await db.execute(
            "SELECT class_name, total_points, rank FROM class_discipline_scores WHERE week_number = 35 ORDER BY rank ASC LIMIT 5"
        )).fetchall()

        # Trạm camera
        cameras = await (await db.execute("SELECT id, name, location, status FROM camera_stations")).fetchall()

    return {
        "date": today,
        "total_students": total_stu,
        "present_today": present,
        "absent_today": max(0, total_stu - present),
        "attendance_rate": round(present / total_stu * 100, 1) if total_stu else 0.0,
        "violations_today": vios,
        "pending_enrollments": pending_stu,
        "pending_disputes": disp_p,
        "top_classes": [dict(tc) for tc in top_classes],
        "camera_stations": [dict(c) for c in cameras],
    }


# ──────────────────────────────────────────────────────────────
#  8. EDGE CAMERA SYNC & LIVE ATTENDANCE INGESTION
# ──────────────────────────────────────────────────────────────

@app.get("/api/v1/edge/sync-students", tags=["Edge Camera Sync"])
async def sync_students_for_edge():
    """Đồng bộ danh sách học sinh hợp lệ cho Edge AI Camera nhận diện Offline 100%."""
    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        rows = await (await db.execute(
            "SELECT ma_hs, ho_ten, lop, photo_url, face_embedding, qr_token FROM HocSinh WHERE status = 'APPROVED'"
        )).fetchall()

        data = []
        for r in rows:
            p_url = r["photo_url"]
            l_path = str(STUFACE_DIR / p_url.replace("/stuface/", "")) if (p_url and p_url.startswith("/stuface/")) else None
            data.append({
                "ma_hs": r["ma_hs"],
                "ho_ten": r["ho_ten"],
                "lop": r["lop"],
                "photo_url": p_url,
                "local_path": l_path,
                "face_embedding": r["face_embedding"],
            })
        return {"count": len(data), "students": data}


@app.post("/api/v1/attendance", status_code=status.HTTP_202_ACCEPTED, tags=["Edge API"])
async def receive_attendance(event: AttendanceEvent):
    """Tiếp nhận sự kiện điểm danh từ Pi 4 Camera AI ngoài cổng."""
    data = event.model_dump()
    await io_worker.put_task("LOG_ATTENDANCE", data)

    # Broadcast WebSocket
    ws_payload = {
        "event": "log",
        "data": {
            "ma_hs": event.ma_hs,
            "ho_ten": event.ho_ten,
            "trang_thai": event.trang_thai,
            "thoi_gian": event.thoi_gian,
            "lop": event.lop,
            "uniform_status": event.uniform_status,
            "proof_image_url": event.proof_image_url,
        }
    }
    sent = await ws_manager.broadcast(ws_payload)
    return {"status": "accepted", "ma_hs": event.ma_hs, "ws_sent": sent}


@app.post("/api/v1/violation", status_code=status.HTTP_202_ACCEPTED, tags=["Edge API"])
async def receive_violation(
    ma_hs:     str                  = Form(...),
    ho_ten:    str                  = Form(...),
    mo_ta:     str                  = Form(...),
    lop:       Optional[str]        = Form(None),
    thoi_gian: Optional[str]        = Form(None),
    photo:     Optional[UploadFile] = File(None),
):
    """Tiếp nhận ảnh vi phạm + bắn cảnh báo đỏ thời gian thực tới Giám Thị & GVCN."""
    ts = thoi_gian or datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    ten_file = ""
    duong_dan = ""

    if photo and photo.filename:
        ext = Path(photo.filename).suffix.lower() or ".jpg"
        ts_safe = datetime.now().strftime("%Y%m%d_%H%M%S")
        ten_file = f"vio_{ma_hs}_{ts_safe}{ext}"
        dest = VIOLATIONS_DIR / ten_file
        with dest.open("wb") as f:
            shutil.copyfileobj(photo.file, f)
        duong_dan = str(dest)

    photo_url = f"/violations/{ten_file}" if ten_file else None

    data = {
        "thoi_gian": ts,
        "ma_hs": ma_hs,
        "ho_ten": ho_ten,
        "lop": lop,
        "mo_ta": mo_ta,
        "ten_file": ten_file,
        "duong_dan": duong_dan,
    }
    await io_worker.put_task("LOG_VIOLATION", data)

    # Bắn cảnh báo đỏ Live Alert
    await ws_manager.broadcast({
        "event": "live_alert",
        "data": {
            "type": "VIOLATION",
            "ma_hs": ma_hs,
            "ho_ten": ho_ten,
            "lop": lop,
            "mo_ta": mo_ta,
            "thoi_gian": ts,
            "photo_url": photo_url,
        }
    })
    return {"status": "accepted", "ma_hs": ma_hs, "photo_url": photo_url}


# ──────────────────────────────────────────────────────────────
#  9. ĐĂNG KÝ HỌC SINH MỚI & THỐNG KÊ DASHBOARD
# ──────────────────────────────────────────────────────────────

@app.post("/api/v1/students/register", status_code=status.HTTP_201_CREATED, tags=["Students"])
async def register_student(
    ho_ten:        str                  = Form(...),
    lop:           str                  = Form(...),
    ma_hs:         Optional[str]        = Form(None),
    ngay_sinh:     Optional[str]        = Form(None),
    sdt_phu_huynh: Optional[str]        = Form(None),
    ten_phu_huynh: Optional[str]        = Form(None),
    photo_base64:  Optional[str]        = Form(None),
    photo:         Optional[UploadFile] = File(None),
    direct_approve: Optional[bool]      = Form(False),
):
    """Đăng ký học sinh trực tuyến từ Web App kèm chụp ảnh AI."""
    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row

        # Tự sinh mã HS nếu chưa có
        student_id = ma_hs.strip().upper() if (ma_hs and ma_hs.strip()) else None
        if not student_id:
            rows = await (await db.execute("SELECT ma_hs FROM HocSinh WHERE ma_hs LIKE 'HS%'")).fetchall()
            max_num = 0
            for r in rows:
                m = re.match(r'HS(\d+)', r[0], re.IGNORECASE)
                if m:
                    num = int(m.group(1))
                    if num > max_num:
                        max_num = num
            student_id = f"HS{max_num + 1:03d}"

        photo_url = None
        clean_name = _clean_ascii(ho_ten)
        file_name = f"{student_id}_{clean_name}.jpg"
        dest_path = STUFACE_DIR / file_name

        if photo and photo.filename:
            contents = await photo.read()
            with open(dest_path, "wb") as f:
                f.write(contents)
            photo_url = f"/stuface/{file_name}"
        elif photo_base64 and len(photo_base64) > 50:
            if "," in photo_base64:
                photo_base64 = photo_base64.split(",", 1)[1]
            img_data = base64.b64decode(photo_base64)
            with open(dest_path, "wb") as f:
                f.write(img_data)
            photo_url = f"/stuface/{file_name}"

        initial_status = "APPROVED" if direct_approve else "PENDING"

        await db.execute(
            """
            INSERT OR REPLACE INTO HocSinh 
            (ma_hs, ho_ten, lop, school_id, ngay_sinh, sdt_phu_huynh, ten_phu_huynh, photo_url, status, current_points)
            VALUES (?, ?, ?, 1, ?, ?, ?, ?, ?, 100)
            """,
            (student_id, ho_ten.strip(), lop.strip(), ngay_sinh, sdt_phu_huynh, ten_phu_huynh, photo_url, initial_status)
        )
        await db.commit()

    await ws_manager.broadcast({
        "event": "student_registered",
        "data": {"ma_hs": student_id, "ho_ten": ho_ten, "lop": lop, "status": initial_status, "photo_url": photo_url}
    })

    return {
        "status": "success",
        "student": {"ma_hs": student_id, "ho_ten": ho_ten, "lop": lop, "status": initial_status, "photo_url": photo_url}
    }


@app.get("/api/v1/stats", response_model=StatsResponse, tags=["Dashboard"])
async def get_stats():
    today = datetime.now().strftime("%d/%m/%Y")
    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row

        tot_r = await (await db.execute("SELECT COUNT(*) AS c FROM HocSinh WHERE status='APPROVED'")).fetchone()
        total = tot_r["c"] if tot_r else 0

        pend_r = await (await db.execute("SELECT COUNT(*) AS c FROM HocSinh WHERE status='PENDING'")).fetchone()
        pending_s = pend_r["c"] if pend_r else 0

        rows = await (await db.execute(
            "SELECT ma_hs, COUNT(*) AS cnt FROM offline_log WHERE thoi_gian LIKE ? GROUP BY ma_hs",
            (f"{today}%",)
        )).fetchall()
        present = sum(1 for r in rows if r["cnt"] % 2 == 1)

        v_row = await (await db.execute("SELECT COUNT(*) AS c FROM offline_violation WHERE thoi_gian LIKE ?", (f"{today}%",))).fetchone()
        vios = v_row["c"] if v_row else 0

        d_row = await (await db.execute("SELECT COUNT(*) AS c FROM disputes WHERE status='PENDING'")).fetchone()
        disp_cnt = d_row["c"] if d_row else 0

        l_row = await (await db.execute("SELECT COUNT(*) AS c FROM leave_requests WHERE status='PENDING'")).fetchone()
        leave_cnt = l_row["c"] if l_row else 0

    return {
        "date": today,
        "total_students": total,
        "present": present,
        "absent": max(0, total - present),
        "violation_count": vios,
        "pending_students": pending_s,
        "pending_disputes": disp_cnt,
        "pending_leaves": leave_cnt,
        "attendance_rate": round(present / total * 100, 1) if total else 0.0,
        "generated_at": datetime.now().isoformat(),
    }


@app.get("/api/v1/logs", tags=["Dashboard"])
async def get_logs(limit: int = 30, lop: Optional[str] = None):
    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        query = "SELECT * FROM offline_log"
        params = []
        if lop:
            query += " WHERE lop = ?"
            params.append(lop)
        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        rows = await (await db.execute(query, params)).fetchall()
        return [dict(r) for r in rows]


@app.get("/api/v1/violations", tags=["Dashboard"])
async def get_violations(limit: int = 20):
    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        rows = await (await db.execute("SELECT * FROM offline_violation ORDER BY id DESC LIMIT ?", (limit,))).fetchall()
        results = []
        for r in rows:
            d = dict(r)
            d["photo_url"] = f"/violations/{d['ten_file']}" if d.get("ten_file") else None
            results.append(d)
        return results


@app.get("/health", tags=["System"])
async def health_check():
    return {
        "status": "ok",
        "version": "5.2.0",
        "server_time": datetime.now().isoformat(),
        "ws_clients": ws_manager.client_count,
        "worker_queue": io_worker.queue_size,
    }


# ──────────────────────────────────────────────────────────────
#  ENTRYPOINT
# ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run(
        "cloud_server:app",
        host        = SERVER_HOST,
        port        = SERVER_PORT,
        reload      = False,
        log_level   = "info",
        access_log  = True,
        workers     = 1,
        loop        = "asyncio",
    )
