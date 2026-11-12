#!/usr/bin/env bash

# Dừng lại nếu có lỗi
set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

echo "=========================================================="
echo "🌾 Khởi động Hệ Thống Smart Farm Multi-Pen & AI Vision"
echo "=========================================================="

# Bắt tín hiệu Ctrl+C để tắt các tiến trình
cleanup() {
    echo ""
    echo "🛑 Đang tắt toàn bộ hệ thống..."
    kill $(jobs -p) 2>/dev/null || true
    echo "✅ Đã tắt hoàn tất!"
    exit 0
}
trap cleanup SIGINT SIGTERM EXIT

# 1. Khởi động Standalone AI Vision Engine (Port 8001)
echo "🤖 [1/3] Đang chạy Standalone AI Vision & Uniform Engine trên http://localhost:8001..."
.venv/bin/uvicorn api_server:app --app-dir standalone_ai_engine --host 0.0.0.0 --port 8001 --reload &
VISION_PID=$!

# Chờ 2 giây để AI Vision Engine sẵn sàng
sleep 2

# 2. Khởi động Backend FastAPI (Port 8000)
echo "🚀 [2/3] Đang chạy Backend FastAPI trên http://localhost:8000..."
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# Chờ 3 giây để backend khởi tạo hoàn tất
sleep 3

# 3. Khởi động Frontend Next.js (Port 3000)
echo "🌐 [3/3] Đang chạy Frontend Next.js trên http://localhost:3000..."
cd "$PROJECT_DIR/frontend"
npm run dev &
FRONTEND_PID=$!

echo ""
echo "🎉 HỆ THỐNG ĐÃ SẴN SÀNG:"
echo "👉 Giao diện Web App (Next.js):     http://localhost:3000"
echo "👉 Backend API & Docs (FastAPI):    http://localhost:8000/docs"
echo "👉 Web Dashboard (FastAPI):         http://localhost:8000"
echo "👉 WebSocket Endpoint:              ws://localhost:8000/ws"
echo "👉 Standalone AI Vision & Uniform:  http://localhost:8001"
echo "👉 API Quét Toàn Thân & Đồng Phục:  http://localhost:8001/api/v1/uniform/inspect"
echo "👉 Backend Proxy Đồng Phục API:     http://localhost:8000/api/uniform/scan"
echo "👉 API Quét Live Camera AI 24/7:    http://localhost:8000/api/staff/live-scan"
echo "👉 Luồng Live Camera MJPEG 30 FPS:  http://localhost:8000/api/camera/video_feed"
echo ""
echo "Nhấn [Ctrl + C] bất cứ lúc nào để dừng toàn bộ hệ thống."
echo "=========================================================="

# Đợi các tiến trình chạy
wait
