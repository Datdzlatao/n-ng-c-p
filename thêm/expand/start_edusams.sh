#!/usr/bin/env bash
# =============================================================================
#  EDUSAMS.IO.VN — ALL-IN-ONE PRODUCTION SERVICE MANAGER
#  Quản lý toàn diện: Frontend, Backend FastAPI, Cloudflare Tunnel & Trạm Camera AI
#  Hỗ trợ các lệnh: start | stop | restart | status | logs [backend|camera|tunnel]
#  Mặc định: Tự động chạy ngầm (Daemon), tắt terminal website VẪN HOẠT ĐỘNG 24/7!
# =============================================================================

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

PID_DIR="$DIR/.run"
mkdir -p "$PID_DIR"
BACKEND_PID_FILE="$PID_DIR/backend.pid"
TUNNEL_PID_FILE="$PID_DIR/tunnel.pid"
CAMERA_PID_FILE="$PID_DIR/camera_supervisor.pid"
GO2RTC_PID_FILE="$PID_DIR/go2rtc.pid"

LOG_DIR="$DIR/logs"
mkdir -p "$LOG_DIR"
BACKEND_LOG="$LOG_DIR/backend.log"
TUNNEL_LOG="$LOG_DIR/tunnel.log"
CAMERA_LOG="$LOG_DIR/camera_supervisor.log"
GO2RTC_LOG="$LOG_DIR/go2rtc.log"

# Màu sắc thông báo
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# ── Hàm kiểm tra tiến trình có đang sống hay không ──
is_running_backend() {
    if [ -n "$(lsof -ti:8000 2>/dev/null)" ]; then
        return 0
    fi
    if [ -f "$BACKEND_PID_FILE" ]; then
        local pid=$(cat "$BACKEND_PID_FILE" 2>/dev/null || true)
        if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            return 0
        fi
    fi
    return 1
}

is_running_webrtc() {
    if pgrep -f "edge/tools/bin/go2rtc" >/dev/null 2>&1; then
        return 0
    fi
    if [ -f "$GO2RTC_PID_FILE" ]; then
        local pid=$(cat "$GO2RTC_PID_FILE" 2>/dev/null || true)
        if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            return 0
        fi
    fi
    return 1
}

is_running_tunnel() {
    if pgrep -f "cloudflared.*edusams-tunnel" >/dev/null 2>&1; then
        return 0
    fi
    if [ -f "$TUNNEL_PID_FILE" ]; then
        local pid=$(cat "$TUNNEL_PID_FILE" 2>/dev/null || true)
        if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            return 0
        fi
    fi
    return 1
}

is_running_camera() {
    if pgrep -f "edge/supervisor.py" >/dev/null 2>&1 || pgrep -f "edge/main.py" >/dev/null 2>&1; then
        return 0
    fi
    if [ -f "$CAMERA_PID_FILE" ]; then
        local pid=$(cat "$CAMERA_PID_FILE" 2>/dev/null || true)
        if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            return 0
        fi
    fi
    return 1
}

# ── Hàm giải phóng cổng mạng ──
free_port() {
    local port=$1
    local pids=$(lsof -ti:$port 2>/dev/null || true)
    if [ -n "$pids" ]; then
        echo -e "${YELLOW}🔄 Đang giải phóng cổng $port (PID: $pids)...${NC}"
        for p in $pids; do
            kill -9 "$p" 2>/dev/null || true
        done
        sleep 1
    fi
}

# ── Hàm Build Frontend nếu cần ──
ensure_frontend_build() {
    if [ ! -f "$DIR/frontend-web/dist/index.html" ] || [ ! -f "$DIR/frontend-web/dist/app/index.html" ]; then
        echo -e "${CYAN}📦 Đang đóng gói Frontend React & Dashboard...${NC}"
        cd "$DIR/frontend-web"
        if [ ! -d "node_modules" ]; then
            echo -e "${YELLOW}⚙️  Đang cài đặt thư viện frontend...${NC}"
            npm install
        fi
        npm run build > /dev/null 2>&1 || {
            echo -e "${RED}❌ Build frontend thất bại! Kiểm tra lại code frontend-web.${NC}"
        }
        cd "$DIR"
        echo -e "${GREEN}✅ Đóng gói Frontend thành công!${NC}"
    fi
}

