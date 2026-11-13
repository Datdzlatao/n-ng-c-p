#!/usr/bin/env bash

# Hệ Thống Smart Farm Multi-Pen & AI Vision
# Script khởi chạy riêng 2 API Backend & AI Vision (Background / Daemon Mode)
# Thích hợp sử dụng khi Frontend đã được deploy trên Vercel!

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"
LOG_DIR="$PROJECT_DIR/logs"
mkdir -p "$LOG_DIR"

AI_PID_FILE="$LOG_DIR/ai_engine.pid"
BACKEND_PID_FILE="$LOG_DIR/backend.pid"

AI_LOG="$LOG_DIR/ai_engine.log"
BACKEND_LOG="$LOG_DIR/backend.log"

# Lấy PID đang chiếm cổng mạng
get_port_pids() {
    local port=$1
    lsof -ti :"$port" 2>/dev/null || fuser "$port"/tcp 2>/dev/null || true
}

# Giải phóng cổng mạng để chống xung đột (Address already in use)
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

# Dừng cả 2 API
stop_apis() {
    echo "=========================================================="
    echo "🛑 Đang dừng 2 API Backend & AI Vision..."
    echo "=========================================================="
    
    kill_pid_file "$AI_PID_FILE" "AI Vision Engine (8001)"
    kill_pid_file "$BACKEND_PID_FILE" "Backend FastAPI (8000)"

    free_port 8001
    free_port 8000

    echo "🔄 Đang reset cấu hình Tailscale Funnel..."
    tailscale funnel reset >/dev/null 2>&1 || sudo tailscale funnel reset >/dev/null 2>&1 || true

    echo "✅ Đã tắt hoàn tất 2 API!"
    echo "=========================================================="
}

# Hiển thị trạng thái 2 API
show_status() {
    echo "=========================================================="
    echo "📊 TRẠNG THÁI 2 API BACKEND & AI VISION (BACKGROUND)"
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

    echo "----------------------------------------------------------"
    echo "🔗 Tailscale Funnel Status:"
    tailscale funnel status 2>/dev/null || sudo tailscale funnel status 2>/dev/null || echo "Tailscale offline hoặc chưa cấu hình"
    echo "=========================================================="
}

# Khởi chạy riêng AI Vision Engine
start_ai() {
    echo "🤖 Khởi động riêng AI Vision Engine (Port 8001) ngầm..."
    kill_pid_file "$AI_PID_FILE" "AI Engine cũ"
    free_port 8001

    nohup "$PROJECT_DIR/.venv/bin/uvicorn" api_server:app \
        --app-dir "$PROJECT_DIR/standalone_ai_engine" \
        --host 0.0.0.0 --port 8001 --reload \
        </dev/null > "$AI_LOG" 2>&1 &
    AI_PID=$!
    echo "$AI_PID" > "$AI_PID_FILE"
    disown "$AI_PID" 2>/dev/null || true

    sleep 2
    tailscale funnel --bg --yes --https=10000 8001 >/dev/null 2>&1 || sudo tailscale funnel --bg --yes --https=10000 8001 >/dev/null 2>&1 || true
    echo "✅ AI Vision Engine đã chạy ngầm trên port 8001 & Funnel 10000"
}

# Khởi chạy riêng Backend FastAPI
start_backend() {
    echo "🚀 Khởi động riêng Backend FastAPI (Port 8000) ngầm..."
    kill_pid_file "$BACKEND_PID_FILE" "Backend cũ"
    free_port 8000

    nohup "$PROJECT_DIR/.venv/bin/uvicorn" app.main:app \
        --host 0.0.0.0 --port 8000 --reload \
        </dev/null > "$BACKEND_LOG" 2>&1 &
    BACKEND_PID=$!
    echo "$BACKEND_PID" > "$BACKEND_PID_FILE"
    disown "$BACKEND_PID" 2>/dev/null || true

    sleep 3
    tailscale funnel --bg --yes --https=8443 8000 >/dev/null 2>&1 || sudo tailscale funnel --bg --yes --https=8443 8000 >/dev/null 2>&1 || true
    echo "✅ Backend FastAPI đã chạy ngầm trên port 8000 & Funnel 8443"
}

# Chờ 2 API sẵn sàng
wait_for_apis() {
    local max_wait=12
    local elapsed=0
    echo -n "⏳ Đang đợi 2 API khởi tạo"
    while [ $elapsed -lt $max_wait ]; do
        if is_port_listening 8001 && is_port_listening 8000; then
            echo " [Sẵn sàng trong ${elapsed}s!]"
            return 0
        fi
        sleep 1
        elapsed=$((elapsed + 1))
        echo -n "."
    done
    echo " [Đã kiểm tra xong]"
}

