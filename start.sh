#!/usr/bin/env bash

# Hệ Thống Smart Farm Multi-Pen & AI Vision
# Script khởi chạy và quản lý nền (Background / Daemon Mode)

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"
LOG_DIR="$PROJECT_DIR/logs"
mkdir -p "$LOG_DIR"

AI_PID_FILE="$LOG_DIR/ai_engine.pid"
BACKEND_PID_FILE="$LOG_DIR/backend.pid"
FRONTEND_PID_FILE="$LOG_DIR/frontend.pid"

AI_LOG="$LOG_DIR/ai_engine.log"
BACKEND_LOG="$LOG_DIR/backend.log"
FRONTEND_LOG="$LOG_DIR/frontend.log"

# Lấy PID đang chiếm cổng mạng
get_port_pids() {
    local port=$1
    lsof -ti :"$port" 2>/dev/null || fuser "$port"/tcp 2>/dev/null || true
}

# Giải phóng cổng mạng để tránh xung đột (Address already in use)
free_port() {
    local port=$1
    local pids
    pids=$(get_port_pids "$port")
    if [ -n "$pids" ]; then
        echo "  ⚠️  Cổng $port đang bị chiếm bởi PID ($pids), đang giải phóng..."
        kill -15 $pids 2>/dev/null || true
        sleep 0.8
        pids=$(get_port_pids "$port")
        if [ -n "$pids" ]; then
            kill -9 $pids 2>/dev/null || true
            sleep 0.2
        fi
    fi
}

# Dừng tiến trình theo PID file
kill_pid_file() {
    local pid_file=$1
    local name=$2
    if [ -f "$pid_file" ]; then
        local pid
        pid=$(cat "$pid_file" 2>/dev/null || true)
        if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            echo "  ⏹️  Đang dừng $name (PID: $pid)..."
            kill -15 "$pid" 2>/dev/null || true
            sleep 0.5
            if kill -0 "$pid" 2>/dev/null; then
                kill -9 "$pid" 2>/dev/null || true
            fi
        fi
        rm -f "$pid_file"
    fi
}

# Kiểm tra trạng thái cổng đang lắng nghe
is_port_listening() {
    local port=$1
    if ss -tlH "( sport = :$port )" 2>/dev/null | grep -q ":$port"; then
        return 0
    elif timeout 1 bash -c "echo > /dev/tcp/127.0.0.1/$port" 2>/dev/null; then
        return 0
    else
        return 1
    fi
}

# Dừng toàn bộ hệ thống
stop_all() {
    echo "=========================================================="
    echo "🛑 Đang tắt toàn bộ hệ thống Smart Farm & AI Vision..."
    echo "=========================================================="
    
    kill_pid_file "$AI_PID_FILE" "AI Vision Engine (8001)"
    kill_pid_file "$BACKEND_PID_FILE" "Backend FastAPI (8000)"
    kill_pid_file "$FRONTEND_PID_FILE" "Frontend Next.js (3000)"

    # Giải phóng triệt để các cổng
    free_port 8001
    free_port 8000
    free_port 3000

    echo "🔄 Đang reset cấu hình Tailscale Funnel..."
    tailscale funnel reset >/dev/null 2>&1 || sudo tailscale funnel reset >/dev/null 2>&1 || true

    echo "✅ Đã tắt hoàn tất toàn bộ dịch vụ!"
    echo "=========================================================="
}

# Hiển thị trạng thái
show_status() {
    echo "=========================================================="
    echo "📊 TRẠNG THÁI HỆ THỐNG SMART FARM (BACKGROUND MODE)"
    echo "=========================================================="

    if is_port_listening 8001; then
        local pids
        pids=$(get_port_pids 8001 | tr '\n' ' ')
        echo "🟢 [Port 8001] AI Vision Engine:        ĐANG CHẠY (PID: $pids)"
    else
        echo "🔴 [Port 8001] AI Vision Engine:        ĐANG DỪNG"
    fi

    if is_port_listening 8000; then
        local pids
        pids=$(get_port_pids 8000 | tr '\n' ' ')
        echo "🟢 [Port 8000] Backend FastAPI:         ĐANG CHẠY (PID: $pids)"
    else
        echo "🔴 [Port 8000] Backend FastAPI:         ĐANG DỪNG"
    fi

    if is_port_listening 3000; then
        local pids
        pids=$(get_port_pids 3000 | tr '\n' ' ')
        echo "🟢 [Port 3000] Frontend Next.js:        ĐANG CHẠY (PID: $pids)"
    else
        echo "🔴 [Port 3000] Frontend Next.js:        ĐANG DỪNG"
    fi

    echo "----------------------------------------------------------"
    echo "🔗 Tailscale Funnel Status:"
    tailscale funnel status 2>/dev/null || sudo tailscale funnel status 2>/dev/null || echo "Tailscale offline hoặc chưa cấu hình"
    echo "=========================================================="
}