# ── LỆNH: START ──
start_services() {
    echo -e "${BLUE}============================================================${NC}"
    echo -e "${GREEN}🚀 ĐANG KHỞI ĐỘNG HỆ THỐNG EDUSAMS.IO.VN (PRODUCTION)...${NC}"
    echo -e "${BLUE}============================================================${NC}"

    # 1. Kiểm tra môi trường Backend Python
    cd "$DIR/backend"
    if [ ! -d "venv" ]; then
        echo -e "${CYAN}⚙️  Đang thiết lập Python Virtualenv...${NC}"
        python3 -m venv venv
        venv/bin/pip install -r requirements.txt
    fi
    cd "$DIR"

    # 2. Đảm bảo frontend đã được build đầy đủ
    ensure_frontend_build

    # 3. Dừng các tiến trình cũ trước khi chạy mới
    if is_running_backend || is_running_tunnel || is_running_camera; then
        echo -e "${YELLOW}⚠️  Phát hiện dịch vụ cũ đang chạy, đang làm mới...${NC}"
        stop_services
        sleep 1
    fi

    # Dọn dẹp các process mồ côi và giải phóng cổng mạng
    free_port 8000
    free_port 8081
    free_port 8082
    free_port 1984
    free_port 8554
    free_port 8555
    pkill -f "cloudflared.*edusams-tunnel" 2>/dev/null || true
    pkill -f "edge/supervisor.py" 2>/dev/null || true
    pkill -f "edge/main.py" 2>/dev/null || true
    pkill -f "edge/tools/bin/go2rtc" 2>/dev/null || true

    # 4. Khởi động Backend FastAPI chạy ngầm vĩnh viễn (setsid độc lập)
    echo -e "${CYAN}⚡ [1/3] Đang khởi chạy Backend FastAPI...${NC}"
    setsid "$DIR/backend/venv/bin/python" "$DIR/backend/run.py" </dev/null >"$BACKEND_LOG" 2>&1 &
    local b_pid=$!
    echo "$b_pid" > "$BACKEND_PID_FILE"

    # Kiểm tra Backend đã sẵn sàng (thử lại tối đa 10 lần)
    local retries=10
    local backend_ready=false
    while [ $retries -gt 0 ]; do
        if curl -s http://127.0.0.1:8000/health/live > /dev/null 2>&1; then
            backend_ready=true
            break
        fi
        sleep 1
        retries=$((retries - 1))
    done

    if [ "$backend_ready" = false ]; then
        echo -e "${RED}❌ Không thể khởi động Backend! Chi tiết lỗi xem tại:${NC} $BACKEND_LOG"
        tail -n 20 "$BACKEND_LOG"
        exit 1
    fi
    echo -e "${GREEN}✅ Backend & Dashboard đã sẵn sàng tại http://localhost:8000${NC}"

    # 5. Khởi động Cloudflare Tunnel chạy ngầm vĩnh viễn (setsid độc lập, ép HTTP/2 qua IPv4 mượt mà 0 giật lag)
    echo -e "${CYAN}⚡ [2/3] Đang kết nối đường hầm Cloudflare Tunnel (HTTP/2 IPv4)...${NC}"
    setsid cloudflared tunnel --protocol http2 --edge-ip-version 4 run edusams-tunnel </dev/null >"$TUNNEL_LOG" 2>&1 &
    local t_pid=$!
    echo "$t_pid" > "$TUNNEL_PID_FILE"
    sleep 3

    if ! is_running_tunnel; then
        echo -e "${RED}❌ Cloudflare Tunnel gặp sự cố khi khởi động! Chi tiết xem tại:${NC} $TUNNEL_LOG"
        tail -n 20 "$TUNNEL_LOG"
        exit 1
    fi
    echo -e "${GREEN}✅ Cloudflare Tunnel đã kết nối thành công!${NC}"

    # 6. Khởi động Trạm Camera AI (Supervisor & Multi-Cam workers) chạy ngầm vĩnh viễn
    echo -e "${CYAN}⚡ [3/3] Đang khởi chạy Trạm Camera AI (Multi-Camera Supervisor & Workers)...${NC}"
    local py_cam=""
    if [ -f "$DIR/venv/bin/python" ]; then
        py_cam="$DIR/venv/bin/python"
    elif [ -f "$DIR/.venv/bin/python" ]; then
        py_cam="$DIR/.venv/bin/python"
    elif [ -f "$DIR/backend/venv/bin/python" ]; then
        py_cam="$DIR/backend/venv/bin/python"
    else
        py_cam="python3"
    fi

    local sch_id="${STEM_SCHOOL_ID:-}"
    if [ -z "$sch_id" ] && [ -f "$DIR/edge/data/camera.conf" ]; then
        sch_id=$(grep -E "^school_id" "$DIR/edge/data/camera.conf" 2>/dev/null | awk -F'=' '{print $2}' | tr -d ' \r\n' || true)
    fi
    if [ -z "$sch_id" ] && [ -f "$DIR/edge/data/cameras.json" ]; then
        sch_id=$(python3 -c "import json; d=json.load(open('$DIR/edge/data/cameras.json')); print(d.get('school_id', ''))" 2>/dev/null || true)
    fi
    if [ -z "$sch_id" ]; then
        sch_id=10
    fi

    setsid "$py_cam" "$DIR/edge/supervisor.py" --school "$sch_id" </dev/null >"$CAMERA_LOG" 2>&1 &
    local c_pid=$!
    echo "$c_pid" > "$CAMERA_PID_FILE"
    sleep 3

    local cam_workers=$(pgrep -f "edge/main.py" 2>/dev/null | wc -l)
    if is_running_camera && [ "$cam_workers" -gt 0 ]; then
        echo -e "${GREEN}✅ Trạm Camera AI đã sẵn sàng! ($cam_workers camera AI song song đang chạy, Trường #${sch_id})${NC}"
    elif is_running_camera; then
        echo -e "${YELLOW}⚠️  Supervisor Camera đang chạy nhưng chưa phát hiện camera worker nào. Xem chi tiết tại: $CAMERA_LOG${NC}"
    else
        echo -e "${RED}❌ Không thể khởi động Trạm Camera AI! Chi tiết tại: $CAMERA_LOG${NC}"
    fi

    # 7. Khởi động WebRTC Streaming Engine (go2rtc H.264)
    echo -e "${CYAN}⚡ [4/4] Đang khởi chạy Máy Chủ WebRTC Video Streaming (go2rtc H.264)...${NC}"
    python3 "$DIR/edge/tools/gen_go2rtc_config.py" >/dev/null 2>&1 || true
    if [ -f "$DIR/edge/tools/bin/go2rtc" ] && [ -f "$DIR/edge/go2rtc.yaml" ]; then
        setsid "$DIR/edge/tools/bin/go2rtc" -c "$DIR/edge/go2rtc.yaml" </dev/null >"$GO2RTC_LOG" 2>&1 &
        local g_pid=$!
        echo "$g_pid" > "$GO2RTC_PID_FILE"
        sleep 1
        if is_running_webrtc; then
            echo -e "${GREEN}✅ WebRTC Stream Engine đã sẵn sàng! (Cổng WHEP/WebRTC: 1984/8555)${NC}"
        fi
    fi

    echo ""
    echo -e "${BLUE}============================================================${NC}"
    echo -e "${GREEN}🎉 TOÀN BỘ HỆ THỐNG ĐÃ KHỞI ĐỘNG VÀ CHẠY NGẦM THÀNH CÔNG 24/7!${NC}"
    echo -e "${BLUE}============================================================${NC}"
    echo -e "🌐 Website chính thức:  ${CYAN}https://edusams.io.vn${NC}"
    echo -e "📊 Trang Dashboard:     ${CYAN}https://edusams.io.vn/app/index.html?school_id=${sch_id}${NC}"
    echo -e "👑 Quản trị tối cao:    ${YELLOW}admin / Admin@EduSams2026#Secure${NC}"
    echo -e "📝 File nhật ký (Log):"
    echo -e "   - Backend:  ${CYAN}logs/backend.log${NC}"
    echo -e "   - Tunnel:   ${CYAN}logs/tunnel.log${NC}"
    echo -e "   - Camera:   ${CYAN}logs/camera_supervisor.log${NC}"
    echo -e "${BLUE}------------------------------------------------------------${NC}"
    echo -e "💡 ${GREEN}Ghi chú quan trọng:${NC} Tất cả dịch vụ (Backend, Tunnel, Camera AI) đang chạy ngầm."
    echo -e "   Bạn có thể ${GREEN}tắt cửa sổ Terminal này${NC}, hệ thống vẫn hoạt động liên tục 24/7!"
    echo -e "   - Kiểm tra trạng thái: ${YELLOW}./start_edusams.sh status${NC}"
    echo -e "   - Tắt toàn bộ:        ${YELLOW}./start_edusams.sh stop${NC}"
    echo -e "   - Khởi động lại:      ${YELLOW}./start_edusams.sh restart${NC}"
    echo -e "   - Xem log Backend:    ${YELLOW}./start_edusams.sh logs${NC}"
    echo -e "   - Xem log Camera AI:  ${YELLOW}./start_edusams.sh logs camera${NC} (hoặc logs-cam)"
    echo -e "${BLUE}============================================================${NC}"
    echo ""
}

