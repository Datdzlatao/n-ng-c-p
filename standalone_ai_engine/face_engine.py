# -*- coding: utf-8 -*-
"""
STANDALONE FACE ENGINE (OpenCV DNN YuNet + SFace)
Hệ thống nhận diện khuôn mặt độc lập thời gian thực.
"""
import os
import re
import cv2
import time
import queue
import urllib.request
import threading
import numpy as np
from typing import Optional, List, Dict, Tuple, Any

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_MODELS_DIR = os.path.join(CURRENT_DIR, "assets", "models")
DEFAULT_FACES_DIR = os.path.join(CURRENT_DIR, "known_faces")
DEFAULT_CACHE_PATH = os.path.join(CURRENT_DIR, "assets", "embeddings_cache.npz")

YUNET_FILENAME = "face_detection_yunet_2023mar.onnx"
SFACE_FILENAME = "face_recognition_sface_2021dec.onnx"

YUNET_URLS = [
    "https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx",
    "https://raw.githubusercontent.com/opencv/opencv_zoo/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx",
]
SFACE_URLS = [
    "https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx",
    "https://raw.githubusercontent.com/opencv/opencv_zoo/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx",
]


def ensure_model_file(model_path: str, urls: List[str], expected_min_bytes: int = 100_000) -> bool:
    if os.path.isfile(model_path) and os.path.getsize(model_path) >= expected_min_bytes:
        return True

    os.makedirs(os.path.dirname(os.path.abspath(model_path)), exist_ok=True)
    filename = os.path.basename(model_path)
    print(f"[MODEL] Đang tải mô hình: {filename}...")

    for url in urls:
        try:
            urllib.request.urlretrieve(url, model_path)
            if os.path.isfile(model_path) and os.path.getsize(model_path) >= expected_min_bytes:
                print(f"[MODEL] Tải thành công: {filename} ({os.path.getsize(model_path):,} bytes)")
                return True
        except Exception as e:
            print(f"[MODEL] Lỗi tải từ {url}: {e}")
            if os.path.exists(model_path):
                try:
                    os.remove(model_path)
                except OSError:
                    pass

    return False


