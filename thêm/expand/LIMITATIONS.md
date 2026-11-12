# ⚠️ BÁO CÁO TỔNG HỢP CÁC HẠN CHẾ, LỖ HỔNG & LỘ TRÌNH KHẮC PHỤC
## DỰ ÁN NỀN TẢNG ĐIỂM DANH STEM (MULTI-TENANT SMART ATTENDANCE)

> **Ngày lập báo cáo:** 06/09/2026  
> **Phạm vi đánh giá:** Toàn bộ mã nguồn hệ thống gồm:
> - 🔧 **Backend API** (`backend/app/`, FastAPI, SQLite, Core Security, Routers)
> - 🌐 **Frontend Web & Portal** (`frontend-web/index.html`, `frontend-web/app/index.html`, `config.js`, `biometric-scanner.js`)
> - 📷 **Edge Camera AI** (`edge/main.py`, `face_engine.py`, `tracker.py`, `server_bridge.py`)
> - 📱 **Mobile App** (`mobile/app/`, Flutter Clean Architecture)
> - 🚀 **DevOps & Triển khai** (`docker-compose.yml`, `nginx/nginx.conf`, `deploy.sh`)

---

## 📑 MỤC LỤC
1. [Tổng Hợp Mức Độ Nghiêm Trọng (Severity Matrix)](#1-tổng-hợp-mức-độ-nghiêm-trọng-severity-matrix)
2. [Hạn Chế & Lỗ Hổng Chi Tiết Tại Backend](#2-hạn-chế--lỗ-hổng-chi-tiết-tại-backend)
3. [Hạn Chế & Rủi Ro Tại Frontend Web & index.html](#3-hạn-chế--rủi-ro-tại-frontend-web--indexhtml)
4. [Hạn Chế Tại Trạm Camera Edge AI](#4-hạn-chế-tại-trạm-camera-edge-ai)
5. [Hạn Chế Tại Ứng Dụng Mobile Flutter](#5-hạn-chế-tại-ứng-dụng-mobile-flutter)
6. [Hạn Chế Về Cơ Sở Dữ Liệu & Hạ Tầng Triển Khai](#6-hạn-chế-về-cơ-sở-dữ-liệu--hạ-tầng-triển-khai)
7. [Bảng Kế Hoạch & Lộ Trình Khắc Phục (Action Items)](#7-bảng-kế-hoạch--lộ-trình-khắc-phục-action-items)

---

## 1. TỔNG HỢP MỨC ĐỘ NGHIÊM TRỌNG & TIẾN ĐỘ KHẮC PHỤC

| Mã lỗi | Phân loại | Mức độ | Trạng thái | Vị trí tập tin | Tác động / Kết quả xử lý |
| :--- | :--- | :---: | :---: | :--- | :--- |
| **SEC-01** | An ninh / Backdoor | 🔴 **CRITICAL** | ✅ **ĐÃ KHẮC PHỤC** | `backend/app/routers/auth.py`<br>`backend/app/routers/platform.py` | Đã xóa toàn bộ mảng mật khẩu thô; xác thực PBKDF2 chuẩn với `platform_admins`. |
| **SEC-02** | An ninh / Token | 🟠 **HIGH** | ✅ **ĐÃ KHẮC PHỤC** | `backend/app/config.py` | Đã có cơ chế chặn khởi động Production và cảnh báo Dev nếu `JWT_SECRET` chưa đổi. |
| **SEC-03** | Lỗ hổng XSS | 🟡 **MEDIUM** | ✅ **ĐÃ KHẮC PHỤC** | `frontend-web/index.html`<br>`frontend-web/app/index.html` | Đã tích hợp hàm `escHtml()` và sanitize toàn bộ dữ liệu bảng trước khi render vào DOM. |
| **BUG-01** | Lỗi logic Login | 🟠 **HIGH** | ✅ **ĐÃ KHẮC PHỤC** | `backend/app/routers/auth.py` | Tự động nhận diện `school_id` thông minh theo username/SĐT nếu client không truyền. |
| **BUG-02** | Lỗi luồng WebSocket | 🟠 **HIGH** | ✅ **ĐÃ KHẮC PHỤC** | `backend/app/routers/attendance.py` | Đã tích hợp `broadcast_to_school()` vào `edge_sync`, Dashboard nhảy dữ liệu tức thì. |
| **BUG-03** | Lặp thẻ Script | 🟢 **LOW** | ✅ **ĐÃ KHẮC PHỤC** | `frontend-web/index.html` | Đã xóa thẻ `<script src="/config.js">` trùng lặp. |
| **ARCH-01** | Nợ kiến trúc Frontend | 🟡 **MEDIUM** | 🔄 **ĐANG TỐI ƯU** | `frontend-web/app/index.html` | Đã khóa Role Switcher trên tài khoản thường, phân quyền chặt chẽ; lộ trình tách module tiếp tục. |
| **ARCH-02** | Nghẽn Concurrency DB | 🟠 **HIGH** | ✅ **SẴN SÀNG PROD** | `docker-compose.yml`<br>`backend/app/config.py` | Đã bổ sung service `PostgreSQL 15` và `Redis 7` trong Docker Compose, sẵn sàng scale đa trường. |
| **ARCH-03** | Bất nhất Nguồn Dữ Liệu | 🟡 **MEDIUM** | 🔄 **ĐANG CHUẨN HÓA** | `mobile/app/` vs `backend/` | Quy hoạch Mobile App gọi REST API Backend FastAPI; Firebase chỉ dùng cho FCM Push Notification. |

---

## 2. HẠN CHẾ & LỖ HỔNG CHI TIẾT TẠI BACKEND

### 2.1. 🔴 Lỗ hổng bảo mật: Hardcoded Master Admin Credentials
- **Vị trí:** 
  - `backend/app/routers/auth.py` (dòng 247)
  - `backend/app/routers/platform.py` (dòng 46)
- **Chi tiết mã nguồn:**
  ```python
  # auth.py
  if req.username_or_phone.strip().lower() in ("admin", "admin@stemapp.vn"):
      if req.password in (PLATFORM_ADMIN_PASSWORD, "123456", "admin", "StemAdmin@2026!", "Admin@2026!"):
          admin_user = { "id": 999999, "role": "ADMIN", ... }
          return { "access_token": _make_token(admin_user), ... }
  ```
- **Hậu quả:** Bất kỳ ai biết tài khoản `admin` và nhập các mật khẩu như `123456` hoặc `admin` đều đăng nhập thành công với quyền Quản trị viên tối cao, bỏ qua kiểm tra băm mật khẩu trong cơ sở dữ liệu.
- **Biện pháp khắc phục:** 
  - Xóa bỏ hoàn toàn mảng mật khẩu hardcoded.
  - Luôn kiểm tra mật khẩu qua `verify_password(req.password, admin["salt"], admin["password_hash"])` đối chiếu với bảng `platform_admins`.

---

### 2.2. 🟠 Lỗi logic truy vấn: Đăng nhập thất bại khi thiếu `school_id`
- **Vị trí:** `backend/app/routers/auth.py` (dòng 275–282)
- **Chi tiết mã nguồn:**
  ```python
  row = conn.execute("""
      SELECT * FROM users
      WHERE school_id=? AND status='ACTIVE'
        AND (username=? OR phone=? OR email=?)
  """, (req.school_id, req.username_or_phone, req.username_or_phone, req.username_or_phone)).fetchone()
  ```
- **Hậu quả:** Mô hình Pydantic định nghĩa `school_id: Optional[int] = None`. Nếu người dùng đăng nhập từ ứng dụng ngoài hoặc không chọn trường (`req.school_id = None`), câu lệnh SQL trở thành `WHERE school_id=NULL`, luôn trả về rỗng vì chuẩn SQL yêu cầu `IS NULL`. Người dùng sẽ nhận thông báo sai tài khoản dù thông tin hoàn toàn đúng.
- **Biện pháp khắc phục:** Nếu `req.school_id` là `None`, cần truy vấn tìm user theo `username/phone/email` trước, sau đó xác định `school_id` của user đó.

---

### 2.3. 🟠 Lỗi tính năng: WebSocket bị "chết" (Dead WebSocket)
- **Vị trí:** 
  - `backend/app/routers/websocket.py` (dòng 42: `broadcast_to_school`)
  - `backend/app/routers/attendance.py` (dòng 105–188: `edge_sync`)
- **Hậu quả:** Hàm `broadcast_to_school(school_id, payload)` được tạo ra nhưng **không hề được gọi** tại bất kỳ router nào. Khi trạm camera nhận diện thành công học sinh và gửi lên `/api/v1/s/{school_id}/attendance/sync`, bản ghi được lưu vào SQLite nhưng không phát tín hiệu qua WebSocket. Giao diện Web Dashboard không nhận được thông báo nhảy thời gian thực.
- **Biện pháp khắc phục:** Gọi `await broadcast_to_school(school_id, {"type": "ATTENDANCE", ...})` ngay sau khi `conn.commit()` trong `edge_sync`.

---

### 2.4. 🟡 Cấu trúc thư mục Models còn trống
- **Vị trí:** `backend/app/models/`
- **Chi tiết:** Thư mục chỉ chứa file rỗng `__init__.py`. Toàn bộ định nghĩa schema SQL bị gộp chung vào `database.py`, còn Pydantic schemas bị viết rải rác trong từng file router. Khi dự án mở rộng, việc thiếu tầng Model/DTO tập trung gây khó khăn cho việc tái sử dụng và kiểm thử tự động.

---

## 3. HẠN CHẾ & RỦI RO TẠI FRONTEND WEB & INDEX.HTML

### 3.1. 🟡 Kiến trúc Monolithic Single-File quá lớn
- **Vị trí:** 
  - `frontend-web/app/index.html` (2.442 dòng, ~130 KB)
  - `frontend-web/index.html` (1.136 dòng, ~53 KB)
- **Hậu quả:** 
  - Toàn bộ HTML layout, CSS stylesheet, và hàng ngàn dòng JavaScript xử lý logic của 5 vai trò (Hiệu trưởng, Giám thị, Giáo viên, Phụ huynh, Học sinh) bị gom chung vào một file duy nhất.
  - Khó phân quyền làm việc nhóm qua Git (dễ xung đột code - merge conflicts).
  - Không thể thực hiện Unit Test / E2E Test cho từng thành phần giao diện.

---

### 3.2. 🟡 Bộ chọn vai trò giả lập (Role Switcher) trên Production
- **Vị trí:** `frontend-web/app/index.html` (dòng 213: `<select id="roleSelect">`)
- **Chi tiết mã nguồn:**
  ```javascript
  function onRoleChange(role) {
    if (currentUser) currentUser.role = role;
    renderSidebar();
    renderLaunchpad();
    navigate(...);
  }
  ```
- **Hậu quả:** Cho phép người dùng bình thường tự do chuyển đổi giao diện sang vai trò Hiệu Trưởng hoặc Giám Thị trên thanh điều hướng. Mặc dù Backend có chặn quyền (trả về lỗi `403 Forbidden` khi gọi API), việc giao diện cho phép chuyển đổi tùy tiện gây trải nghiệm người dùng xấu (màn hình hiển thị quyền quản trị nhưng thao tác nút nào cũng báo lỗi 403).

---

### 3.3. 🟡 Rủi ro DOM-based XSS do nối chuỗi HTML
- **Vị trí:** Nhiều vị trí trong `index.html` và `app/index.html`
- **Ví dụ:**
  ```javascript
  tbody.innerHTML = list.map(s => `<tr><td><b>${s.name}</b><br><small>${s.address}</small></td>...</tr>`).join('');
  ```
- **Hậu quả:** Dữ liệu trả về từ API được đưa thẳng vào DOM qua `innerHTML`. Nếu một trường học hoặc học sinh đăng ký với tên chứa mã script độc hại (ví dụ: `<img src=x onerror=alert(1)>`), đoạn mã sẽ tự động thực thi trên trình duyệt của Quản trị viên.

---

### 3.4. 🟢 Lặp thẻ nhúng Script
- **Vị trí:** `frontend-web/index.html`
- **Chi tiết:** Thẻ `<script src="/config.js"></script>` được gọi 2 lần:
  - Dòng 297: Bên trong thẻ `<head>`
  - Dòng 611: Trước khi đóng thẻ `<body>`

---

## 4. HẠN CHẾ TẠI TRẠM CAMERA EDGE AI (`edge/`)

### 4.1. Mã nguồn `edge/main.py` quá cồng kềnh (1.238 dòng)
- File `main.py` ôm đồm quá nhiều trách nhiệm:
  1. Quản lý camera stream (ThreadedCamera)
  2. Xử lý nhận diện khuôn mặt đa luồng (AsyncFaceWorker)
  3. Theo dõi nhiều người (MultiObjectTracker)
  4. Phân tích đồng phục và chống giả mạo (UniformChecker, AntiSpoofing)
  5. Phát trực tiếp luồng MJPEG qua HTTP Server nội bộ
  6. Ghi log ngoại tuyến vào SQLite
  7. Đồng bộ lên Google Sheets qua `gspread`
  8. Gửi tín hiệu Heartbeat và điểm danh lên Backend FastAPI qua `server_bridge.py`
- **Rủi ro:** Khi có nhiều luồng cùng tranh chấp tài nguyên trên Raspberry Pi (CPU yếu, RAM hạn chế), rất dễ xảy ra hiện tượng tràn bộ đệm khung hình (frame drop) hoặc deadlock khi camera USB bị lỏng giắc cắm.

### 4.2. Phân mảnh kênh đồng bộ dữ liệu
- Hệ thống duy trì song song 2 kênh đồng bộ: **Google Sheets** và **Backend REST API**. Việc duy trì kết nối OAuth2 với Google Sheets trong môi trường mạng chập chờn thường làm chậm vòng lặp chính của camera nếu không được tách riêng thành background process độc lập.

---

## 5. HẠN CHẾ TẠI ỨNG DỤNG MOBILE FLUTTER (`mobile/app/`)

### 5.1. Bất nhất về nguồn dữ liệu chính (Source of Truth Conflict)
- Trong `mobile/app/lib/main.dart`, ứng dụng khởi tạo `Firebase.initializeApp()` và có file cấu hình `firestore.rules`.
- Trong khi đó, toàn bộ dữ liệu trường học, điểm danh, nề nếp của hệ sinh thái lại đang được quản lý tập trung trên **Backend FastAPI**.
- **Hạn chế:** Việc thiếu một cơ chế đồng bộ nhất quán 2 chiều giữa Firebase Firestore và Backend FastAPI có thể dẫn đến việc lệch dữ liệu giữa phiên bản Mobile và phiên bản Web.

---

## 6. HẠN CHẾ VỀ CƠ SỞ DỮ LIỆU & HẠ TẦNG TRIỂN KHAI

### 6.1. Giới hạn Concurrency của SQLite
- Hiện tại hệ thống đang sử dụng file SQLite (`stem_platform.db`).
- Mặc dù đã kích hoạt chế độ `PRAGMA journal_mode=WAL`, SQLite theo thiết kế chỉ cho phép **1 kết nối ghi (Single Writer)** tại một thời điểm.
- **Kịch bản rủi ro:** Vào khung giờ cao điểm (06:45 – 07:15 sáng), hàng chục trạm camera từ nhiều cổng trường cùng đẩy dữ liệu điểm danh (`/attendance/sync`) kết hợp với hàng trăm giáo viên, phụ huynh cùng truy cập đăng ký/tra cứu, SQLite sẽ lập tức gặp lỗi:
  ```
  sqlite3.OperationalError: database is locked
  ```

### 6.2. File `docker-compose.yml` chưa có dịch vụ cơ sở dữ liệu độc lập
- Trong `docker-compose.yml`, backend chỉ mount thư mục volume SQLite cục bộ. Chưa có cấu hình container dịch vụ cho **PostgreSQL** và **Redis**, khiến hệ thống chưa phát huy được tính năng Rate Limiting phân tán và xử lý đồng thời lớn.

---

## 7. BẢNG KẾ HOẠCH & LỘ TRÌNH KHẮC PHỤC (ACTION ITEMS)

### Giai đoạn 1: Khắc phục khẩn cấp (Hotfixes — 1 đến 2 ngày)
1. **[SEC-01]** Xóa bỏ tài khoản Master Admin hardcode trong `auth.py` và `platform.py`. Tạo tài khoản admin thông qua migration hoặc dòng lệnh CLI mã hóa an toàn.
2. **[SEC-02]** Cập nhật `backend/.env.example` và cảnh báo bắt buộc đổi `JWT_SECRET` ngẫu nhiên 64 ký tự trước khi chạy.
3. **[BUG-01]** Sửa câu lệnh SQL login trong `auth.py` để xử lý đúng trường hợp `school_id is None`.
4. **[BUG-02]** Tích hợp lệnh `await broadcast_to_school()` vào hàm `edge_sync` để đưa luồng Live WebSocket vào hoạt động.
5. **[BUG-03]** Xóa thẻ script trùng lặp tại dòng 611 của `frontend-web/index.html`.

### Giai đoạn 2: Ổn định & Tối ưu hóa (Stabilization — 1 đến 2 tuần)
1. **[ARCH-02] Chuyển đổi sang PostgreSQL**:
   - Kích hoạt cấu hình `DATABASE_URL=postgresql+asyncpg://...` đã chuẩn bị sẵn trong `app/config.py`.
   - Bổ sung service `postgres:15-alpine` vào `docker-compose.yml` để giải quyết triệt để vấn đề nghẽn ghi của SQLite.
2. **[SEC-03] Chống XSS**:
   - Viết hàm helper `escapeHTML(str)` trên frontend để làm sạch toàn bộ dữ liệu trước khi render vào DOM.
3. **[UI/UX] Khóa Role Selector**:
   - Ẩn hoàn toàn `<select id="roleSelect">` trên môi trường thật, cố định vai trò hiển thị theo đúng token JWT trả về từ server.

### Giai đoạn 3: Tái cấu trúc dài hạn (Refactoring — 3 đến 4 tuần)
1. **[ARCH-01] Module hóa Frontend**:
   - Tách `frontend-web/app/index.html` thành các file nhỏ: `app.css`, `api.js`, `auth.js`, và các views tương ứng (`views/teacher.js`, `views/headmaster.js`, ...).
2. **[ARCH-03] Chuẩn hóa Mobile App API**:
   - Cấu hình Mobile App gọi trực tiếp Backend FastAPI REST API, chỉ sử dụng Firebase cho tính năng FCM Push Notification.
3. **Tách module Edge AI**:
   - Tách `edge/main.py` thành các service riêng biệt: Camera Ingestion Service, Inference Service, và Cloud Sync Service.
