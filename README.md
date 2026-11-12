# Smart Farm & Agriculture AI Agent System (MCP + Gemini + Supabase + FastAPI)

Hệ thống Backend Quản lý Trang Trại & Chuồng Trại Nông Nghiệp Thông Minh tích hợp AI Agent thông qua giao thức **Model Context Protocol (FastMCP)**, Google Gemini API (`google-genai`), cơ sở dữ liệu Supabase (PostgreSQL), và FastAPI với Realtime WebSocket & Background Monitoring (Watcher & APScheduler).

---

## 🏛️ Kiến Trúc Hệ Thống (Clean Architecture)

```
new project/
├── .env                              # Cấu hình biến môi trường (Supabase & Gemini API)
├── requirements.txt                  # Danh sách thư viện Python (mcp, fastapi, google-genai...)
├── schema.sql                        # Toàn bộ DDL hoàn chỉnh, RLS Policies & Seed Data cho trang trại
├── database.sql                      # Schema tham chiếu các bảng gốc
├── mcp_server.py                     # Entrypoint FastMCP Server độc lập
├── scripts/
│   ├── verify_farm_system.py         # Script kiểm tra toàn diện E2E tất cả các module
│   └── verify_all_phases.py         # Script kiểm thử ban đầu
└── app/
    ├── config.py                     # Quản lý Settings bằng pydantic-settings
    ├── models/
    │   └── schemas.py                # Pydantic schemas cho 10+ thực thể trang trại & IoT
    ├── db/
    │   ├── supabase_client.py        # Singleton Client kết nối Supabase
    │   └── repositories/             # Data Access Layer
    │       ├── pens.py               # Quản lý chuồng trại (pens)
    │       ├── devices.py            # Quản lý thiết bị IoT chuồng (quạt hút, phun sương, đèn)
    │       ├── animals.py            # Quản lý vật nuôi, theo dõi tăng trọng & y tế
    │       ├── crops.py              # Quản lý cây trồng, chu kỳ sinh trưởng & thu hoạch
    │       ├── env_logs.py           # Quản lý cảm biến môi trường (nhiệt độ, độ ẩm, mùi)
    │       ├── inventory.py          # Quản lý kho thức ăn, phân bón & thuốc thú y
    │       ├── feed_logs.py          # Quản lý nhật ký cho ăn & trừ tồn kho
    │       ├── schedules.py          # Quản lý lịch trình công việc
    │       └── alerts.py             # Quản lý cảnh báo hệ thống
    ├── mcp/
    │   └── mcp_server.py             # FastMCP Server (5 Resources & 6 Tools)
    ├── services/
    │   ├── agent_service.py          # AI Agent MCP Host / Gemini Client + Fallback Engine
    │   ├── rag_service.py            # RAG Engine (Pinecone VectorStore + Gemini Embeddings + Diagnosis)
    │   └── embeddings.py             # Custom Gemini Embeddings (dim: 1024)
    ├── background/
    │   ├── watcher.py                # The Watcher: Giám sát đột biến nhiệt độ & mùi hôi chuồng (tự bật quạt)
    │   └── scheduler.py              # APScheduler: Tổng hợp bản tin trang trại buổi sáng 07:00
    ├── api/
    │   └── websocket_manager.py      # Quản lý WebSocket realtime
    └── main.py                       # FastAPI Web Server & Web Dashboard UI
```

---

## 🚀 Tính Năng Nâng Cấp Nổi Bật

### 1. Phân Hệ Cơ Sở Dữ Liệu Trang Trại ([`schema.sql`](file:///home/dat/new%20project/schema.sql))
* **Chuồng trại (`pens`)**: Quản lý các phân khu nuôi trồng.
* **Cảm biến môi trường (`env_logs`)**: Đo nhiệt độ, độ ẩm và **chỉ số mùi hôi / khí chuồng (`smell_level`)**.
* **Thiết bị IoT (`devices`)**: Quạt hút mùi, máy phun sương, đèn sưởi có thể điều khiển trực tiếp qua AI hoặc Watcher.
* **Vật nuôi (`animals` ➔ `health_logs`, `weight_logs`)**: Quản lý thể trạng, theo dõi tăng trọng và hồ sơ tiêm chủng, dịch bệnh.
* **Cây trồng (`crops` ➔ `crop_growth_logs`, `crop_care_logs`)**: Theo dõi ngày trồng và ngày dự kiến thu hoạch.
* **Kho thức ăn & vật tư (`inventory` & `feed_logs`)**: Tự động trừ tồn kho khi cho ăn hoặc xuất dùng.

### 2. FastMCP Server Cho AI Agent ([`app/mcp/mcp_server.py`](file:///home/dat/new%20project/app/mcp/mcp_server.py))
* **MCP Resources (Cung cấp ngữ cảnh)**:
  * `resource://farm/overview`: Thống kê toàn trang trại.
  * `resource://env/latest`: Dữ liệu cảm biến mới nhất (kèm `smell_level` và `pen_id`).
  * `resource://inventory/low-stock`: Vật tư, thức ăn chạm hoặc dưới ngưỡng tối thiểu.
  * `resource://animals/attention`: Danh sách cá thể vật nuôi ốm, sốt hoặc cần chăm sóc.
  * `resource://crops/harvest`: Cây trồng sắp đến kỳ thu hoạch trong 7 ngày tới.
