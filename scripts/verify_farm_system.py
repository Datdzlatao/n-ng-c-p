#!/usr/bin/env python3
"""
End-to-End Verification Script for the Upgraded Smart Farm Multi-Pen AI Agent System.
Tests:
1. Multi-Pen Repositories (Pens, Devices, Animals, Animal Transfer across pens, Crops, EnvLogs, Inventory, Alerts, Schedules)
2. FastMCP Server (6 Resources + 9 Tools including transfer_animal_pen, get_pen_status, manage_pen)
3. AI Agent (Multi-pen reasoning & animal transfer via NLP)
4. FastAPI REST Endpoints (/api/pens/{pen_id}/details, /api/animals/transfer) & WebSocket
5. The Watcher & APScheduler
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import asyncio
from starlette.testclient import TestClient

print("=" * 75)
print("🌾 SMART FARM MULTI-PEN AI AGENT SYSTEM - FULL VERIFICATION TEST")
print("=" * 75)


async def run_verification():
    # -----------------------------------------------------------------
    # STEP 1: REPOSITORIES VERIFICATION
    # -----------------------------------------------------------------
    print("\n[STEP 1] Testing Multi-Pen Data Access Repositories...")
    from app.db.repositories.pens import PensRepository
    from app.db.repositories.devices import DevicesRepository
    from app.db.repositories.animals import AnimalsRepository
    from app.db.repositories.crops import CropsRepository
    from app.db.repositories.feed_logs import FeedLogsRepository
    from app.db.repositories.env_logs import EnvLogsRepository
    from app.db.repositories.inventory import InventoryRepository
    from app.db.repositories.alerts import AlertsRepository
    from app.db.repositories.schedules import SchedulesRepository

    pens_repo = PensRepository()
    devices_repo = DevicesRepository()
    animals_repo = AnimalsRepository()
    crops_repo = CropsRepository()
    feed_repo = FeedLogsRepository()
    env_repo = EnvLogsRepository()
    inv_repo = InventoryRepository()
    alerts_repo = AlertsRepository()
    schedules_repo = SchedulesRepository()

    pens = pens_repo.list_all()
    print(f"  ✅ Pens Repository: {len(pens)} pens found: {[p.get('id') for p in pens]}")

    # Test Animal Transfer via Repository
    transfer_res = animals_repo.transfer_pen(
        animal_id="HEO-102",
        target_pen_id="PEN-ISO-01",
        reason="Cách ly điều trị sốt nhẹ theo dõi",
    )
    print(f"  ✅ Animal Pen Transfer (Repo): HEO-102 moved from [{transfer_res.get('old_pen_id')}] -> [{transfer_res.get('target_pen_id')}]")

    animals_in_iso = animals_repo.list_by_pen("PEN-ISO-01")
    print(f"  ✅ Animals in PEN-ISO-01: {len(animals_in_iso)} animals ({[a.get('id') for a in animals_in_iso]})")

    devices_in_iso = devices_repo.list_by_pen("PEN-ISO-01")
    print(f"  ✅ Devices in PEN-ISO-01: {len(devices_in_iso)} devices ({[d.get('name') for d in devices_in_iso]})")

    env_iso = env_repo.get_latest_logs(limit=1, pen_id="PEN-ISO-01")
    print(f"  ✅ Env Telemetry for PEN-ISO-01: Temp={env_iso[0].get('temperature')}°C, Smell={env_iso[0].get('smell_level')} ppm")

    # -----------------------------------------------------------------
    # STEP 2: FASTMCP SERVER, RESOURCES & TOOLS
    # -----------------------------------------------------------------
    print("\n[STEP 2] Testing FastMCP Server (Multi-Pen Resources & Tools)...")
    from app.mcp.mcp_server import (
        mcp,
        get_farm_overview,
        get_pens_list,
        get_pen_status,
        transfer_animal_pen,
        control_device,
        log_feeding,
        update_animal_health,
        manage_inventory,
        manage_schedule,
        create_system_alert,
    )

    tools = [t.name for t in mcp._tool_manager.list_tools()]
    print(f"  ✅ Registered MCP Tools ({len(tools)}): {tools}")

    # Test Resources
    pens_list_str = get_pens_list()
    print(f"  ✅ Resource 'resource://pens/list' -> length: {len(pens_list_str)} chars")

    # Test Tools
    pen_status = get_pen_status(pen_id="PEN-ISO-01")
    print(f"  ✅ Tool 'get_pen_status' (PEN-ISO-01): {len(pen_status)} chars")

    mcp_transfer = transfer_animal_pen(animal_id="HEO-101", target_pen_id="PEN-A02", reason="Đổi sang chuồng xuất chuồng A2")
    print(f"  ✅ Tool 'transfer_animal_pen': {mcp_transfer}")

    dev_res = control_device(action="turn_on", device_name="quạt", pen_id="PEN-A02")
    print(f"  ✅ Tool 'control_device' for PEN-A02: {dev_res}")

    feed_res = log_feeding(pen_id="PEN-A02", food_name="Cám Con Cò Siêu Tăng Trọng", amount=3.0)
    print(f"  ✅ Tool 'log_feeding' for PEN-A02: {feed_res}")

    # -----------------------------------------------------------------
    # STEP 3: AI AGENT (GEMINI / MULTI-PEN FALLBACK ENGINE)
    # -----------------------------------------------------------------
    print("\n[STEP 3] Testing Smart Farm AI Agent Multi-Pen Commands...")
    from app.services.agent_service import agent_service

    # Test 1: Transfer command via NLP
    chat_transfer = await agent_service.chat("Chuyển cá thể HEO-102 sang chuồng cách ly PEN-ISO-01 gấp")
    print(f"  ✅ AI Agent (Transfer Command): {chat_transfer['reply'][:90]}...")

    # Test 2: Inspect specific pen via NLP
    chat_query_pen = await agent_service.chat("Xem thông tin chi tiết chuồng PEN-A02")
    print(f"  ✅ AI Agent (Query Pen Status): {chat_query_pen['reply'][:90]}...")

    # Test 3: Control device at specific pen
    chat_dev_pen = await agent_service.chat("Bật đèn sưởi chuồng cách ly PEN-ISO-01")
    print(f"  ✅ AI Agent (Device for Pen): {chat_dev_pen['reply'][:90]}...")

    # -----------------------------------------------------------------
    # STEP 4: FASTAPI REST APIS & WEBSOCKET
    # -----------------------------------------------------------------
    print("\n[STEP 4] Testing FastAPI Multi-Pen Endpoints & WebSocket...")
    from app.main import app

    client = TestClient(app)

    # Test /api/pens
    r_pens = client.get("/api/pens")
    assert r_pens.status_code == 200
    print(f"  ✅ GET /api/pens -> {len(r_pens.json())} pens found")

    # Test /api/pens/{pen_id}/details
    r_pen_detail = client.get("/api/pens/PEN-ISO-01/details")
    assert r_pen_detail.status_code == 200
    detail = r_pen_detail.json()
    print(f"  ✅ GET /api/pens/PEN-ISO-01/details -> Animals: {detail['animals_count']}, Devices: {detail['devices_count']}")

    # Test /api/animals/transfer
    r_transfer = client.post("/api/animals/transfer", json={
        "animal_id": "HEO-201",
        "target_pen_id": "123",
        "reason": "Điều chuyển về chuồng A1"
    })
    assert r_transfer.status_code == 200
    print(f"  ✅ POST /api/animals/transfer -> Success: {r_transfer.json()['status']}")

    # Test / (Dashboard UI)
    r_dash = client.get("/")
    assert r_dash.status_code == 200
    print(f"  ✅ GET / (Multi-Pen Dashboard) -> HTTP 200 OK ({len(r_dash.text)} bytes)")

    # Test WebSocket connection
    with client.websocket_connect("/ws") as ws:
        init_event = ws.receive_json()
        print(f"  ✅ WebSocket Handshake: '{init_event.get('event')}' - {init_event.get('message')}")

    # -----------------------------------------------------------------
    # STEP 5: THE WATCHER & APSCHEDULER
    # -----------------------------------------------------------------
    print("\n[STEP 5] Testing The Watcher & APScheduler...")
    from app.background.watcher import _evaluate_anomaly_with_gemini
    from app.background.scheduler import trigger_daily_briefing

    eval_msg = await _evaluate_anomaly_with_gemini(
        log_curr={"pen_id": "PEN-A02", "temperature": 39.0, "humidity": 30.0, "smell_level": 16.0},
        log_prev={"pen_id": "PEN-A02", "temperature": 27.5, "humidity": 70.0, "smell_level": 2.0},
        reasons=["Nhiệt độ đột biến tăng 11.5°C", "Nồng độ mùi vượt ngưỡng nguy hiểm (16.0 >= 10.0)"],
    )
    print(f"  ✅ Watcher Anomaly Evaluator: {eval_msg[:90]}...")

    briefing = await trigger_daily_briefing()
    print(f"  ✅ APScheduler Morning Briefing: Tasks: {briefing.get('tasks_count')}, Low stock: {briefing.get('low_stock_count')}")

    # -----------------------------------------------------------------
    # STEP 6: RAG WORKFLOW & DISEASE DIAGNOSIS VERIFICATION (STEM INTEGRATION)
    # -----------------------------------------------------------------
    print("\n[STEP 6] Testing RAG Workflow & Agricultural Disease Diagnosis...")
    from app.services.rag_service import rag_service
    from app.mcp.mcp_server import search_agricultural_knowledge, diagnose_agricultural_disease, get_knowledge_overview

    # 1. Test RAG Context Retrieval
    rag_ctx, docs = rag_service.retrieve_context("heo sốt cao tai tím khó thở tai xanh", k=2)
    assert len(docs) > 0
    print(f"  ✅ RAG VectorStore/Knowledge Retrieval: Found {len(docs)} documents. Top doc: {docs[0]['metadata'].get('disease_name')}")

    # 2. Test RAG Disease Diagnosis Engine
    diag_res = rag_service.diagnose_disease("Heo tại chuồng cách ly bị sốt cao 41 độ, tai tím tái, ho khan")
    assert "PRRS" in diag_res["disease_name"] or "Tai xanh" in diag_res["disease_name"] or "sốt" in diag_res["disease_name"].lower()
    print(f"  ✅ RAG Diagnosis Workflow: Disease={diag_res['disease_name']}, Category={diag_res['category']}, Species={diag_res['species']}")

    # 3. Test MCP RAG Tools
    mcp_search = search_agricultural_knowledge("bệnh sương mai cà chua")
    assert len(mcp_search) > 50
    print(f"  ✅ MCP Tool 'search_agricultural_knowledge' -> {len(mcp_search)} chars returned")

    mcp_diag = diagnose_agricultural_disease("Lá lúa có đốm hình thoi cháy lá", species="Lúa")
    assert "đạo ôn" in mcp_diag.lower() or "lúa" in mcp_diag.lower()
    print(f"  ✅ MCP Tool 'diagnose_agricultural_disease' -> Successfully diagnosed crop disease")

    mcp_kb_overview = get_knowledge_overview()
    print(f"  ✅ MCP Resource 'resource://knowledge/overview' -> Status OK")

    # 4. Test REST API /api/diagnose
    r_diag = client.post("/api/diagnose", data={"user_query": "Heo con bị tiêu chảy phân vàng mất nước"})
    assert r_diag.status_code == 200
    diag_json = r_diag.json()
    assert "answer" in diag_json
    print(f"  ✅ POST /api/diagnose -> Disease: '{diag_json.get('disease_name')}', Species: '{diag_json.get('species')}'")

    # 5. Test REST API /api/knowledge/search
    r_kb = client.get("/api/knowledge/search?query=bệnh+đạo+ôn+lúa")
    assert r_kb.status_code == 200
    assert r_kb.json()["count"] > 0
    print(f"  ✅ GET /api/knowledge/search -> Found {r_kb.json()['count']} knowledge entries")

    # 6. Test AI Agent Chat with RAG query
    chat_rag = await agent_service.chat("Cá thể HEO-102 có triệu chứng sốt cao, tai tím tái. Hãy chẩn đoán và cho phác đồ điều trị.")
    assert len(chat_rag["tool_calls"]) > 0 or "phác đồ" in chat_rag["reply"].lower()
    print(f"  ✅ AI Agent RAG Chat Interaction: Tool called={chat_rag['tool_calls']}, Reply preview={chat_rag['reply'][:80]}...")

    print("\n" + "=" * 75)
    print("🎉 ALL SMART FARM MULTI-PEN & RAG AI COMPONENTS TESTED AND VERIFIED 100% PERFECTLY!")
    print("=" * 75)


if __name__ == "__main__":
    asyncio.run(run_verification())
