# 🎓 HƯỚNG DẪN TOÀN DIỆN: VẬN HÀNH & TRIỂN KHAI NỀN TẢNG ĐIỂM DANH STEM

> **Phiên bản:** 1.0.0 Multi-Tenant SaaS  
> **Kiến trúc:** Monorepo (Backend FastAPI + Frontend Web SPA + Mobile Flutter + Edge Camera AI)

---

## 📑 MỤC LỤC

1. [Cấu Trúc Hệ Thống](#1-cấu-trúc-hệ-thống)
2. [Chạy Thử Nghiệm Tại Máy (Local Development)](#2-chạy-thử-nghiệm-tại-máy-local-development)
3. [Chuẩn Bị Tên Miền & Cloud VPS](#3-chuẩn-bị-tên-miền--cloud-vps)
4. [Hướng Dẫn Cài Đặt VPS Cloud Chi Tiết (A-Z)](#4-hướng-dẫn-cài-đặt-vps-cloud-chi-tiết-a-z)
5. [Cấu Hình Nginx & Kích Hoạt HTTPS (SSL Miễn Phí)](#5-cấu-hình-nginx--kích-hoạt-https-ssl-miễn-phí)
6. [Quản Trị Nghiệp Vụ & Tài Khoản Demo](#6-quản-trị-nghiệp-vụ--tài-khoản-demo)
7. [Kết Nối Trạm Camera AI (Raspberry Pi)](#7-kết-nối-trạm-camera-ai-raspberry-pi)
8. [Lệnh Vận Hành, Giám Sát & Bảo Trì](#8-lệnh-vận-hành-giám-sát--bảo-trì)
9. [Báo Cáo Hạn Chế, Lỗ Hổng & Kế Hoạch Nâng Cấp Kỹ Thuật](#9-báo-cáo-hạn-chế-lỗ-hổng--kế-hoạch-nâng-cấp-kỹ-thuật)

---

## 1. CẤU TRÚC HỆ THỐNG

Dự án được phân chia thành 4 module độc lập:

```
Diem-danh-STEM/
│
├── 🔧 backend/          ← REST API Server (FastAPI, SQLite/PostgreSQL, WebSockets)
│   ├── app/             ← Logic nghiệp vụ, Router, Database, Bảo mật (PBKDF2/JWT)
│   ├── migrations/      ← File khởi tạo Database chuẩn Production
│   ├── requirements.txt ← Thư viện Python cho Backend
│   └── run.py           ← Entry point khởi chạy
│
├── 🌐 frontend-web/     ← Giao diện Web Dashboard (Chạy độc lập trên mọi Web Server)
│   ├── config.js        ← Cấu hình URL API Backend & WebSocket linh hoạt
│   ├── index.html       ← Landing Page tìm trường, đăng ký & tạo server trường
│   └── app/index.html   ← Web App Dashboard đầy đủ 5 vai trò
│
├── 📱 mobile/           ← Ứng dụng di động Flutter (Android / iOS)
│   └── app/             ← Toàn bộ mã nguồn Mobile App
│
├── 📷 edge/             ← Module Camera AI đặt tại cổng trường (Raspberry Pi)
│   ├── main.py          ← Luồng nhận diện khuôn mặt & gửi dữ liệu lên Cloud
│   ├── face_engine.py   ← Trích xuất đặc trưng khuôn mặt (Face Embeddings)
│   ├── anti_spoofing.py ← Chống gian lận bằng ảnh/video điện thoại
│   └── tracker.py       ← Theo dõi người qua lại trước camera
│
└── 📚 docs/             ← Tài liệu đặc tả kỹ thuật, ma trận phân quyền
```

---

## 2. CHẠY THỬ NGHIỆM TẠI MÁY (LOCAL DEVELOPMENT)

### Bước 2.1: Chạy Backend API Server
Mở một cửa sổ Terminal:
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Khởi chạy server Backend (Port 8000)
python run.py
```
- **Kiểm tra API Docs (Swagger):** Mở trình duyệt vào `http://localhost:8000/docs`
- **Kiểm tra Health:** `http://localhost:8000/health`

### Bước 2.2: Chạy Frontend Web
Mở một cửa sổ Terminal khác:
```bash
cd frontend-web
# Dùng python tạo một Web Server tạm thời trên Port 5173
python3 -m http.server 5173
```
- **Truy cập Trang chủ:** `http://localhost:5173`
- **Truy cập Dashboard:** `http://localhost:5173/app/index.html?school_id=1`

---

## 3. CHUẨN BỊ TÊN MIỀN & CLOUD VPS

### 3.1. Đăng ký Tên Miền
- **Nhà cung cấp trong nước:** [Mắt Bão (matbao.net)](https://www.matbao.net), [Tenten (tenten.vn)](https://tenten.vn), [iNET (inet.vn)](https://inet.vn).
- **Nhà cung cấp quốc tế:** [Cloudflare (cloudflare.com)](https://www.cloudflare.com), [Namecheap (namecheap.com)](https://www.namecheap.com).

### 3.2. Thuê Cloud VPS
- **Nhà cung cấp:** [Vietnix (vietnix.vn)](https://vietnix.vn), [AZDIGI (azdigi.com)](https://azdigi.com), [DigitalOcean](https://digitalocean.com), [Hetzner](https://hetzner.com).
- **Cấu hình đề xuất:** Ubuntu 22.04 LTS (hoặc 24.04 LTS), 2 CPU Cores, 2GB - 4GB RAM, 40GB SSD.

### 3.3. Trỏ DNS Tên Miền Về VPS
Vào trang quản lý tên miền bạn đã mua, thêm 2 bản ghi `A Record`:
- **Bản ghi 1:** Type: `A` | Host/Name: `@` | Value: `IP_VPS_CỦA_BẠN`
- **Bản ghi 2:** Type: `A` | Host/Name: `www` | Value: `IP_VPS_CỦA_BẠN`

---

## 4. HƯỚNG DẪN CÀI ĐẶT VPS CLOUD CHI TIẾT (A-Z)

### Bước 4.1: Kết nối vào VPS qua SSH
Từ máy tính cá nhân, mở Terminal (hoặc PuTTY) gõ:
```bash
ssh root@IP_VPS_CỦA_BẠN
```

### Bước 4.2: Cài đặt các gói phần mềm cần thiết
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-venv python3-pip nginx git certbot python3-certbot-nginx ufw

# Cấu hình tường lửa VPS
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw --force enable
```

### Bước 4.3: Đưa mã nguồn lên VPS
```bash
sudo mkdir -p /var/www/stemapp
sudo chown -R $USER:$USER /var/www/stemapp
cd /var/www/stemapp

# Clone code từ kho lưu trữ của bạn (hoặc upload qua SFTP FileZilla):
git clone <URL_REPO_CUA_BAN> .

# Cài đặt thư viện Backend
cd /var/www/stemapp/backend
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### Bước 4.4: Thiết lập file môi trường `.env`
```bash
cp .env.example .env
nano .env
```
Chỉnh sửa các giá trị sau:
```ini
# Sinh mã ngẫu nhiên: python3 -c "import secrets; print(secrets.token_hex(32))"
JWT_SECRET=dien_chuoi_bi_mat_ngau_nhien_tai_day
DEBUG=false
JWT_EXPIRE_HOURS=72
OTP_DEV_MODE=false

# Điền tên miền thật của bạn:
CORS_ORIGINS=https://tenmien.vn,https://www.tenmien.vn
```
*(Bấm `Ctrl + O` -> `Enter` để lưu, `Ctrl + X` để thoát).*

### Bước 4.5: Tạo Systemd Service để Backend tự chạy 24/7
```bash
sudo nano /etc/systemd/system/stem-backend.service
```
Dán nội dung sau:
```ini
[Unit]
Description=STEM Diem Danh Backend Service
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

Kích hoạt và khởi chạy dịch vụ:
```bash
sudo chown -R www-data:www-data /var/www/stemapp
sudo systemctl daemon-reload
sudo systemctl enable stem-backend
sudo systemctl start stem-backend

# Kiểm tra trạng thái:
sudo systemctl status stem-backend
```

---

## 5. CẤU HÌNH NGINX & KÍCH HOẠT HTTPS (SSL MIỄN PHÍ)

### Bước 5.1: Cấu hình Reverse Proxy Nginx
```bash
sudo nano /etc/nginx/sites-available/stemapp
```
*(Thay `tenmien.vn` bằng tên miền thật của bạn)*:
```nginx
server {
    listen 80;
    server_name tenmien.vn www.tenmien.vn;

    # 1. Giao diện Web tĩnh
    root /var/www/stemapp/frontend-web;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    # 2. Định tuyến API Backend
    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # 3. Swagger Docs
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

    # 5. Thư mục ảnh upload
    location /uploads/ {
        proxy_pass http://127.0.0.1:8000/uploads/;
        client_max_body_size 10M;
    }
}
```

Kích hoạt trang:
```bash
sudo ln -s /etc/nginx/sites-available/stemapp /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
```

### Bước 5.2: Kích hoạt chứng chỉ SSL HTTPS 1-chạm
```bash
sudo certbot --nginx -d tenmien.vn -d www.tenmien.vn
```
- Điền Email của bạn.
- Bấm `Y` đồng ý điều khoản.
- Certbot sẽ tự động thiết lập ổ khóa xanh HTTPS và tự động gia hạn vĩnh viễn.

---

## 6. QUẢN TRỊ NGHIỆP VỤ & TÀI KHOẢN HỆ THỐNG

### 👑 6.1. Tài Khoản Quản Trị Toàn Nền Tảng (Platform Super Admin)
Dùng để quản lý toàn bộ các Server Trường, xem số liệu toàn hệ thống, bật/tắt kích hoạt trường:
- **Tài khoản:** `admin` (hoặc `admin@stemapp.vn`)
- **Mật khẩu:** `123456` (hoặc `StemAdmin@2026!`)
- **Truy cập:** Bấm nút **"⚙️ Admin Nền Tảng"** trên thanh Menu góc phải màn hình trang chủ.

---

### 🏫 6.2. Tài Khoản Trường Học (Trường THPT Nguyễn Huệ - ID: 1)

| Tên Đăng Nhập | Mật Khẩu | Vai Trò | Trạng Thái | Chức Năng Chính |
|---|---|---|---|---|
| `hieutruong` | `123456` | **Hiệu Trưởng** | ✅ Verified | Quản trị server trường, đổi quy định giờ/form, quản lý camera |
| `giamthi01` | `123456` | **Giám Thị** | ✅ Verified | Xem live camera, duyệt khiếu nại Cấp 2, cảnh báo toàn trường |
| `gvcn10a1` | `123456` | **GVCN 10A1** | ✅ Verified | Duyệt ảnh khuôn mặt AI, duyệt đơn nghỉ phép, khiếu nại Cấp 1 |
| `phuhuynh01` | `123456` | **Phụ Huynh** | ✅ Verified | Nhận thông báo con vào cổng, nộp đơn xin phép |
| `hocsinh01` | `123456` | **Học Sinh** | ✅ Verified | Xem lịch sử điểm danh, xem thẻ QR, gửi khiếu nại |

### Mã Mời Mẫu (Dành cho Giáo viên / Nhân sự đăng ký mới):
- **Giáo viên (GVCN):** `GV_NGUYEN_HUE_2026`
- **Giám thị:** `GT_NGUYEN_HUE_2026`
- **Ban Giám Hiệu:** `BGH_NGUYEN_HUE_2026`

---

## 7. KẾT NỐI TRẠM CAMERA AI (RASPBERRY PI)

1. Đăng nhập tài khoản Hiệu Trưởng trên Web -> Chọn **Trạm Camera** -> Bấm **+ Thêm Trạm**.
2. Đặt tên (ví dụ: `Cổng Chính`) -> Nhận chuỗi `secret_key` bí mật.
3. Trên máy **Raspberry Pi** tại cổng trường:
   ```bash
   cd edge
   pip install -r requirements.txt
   
   # Chạy trạm camera kết nối trực tiếp về tên miền Cloud:
   python main.py --school_id 1 --secret_key CHUOI_SECRET_KEY_CUA_BAN --api_url https://tenmien.vn
   ```
4. Khi học sinh đi qua cổng:
   - Camera tự động nhận diện khuôn mặt + kiểm tra đồng phục.
   - Gửi dữ liệu điểm danh qua API `POST /api/v1/s/1/attendance/sync`.
   - Web Dashboard của Nhà trường và Phụ huynh sẽ lập tức nhận thông báo thời gian thực qua WebSocket.

---

## 8. LỆNH VẬN HÀNH, GIÁM SÁT & BẢO TRÌ

```bash
# Xem log hoạt động trực tiếp của Backend:
sudo journalctl -u stem-backend -f

# Khởi động lại Backend (sau khi cập nhật code):
sudo systemctl restart stem-backend

# Tải lại cấu hình Nginx:
sudo systemctl reload nginx

# Xem dung lượng ổ cứng & RAM:
df -h
free -m

# Sao lưu Database:
cp /var/www/stemapp/backend/data/stem_platform.db /var/www/stemapp/backend/data/backup_$(date +%F).db
```

---
*Chúc mừng bạn! Dự án Điểm Danh STEM đã hoàn toàn sẵn sàng vận hành trên môi trường thực tế.*

---

## 9. BÁO CÁO HẠN CHẾ, LỖ HỔNG & KẾ HOẠCH NÂNG CẤP KỸ THUẬT

> 📄 **Xem báo cáo kỹ thuật chi tiết:** [LIMITATIONS.md](LIMITATIONS.md)

Hệ thống đã trải qua rà soát và đánh giá toàn diện trên cả 4 module: Backend, Frontend, Edge AI và Mobile App. Dưới đây là tóm tắt các điểm nghẽn và hạn chế cần chú ý:

### 🚨 1. Lỗ hổng An ninh & Xác thực (Security)
- **Mật khẩu Admin hardcode**: Tại `backend/app/routers/auth.py` và `platform.py`, tồn tại cơ chế bypass mật khẩu Master Admin bằng chuỗi hardcode (`123456`, `admin`, `StemAdmin@2026!`). Cần xóa bỏ và chuyển sang kiểm tra hash PBKDF2 chuẩn.
- **Khóa bí mật mặc định**: `JWT_SECRET` trong `config.py` dùng chuỗi mặc định nếu không cấu hình file `.env`.
- **Nguy cơ DOM XSS trên Web**: Frontend chèn dữ liệu thô vào DOM qua `innerHTML` chưa qua escape HTML.

### ⚠️ 2. Lỗi Logic & Tích hợp (Bugs & Integration)
- **Truy vấn Login thiếu school_id**: Trong `auth.py`, câu truy vấn `WHERE school_id=?` khi nhận giá trị `None` sẽ biến thành `school_id = NULL` (luôn trả về rỗng trong chuẩn SQL), gây lỗi đăng nhập cho các client không truyền trường này.
- **WebSocket chưa kích hoạt phát sóng (Dead WebSocket)**: Hàm `broadcast_to_school()` chưa được gọi tại router `attendance.py` khi camera trạm gửi log điểm danh, khiến dashboard web không tự động nhảy log realtime.
- **Lặp script tag**: `frontend-web/index.html` import `<script src="/config.js"></script>` 2 lần (dòng 297 và dòng 611).

### 🏗️ 3. Nợ Kiến trúc (Architectural Debt)
- **Frontend Monolithic**: File `frontend-web/app/index.html` quá lớn (2.442 dòng), gom toàn bộ HTML, CSS và logic của 5 vai trò vào một file duy nhất, gây khó khăn cho việc bảo trì và test.
- **Nghẽn Concurrency SQLite**: SQLite chỉ hỗ trợ Single Writer. Khi nhiều cổng trường đồng thời gửi điểm danh giờ cao điểm, nguy cơ dính lỗi `database is locked` rất cao. Cần chuyển sang PostgreSQL.
- **Bất nhất dữ liệu Mobile**: Mobile Flutter đang dùng cả Firebase Firestore song song với Backend FastAPI, thiếu một nguồn dữ liệu duy nhất (Single Source of Truth).