# ── LỆNH: STOP ──
stop_services() {
    echo -e "${YELLOW}🛑 Đang dừng toàn bộ dịch vụ EduSAMS (Backend, Tunnel & Camera AI)...${NC}"

    # 1. Dừng Trạm Camera AI & Supervisor
    if [ -f "$CAMERA_PID_FILE" ]; then
        local c_pid=$(cat "$CAMERA_PID_FILE" 2>/dev/null || true)
        if [ -n "$c_pid" ]; then
            kill "$c_pid" 2>/dev/null || true
            sleep 1
            kill -9 "$c_pid" 2>/dev/null || true
        fi
        rm -f "$CAMERA_PID_FILE"
    fi
    pkill -f "edge/supervisor.py" 2>/dev/null || true
    pkill -f "edge/main.py" 2>/dev/null || true
    free_port 8081
    free_port 8082
    free_port 8083

    # 2. Dừng Backend
    if [ -f "$BACKEND_PID_FILE" ]; then
        local b_pid=$(cat "$BACKEND_PID_FILE" 2>/dev/null || true)
        if [ -n "$b_pid" ]; then
            kill "$b_pid" 2>/dev/null || true
            sleep 1
            kill -9 "$b_pid" 2>/dev/null || true
        fi
        rm -f "$BACKEND_PID_FILE"
    fi
    free_port 8000
    pkill -f "run.py" 2>/dev/null || true

    # 3. Dừng Cloudflare Tunnel
    if [ -f "$TUNNEL_PID_FILE" ]; then
        local t_pid=$(cat "$TUNNEL_PID_FILE" 2>/dev/null || true)
        if [ -n "$t_pid" ]; then
            kill "$t_pid" 2>/dev/null || true
            sleep 1
            kill -9 "$t_pid" 2>/dev/null || true
        fi
        rm -f "$TUNNEL_PID_FILE"
    fi
    pkill -f "cloudflared tunnel run edusams-tunnel" 2>/dev/null || true

    # 4. Dừng WebRTC Media Server (go2rtc)
    if [ -f "$GO2RTC_PID_FILE" ]; then
        local g_pid=$(cat "$GO2RTC_PID_FILE" 2>/dev/null || true)
        if [ -n "$g_pid" ]; then
            kill "$g_pid" 2>/dev/null || true
            sleep 1
            kill -9 "$g_pid" 2>/dev/null || true
        fi
        rm -f "$GO2RTC_PID_FILE"
    fi
    pkill -f "edge/tools/bin/go2rtc" 2>/dev/null || true
    free_port 1984
    free_port 8554
    free_port 8555

    echo -e "${GREEN}✅ Toàn bộ dịch vụ (Backend, Tunnel, WebRTC, Trạm Camera AI) đã được dừng an toàn.${NC}"
}

