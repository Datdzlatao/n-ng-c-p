#!/usr/bin/env python3
"""
edge/tools/gen_go2rtc_config.py
Tự động sinh cấu hình go2rtc.yaml cho tất cả camera trong trường học.
Hỗ trợ cả:
  - Luồng AI (cam_{id}_ai): lấy từ stream MJPEG cổng 8081..8089, transcode sang H.264 bằng NVENC (RTX 2050) hoặc CPU x264.
  - Luồng RAW (cam_{id}_raw): passthrough trực tiếp từ RTSP camera (0% CPU, siêu nét).
"""
import os
import json
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
FFMPEG_BIN = BASE_DIR / "edge" / "tools" / "bin" / "ffmpeg"
CONF_FILE = BASE_DIR / "edge" / "go2rtc.yaml"
CAMERAS_JSON = BASE_DIR / "edge" / "data" / "cameras.json"
DB_FILE = BASE_DIR / "backend" / "data" / "stem_platform.db"

def has_nvenc(ffmpeg_path: Path) -> bool:
    """Kiểm tra ffmpeg có thực sự encode được h264_nvenc trên GPU hay không."""
    if not ffmpeg_path.exists():
        return False
    try:
        import subprocess
        cmd = [
            str(ffmpeg_path), "-f", "lavfi", "-i", "testsrc=duration=0.1:size=320x240:rate=10",
            "-c:v", "h264_nvenc", "-f", "null", "-"
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=3.0)
        return res.returncode == 0
    except Exception:
        return False

def generate_config():
    # 1. Thu thập danh sách camera
    cameras = []
    if CAMERAS_JSON.is_file():
        try:
            with open(CAMERAS_JSON, "r", encoding="utf-8") as f:
                d = json.load(f)
                cameras = d.get("cameras", [])
        except Exception:
            pass

    if not cameras and DB_FILE.is_file():
        try:
            conn = sqlite3.connect(str(DB_FILE))
            rows = conn.execute("SELECT id, school_id, camera_num, stream_url FROM camera_stations").fetchall()
            conn.close()
            for r in rows:
                c_num = r[2] or 1
                cameras.append({
                    "id": r[0],
                    "school_id": r[1],
                    "camera_num": c_num,
                    "stream_url": r[3],
                    "stream_port": 8080 + int(c_num)
                })
        except Exception:
            pass

    ffmpeg_str = str(FFMPEG_BIN) if FFMPEG_BIN.exists() else "ffmpeg"
    nvenc_supported = has_nvenc(FFMPEG_BIN)

    # Chọn encoder: Ưu tiên h264_nvenc (Nvidia GPU RTX 2050), fallback libx264 siêu tốc
    if nvenc_supported:
        v_enc = "h264_nvenc -preset p1 -tune ull -zerolatency 1 -b:v 2500k -maxrate 3000k -bufsize 6000k -g 30 -pix_fmt yuv420p"
    else:
        v_enc = "libx264 -preset ultrafast -tune zerolatency -b:v 2000k -maxrate 2500k -bufsize 5000k -g 30 -pix_fmt yuv420p"

    lines = [
        "# go2rtc.yaml — Tự động sinh bởi EduSAMS WebRTC Engine",
        "log:",
        "  level: info",
        "",
        "api:",
        "  listen: \"127.0.0.1:1984\"",
        "",
        "rtsp:",
        "  listen: \"127.0.0.1:8554\"",
        "",
        "webrtc:",
        "  listen: \":8555\"",
        "  candidates:",
        "    - stun:stun.l.google.com:19302",
        "",
        "ffmpeg:",
        f"  bin: \"{ffmpeg_str}\"",
        f"  h264: \"-c:v {v_enc}\"",
        "",
        "streams:"
    ]

    for cam in cameras:
        cam_id = cam.get("id")
        rtsp_url = cam.get("stream_url")
        mjpeg_port = cam.get("stream_port", 8081)

        # 1. Luồng AI có khung viền bounding box:
        # Đọc từ mjpeg_port do edge/main.py phát ra -> encode H.264 qua GPU/CPU -> WebRTC
        lines.append(f"  cam_{cam_id}_ai:")
        lines.append(f"    - ffmpeg:http://127.0.0.1:{mjpeg_port}/stream#video=h264")

        # 2. Luồng RAW gốc trực tiếp từ RTSP (0% CPU, cực mượt):
        if rtsp_url and rtsp_url.startswith("rtsp://"):
            lines.append(f"  cam_{cam_id}_raw:")
            lines.append(f"    - \"{rtsp_url}\"")

    lines.append("")
    content = "\n".join(lines)
    with open(CONF_FILE, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"✅ Đã tạo cấu hình go2rtc tại: {CONF_FILE}")
    print(f"   Encoder: {'NVIDIA NVENC (GPU RTX 2050)' if nvenc_supported else 'libx264 (CPU Ultrafast)'}")

if __name__ == "__main__":
    generate_config()