* **MCP Tools (Cánh tay hành động cho AI)**:
  * `control_device(action, device_name, pen_id)`: Bật/tắt quạt thông gió, máy phun sương, đèn sưởi.
  * `log_feeding(pen_id, food_name, amount)`: Ghi nhận cho ăn và tự động trừ kho thức ăn.
  * `update_animal_health(animal_id, status, note)`: Cập nhật tình trạng sức khỏe và ghi log y tế.
  * `manage_inventory(action, name, quantity, unit, category)`: Nhập/xuất/tạo mới vật tư kho.
  * `manage_schedule(action, task_name, target_date, pen_id, note)`: Lên lịch trình công việc.
  * `create_system_alert(alert_type, message, pen_id)`: Tạo cảnh báo và phát realtime qua WebSocket.
  * `search_agricultural_knowledge(query, limit)`: Tra cứu cẩm nang y tế nông nghiệp, phác đồ điều trị từ Pinecone VectorStore.
  * `diagnose_agricultural_disease(symptoms_or_description, species)`: Chẩn đoán bệnh cây trồng & vật nuôi, trả về phác đồ can thiệp.

### 3. Phân Hệ RAG Tri Thức Nông Nghiệp & Chẩn Đoán Bệnh ([`app/services/rag_service.py`](file:///storage/emulated/0/2/3/app/services/rag_service.py))
Tích hợp từ dự án **`stem`**:
* **Pinecone Vector Store & Gemini Embeddings**: Kết nối index `smart-farm-knowledge-base` với vector embedding 1024 chiều (`models/gemini-embedding-2`).
* **Cơ sở tri thức y tế thú y & cây trồng (Fallback & Built-in)**: Lưu trữ các phác đồ chuẩn cho dịch bệnh gia súc (Tai xanh PRRS, Dịch tả lợn châu Phi ASF, Tiêu chảy PED, Lở mồm long móng FMD) và cây trồng (Đạo ôn lúa, Sương mai cà chua/dưa lưới, Rầy nâu...).
* **API Chẩn đoán Multimodal (`POST /api/diagnose`)**: Tiếp nhận câu hỏi triệu chứng và/hoặc hình ảnh chụp thực tế cây trồng/vật nuôi, nhận diện bệnh lý và trích xuất phác đồ điều trị chuẩn JSON.
* **API Tra cứu tri thức (`GET /api/knowledge/search`)**: Tra cứu ngữ cảnh và tài liệu y tế trực tiếp.

### 4. Tự Động Hóa Thông Minh 24/7 ([`app/background/`](file:///home/dat/new%20project/app/background/))
* **The Watcher**: Giám sát đột biến môi trường. Khi phát hiện **mùi hôi chuồng cao (`smell_level >= 10.0`)** hoặc nhiệt độ quá nóng, Watcher **tự động kích hoạt quạt thông gió** tại chuồng đó và đẩy cảnh báo realtime qua WebSocket.
* **The Scheduler**: 07:00 sáng hàng ngày quét việc cần làm hôm nay, thức ăn sắp hết, vật nuôi bị bệnh, cây sắp thu hoạch -> Gemini viết bản tin ngắn gọn, thúc đẩy công việc và gửi tới Web/App.

### 5. Quản Lý Nhân Sự & Điểm Danh FaceID ([`standalone_ai_engine/`](file:///storage/emulated/0/2/3/standalone_ai_engine/))
Tích hợp từ module **Standalone AI Vision Engine**:
* **Nhận diện khuôn mặt & Chống giả mạo**: Kết nối YuNet + SFace (128D embeddings) và MiniFASNet Liveness qua Microservice REST API hoặc Local Fallback.
* **FastMCP Tools & Resources**:
  * `resource://staff/today`: Tra cứu danh sách nhân sự đã có mặt hôm nay.
  * `resource://staff/list`: Toàn bộ nhân sự trang trại và chuồng phụ trách.
  * `get_staff_list(pen_id)`: Tra cứu danh sách theo chuồng.
  * `check_in_staff_face(staff_id, pen_id, note)`: Điểm danh vào ca trực qua FaceID.
  * `get_today_attendance_summary()`: Báo cáo tổng hợp điểm danh trong ngày.
* **FastAPI Endpoints**:
  * `GET /api/staff` & `POST /api/staff`: Quản lý hồ sơ nhân sự.
  * `POST /api/staff/checkin`: Điểm danh FaceID tự động qua ảnh Base64 hoặc staff_id.
  * `POST /api/staff/checkin-upload`: Tải file ảnh chụp trực tiếp từ camera.
  * `POST /api/staff/enroll`: Đăng ký FaceID mới và lưu vào cơ sở dữ liệu.
* **Realtime WebSocket & Web Dashboard**: Tự động phát sự kiện `staff_checkin` lên Dashboard, cập nhật số lượng nhân sự vào ca trực tiếp.

---

## 🛠️ Hướng Dẫn Vận Hành

### 1. Khởi động Web Dashboard & REST API
```bash
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
Truy cập:
* **Web Dashboard**: [http://localhost:8000](http://localhost:8000)
* **API Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
* **WebSocket Endpoint**: `ws://localhost:8000/ws`

### 2. Chạy MCP Server Độc Lập (FastMCP stdio)
Nếu cần kết nối với MCP Client ngoài (Claude Desktop, Cursor, Gemini MCP Host):
```bash
.venv/bin/python mcp_server.py
```

### 3. Kiểm Tra Toàn Bộ Hệ Thống (E2E Test)
```bash
.venv/bin/python scripts/verify_farm_system.py
.venv/bin/python scripts/verify_staff_workflow.py
```