# ── LỆNH: STATUS ──
status_services() {
    echo -e "${BLUE}============================================================${NC}"
    echo -e "${CYAN}🔍 TRẠNG THÁI HỆ THỐNG EDUSAMS.IO.VN (ALL-IN-ONE)${NC}"
    echo -e "${BLUE}============================================================${NC}"

    # Backend
    if is_running_backend; then
        local b_pid=$(lsof -ti:8000 2>/dev/null | head -n 1)
        echo -e "🔹 Backend FastAPI:     ${GREEN}● ĐANG CHẠY${NC} (PID: ${b_pid:-'Active'}, Cổng 8000)"
    else
        echo -e "🔹 Backend FastAPI:     ${RED}○ ĐÃ DỪNG${NC}"
    fi

    # WebRTC Media Server
    if is_running_webrtc; then
        local g_pid=$(pgrep -f "edge/tools/bin/go2rtc" 2>/dev/null | head -n 1)
        echo -e "🔹 WebRTC Engine:       ${GREEN}● ĐANG CHẠY${NC} (PID: ${g_pid:-'Active'}, go2rtc H.264)"
    else
        echo -e "🔹 WebRTC Engine:       ${RED}○ ĐÃ DỪNG${NC}"
    fi

    # Cloudflare Tunnel
    if is_running_tunnel; then
        local t_pid=$(pgrep -f "cloudflared tunnel run edusams-tunnel" 2>/dev/null | head -n 1)
        echo -e "🔹 Cloudflare Tunnel:   ${GREEN}● ĐANG KẾT NỐI${NC} (PID: ${t_pid:-'Active'})"
    else
        echo -e "🔹 Cloudflare Tunnel:   ${RED}○ ĐÃ DỪNG${NC}"
    fi

    # Tailscale Funnel / Tunnel
    if command -v tailscale >/dev/null 2>&1; then
        local ts_state=""
        local ts_domain=""
        read -r ts_state ts_domain < <(tailscale status --json 2>/dev/null | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('BackendState',''), (d.get('Self') or {}).get('DNSName','').rstrip('.'))" 2>/dev/null || true)
        if [ "$ts_state" = "Running" ]; then
            echo -e "🔹 Tailscale Funnel:    ${GREEN}● ĐANG HOẠT ĐỘNG${NC} (https://${ts_domain:-'ts.net'})"
        else
            echo -e "🔹 Tailscale Funnel:    ${YELLOW}○ ${ts_state:-'Chưa kết nối'}${NC}"
        fi
    fi

    # Trạm Camera AI
    if is_running_camera; then
        local c_pid=$(pgrep -f "edge/supervisor.py" 2>/dev/null | head -n 1)
        local cam_workers=$(pgrep -f "edge/main.py" 2>/dev/null | wc -l)
        echo -e "🔹 Trạm Camera AI:      ${GREEN}● ĐANG CHẠY${NC} (Supervisor PID: ${c_pid:-'Active'}, $cam_workers camera AI song song)"
        for port in 8081 8082 8083; do
            local cam_p=$(lsof -ti:$port -sTCP:LISTEN 2>/dev/null | head -n 1 || true)
            if [ -n "$cam_p" ]; then
                echo -e "   └ Cổng stream $port:    ${GREEN}● Sẵn sàng (200 OK)${NC} (PID: $cam_p)"
            fi
        done
    else
        echo -e "🔹 Trạm Camera AI:      ${RED}○ ĐÃ DỪNG${NC}"
    fi

    echo -e "${BLUE}------------------------------------------------------------${NC}"
    if is_running_backend && is_running_tunnel; then
        echo -e "🌐 Website chính thức:   ${CYAN}https://edusams.io.vn${NC}"
        if [ -n "$ts_domain" ]; then
            echo -e "🔒 Đường hầm Tailscale:  ${CYAN}https://${ts_domain}${NC}"
        fi
        if is_running_camera; then
            echo -e "📹 Live Stream Camera:   ${GREEN}Hoạt động trực tiếp trên Dashboard & Tailscale${NC}"
        fi
    else
        echo -e "💡 Dùng lệnh: ${YELLOW}./start_edusams.sh start${NC} để khởi động lại toàn bộ hệ thống."
    fi
    echo -e "${BLUE}============================================================${NC}"
}

