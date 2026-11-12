import json
import logging
import urllib.request
import urllib.error
from typing import Optional, Dict, Any
from app.config import get_settings

logger = logging.getLogger("smart_manager.face_service")


class FaceVisionService:
    """
    Client service interfacing with Standalone AI Vision Engine (api_server.py).
    Handles face recognition, anti-spoofing liveness verification, and face enrollment.
    """

    def __init__(self):
        self.settings = get_settings()

    @property
    def base_url(self) -> str:
        return self.settings.VISION_ENGINE_URL.rstrip("/")

    def check_health(self) -> dict:
        """Check if standalone AI engine is online."""
        url = f"{self.base_url}/api/v1/health"
        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=3) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    return {"online": True, **data}
        except Exception as e:
            logger.debug(f"Standalone AI engine offline at {url}: {e}")
        return {"online": False, "status": "offline", "engine_url": self.base_url}

    def analyze_face_base64(self, image_base64: str) -> dict:
        """
        Send base64 image to standalone AI engine for face recognition & anti-spoofing check.
        Returns normalized dictionary with detected faces and liveness status.
        """
        url = f"{self.base_url}/api/v1/analyze"
        payload = json.dumps({"image_base64": image_base64}).encode("utf-8")

        try:
            req = urllib.request.Request(
                url,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status == 200:
                    return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as he:
            err_body = he.read().decode("utf-8")
            logger.warning(f"AI Vision API error {he.code}: {err_body}")
            return {"error": f"AI Engine HTTP {he.code}", "detail": err_body, "faces": []}
        except Exception as e:
            logger.warning(f"Could not connect to AI Vision Engine at {url}: {e}")

        # Local fallback attempt if direct import is possible
        try:
            import base64
            import cv2
            import numpy as np
            from standalone_ai_engine.face_engine import FaceEngine
            from standalone_ai_engine.anti_spoofing import AntiSpoofingDetector

            if "," in image_base64:
                image_base64 = image_base64.split(",", 1)[1]
            img_bytes = base64.b64decode(image_base64)
            arr = np.frombuffer(img_bytes, dtype=np.uint8)
            img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if img is not None:
                engine = FaceEngine()
                results = engine.recognize(img)
                anti_spoof = AntiSpoofingDetector()
                for fr in results:
                    loc = fr.get("location")
                    if loc:
                        fr["liveness"] = anti_spoof.check_liveness(img, loc)
                    else:
                        fr["liveness"] = {"is_real": True, "status": "SKIPPED", "confidence": 1.0}
                return {
                    "mode": "embedded_fallback",
                    "faces_detected": len(results),
                    "faces": results
                }
        except Exception as direct_err:
            logger.debug(f"Direct embedded engine fallback not available: {direct_err}")

        return {
            "status": "vision_engine_offline",
            "message": "AI Vision Engine đang offline. Vui lòng khởi động standalone_ai_engine/api_server.py trên cổng 8001.",
            "faces_detected": 0,
            "faces": []
        }

    def inspect_uniform_base64(self, image_base64: str, weekday: int = -1, return_annotated: bool = True) -> dict:
        """
        Send base64 image to standalone AI engine for full-body person detection & uniform inspection.
        """
        url = f"{self.base_url}/api/v1/uniform/inspect"
        payload = json.dumps({
            "image_base64": image_base64,
            "weekday": weekday,
            "return_annotated": return_annotated
        }).encode("utf-8")

        try:
            req = urllib.request.Request(
                url,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status == 200:
                    return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            logger.warning(f"Could not connect to AI Uniform Engine at {url}: {e}")

        # Local fallback if standalone server is offline
        try:
            import base64
            import cv2
            import numpy as np
            import sys
            import os
            engine_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "standalone_ai_engine")
            if engine_dir not in sys.path:
                sys.path.insert(0, engine_dir)
            from standalone_ai_engine.uniform_checker import UniformChecker
            from standalone_ai_engine.face_engine import FaceEngine

            raw_b64 = image_base64
            if "," in raw_b64:
                raw_b64 = raw_b64.split(",", 1)[1]
            img_bytes = base64.b64decode(raw_b64)
            arr = np.frombuffer(img_bytes, dtype=np.uint8)
            img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if img is not None:
                fe = FaceEngine()
                faces = fe.recognize(img)
                floc = faces[0]["location"] if faces else None
                checker = UniformChecker()
                res = checker.check_uniform(img, face_location=floc, weekday_override=weekday)
                annotated_b64 = None
                if return_annotated:
                    hud = checker.draw_uniform_hud(img, res)
                    _, buf = cv2.imencode(".jpg", hud, [cv2.IMWRITE_JPEG_QUALITY, 85])
                    annotated_b64 = "data:image/jpeg;base64," + base64.b64encode(buf.tobytes()).decode("utf-8")
                return {
                    "status": "success",
                    "mode": "embedded_fallback",
                    "person_detected": res.get("person_detected", False),
                    "faces_detected": len(faces),
                    "faces": faces,
                    "uniform": res,
                    "annotated_image_base64": annotated_b64
                }
        except Exception as direct_err:
            logger.debug(f"Direct embedded uniform fallback error: {direct_err}")

        return {
            "status": "vision_engine_offline",
            "message": "AI Vision Engine đang offline. Vui lòng chạy start.sh để khởi động cổng 8001.",
            "person_detected": False,
            "uniform": None
        }

    def enroll_face(self, staff_id: str, staff_name: str, image_bytes: bytes, filename: str = "avatar.jpg") -> dict:
        """
        Enroll a new staff member face into the known faces database.
        Uses multipart form data to call /api/v1/faces/enroll.
        """
        url = f"{self.base_url}/api/v1/faces/enroll"
        boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
        
        body_parts = []
        # student_id field
        body_parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"student_id\"\r\n\r\n{staff_id}\r\n".encode("utf-8"))
        # student_name field
        body_parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"student_name\"\r\n\r\n{staff_name}\r\n".encode("utf-8"))
        # file field
        file_header = f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{filename}\"\r\nContent-Type: image/jpeg\r\n\r\n".encode("utf-8")
        body_parts.append(file_header)
        body_parts.append(image_bytes)
        body_parts.append(f"\r\n--{boundary}--\r\n".encode("utf-8"))

        full_body = b"".join(body_parts)

        try:
            req = urllib.request.Request(
                url,
                data=full_body,
                headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status == 200:
                    return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            logger.warning(f"Error enrolling face at {url}: {e}")

        # Local fallback enrollment directly to disk if possible
        try:
            import os
            import cv2
            import numpy as np
            arr = np.frombuffer(image_bytes, dtype=np.uint8)
            img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if img is not None:
                faces_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "standalone_ai_engine", "known_faces")
                os.makedirs(faces_dir, exist_ok=True)
                clean_name = staff_name.replace(" ", "_")
                out_path = os.path.join(faces_dir, f"{staff_id}_{clean_name}.jpg")
                cv2.imwrite(out_path, img)
                return {"status": "success", "message": f"Đã lưu ảnh nhân sự {staff_name} vào {out_path}", "local_fallback": True}
        except Exception as fe:
            logger.debug(f"Direct local enrollment error: {fe}")

        return {"status": "error", "message": "Không thể kết nối tới AI Vision Engine để đăng ký khuôn mặt."}


face_service = FaceVisionService()
