# 🚀 Hướng Dẫn Triển Khai Production (VPS Cloud & Domain)

Tài liệu này hướng dẫn chi tiết cách đưa hệ thống **Điểm Danh STEM** lên **VPS Cloud** (Ubuntu 22.04 / Debian 12) với tên miền thật và chứng chỉ SSL HTTPS miễn phí.

---

## 1. Yêu Cầu Hạ Tầng & Chuẩn Bị

### Cấu hình VPS khuyến nghị
- **OS**: Ubuntu 22.04 LTS hoặc 24.04 LTS
- **CPU**: 2 Cores
- **RAM**: 4GB (cho trường 1.000 - 3.000 học sinh)
- **Ổ cứng**: 40GB SSD
- **Port mở trên Firewall / Cloud Security Group**: `80` (HTTP), `443` (HTTPS), `22` (SSH)

### Trỏ Tên Miền (DNS Records)
Vào trang quản lý tên miền (Cloudflare, Tenten, Matbao, PA Vietnam...):
- `A` record: `@` → `IP_VPS_CỦA_BẠN`
- `A` record: `www` → `IP_VPS_CỦA_BẠN`
- `A` record: `api` (tùy chọn, nếu muốn subdomain riêng) → `IP_VPS_CỦA_BẠN`

---

## 2. Cài Đặt Môi Trường Trên VPS

```bash
# Cập nhật hệ thống
sudo apt update && sudo apt upgrade -y

# Cài đặt Python 3, Nginx, Git, Certbot
sudo apt install -y python3 python3-venv python3-pip nginx git certbot python3-certbot-nginx

# Tạo thư mục chạy ứng dụng
sudo mkdir -p /var/www/stemapp
sudo chown -R $USER:$USER /var/www/stemapp
```

---

## 3. Đưa Source Code Lên VPS

```bash
# Clone source code
cd /var/www/stemapp
git clone <URL_REPO_CUA_BAN> .

# Setup Backend venv
cd /var/www/stemapp/backend
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Cấu hình biến môi trường production
cp .env.example .env
nano .env
```

### Nội dung file `.env` chuẩn Production:
```ini
# Sinh secret key mạnh: python3 -c "import secrets; print(secrets.token_hex(32))"
JWT_SECRET=b79a83f982b1c4e9d08e5a7b6c3d2e1f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d
DEBUG=false
JWT_EXPIRE_HOURS=72

# Tắt dev mode khi chạy thật
OTP_DEV_MODE=false
ZALO_OA_TOKEN=your_zalo_token_here
FCM_SERVER_KEY=your_fcm_key_here

# Cho phép domain của bạn
CORS_ORIGINS=https://stemapp.vn,https://www.stemapp.vn
```

---

## 4. Cấu Hình Systemd Service (Chạy Backend ngầm tự khởi động)

Tạo file dịch vụ systemd:
```bash
sudo nano /etc/systemd/system/stem-backend.service
```

Dán nội dung sau:
```ini
[Unit]
Description=STEM Diem Danh FastAPI Backend
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/stemapp/backend
EnvironmentFile=/var/www/stemapp/backend/.env
ExecStart=/var/www/stemapp/backend/venv/bin/gunicorn app.main:app \
          --workers 4 \
          --worker-class uvicorn.workers.UvicornWorker \
          --bind 127.0.0.1:8000 \
          --access-logfile /var/log/stem_access.log \
          --error-logfile /var/log/stem_error.log

Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

Phân quyền và kích hoạt service:
```bash
sudo chown -R www-data:www-data /var/www/stemapp
sudo systemctl daemon-reload
sudo systemctl enable stem-backend
sudo systemctl start stem-backend
sudo systemctl status stem-backend
```

---

## 5. Cấu Hình Nginx Reverse Proxy (Frontend + Backend + WebSocket)

Tạo cấu hình Nginx:
```bash
sudo nano /etc/nginx/sites-available/stemapp.vn
```

Dán nội dung sau (thay `stemapp.vn` bằng tên miền thật của bạn):
```nginx
server {
    listen 80;
    server_name stemapp.vn www.stemapp.vn;

    # 1. Frontend Static Files (HTML, JS, CSS)
    root /var/www/stemapp/frontend-web;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    # 2. REST API Reverse Proxy
    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # 3. Swagger API Docs & Health Check
    location ~ ^/(docs|redoc|openapi.json|health) {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # 4. WebSocket Real-time Alerts
    location /ws/ {
        proxy_pass http://127.0.0.1:8000/ws/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "Upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400s;
        proxy_send_timeout 86400s;
    }

    # 5. Uploaded Documents & Photos
    location /uploads/ {
        proxy_pass http://127.0.0.1:8000/uploads/;
        client_max_body_size 10M;
    }
}
```

Kích hoạt site và kiểm tra:
```bash
sudo ln -s /etc/nginx/sites-available/stemapp.vn /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

## 6. Cài Đặt Chứng Chỉ SSL Miễn Phí (HTTPS)

```bash
sudo certbot --nginx -d stemapp.vn -d www.stemapp.vn
```
Certbot sẽ tự động cấu hình redirect từ HTTP sang HTTPS và tạo chứng chỉ Let's Encrypt tự động gia hạn sau mỗi 90 ngày.

---

## 7. Kiểm Tra Sau Khi Triển Khai

1. Mở trình duyệt truy cập: `https://stemapp.vn` (Phải hiển thị Landing Page & Tìm trường)
2. Truy cập API Docs: `https://stemapp.vn/docs` (Swagger UI đầy đủ)
3. Thử tạo Server Trường mới hoặc đăng nhập tài khoản Hiệu Trưởng `hieutruong` / `123456`
4. Kiểm tra log hệ thống khi cần:
   ```bash
   sudo journalctl -u stem-backend -f
   sudo tail -f /var/log/stem_error.log
   ```