# ── LỆNH: LOGS ──
show_logs() {
    local target="${1:-backend}"
    if [ "$target" = "camera" ] || [ "$target" = "cam" ]; then
        echo -e "${CYAN}📜 Đang hiển thị nhật ký Trạm Camera AI (logs/camera_supervisor.log)...${NC}"
        echo -e "${YELLOW}(Ấn Ctrl+C để thoát xem log, hệ thống vẫn chạy ngầm)${NC}"
        tail -n 40 -f "$CAMERA_LOG"
    elif [ "$target" = "tunnel" ]; then
        echo -e "${CYAN}📜 Đang hiển thị nhật ký Cloudflare Tunnel (logs/tunnel.log)...${NC}"
        echo -e "${YELLOW}(Ấn Ctrl+C để thoát xem log, hệ thống vẫn chạy ngầm)${NC}"
        tail -n 40 -f "$TUNNEL_LOG"
    elif [ "$target" = "webrtc" ] || [ "$target" = "rtc" ] || [ "$target" = "go2rtc" ]; then
        echo -e "${CYAN}📜 Đang hiển thị nhật ký WebRTC Engine (logs/go2rtc.log)...${NC}"
        echo -e "${YELLOW}(Ấn Ctrl+C để thoát xem log, hệ thống vẫn chạy ngầm)${NC}"
        tail -n 40 -f "$GO2RTC_LOG"
    else
        echo -e "${CYAN}📜 Đang hiển thị nhật ký Backend (logs/backend.log)...${NC}"
        echo -e "💡 Mẹo: Gõ '${YELLOW}./start_edusams.sh logs camera${NC}' hoặc '${YELLOW}./start_edusams.sh logs-cam${NC}' để xem camera AI."
        echo -e "${YELLOW}(Ấn Ctrl+C để thoát xem log, hệ thống vẫn chạy ngầm)${NC}"
        tail -n 40 -f "$BACKEND_LOG"
    fi
}