class FaceEngine:
    def __init__(self,
                 faces_dir: str = DEFAULT_FACES_DIR,
                 models_dir: str = DEFAULT_MODELS_DIR,
                 cache_path: str = DEFAULT_CACHE_PATH,
                 score_threshold: float = 0.65,
                 nms_threshold: float = 0.30,
                 cosine_threshold: float = 0.42,
                 margin_threshold: float = 0.08,
                 min_face_size: int = 18,
                 force_reload: bool = False):

        self.faces_dir = faces_dir
        self.models_dir = models_dir
        self.cache_path = cache_path
        self.score_threshold = score_threshold
        self.nms_threshold = nms_threshold
        self.cosine_threshold = cosine_threshold
        self.margin_threshold = margin_threshold
        self.min_face_size = min_face_size

        os.makedirs(self.faces_dir, exist_ok=True)
        os.makedirs(self.models_dir, exist_ok=True)

        self.yunet_path = os.path.join(self.models_dir, YUNET_FILENAME)
        self.sface_path = os.path.join(self.models_dir, SFACE_FILENAME)

        ensure_model_file(self.yunet_path, YUNET_URLS)
        ensure_model_file(self.sface_path, SFACE_URLS)

        # Initialize YuNet Detector
        self.detector = cv2.FaceDetectorYN.create(
            model=self.yunet_path,
            config="",
            input_size=(320, 320),
            score_threshold=self.score_threshold,
            nms_threshold=self.nms_threshold,
            top_k=5000,
            backend_id=cv2.dnn.DNN_BACKEND_OPENCV,
            target_id=cv2.dnn.DNN_TARGET_CPU
        )

        # Initialize SFace Recognizer
        self.recognizer = cv2.FaceRecognizerSF.create(
            model=self.sface_path,
            config="",
            backend_id=cv2.dnn.DNN_BACKEND_OPENCV,
            target_id=cv2.dnn.DNN_TARGET_CPU
        )

        self.current_input_size = (320, 320)
        self.known_embeddings: List[np.ndarray] = []
        self.known_ids: List[str] = []
        self.known_names: List[str] = []

        self.load_known_faces(force_reload=force_reload)

    def _update_detector_size(self, w: int, h: int):
        if (w, h) != self.current_input_size:
            self.detector.setInputSize((w, h))
            self.current_input_size = (w, h)

    def extract_embedding_from_image(self, img_bgr: np.ndarray) -> Optional[np.ndarray]:
        if img_bgr is None or img_bgr.size == 0:
            return None
        h, w = img_bgr.shape[:2]
        self._update_detector_size(w, h)
        _, faces = self.detector.detect(img_bgr)
        if faces is None or len(faces) == 0:
            return None

        # Choose largest face
        best_face = max(faces, key=lambda f: f[2] * f[3])
        aligned = self.recognizer.alignCrop(img_bgr, best_face)
        feature = self.recognizer.feature(aligned)
        norm = np.linalg.norm(feature)
        if norm > 1e-6:
            feature = feature / norm
        return feature.flatten()

    @staticmethod
    def parse_filename(fname: str) -> Tuple[str, str]:
        """Tách MSSV/ID và Tên từ tên file, loại bỏ đuôi file trùng lặp và hậu tố tư thế ảnh."""
        name = fname.strip()
        while True:
            root, ext = os.path.splitext(name)
            if ext.lower() in {".jpg", ".jpeg", ".png", ".webp", ".bmp"} or ext.strip().lower() in {".jpg", ".jpeg", ".png", ".webp"}:
                name = root.strip()
            else:
                break

        parts = name.split("_")
        if len(parts) == 1:
            return parts[0].strip(), parts[0].strip()

        stu_id = parts[0].strip()
        tokens = parts[1:]

        pose_keywords = {
            "camera", "thang", "nghieng", "phai", "trai", "chinhdien", "chinh_dien",
            "mattruoc", "mat_truoc", "front", "left", "right", "center", "face", "avatar"
        }
        while len(tokens) > 1 and (tokens[-1].lower() in pose_keywords or tokens[-1].isdigit() or tokens[-1].lower() in {"nghieng_phai", "nghieng_trai"}):
            tokens.pop()
        if len(tokens) >= 2 and tokens[-2].lower() == "nghieng" and tokens[-1].lower() in {"trai", "phai"}:
            tokens.pop()
            tokens.pop()

        stu_name = " ".join(tokens).strip()
        return stu_id, stu_name if stu_name else stu_id

    def load_known_faces(self, force_reload: bool = False):
        valid_exts = {".jpg", ".jpeg", ".png", ".webp"}
        files = [f for f in os.listdir(self.faces_dir) if any(f.strip().lower().endswith(ext) for ext in valid_exts)]
        files = sorted(files)

        # Kiểm tra xem cache hiện tại có hợp lệ và khớp danh sách file không
        if not force_reload and os.path.isfile(self.cache_path):
            try:
                data = np.load(self.cache_path, allow_pickle=True)
                cached_files = list(data["files"]) if "files" in data else None
                if cached_files is not None and sorted(cached_files) == files:
                    self.known_ids = list(data["ids"])
                    self.known_names = list(data["names"])
                    self.known_embeddings = list(data["embeddings"])
                    print(f"[FACE ENGINE] Đã nạp {len(self.known_ids)} khuôn mặt từ cache: {os.path.basename(self.cache_path)}")
                    return
                elif cached_files is None and len(data["ids"]) == len(files):
                    self.known_ids = list(data["ids"])
                    self.known_names = list(data["names"])
                    self.known_embeddings = list(data["embeddings"])
                    print(f"[FACE ENGINE] Đã nạp {len(self.known_ids)} khuôn mặt từ cache: {os.path.basename(self.cache_path)}")
                    return
                else:
                    print(f"[FACE ENGINE] Thư mục ảnh đã thay đổi ({len(files)} ảnh hiện tại), cập nhật lại cache...")
            except Exception as e:
                print(f"[FACE ENGINE] Cache không đọc được ({e}), quét lại thư mục...")

        self.known_ids.clear()
        self.known_names.clear()
        self.known_embeddings.clear()
        loaded_files = []

        print(f"[FACE ENGINE] Đang quét {len(files)} ảnh trong {self.faces_dir}...")

        for fname in files:
            stu_id, stu_name = self.parse_filename(fname)

            img_path = os.path.join(self.faces_dir, fname)
            img = cv2.imread(img_path)
            if img is None:
                continue

            emb = self.extract_embedding_from_image(img)
            if emb is not None:
                self.known_ids.append(stu_id)
                self.known_names.append(stu_name)
                self.known_embeddings.append(emb)
                loaded_files.append(fname)

        if self.known_ids:
            try:
                os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
                np.savez_compressed(
                    self.cache_path,
                    ids=np.array(self.known_ids),
                    names=np.array(self.known_names),
                    embeddings=np.array(self.known_embeddings),
                    files=np.array(loaded_files)
                )
                print(f"[FACE ENGINE] Đã lưu cache {len(self.known_ids)} đặc trưng vào {self.cache_path}")
            except Exception as e:
                print(f"[FACE ENGINE] Lỗi ghi cache: {e}")

    def register_face(self, student_id: str, student_name: str, image_bgr: np.ndarray, save_disk: bool = True, suffix: str = "") -> bool:
        emb = self.extract_embedding_from_image(image_bgr)
        if emb is None:
            return False

        if save_disk:
            safe_name = re.sub(r"[^a-zA-Z0-9_-]", "", student_name.replace(" ", "_"))
            clean_suffix = suffix.strip().lstrip("_")
            if clean_suffix:
                out_fn = f"{student_id}_{safe_name}_{clean_suffix}.jpg" if safe_name else f"{student_id}_{clean_suffix}.jpg"
            else:
                out_fn = f"{student_id}_{safe_name}.jpg" if safe_name else f"{student_id}.jpg"
            
            cv2.imwrite(os.path.join(self.faces_dir, out_fn), image_bgr)
            try:
                self.load_known_faces(force_reload=True)
            except Exception as e:
                print(f"[FACE ENGINE] Lỗi nạp lại cache: {e}")
        else:
            self.known_ids.append(student_id)
            self.known_names.append(student_name)
            self.known_embeddings.append(emb)

        return True

    def register_faces_3_angles(
        self,
        student_id: str,
        student_name: str,
        img_thang: np.ndarray,
        img_nghieng_trai: np.ndarray,
        img_nghieng_phai: np.ndarray,
        save_disk: bool = True
    ) -> Dict[str, Any]:
        """
        Đăng ký FaceID 3 góc theo chuẩn eKYC ngân hàng:
        - thang: Chính diện
        - nghieng_trai: Nghiêng góc trái ~30 độ
        - nghieng_phai: Nghiêng góc phải ~30 độ
        """
        angles = {
            "thang": img_thang,
            "nghieng_trai": img_nghieng_trai,
            "nghieng_phai": img_nghieng_phai
        }

        # 1. Kiểm tra trích xuất đặc trưng của cả 3 ảnh
        embeddings = {}
        for ang_name, img in angles.items():
            emb = self.extract_embedding_from_image(img)
            if emb is None:
                return {
                    "success": False,
                    "error": f"Không tìm thấy khuôn mặt rõ nét ở góc '{ang_name}'."
                }
            embeddings[ang_name] = emb

        # 2. Lưu các tệp ảnh với hậu tố tương ứng
        if save_disk:
            safe_name = re.sub(r"[^a-zA-Z0-9_-]", "", student_name.replace(" ", "_"))
            for ang_name, img in angles.items():
                out_fn = f"{student_id}_{safe_name}_{ang_name}.jpg" if safe_name else f"{student_id}_{ang_name}.jpg"
                out_path = os.path.join(self.faces_dir, out_fn)
                cv2.imwrite(out_path, img)

            # 3. Reload toàn bộ để đồng bộ cache .npz
            self.load_known_faces(force_reload=True)

        return {
            "success": True,
            "message": f"Đã đăng ký thành công 3 góc khuôn mặt cho {student_name} ({student_id})",
            "angles": list(angles.keys()),
            "total_faces": len(self.known_ids)
        }

    def detect_locations(self, frame: np.ndarray) -> List[Tuple[int, int, int, int]]:
        if frame is None or frame.size == 0:
            return []
        h, w = frame.shape[:2]
        self._update_detector_size(w, h)
        _, faces = self.detector.detect(frame)
        if faces is None or len(faces) == 0:
            return []

        locations = []
        for face in faces:
            x, y, fw, fh = int(face[0]), int(face[1]), int(face[2]), int(face[3])
            if fw < self.min_face_size or fh < self.min_face_size:
                continue
            top = max(0, y)
            left = max(0, x)
            bottom = min(h, y + fh)
            right = min(w, x + fw)
            locations.append((top, right, bottom, left))
        return locations

    def recognize(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        if frame is None or frame.size == 0:
            return []
        h, w = frame.shape[:2]
        self._update_detector_size(w, h)
        _, faces = self.detector.detect(frame)
        if faces is None or len(faces) == 0:
            return []

        results = []
        embeddings_matrix = np.array(self.known_embeddings) if self.known_embeddings else None

        for face in faces:
            x, y, fw, fh = int(face[0]), int(face[1]), int(face[2]), int(face[3])
            if fw < self.min_face_size or fh < self.min_face_size:
                continue

            top = max(0, y)
            left = max(0, x)
            bottom = min(h, y + fh)
            right = min(w, x + fw)
            loc = (top, right, bottom, left)

            aligned = self.recognizer.alignCrop(frame, face)
            feat = self.recognizer.feature(aligned)
            norm = np.linalg.norm(feat)
            if norm > 1e-6:
                feat = feat / norm
            probe = feat.flatten()

            best_id = None
            best_name = None
            best_sim = 0.0
            status = "stranger"

            if embeddings_matrix is not None and len(embeddings_matrix) > 0:
                sims = np.dot(embeddings_matrix, probe)
                sorted_indices = np.argsort(sims)[::-1]
                top1_idx = sorted_indices[0]
                top1_sim = float(sims[top1_idx])
                top1_id = self.known_ids[top1_idx]

                # Tìm độ tương đồng cao nhất của một NGƯỜI KHÁC (khác student_id)
                top2_sim = 0.0
                has_other_identity = False
                for idx in sorted_indices[1:]:
                    if self.known_ids[idx] != top1_id:
                        top2_sim = float(sims[idx])
                        has_other_identity = True
                        break

                # Đạt ngưỡng cosine_threshold và (không có người khác trong DB hoặc vượt qua khoảng cách margin_threshold)
                if top1_sim >= self.cosine_threshold and (not has_other_identity or (top1_sim - top2_sim >= self.margin_threshold)):
                    best_id = top1_id
                    best_name = self.known_names[top1_idx]
                    best_sim = top1_sim
                    status = "ok"
                else:
                    best_sim = top1_sim

            results.append({
                "student_id": best_id,
                "name": best_name if best_name else "Người lạ",
                "location": loc,
                "confidence": round(best_sim, 4),
                "status": status,
                "landmarks": face[4:14].reshape((5, 2)).tolist() if len(face) >= 14 else []
            })

        return results


class ThreadedCamera:
    """Luồng capture camera độc lập 30 FPS, chống drop lag RTSP."""
    def __init__(self, src=0):
        self.cap = cv2.VideoCapture(src)
        self.lock = threading.Lock()
        self.stopped = False
        self.ret, self.frame = self.cap.read()
        self.thread = threading.Thread(target=self._update, daemon=True)
        self.thread.start()

    def _update(self):
        while not self.stopped:
            ret, frame = self.cap.read()
            with self.lock:
                self.ret = ret
                if ret:
                    self.frame = frame
            time.sleep(0.01)

    def read(self):
        with self.lock:
            return self.ret, (self.frame.copy() if self.frame is not None else None)

    def release(self):
        self.stopped = True
        self.thread.join(timeout=1.0)
        self.cap.release()
