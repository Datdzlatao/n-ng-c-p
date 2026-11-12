# ĐẶC TẢ GIAO DIỆN TRANG DASHBOARD QUẢN TRỊ (ADMIN DASHBOARD)
## DỰ ÁN: ĐIỂM DANH STEM (EDUSAMS) — DÀNH CHO HIỆU TRƯỞNG & GIÁO VIÊN
*Trang mục tiêu: `/app/index.html`*  
*Chuẩn thiết kế: UI/UX Pro Max Bento Grid & Glassmorphism*

---

## 1. TỔNG QUAN KIẾN TRÚC TRANG DASHBOARD
Giao diện quản trị trung tâm được thiết kế đặc thù cho **Hiệu Trưởng (Headmaster)** và **Giáo Viên Chủ Nhiệm (Teacher)** để giám sát toàn bộ hoạt động vào cổng, tình trạng nề nếp và nhận diện AI khuôn mặt theo thời gian thực.

### Các Phân Khu Chính (Bento Architecture):
```
┌───────────────────────────────────────────────────────────────────────────────────────┐
│ 1. EXECUTIVE WELCOME BANNER (Avatar, Chào mừng, Trạng thái AI Hub, Live Clock)        │
├───────────────────┬───────────────────┬───────────────────┬───────────────────────────┤
│ KPI 1: TỔNG SĨ SỐ │ KPI 2: TỶ LỆ %    │ KPI 3: ĐI TRỄ     │ KPI 4: CẢNH BÁO ĐỒNG PHỤC │
│ 1,248 HS (+0.8%)  │ 96.4% (+1.2%)     │ 12 HS (-3 HS)     │ 4 ca (-2 ca)              │
├───────────────────┴───────────────────┴───────────────────┼───────────────────────────┤
│ 2. NHẬT KÝ CAMERA AI CỔNG TRƯỜNG (REAL-TIME LIVE FEED)    │ 3. TIẾN ĐỘ THEO LỚP       │
│    - Trạng thái: Trạm #1 Cổng Chính 🟢 ONLINE (Pulsing)    │    - 12A1: 100%           │
│    - Telemetry: 30 FPS • 24ms • Camera RTSP / USB         │    - 12A2: 97.5%          │
│    - Filter: [Tất cả] [Đúng giờ] [Đi trễ] [Lỗi đồng phục] │    - 11B1: 94.7%          │
│    - Danh sách thẻ học sinh vừa qua cổng thời gian thực   ├───────────────────────────┤
│ ───────────────────────────────────────────────────────── │ 4. LỐI TẮT NGHIỆP VỤ      │
│    - Biểu đồ phân bổ lưu lượng theo khung giờ sáng        │    (DS HS, Đơn nghỉ phép, │
│      (06:30 - 07:45) với cột giờ cao điểm 06:45 - 07:15   │     Khiếu nại, Cấu hình)  │
└───────────────────────────────────────────────────────────┴───────────────────────────┘
```

---

## 2. CHI TIẾT CÁC THÀNH PHẦN (COMPONENT SPECIFICATIONS)

### 2.1. Thống Kê Nhanh (4 KPI Summary Cards)
- **Thẻ 1: Tổng Sĩ Số Học Sinh**
  - Icon: SVG Lucide `users` trên đĩa icon xanh Cyan-Blue (`rgba(56, 189, 248, 0.15)`).
  - Viền Gradient Kính: `linear-gradient(135deg, rgba(37, 99, 235, 0.12), rgba(6, 182, 212, 0.03))` với viền mảnh `rgba(56, 189, 248, 0.22)`.
  - Chỉ số: `1,248` (tải động từ `stats.total_students`).
  - So sánh hôm qua: Badge xanh `↑ +0.8% (+10 HS)`.
- **Thẻ 2: Tỷ Lệ Đúng Giờ Hôm Nay %**
  - Icon: SVG Lucide `check-circle-2` trên đĩa icon Emerald (`rgba(52, 211, 153, 0.15)`).
  - Viền Gradient Kính: `linear-gradient(135deg, rgba(16, 185, 129, 0.12), rgba(5, 150, 105, 0.03))`.
  - Chỉ số: `96.4%` (tính toán động từ số đúng giờ và tổng có mặt).
  - So sánh hôm qua: Badge xanh `↑ +1.2%`.
  - Mini Progress Bar: Thanh tiến độ bo góc mềm 96.4% màu xanh lá ngọc.