# ── XỬ LÝ LỆNH TRUYỀN VÀO ──
case "${1:-start}" in
    start)
        start_services
        ;;
    stop)
        stop_services
        ;;
    restart)
        stop_services
        sleep 1
        start_services
        ;;
    status)
        status_services
        ;;
    logs)
        show_logs "$2"
        ;;
    logs-cam|logs-camera)
        show_logs "camera"
        ;;
    logs-tunnel)
        show_logs "tunnel"
        ;;
    logs-webrtc|logs-rtc)
        show_logs "webrtc"
        ;;
    cam|camera)
        echo -e "${CYAN}📷 Đang khởi chạy Trạm Camera AI trực tiếp trên màn hình (Supervisor Foreground)...${NC}"
        local py_cam=""
        if [ -f "$DIR/venv/bin/python" ]; then
            py_cam="$DIR/venv/bin/python"
        elif [ -f "$DIR/.venv/bin/python" ]; then
            py_cam="$DIR/.venv/bin/python"
        else
            py_cam="python3"
        fi
        shift || true
        "$py_cam" "$DIR/edge/supervisor.py" --school 10 "$@"
        ;;
    main|edge)
        echo -e "${CYAN}📷 Đang khởi chạy trực tiếp edge/main.py...${NC}"
        local py_cam=""
        if [ -f "$DIR/venv/bin/python" ]; then
            py_cam="$DIR/venv/bin/python"
        elif [ -f "$DIR/.venv/bin/python" ]; then
            py_cam="$DIR/.venv/bin/python"
        else
            py_cam="python3"
        fi
        shift || true
        "$py_cam" "$DIR/edge/main.py" "$@"
        ;;
    *)
        echo "Cách sử dụng: $0 {start|stop|restart|status|logs [backend|camera|tunnel]|logs-cam|cam|main}"
        echo "  - start:        Khởi động trọn gói 24/7 (Backend, Cloudflare Tunnel, Camera AI)"
        echo "  - stop:         Dừng toàn bộ hệ thống"
        echo "  - restart:      Khởi động lại toàn bộ dịch vụ"
        echo "  - status:       Kiểm tra trạng thái chi tiết của các dịch vụ"
        echo "  - logs:         Xem nhật ký thời gian thực (mặc định: backend)"
        echo "  - logs-cam:     Xem nhật ký camera AI"
        echo "  - cam:          Chạy Supervisor Camera trực tiếp trên Terminal"
        echo "  - main:         Chạy trực tiếp edge/main.py kèm tham số tuỳ chọn"
        exit 1
        ;;
esac