# Khởi chạy cả 2 API
start_both_apis() {
    echo "=========================================================="
    echo "🌾 Khởi động 2 API Backend & AI Vision (Không chạy Frontend)"
    echo "🚀 CHẾ ĐỘ: BACKGROUND MODE (Tự động chống xung đột cổng)"
    echo "💡 Tối ưu cho hệ thống có Frontend chạy trên Vercel!"
    echo "=========================================================="

    # Bước 1: Dọn dẹp tiến trình cũ và giải phóng cổng 8000 & 8001
    echo "🧹 [Bước 1/3] Kiểm tra và giải phóng cổng (8000, 8001)..."
    kill_pid_file "$AI_PID_FILE" "AI Engine cũ"
    kill_pid_file "$BACKEND_PID_FILE" "Backend cũ"
    free_port 8001
    free_port 8000

    # Bước 2: Khởi động AI Vision Engine ở background (Port 8001)
    echo "🤖 [Bước 2/3] Khởi động AI Vision Engine (Port 8001) ngầm..."
    nohup "$PROJECT_DIR/.venv/bin/uvicorn" api_server:app \
        --app-dir "$PROJECT_DIR/standalone_ai_engine" \
        --host 0.0.0.0 --port 8001 --reload \
        </dev/null > "$AI_LOG" 2>&1 &
    AI_PID=$!
    echo "$AI_PID" > "$AI_PID_FILE"
    disown "$AI_PID" 2>/dev/null || true

    # Bước 3: Khởi động Backend FastAPI ở background (Port 8000)
    echo "🚀 [Bước 3/3] Khởi động Backend FastAPI (Port 8000) ngầm..."
    nohup "$PROJECT_DIR/.venv/bin/uvicorn" app.main:app \
        --host 0.0.0.0 --port 8000 --reload \
        </dev/null > "$BACKEND_LOG" 2>&1 &
    BACKEND_PID=$!
    echo "$BACKEND_PID" > "$BACKEND_PID_FILE"
    disown "$BACKEND_PID" 2>/dev/null || true

    # Đợi 2 API sẵn sàng
    wait_for_apis

    local v_ok="🔴 Khởi động chậm (Xem $AI_LOG)"
    local b_ok="🔴 Khởi động chậm (Xem $BACKEND_LOG)"

    is_port_listening 8001 && v_ok="🟢 Đang lắng nghe (:8001)"
    is_port_listening 8000 && b_ok="🟢 Đang lắng nghe (:8000)"

    # Khởi động Tailscale Funnel cho 2 API
    echo "🔗 Đang kết nối Tailscale Funnel cho 2 API..."
    tailscale funnel reset >/dev/null 2>&1 || sudo tailscale funnel reset >/dev/null 2>&1 || true
    tailscale funnel --bg --yes --https=8443 8000 >/dev/null 2>&1 || sudo tailscale funnel --bg --yes --https=8443 8000 >/dev/null 2>&1 || true
    tailscale funnel --bg --yes --https=10000 8001 >/dev/null 2>&1 || sudo tailscale funnel --bg --yes --https=10000 8001 >/dev/null 2>&1 || true

    echo ""
    echo "🎉 2 API ĐÃ SẴN SÀNG Ở CHẾ ĐỘ NỀN (BACKGROUND):"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🌐 ĐỊA CHỈ NỘI BỘ (LOCAL):"
    echo "👉 Backend API & Docs (FastAPI):       http://localhost:8000/docs [$b_ok]"
    echo "👉 Web Dashboard (FastAPI):            http://localhost:8000"
    echo "👉 WebSocket Endpoint:                 ws://localhost:8000/ws"
    echo "👉 Standalone AI Vision & Uniform:     http://localhost:8001     [$v_ok]"
    echo "👉 API Quét Toàn Thân & Đồng Phục:     http://localhost:8001/api/v1/uniform/inspect"
    echo "👉 Luồng Live Camera MJPEG:            http://localhost:8001/api/v1/camera/video_feed"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🚀 ĐỊA CHỈ TAILSCALE FUNNEL (PUBLIC CHO VERCEL GỌI VỀ):"
    echo "👉 API Agent Backend (HTTPS 8443):     https://dat-latitude-5590-2.tail2bda46.ts.net:8443"
    echo "👉 API Quét Khuôn Mặt (HTTPS 10000):   https://dat-latitude-5590-2.tail2bda46.ts.net:10000"
    echo "👉 Swagger Docs Agent:                 https://dat-latitude-5590-2.tail2bda46.ts.net:8443/docs"
    echo "👉 Swagger Docs Quét Mặt:              https://dat-latitude-5590-2.tail2bda46.ts.net:10000/docs"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📋 THEO DÕI NHẬT KÝ (LOGS REALTIME):"
    echo "  • AI Vision:  tail -f logs/ai_engine.log"
    echo "  • Backend:    tail -f logs/backend.log"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "⚙️  LỆNH ĐIỀU KHIỂN:"
    echo "  • Kiểm tra trạng thái: ./start_apis.sh status"
    echo "  • Tắt 2 API:           ./stop_apis.sh  (hoặc ./start_apis.sh stop)"
    echo "  • Khởi động lại 2 API: ./start_apis.sh restart"
    echo "  • Chạy riêng Backend:  ./start_apis.sh backend"
    echo "  • Chạy riêng AI:       ./start_apis.sh ai"
    echo "=========================================================="
    echo "💡 Terminal đã được giải phóng. 2 API đang chạy ngầm an toàn để phục vụ Vercel!"
}

# Điều hướng tham số dòng lệnh
ACTION="${1:-start}"
case "$ACTION" in
    start)
        start_both_apis
        ;;
    backend)
        start_backend
        ;;
    ai)
        start_ai
        ;;
    stop)
        stop_apis
        ;;
    restart)
        stop_apis
        sleep 1
        start_both_apis
        ;;
    status)
        show_status
        ;;
    *)
        echo "Cách dùng: $0 {start|backend|ai|stop|restart|status}"
        echo "  - Không tham số hoặc 'start': Khởi động cả 2 API"
        echo "  - 'backend': Khởi động riêng Backend FastAPI (Port 8000)"
        echo "  - 'ai': Khởi động riêng AI Vision Engine (Port 8001)"
        echo "  - 'stop': Tắt cả 2 API"
        echo "  - 'status': Xem trạng thái 2 API"
        exit 1
        ;;
esac