- **Thẻ 3: Số Học Sinh Đi Trễ**
  - Icon: SVG Lucide `clock` trên đĩa icon Amber (`rgba(251, 191, 36, 0.15)`).
  - Viền Gradient Kính: `linear-gradient(135deg, rgba(245, 158, 11, 0.12), rgba(217, 119, 6, 0.03))`.
  - Chỉ số: `12` HS (màu hổ phách `#fbbf24`).
  - So sánh hôm qua: Badge xanh `↓ -3 HS (-20%)` (giảm trễ so với hôm qua là tích cực).
- **Thẻ 4: Số Cảnh Báo Đồng Phục**
  - Icon: SVG Lucide `shirt` / `shield-alert` trên đĩa icon Purple (`rgba(192, 132, 252, 0.15)`).
  - Viền Gradient Kính: `linear-gradient(135deg, rgba(168, 85, 247, 0.12), rgba(124, 58, 237, 0.03))`.
  - Chỉ số: `4` ca (màu tím `#c084fc`).
  - So sánh hôm qua: Badge xanh `↓ -2 ca (-33%)` (số ca vi phạm giảm).

### 2.2. Nhật Ký Camera AI Cổng Trường (Live AI Attendance Feed)
- **Status Camera Header:**
  - Tiêu đề: "Nhật Ký Camera AI Cổng Trường (Real-Time)"
  - Đèn tín hiệu **Pulsing Green Light**: Chớp nháy tuần hoàn 1.8s (`@keyframes camPulse`) tạo cảm giác luồng AI đang giám sát trực tiếp.
  - Badge Online: `Trạm #1: ONLINE` kèm telemetry `30 FPS • 24ms • Cổng Chính`.
  - Nút tương tác: "Xem Live Stream" kích hoạt modal stream camera độ phân giải cao trực tiếp từ trạm AI edge.
- **Thẻ Học Sinh Trong Luồng (Live Student Feed Cards):**
  - Cấu trúc: Thumbnail chân dung (`44px × 44px`, `rounded-xl`, viền phản chiếu ánh sáng), Họ tên font `Plus Jakarta Sans` Bold, Mã số học sinh Monospace `HS-2026-xxx`, Lớp, và Tỷ lệ khớp AI (`99.4% Match`).
  - Thời gian chính xác: Monospace `hh:mm:ss` (`07:14:28`).
  - Huy hiệu trạng thái:
    - Đúng giờ: Green Emerald badge (`bg-emerald-500/15 text-emerald-400`).
    - Đi trễ: Amber badge (`bg-amber-500/15 text-amber-400`).
    - Lỗi đồng phục: Purple badge (`bg-purple-500/15 text-purple-400`).
- **WebSocket Ingestion:**
  - Tự động gắn kết với luồng WebSocket `ws://${location.host}/ws/${schoolId}/live`.
  - Khi học sinh quét mặt tại cổng, thẻ mới tự động trượt vào đầu danh sách với hiệu ứng `feedSlideDown` mượt mà (350ms).

### 2.3. Biểu Đồ Lưu Lượng Điểm Danh Theo Khung Giờ (Hourly Attendance Chart)
- Cột trực quan hóa số lượng học sinh đổ về cổng trường theo các mốc 15 phút:
  - 06:30: 145 HS
  - 06:45: 480 HS (Đỉnh cao điểm đúng giờ)
  - 07:00: 395 HS
  - 07:15: 180 HS (Cận giờ vào lớp)
  - 07:30: 28 HS (Đi trễ)
  - 07:45: 8 HS (Trễ tiết)
- Cột đi trễ sau 07:15 tự động đổi sang dải màu gradient Hổ phách/Cam để cảnh báo trực quan.

---

## 3. TƯƠNG THÍCH MÀN HÌNH (RESPONSIVE RULES)

- **Desktop (≥ 1200px):**
  - KPI Cards chia 4 cột ngang cân đối.
  - Lưới chính chia 2 cột lớn (Tỉ lệ 1.8fr : 1.1fr) đảm bảo danh sách camera và biểu đồ chiếm trung tâm thị giác.
- **Tablet (768px - 1199px):**
  - KPI Cards chuyển sang lưới 2x2.
  - Lưới chính chuyển sang 1 cột full-width (`grid-template-columns: 1fr`).
- **Mobile (< 768px):**
  - Tự động ẩn Sidebar, mở rộng Content chiếm 100% bề ngang.
  - Padding tối ưu `14px` chống chật chội.
  - Toàn bộ các thẻ KPI xếp chồng 1 cột.
  - **Triệt tiêu cuộn ngang (No horizontal scroll):** Thiết lập `overflow-x: hidden !important; width: 100% !important; box-sizing: border-box !important;`.
  - Tuân thủ kích thước chạm tối thiểu `44px` cho toàn bộ các nút bấm và tab lọc.

---
*Tài liệu đặc tả trang được tạo tự động và đồng bộ với `/app/index.html`.*
