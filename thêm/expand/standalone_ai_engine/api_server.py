# -*- coding: utf-8 -*-
"""
STANDALONE AI REST API MICROSERVICE
api_server.py

Dịch vụ REST API độc lập cho phép tích hợp AI Nhận diện khuôn mặt
và Trang phục vào bất kỳ hệ thống nào (Node.js, C#, PHP, Java, Python...).

Khởi chạy:
  uvicorn api_server:app --host 0.0.0.0 --port 8001
"""
import base64
import cv2
import numpy as np
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import HTMLResponse, StreamingResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Union

from standalone_runner import StandaloneVisionPipeline
from camera_service import CameraStreamService
from web_viewer import VIEWER_HTML

app = FastAPI(
    title="Standalone AI Vision API",
    version="1.0.0",
    description="Microservice Nhận diện Khuôn mặt, Chống Giả mạo & Kiểm tra Trang phục"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

pipeline = StandaloneVisionPipeline()
camera_service = CameraStreamService(pipeline)


@app.on_event("shutdown")
def shutdown_event():
    """Giải phóng camera khi tắt server."""
    camera_service.stop()


class Base64AnalyzeRequest(BaseModel):
    image_base64: str
    weekday_override: Optional[int] = None


class CameraStartRequest(BaseModel):
    source: Union[int, str] = 0
    weekday_override: Optional[int] = None


# ═══════════════════════════════════════════════════════════════════════════════
# 1. GIAO DIỆN WEB VIEWER & CAMERA STREAMING ONLINE (API SOI CAM)
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/", response_class=HTMLResponse)
@app.get("/viewer", response_class=HTMLResponse)
async def get_viewer_page():
    """Giao diện Web xem trực tiếp luồng camera và thông số nhận diện AI."""
    return HTMLResponse(content=VIEWER_HTML, status_code=200)


@app.get("/api/v1/camera/video_feed")
async def get_camera_video_feed(overlay: bool = Query(True, description="Vẽ khung HUD phân tích AI")):
    """
    Luồng video MJPEG thời gian thực (chuẩn multipart/x-mixed-replace).
    Nhúng trực tiếp vào HTML bằng: <img src="/api/v1/camera/video_feed">
    """
    if not camera_service.is_running:
        started = camera_service.start(source=0)
        if not started:
            raise HTTPException(503, f"Không thể khởi động camera: {camera_service.error_message}")

    return StreamingResponse(
        camera_service.generate_mjpeg(overlay=overlay),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@app.get("/api/v1/camera/status")
async def get_camera_status():
    """Lấy trạng thái hoạt động của camera và chỉ số FPS."""
    return camera_service.get_status()


@app.get("/api/v1/camera/latest")
async def get_camera_latest_telemetry():
    """Lấy kết quả nhận diện khuôn mặt, chống gian lận và đồng phục mới nhất."""
    return camera_service.get_latest_result()


@app.get("/api/v1/camera/snapshot")
async def get_camera_snapshot(overlay: bool = Query(True, description="Kèm khung vẽ AI")):
    """Chụp 1 khung hình tĩnh chất lượng cao từ camera."""
    if not camera_service.is_running:
        camera_service.start(source=0)

    jpeg_bytes = camera_service.get_snapshot(overlay=overlay)
    if jpeg_bytes is None:
        raise HTTPException(503, "Camera đang khởi tạo hoặc chưa có dữ liệu hình ảnh.")

    return Response(content=jpeg_bytes, media_type="image/jpeg")


@app.post("/api/v1/camera/start")
async def start_camera_stream(req: CameraStartRequest):
    """Khởi động luồng camera với nguồn chỉ định (Webcam 0, 1 hoặc link RTSP)."""
    ok = camera_service.start(source=req.source, weekday_override=req.weekday_override)
    if not ok:
        raise HTTPException(400, f"Không thể mở nguồn camera: {camera_service.error_message}")

    return {
        "status": "success",
        "message": f"Đã kết nối nguồn camera: {req.source}",
        "source": req.source,
        "weekday_override": req.weekday_override
    }


@app.post("/api/v1/camera/stop")
async def stop_camera_stream():
    """Dừng luồng camera và giải phóng thiết bị phần cứng."""
    camera_service.stop()
    return {
        "status": "success",
        "message": "Đã dừng và giải phóng luồng camera thành công."
    }


def decode_image_base64(b64_str: str) -> np.ndarray:
    if "," in b64_str:
        b64_str = b64_str.split(",", 1)[1]
    img_bytes = base64.b64decode(b64_str)
    arr = np.frombuffer(img_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(400, "Không thể giải mã dữ liệu ảnh Base64.")
    return img


@app.get("/api/v1/health")
async def health_check():
    return {
        "status": "online",
        "registered_faces": len(pipeline.face_engine.known_ids),
        "anti_spoof_mode": pipeline.anti_spoof.backend_mode if pipeline.anti_spoof else "DISABLED"
    }


@app.get("/api/v1/faces")
async def list_faces():
    return {
        "total": len(pipeline.face_engine.known_ids),
        "students": [
            {"id": sid, "name": name}
            for sid, name in zip(pipeline.face_engine.known_ids, pipeline.face_engine.known_names)
        ]
    }


@app.post("/api/v1/analyze")
async def analyze_image_base64(req: Base64AnalyzeRequest):
    """Phân tích toàn diện: Nhận diện khuôn mặt + Chống giả mạo + Đồng phục qua Base64."""
    img = decode_image_base64(req.image_base64)
    res = pipeline.process_frame(img, weekday_override=req.weekday_override)
    return res


@app.post("/api/v1/analyze-upload")
async def analyze_image_file(
    file: UploadFile = File(...),
    weekday_override: Optional[int] = Form(None)
):
    """Phân tích toàn diện qua tải file ảnh trực tiếp (multipart/form-data)."""
    contents = await file.read()
    arr = np.frombuffer(contents, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(400, "Tệp tải lên không phải ảnh hợp lệ.")
    res = pipeline.process_frame(img, weekday_override=weekday_override)
    return res


@app.post("/api/v1/faces/reload")
async def reload_faces():
    """Tải lại toàn bộ khuôn mặt trong thư mục và làm mới bộ nhớ cache."""
    pipeline.face_engine.load_known_faces(force_reload=True)
    return {
        "status": "success",
        "message": f"Đã làm mới {len(pipeline.face_engine.known_ids)} khuôn mặt từ thư mục.",
        "total_faces": len(pipeline.face_engine.known_ids)
    }


@app.post("/api/v1/faces/enroll")
async def enroll_face(
    student_id: str = Form(...),
    student_name: str = Form(...),
    file: UploadFile = File(...)
):
    """Đăng ký khuôn mặt mới vào hệ sinh thái."""
    contents = await file.read()
    arr = np.frombuffer(contents, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(400, "Tệp ảnh không hợp lệ.")

    ok = pipeline.face_engine.register_face(student_id.strip(), student_name.strip(), img, save_disk=True)
    if not ok:
        raise HTTPException(422, "Không tìm thấy khuôn mặt rõ nét trong ảnh cung cấp.")

    return {
        "status": "success",
        "message": f"Đã đăng ký thành công FaceID cho {student_name} ({student_id})",
        "total_faces": len(pipeline.face_engine.known_ids)
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