# Chờ các cổng sẵn sàng
wait_for_services() {
    local max_wait=12
    local elapsed=0
    echo -n "⏳ Đang đợi các dịch vụ khởi tạo"
    while [ $elapsed -lt $max_wait ]; do
        if is_port_listening 8001 && is_port_listening 8000 && is_port_listening 3000; then
            echo " [Sẵn sàng trong ${elapsed}s!]"
            return 0
        fi
        sleep 1
        elapsed=$((elapsed + 1))
        echo -n "."
    done
    echo " [Đã kiểm tra xong]"
}

# Khởi chạy hệ thống ở chế độ background
start_all() {
    echo "=========================================================="
    echo "🌾 Khởi động Hệ Thống Smart Farm Multi-Pen & AI Vision"
    echo "🚀 CHẾ ĐỘ: BACKGROUND MODE (Tự động chống xung đột cổng)"
    echo "=========================================================="

    # Bước 1: Dọn dẹp tiến trình cũ và giải phóng cổng trước khi chạy
    echo "🧹 [Bước 1/4] Kiểm tra và giải phóng cổng (8000, 8001, 3000)..."
    kill_pid_file "$AI_PID_FILE" "AI Engine cũ"
    kill_pid_file "$BACKEND_PID_FILE" "Backend cũ"
    kill_pid_file "$FRONTEND_PID_FILE" "Frontend cũ"
    free_port 8001
    free_port 8000
    free_port 3000

    # Bước 2: Khởi động AI Vision Engine ở background
    echo "🤖 [Bước 2/4] Khởi động AI Vision Engine (Port 8001) ngầm..."
    nohup "$PROJECT_DIR/.venv/bin/uvicorn" api_server:app \
        --app-dir "$PROJECT_DIR/standalone_ai_engine" \
        --host 0.0.0.0 --port 8001 --reload \
        </dev/null > "$AI_LOG" 2>&1 &
    AI_PID=$!
    echo "$AI_PID" > "$AI_PID_FILE"
    disown "$AI_PID" 2>/dev/null || true

    # Bước 3: Khởi động Backend FastAPI ở background
    echo "🚀 [Bước 3/4] Khởi động Backend FastAPI (Port 8000) ngầm..."
    nohup "$PROJECT_DIR/.venv/bin/uvicorn" app.main:app \
        --host 0.0.0.0 --port 8000 --reload \
        </dev/null > "$BACKEND_LOG" 2>&1 &
    BACKEND_PID=$!
    echo "$BACKEND_PID" > "$BACKEND_PID_FILE"
    disown "$BACKEND_PID" 2>/dev/null || true

    # Bước 4: Khởi động Frontend Next.js ở background
    echo "🌐 [Bước 4/4] Khởi động Frontend Next.js (Port 3000) ngầm..."
    (
        cd "$PROJECT_DIR/frontend"
        nohup npm run dev </dev/null > "$FRONTEND_LOG" 2>&1 &
        echo $! > "$FRONTEND_PID_FILE"
        disown $! 2>/dev/null || true
    )

    # Đợi dịch vụ sẵn sàng
    wait_for_services

    # Kiểm tra cổng thực tế
    local v_ok="🔴 Khởi động chậm (Xem $AI_LOG)"
    local b_ok="🔴 Khởi động chậm (Xem $BACKEND_LOG)"
    local f_ok="🔴 Khởi động chậm (Xem $FRONTEND_LOG)"

    is_port_listening 8001 && v_ok="🟢 Đang lắng nghe (:8001)"
    is_port_listening 8000 && b_ok="🟢 Đang lắng nghe (:8000)"
    is_port_listening 3000 && f_ok="🟢 Đang lắng nghe (:3000)"

    # Khởi động Tailscale Funnel ở chế độ background
    echo "🔗 Đang kết nối Tailscale Funnel (HTTPS Public Internet)..."
    tailscale funnel reset >/dev/null 2>&1 || sudo tailscale funnel reset >/dev/null 2>&1 || true
    tailscale funnel --bg --yes --https=443 3000 >/dev/null 2>&1 || sudo tailscale funnel --bg --yes --https=443 3000 >/dev/null 2>&1 || true
    tailscale funnel --bg --yes --https=8443 8000 >/dev/null 2>&1 || sudo tailscale funnel --bg --yes --https=8443 8000 >/dev/null 2>&1 || true
    tailscale funnel --bg --yes --https=10000 8001 >/dev/null 2>&1 || sudo tailscale funnel --bg --yes --https=10000 8001 >/dev/null 2>&1 || true

    echo ""
    echo "🎉 HỆ THỐNG ĐÃ SẴN SÀNG Ở CHẾ ĐỘ NỀN (BACKGROUND):"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🌐 ĐỊA CHỈ NỘI BỘ (LOCAL):"
    echo "👉 Giao diện Web App (Next.js):        http://localhost:3000     [$f_ok]"
    echo "👉 Backend API & Docs (FastAPI):       http://localhost:8000/docs [$b_ok]"
    echo "👉 Web Dashboard (FastAPI):            http://localhost:8000"
    echo "👉 WebSocket Endpoint:                 ws://localhost:8000/ws"
    echo "👉 Standalone AI Vision & Uniform:     http://localhost:8001     [$v_ok]"
    echo "👉 API Quét Toàn Thân & Đồng Phục:     http://localhost:8001/api/v1/uniform/inspect"
    echo "👉 Luồng Live Camera MJPEG:            http://localhost:8001/api/v1/camera/video_feed"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🚀 ĐỊA CHỈ TAILSCALE FUNNEL (PUBLIC INTERNET):"
    echo "👉 Giao diện Web App (HTTPS 443):      https://dat-latitude-5590-2.tail2bda46.ts.net"
    echo "👉 API Agent Backend (HTTPS 8443):     https://dat-latitude-5590-2.tail2bda46.ts.net:8443"
    echo "👉 API Quét Khuôn Mặt (HTTPS 10000):   https://dat-latitude-5590-2.tail2bda46.ts.net:10000"
    echo "👉 Swagger Docs Agent:                 https://dat-latitude-5590-2.tail2bda46.ts.net:8443/docs"
    echo "👉 Swagger Docs Quét Mặt:              https://dat-latitude-5590-2.tail2bda46.ts.net:10000/docs"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📋 THEO DÕI NHẬT KÝ (LOGS REALTIME):"
    echo "  • AI Vision:  tail -f logs/ai_engine.log"
    echo "  • Backend:    tail -f logs/backend.log"
    echo "  • Frontend:   tail -f logs/frontend.log"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "⚙️  LỆNH ĐIỀU KHIỂN HỆ THỐNG:"
    echo "  • Kiểm tra trạng thái: ./start.sh status"
    echo "  • Tắt toàn bộ:         ./stop.sh  (hoặc ./start.sh stop)"
    echo "  • Khởi động lại:       ./start.sh restart"
    echo "=========================================================="
    echo "💡 Terminal đã được giải phóng. Các dịch vụ đang chạy ngầm an toàn!"
}

# Điều hướng tham số dòng lệnh
ACTION="${1:-start}"
case "$ACTION" in
    start)
        start_all
        ;;
    apis)
        exec "$PROJECT_DIR/start_apis.sh" start
        ;;
    backend)
        exec "$PROJECT_DIR/start_apis.sh" backend
        ;;
    ai)
        exec "$PROJECT_DIR/start_apis.sh" ai
        ;;
    stop)
        stop_all
        ;;
    restart)
        stop_all
        sleep 1
        start_all
        ;;
    status)
        show_status
        ;;
    *)
        echo "Cách dùng: $0 {start|apis|backend|ai|stop|restart|status}"
        echo "  - Không tham số hoặc 'start': Khởi động cả 3 (Frontend + Backend + AI)"
        echo "  - 'apis': Khởi động riêng 2 API Backend & AI (dành cho khi Frontend chạy Vercel)"
        echo "  - 'backend': Khởi động riêng Backend FastAPI"
        echo "  - 'ai': Khởi động riêng AI Vision Engine"
        echo "  - 'stop': Tắt toàn bộ"
        echo "  - 'status': Xem trạng thái hệ thống"
        exit 1
        ;;
esac
