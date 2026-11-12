# 📡 HƯỚNG DẪN TỐI ƯU HÓA MẠNG & CAMERA RTSP ĐA TRẠM (STEM ATTENDANCE)

Tài liệu này hướng dẫn chi tiết cách cấu hình phần cứng camera IP, tối ưu tốc độ khung hình (FPS) từ 12 lên 25–30 FPS, và các phương án mạng chuẩn để không bao giờ bị mất kết nối camera RTSP khi đổi mạng hoặc mang máy đi thi STEM.

---

## I. TẠI SAO CAMERA IP MẶC ĐỊNH CHỈ ĐẠT ~10-12 FPS VÀ CÁCH NÂNG LÊN 25-30 FPS

### 1. Nguyên nhân
Hầu hết các dòng camera an ninh IP (Hikvision, Dahua, Ezviz, Imou) khi xuất xưởng được cài đặt mặc định ở **10 – 15 FPS** (đôi khi là 12 FPS) nhằm tiết kiệm dung lượng thẻ nhớ và băng thông đường truyền gia đình. Vì vậy, dù phần mềm AI máy tính có mạnh đến đâu, nguồn phát từ camera bị giới hạn thì hệ thống chỉ nhận được tối đa 12 FPS.

### 2. Cách chỉnh Camera lên 25 - 30 FPS mượt mà
1. **Mở trình duyệt web**, truy cập địa chỉ IP của camera:
   ```
   http://192.168.1.2   (hoặc IP camera hiện tại của bạn)
   ```
2. **Đăng nhập** tài khoản quản trị (Username: `admin`, Password của camera).
3. Vào mục **Configuration (Cấu hình)** → **Video/Audio (Hình ảnh/Âm thanh)**:
   - **Stream Type**: Chọn `Main Stream (Normal)`.
   - **Video Type**: `Video Stream`.
   - **Resolution (Độ phân giải)**: Khuyên dùng `1280*720P` (HD) hoặc `1920*1080P` (Full HD).
   - **Bitrate Type**: `Constant` (Cố định).
   - **Video Quality**: `Higher` hoặc `Medium`.
   - **Frame Rate (Tốc độ khung hình)**: **NÂNG TỪ 12 LÊN 25 HOẶC 30 FPS**.
   - **Max Bitrate (Kbps)**: Đặt khoảng `2048 - 4096 Kbps`.
   - **Video Encoding**: Chọn `H.264` (Chuẩn tương thích cao nhất với OpenCV và Web MJPEG).
   - **I Frame Interval (GOP)**: Đặt bằng số Frame Rate (ví dụ 25 hoặc 30) để giảm độ trễ giật hình.
4. Bấm **Save (Lưu)**. Camera sẽ khởi động lại luồng phát ở **25 - 30 FPS**.

---

## II. GIẢI QUYẾT TRIỆT ĐỂ VẤN ĐỀ "ĐỔI MẠNG MẤY KẾT NỐI CAMERA RTSP"

### 1. Tính năng "Tự Động Quét & Sửa IP" trên Web Dashboard (Đã Tích Hợp)
Khi bạn mang máy tính sang mạng WiFi khác (ví dụ: chuyển từ nhà đến trường, hoặc đổi router):
1. Đăng nhập vào Web Dashboard.
2. Vào mục **Cài Đặt Camera** → Bấm **✏️ Sửa RTSP** tại trạm camera cần đổi.
3. Bạn sẽ thấy 3 công cụ mới:
   - **⚡ Kiểm Tra**: Kiểm tra tức thời thông mạng, cổng 554, độ trễ và báo lỗi nếu bị lệch dải IP.
   - **🔍 Quét IP Mạng**: Tự động dò quét toàn bộ dải mạng LAN mới trong **1 - 2 giây** và hiển thị danh sách tất cả camera tìm thấy. Bấm **`+ Dùng IP này`** để tự động điền IP mới.
   - **🔄 Tự Sửa IP**: Chỉ cần bấm 1 click, hệ thống tự động quét, phát hiện IP mới của camera và cập nhật cấu hình cho toàn bộ trạm AI!

---

### 2. Phương Án Tuyệt Vời Nhất Khi Đi Thi STEM / Triển Lãm / Phòng Lab: "Điểm Phát Sóng Di Động" (Mobile Hotspot)

Khi đi thi khoa học kỹ thuật, đi hội trường hoặc demo ngoài trời, bạn sẽ không có quyền truy cập vào Router của ban tổ chức để cài đặt IP tĩnh. Giải pháp chuẩn xác và chuyên nghiệp nhất là:

1. **Dùng 1 chiếc điện thoại (hoặc cục phát WiFi 4G mini)**:
   - Bật tính năng **Điểm phát sóng cá nhân (Personal Hotspot)**.
   - Đặt Tên WiFi (SSID) và Mật khẩu cố định, ví dụ:
     + SSID: `STEM_AI_HUB`
     + Pass: `StemAttendance2026`
2. **Cài đặt cho Camera và Máy Tính**:
   - Dùng app điện thoại (Hik-Connect / Ezviz) kết nối camera vào WiFi `STEM_AI_HUB`.
   - Kết nối máy tính xách tay vào WiFi `STEM_AI_HUB`.
3. **Lợi ích**:
   - Dù bạn mang máy tính và camera đi bất cứ đâu (ở nhà, ở trường, lên phòng thi, sang tỉnh khác), chỉ cần bật điện thoại và cắm điện camera là **hai thiết bị tự động kết nối vào nhau trong 3 giây**!
   - Không bị chặn tường lửa (firewall), không bị đổi dải mạng IP.

---

### 3. Phương Án Cố Định Tại Trường Học (Fixed School Router)
Nếu lắp đặt cố định tại cổng trường:
1. Đăng nhập vào trang quản trị Modem/Router của nhà trường (thường là `192.168.1.1`).
2. Tìm mục **DHCP Static IP Lease / MAC Address Reservation**.
3. Thêm địa chỉ MAC của Camera (ví dụ `64:24:4D:68:55:0A`) gán cố định cho IP `192.168.1.2`.
4. Khi đó dù Router có khởi động lại bao nhiêu lần, Camera vẫn luôn luôn giữ nguyên IP `192.168.1.2`.
