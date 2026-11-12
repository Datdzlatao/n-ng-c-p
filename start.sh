#!/usr/bin/env bash

# Dừng lại nếu có lỗi
set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

echo "=========================================================="
echo "🌾 Khởi động Hệ Thống Smart Farm Multi-Pen (Backend & Frontend)"
echo "=========================================================="

# Bắt tín hiệu Ctrl+C để tắt cả hai tiến trình
cleanup() {
    echo ""
    echo "🛑 Đang tắt toàn bộ hệ thống..."
    kill $(jobs -p) 2>/dev/null || true
    echo "✅ Đã tắt hoàn tất!"
    exit 0
}
trap cleanup SIGINT SIGTERM EXIT

# 1. Khởi động Backend FastAPI (Port 8000)
echo "🚀 [1/2] Đang chạy Backend FastAPI trên http://localhost:8000..."
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# Chờ 2 giây để backend khởi tạo
sleep 2

# 2. Khởi động Frontend Next.js (Port 3000)
echo "🌐 [2/2] Đang chạy Frontend Next.js trên http://localhost:3000..."
cd "$PROJECT_DIR/frontend"
npm run dev &
FRONTEND_PID=$!

echo ""
echo "🎉 HỆ THỐNG ĐÃ SẴN SÀNG:"
echo "👉 Giao diện Web App:      http://localhost:3000"
echo "👉 Backend API & Docs:     http://localhost:8000/docs"
echo "👉 WebSocket Endpoint:     ws://localhost:8000/ws"
echo ""
echo "Nhấn [Ctrl + C] bất cứ lúc nào để dừng cả 2 phần."
echo "=========================================================="

# Đợi các tiến trình chạy
wait
