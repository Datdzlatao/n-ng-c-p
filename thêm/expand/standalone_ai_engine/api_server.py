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
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List

from standalone_runner import StandaloneVisionPipeline

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


class Base64AnalyzeRequest(BaseModel):
    image_base64: str
    weekday_override: Optional[int] = None


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
