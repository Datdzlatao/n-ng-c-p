# 🤖 STANDALONE AI VISION ENGINE (FACE RECOGNITION & UNIFORM)

Hệ thống thị giác máy tính độc lập (Standalone AI Vision Engine) tách rời hoàn toàn khỏi mã nguồn gốc của dự án Điểm Danh STEM. Bạn có thể sử dụng module này để triển khai độc lập trên bất kỳ máy tính, máy chủ, Raspberry Pi hoặc container Docker mà **không cần chạy Backend, Database hay Google Sheets**.

---

## 📁 CẤU TRÚC THƯ MỤC STANDALONE

```
standalone_ai_engine/
├── assets/models/             ← Tự động tải ONNX models về đây (YuNet, SFace, MiniFASNet)
├── known_faces/               ← Thư mục chứa ảnh học sinh đã đăng ký
│   ├── HS01_Nguyen_Van_A.jpg
│   └── HS02_Tran_Thi_B.jpg
├── face_engine.py             ← Engine nhận diện YuNet (Detection) + SFace (Embeddings 128D)
├── anti_spoofing.py           ← Engine chống giả mạo MiniFASNet + Heuristic
├── person_detector.py         ← Engine phát hiện vóc dáng người HOG + SVM
├── uniform_color_analyzer.py  ← Phân tích màu sắc HSV áo và quần
├── uniform_checker.py         ← Điều phối kiểm tra quy định đồng phục theo thứ trong tuần
├── standalone_runner.py       ← Ứng dụng chạy trực tiếp với Webcam, Camera IP hoặc Ảnh tĩnh
├── api_server.py              ← REST API Microservice (FastAPI) để tích hợp đa nền tảng
└── requirements.txt           ← Thư viện tối giản (chỉ cần opencv-python và numpy)
```

---

## ⚡ 1. CÀI ĐẶT NHANH (QUICK START)

### Bước 1: Cài đặt thư viện Python
```bash
cd standalone_ai_engine
python3 -m venv venv
source venv/bin/activate       # Trên Linux / macOS
# hoặc: venv\Scripts\activate   # Trên Windows

pip install -r requirements.txt
```

> **Lưu ý:** Lần đầu tiên chạy, hệ thống sẽ tự động tải các file mô hình ONNX chính thức từ OpenCV Zoo CDN về thư mục `assets/models/`. Bạn không cần phải tải thủ công.

---

## 🎯 2. CÁCH SỬ DỤNG

### Cách 2.1: Chạy camera Webcam trực tiếp (Có HUD hiển thị)
```bash
python standalone_runner.py --source 0
```
- Khung màu **Xanh lá**: Học sinh đã nhận diện thành công + Đúng đồng phục + Người thật.
- Khung màu **Đỏ**: Người giả mạo (ảnh in, màn hình) hoặc Vi phạm đồng phục.
- Khung màu **Cam**: Người lạ (chưa đăng ký trong hệ thống).

### Cách 2.2: Chạy với Camera IP / Trạm Cổng trường (RTSP)
```bash
python standalone_runner.py --source "rtsp://admin:123456@192.168.1.100:554/Streaming/Channels/101"
```

### Cách 2.3: Kiểm tra một file ảnh tĩnh bất kỳ
```bash
python standalone_runner.py --image "test_hoc_sinh.jpg"
```

### Cách 2.4: Đăng ký một khuôn mặt học sinh mới
Có 2 cách:
1. **Cách 1 (Thủ công):** Chép ảnh thẻ rõ mặt vào thư mục `known_faces/` với tên file dạng `MãHS_Họ_Tên.jpg` (Ví dụ: `HS01_Nguyen_Van_A.jpg`).
2. **Cách 2 (Lệnh CLI):**
   ```bash
   python standalone_runner.py --register "HS10A1_05" "Lê Hoàng Long" --image "avatar.jpg"
   ```

---

## 🌐 3. CHẠY DƯỚI DẠNG MICROSERVICE REST API

Nếu bạn muốn ứng dụng Node.js, C#, PHP, Java hoặc Website khác gọi tới AI để nhận kết quả:

### Khởi động API Server
```bash
python api_server.py
# Hoặc: uvicorn api_server:app --host 0.0.0.0 --port 8001
```

### Các Endpoint chính:
1. **Kiểm tra trạng thái:** `GET http://localhost:8001/api/v1/health`
2. **Lấy danh sách khuôn mặt:** `GET http://localhost:8001/api/v1/faces`
3. **Phân tích ảnh qua File:**
   ```bash
   curl -X POST "http://localhost:8001/api/v1/analyze-upload" \
        -F "file=@anh_hoc_sinh.jpg"
   ```
4. **Phân tích ảnh qua chuỗi Base64:**
   ```bash
   curl -X POST "http://localhost:8001/api/v1/analyze" \
        -H "Content-Type: application/json" \
        -d '{"image_base64": "data:image/jpeg;base64,/9j/4AAQSkZJRg..."}'
   ```
5. **Đăng ký FaceID mới qua API:**
   ```bash
   curl -X POST "http://localhost:8001/api/v1/faces/enroll" \
        -F "student_id=HS99" \
        -F "student_name=Nguyen Van C" \
        -F "file=@face.jpg"
   ```

---

## ✂️ 4. HƯỚNG DẪN LOẠI BỎ HOÀN TOÀN KHỎI MÃ NGUỒN GỐC

Nếu bạn muốn mã nguồn gốc (`edge/` và `backend/`) hoàn toàn sạch bóng AI, chỉ hoạt động bằng thẻ QR hoặc gọi sang Service độc lập này:

1. **Trên Trạm Camera (`edge/config.py`):**
   Đổi:
   ```python
   ATTENDANCE_MODE = "QR_ONLY"      # Chuyển từ "AUTO" hoặc "FACE_ONLY" sang "QR_ONLY"
   ANTI_SPOOF_ENABLE = False
   UNIFORM_CHECK_ENABLE = False
   ```
   Lúc này, `edge/main.py` sẽ bỏ qua toàn bộ việc chạy inference của YuNet, SFace, MiniFASNet, giúp camera chạy siêu mượt mà không tốn tài nguyên.

2. **Trên Backend (`backend/app/main.py`):**
   - Comment hoặc xóa dòng:
     ```python
     # app.include_router(biometric.router)
     ```
   - Hệ thống Backend vẫn nhận log điểm danh bình thường từ module độc lập của bạn bằng cách gửi HTTP POST lên:
     ```
     POST /api/v1/s/{school_id}/attendance/sync
     ```
     với `station_secret_key` và `check_type="FACE_AI"`.
