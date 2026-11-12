# 📷 Edge — Camera AI Module (Raspberry Pi)

Module chạy trên **Raspberry Pi** tại cổng trường. Điểm danh bằng Face AI và gửi log lên Cloud API.

## Hardware Requirements
- Raspberry Pi 4B (4GB RAM) hoặc Pi 5
- USB Camera hoặc Camera Module v3
- Kết nối internet (WiFi / LAN)

## Cách Chạy

```bash
cd edge
pip install -r requirements.txt
python main.py --school_id 1 --station_secret YOUR_SECRET_KEY
```

## Đăng Ký Trạm Camera
1. Hiệu Trưởng vào Dashboard → Trạm Camera → Thêm Trạm
2. Copy **Secret Key** (chỉ hiển thị 1 lần)
3. Lưu vào `/etc/stem_camera.conf`:
   ```
   SCHOOL_ID=1
   STATION_SECRET=xxxxxxxxxxxxxxxxxxxxxxxx
   API_URL=https://api.stemapp.vn
   ```

## Files
```
edge/
├── main.py           ← Entry point: camera loop + face detection
├── tracker.py        ← Tracking multiple faces in frame
├── smart_capture.py  ← Capture & preprocess face images
├── uniform_checker.py← Đồng phục detection
└── utils.py          ← Utility functions
```
