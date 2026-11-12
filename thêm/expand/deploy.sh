#!/usr/bin/env bash
# =============================================================================
#  ĐIỂM DANH STEM — 1-CLICK PRODUCTION DEPLOY SCRIPT (Ubuntu VPS)
# =============================================================================
set -e

echo "============================================================"
echo "🚀 ĐANG TRIỂN KHAI HỆ THỐNG ĐIỂM DANH STEM LÊN CLOUD SERVER..."
echo "============================================================"

# 1. Update system packages
echo "📦 1/4: Cập nhật gói hệ thống..."
sudo apt-get update -y
sudo apt-get install -y curl git ufw

# 2. Install Docker & Docker Compose if not installed
if ! command -v docker &> /dev/null; then
    echo "🐳 2/4: Đang cài đặt Docker Engine..."
    curl -fsSL https://get.docker.com | sh
    sudo usermod -aG docker $USER
fi

if ! command -v docker compose &> /dev/null; then
    echo "🐳 Cài đặt Docker Compose Plugin..."
    sudo apt-get install -y docker-compose-plugin
fi

# 3. Open Firewall Ports (HTTP, HTTPS, SSH)
echo "🛡️ 3/4: Cấu hình tường lửa UFW (Port 80, 443, 22)..."
sudo ufw allow 22/tcp || true
sudo ufw allow 80/tcp || true
sudo ufw allow 443/tcp || true

# 4. Build and Launch Containers
echo "⚡ 4/4: Khởi động hệ thống với Docker Compose..."
docker compose down || true
docker compose up --build -d

echo ""
echo "============================================================"
echo "🎉 TRIỂN KHAI HOÀN TẤT THÀNH CÔNG!"
echo "🌐 Truy cập Web: http://$(curl -s ifconfig.me || echo 'IP_VPS_CUA_BAN')"
echo "============================================================"
