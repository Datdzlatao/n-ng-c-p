# 🔧 Backend — Điểm Danh STEM API Server

FastAPI REST API — Multi-Tenant School Attendance Platform

## Tech Stack
- **Python 3.11+** + **FastAPI** + **SQLite** (→ PostgreSQL production)
- **JWT HS256** (stdlib hmac) + **PBKDF2-HMAC-SHA256** (stdlib hashlib)
- **WebSocket** real-time alerts per school

## Cách Chạy

```bash
# Development
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python run.py
# → http://localhost:8000
# → http://localhost:8000/docs  (Swagger)
```

## Structure
```
backend/
├── app/
│   ├── config.py         ← Settings (JWT_SECRET, DB_PATH...)
│   ├── database.py       ← SQLite schema + seed
│   ├── main.py           ← FastAPI entry
│   ├── core/
│   │   ├── security.py   ← PBKDF2 + JWT
│   │   └── deps.py       ← Auth dependencies
│   └── routers/
│       ├── auth.py       ← Auth + Verification
│       ├── schools.py    ← School CRUD + config
│       ├── students.py   ← Student management
│       ├── attendance.py ← Attendance logs + edge sync
│       ├── disputes.py   ← 2-level disputes
│       ├── leaves.py     ← Leave requests
│       ├── classes.py    ← Class management
│       ├── cameras.py    ← Camera stations
│       └── websocket.py  ← Real-time WS
├── migrations/
│   └── 001_initial_schema.sql  ← PostgreSQL migration
├── run.py
├── requirements.txt
└── .env.example
```

## Environment Variables (.env)
```
JWT_SECRET=<openssl rand -hex 32>
DEBUG=false
OTP_DEV_MODE=false
ZALO_OA_TOKEN=<your_token>
FCM_SERVER_KEY=<your_key>
```

## API Base URL
- Development: `http://localhost:8000`
- Production:  `https://api.stemapp.vn`
