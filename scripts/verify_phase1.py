#!/usr/bin/env python3
"""
Verification script for Phase 1:
- Validates environment & configuration loading
- Validates Pydantic schemas
- Tests Repositories initialization
- Tests Supabase connection (if credentials provided)
- Verifies FastMCP and Google GenAI imports
"""

import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from datetime import datetime, date, timezone

print("=" * 60)
print("🚀 SMART MANAGEMENT BACKEND - PHASE 1 VERIFICATION")
print("=" * 60)

# 1. Config & Settings Check
print("\n[1/5] Checking Configuration & Settings...")
try:
    from app.config import get_settings
    settings = get_settings()
    print(f"  ✅ App Name: {settings.APP_NAME}")
    print(f"  ✅ Environment: {settings.APP_ENV} | Host: {settings.HOST}:{settings.PORT}")
    print(f"  ℹ️ Supabase Configured: {settings.is_supabase_configured}")
    print(f"  ℹ️ Gemini Configured: {settings.is_gemini_configured}")
except Exception as e:
    print(f"  ❌ Config Error: {e}")
    sys.exit(1)

# 2. Schema Validation Check
print("\n[2/5] Validating Pydantic Data Models...")
try:
    from app.models.schemas import (
        EnvLogInDB,
        InventoryCreate,
        ScheduleCreate,
        AlertCreate,
    )
    env_sample = EnvLogInDB(id=1, temperature=28.5, humidity=75.0, created_at=datetime.now(timezone.utc))
    inv_sample = InventoryCreate(item_name="Phân bón NPK", quantity=15.0, unit="kg", min_threshold=20.0)
    sch_sample = ScheduleCreate(task_name="Tưới cây", target_date=date.today())
    alert_sample = AlertCreate(alert_type="TEST", message="Test Alert")
    print(f"  ✅ EnvLog Schema: {env_sample.temperature}°C, {env_sample.humidity}%")
    print(f"  ✅ Inventory Schema: {inv_sample.item_name} ({inv_sample.quantity} {inv_sample.unit})")
    print(f"  ✅ Schedule Schema: {sch_sample.task_name} on {sch_sample.target_date}")
    print(f"  ✅ Alert Schema: {alert_sample.alert_type} - {alert_sample.message}")
except Exception as e:
    print(f"  ❌ Model Validation Error: {e}")
    sys.exit(1)

# 3. AI & MCP SDK Availability
print("\n[3/5] Verifying AI & Protocol SDKs...")
try:
    from mcp.server.fastmcp import FastMCP
    mcp_app = FastMCP("SmartManagerTest")
    print("  ✅ FastMCP Server initialized successfully.")
except Exception as e:
    print(f"  ❌ FastMCP Error: {e}")
    sys.exit(1)

try:
    from google import genai
    print("  ✅ Google GenAI SDK (google-genai) imported successfully.")
except Exception as e:
    print(f"  ❌ Google GenAI SDK Error: {e}")
    sys.exit(1)

# 4. Database Repositories Instantiation
print("\n[4/5] Testing Repository Layer Instantiation...")
try:
    from app.db.repositories import (
        EnvLogsRepository,
        InventoryRepository,
        SchedulesRepository,
        AlertsRepository,
    )
    env_repo = EnvLogsRepository()
    inv_repo = InventoryRepository()
    sch_repo = SchedulesRepository()
    alt_repo = AlertsRepository()
    print("  ✅ All 4 repositories instantiated cleanly (Clean Architecture ready).")
except Exception as e:
    print(f"  ❌ Repositories Error: {e}")
    sys.exit(1)

# 5. Live Supabase Connectivity Test
print("\n[5/5] Testing Supabase Live Connection...")
try:
    from app.db.supabase_client import test_supabase_connection
    res = test_supabase_connection()
    if res["connected"]:
        print(f"  ✅ {res['details']}")
        for tbl, info in res.get("tables", {}).items():
            status = "FOUND" if info.get("exists") else "MISSING"
            print(f"     - Table '{tbl}': {status}")
    else:
        print(f"  ⚠️ {res['details']}")
        print("  💡 Hướng dẫn: Tạo file .env dựa trên .env.example và điền SUPABASE_URL, SUPABASE_KEY để kết nối trực tiếp.")
except Exception as e:
    print(f"  ❌ Connection Test Error: {e}")

print("\n" + "=" * 60)
print("🎉 PHASE 1 SETUP & VERIFICATION COMPLETED!")
print("=" * 60)
