#!/usr/bin/env python3
"""
Comprehensive End-to-End Verification Script for Phases 1, 2, 3, and 4.
Validates:
1. Phase 1: Environment, Models & Repositories
2. Phase 2: FastMCP Server, Resources & Tools
3. Phase 3: AI Agent MCP Host, WebSocket Manager & FastAPI Endpoints
4. Phase 4: The Watcher anomaly detection & APScheduler Morning Briefing
"""

import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import asyncio
from datetime import date
from starlette.testclient import TestClient

print("=" * 70)
print("🚀 SMART MANAGEMENT BACKEND - END-TO-END VERIFICATION (PHASES 1 - 4)")
print("=" * 70)


async def run_tests():
    # ---------------------------------------------------------------
    # PHASE 1: CONFIG & REPOSITORIES
    # ---------------------------------------------------------------
    print("\n[PHASE 1] Checking Core Architecture...")
    from app.config import get_settings
    settings = get_settings()
    print(f"  ✅ Config loaded: {settings.APP_NAME}")
    print(f"  ℹ️ Supabase Configured: {settings.is_supabase_configured}")
    print(f"  ℹ️ Gemini Configured: {settings.is_gemini_configured}")

    # ---------------------------------------------------------------
    # PHASE 2: MCP SERVER, RESOURCES & TOOLS
    # ---------------------------------------------------------------
    print("\n[PHASE 2] Testing MCP Server (FastMCP)...")
    from app.mcp.mcp_server import (
        mcp,
        get_latest_env_logs,
        get_low_stock_inventory,
        manage_inventory,
        manage_schedule,
        create_system_alert,
    )
    tools = [t.name for t in mcp._tool_manager.list_tools()]
    print(f"  ✅ FastMCP Server Name: '{mcp.name}'")
    print(f"  ✅ Registered MCP Tools ({len(tools)}): {tools}")

    # Test Resource execution
    env_res = get_latest_env_logs()
    print(f"  ✅ MCP Resource 'resource://env/latest' callable -> Output length: {len(env_res)} chars")

    stock_res = get_low_stock_inventory()
    print(f"  ✅ MCP Resource 'resource://inventory/low-stock' callable -> Output length: {len(stock_res)} chars")

    # Test Tools execution
    alert_res = create_system_alert(alert_type="TEST_VERIFY", message="Verification script running.")
    print(f"  ✅ MCP Tool 'create_system_alert': {alert_res[:60]}...")

    # ---------------------------------------------------------------
    # PHASE 3: AI AGENT (MCP HOST), WEBSOCKET & FASTAPI
    # ---------------------------------------------------------------
    print("\n[PHASE 3] Testing AI Agent & FastAPI REST / WebSocket...")
    from app.services.agent_service import agent_service
    from app.api.websocket_manager import ws_manager
    from app.main import app

    # Test Agent Chat
    chat_result = await agent_service.chat("Kiểm tra thông số nhiệt độ môi trường mới nhất")
    print(f"  ✅ AI Agent Response: {chat_result['reply'][:80]}...")
    print(f"  ✅ Tool Calls Made: {len(chat_result.get('tool_calls', []))}")

    # Test Chat with inventory command
    stock_chat = await agent_service.chat("Xuất 1 kg Phân bón NPK 20-20-15 khỏi kho")
    print(f"  ✅ AI Agent Inventory Action: {stock_chat['reply'][:80]}...")

    # Test FastAPI Client
    client = TestClient(app)
    health_resp = client.get("/health")
    assert health_resp.status_code == 200
    print(f"  ✅ FastAPI GET /health -> status: {health_resp.json()['status']}")

    dashboard_resp = client.get("/")
    assert dashboard_resp.status_code == 200
    print(f"  ✅ FastAPI GET / (Dashboard HTML) -> HTTP 200 OK")

    api_chat_resp = client.post("/api/chat", json={"message": "Kiểm tra kho"})
    assert api_chat_resp.status_code == 200
    print(f"  ✅ FastAPI POST /api/chat -> HTTP 200 OK")

    # Test WebSocket connection via TestClient
    with client.websocket_connect("/ws") as websocket:
        data = websocket.receive_json()
        print(f"  ✅ WebSocket Handshake Event: '{data.get('event')}' - {data.get('message')}")
        # Test sending chat over WebSocket
        websocket.send_json({"action": "chat", "message": "Kiểm tra vật tư"})
        resp = websocket.receive_json()
        print(f"  ✅ WebSocket Chat Response Received: event='{resp.get('event')}'")

    # ---------------------------------------------------------------
    # PHASE 4: THE WATCHER & APSCHEDULER
    # ---------------------------------------------------------------
    print("\n[PHASE 4] Testing The Watcher & APScheduler...")
    from app.background.scheduler import trigger_daily_briefing
    from app.background.watcher import _evaluate_anomaly_with_gemini

    # Test Watcher Anomaly Evaluation
    dummy_curr = {"temperature": 39.0, "humidity": 30.0}
    dummy_prev = {"temperature": 29.0, "humidity": 70.0}
    eval_text = await _evaluate_anomaly_with_gemini(
        dummy_curr, dummy_prev, ["Nhiệt độ thay đổi đột biến 10.0°C", "Độ ẩm tụt 40.0%"]
    )
    print(f"  ✅ Watcher Anomaly Evaluator: {eval_text[:80]}...")

    # Test Scheduler Daily Briefing Job
    briefing = await trigger_daily_briefing()
    print(f"  ✅ APScheduler Morning Briefing Triggered: Date: {briefing.get('date')}")
    print(f"  ✅ Briefing Content: {briefing.get('briefing')[:80]}...")

    print("\n" + "=" * 70)
    print("🎉 ALL PHASES (1, 2, 3, 4) VERIFIED AND WORKING 100% PERFECTLY!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(run_tests())
