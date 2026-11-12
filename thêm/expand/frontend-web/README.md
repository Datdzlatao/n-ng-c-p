# 🌐 Frontend Web — Điểm Danh STEM Dashboard

Web Dashboard SPA (Vanilla JS) dành cho GVCN, Giám Thị, Hiệu Trưởng.

## Tech Stack
- **Vanilla JS** (không cần build step)
- Giao tiếp với Backend qua **REST API** và **WebSocket**
- Responsive cho Desktop + Tablet

## Cách Chạy

```bash
# Option 1: Dùng Python simple server (development)
cd frontend-web
python3 -m http.server 5173
# → http://localhost:5173

# Option 2: VS Code Live Server extension (click chuột phải → Open with Live Server)

# Option 3: Production — Nginx serve static
# server { root /var/www/stemapp/frontend-web; ... }
```

## Cấu Hình Backend URL

Mở file `app/index.html` hoặc `index.html`, tìm và đổi:
```js
const API_BASE = 'http://localhost:8000';   // development
// const API_BASE = 'https://api.stemapp.vn';  // production
```

## Structure
```
frontend-web/
├── index.html          ← Landing page: Tìm trường, Đăng nhập, Tạo server
└── app/
    └── index.html      ← Dashboard SPA: 5 vai trò đầy đủ tính năng
```

## Chức Năng Theo Vai Trò
| Role | Tính Năng |
|---|---|
| HEADMASTER | Tất cả + Cấu hình trường + Camera |
| INSPECTOR | Điểm danh, Khiếu nại cấp 2, Camera |
| TEACHER | DS học sinh, Điểm danh, Duyệt khiếu nại, Đơn nghỉ |
| PARENT | Xem trạng thái con, Gửi đơn |
| STUDENT | Xem cá nhân, QR card |
