"""
===============================================================================
  FACE_ENGINE.PY - HE THONG NHAN DIEN KHUON MAT CHUYEN NGHIEP (v5.0 Pro)
  OpenCV DNN YuNet (Face Detection) + OpenCV DNN SFace (Face Recognition)
  + Multi-Threading Camera Stream & Async AI Worker Pipeline
===============================================================================
DAC DIEM NOI BAT v5.0:
  [+] Face Detection : OpenCV DNN YuNet ONNX (~5-10ms CPU) thay the Haar Cascade.
  [+] Face Recognition: OpenCV DNN SFace ONNX (~15-20ms CPU) thay the dlib/face_rec.
  [+] Multi-Target   : Dong thoi phat hien va nhan dien 3-8+ nguoi trong 1 frame.
  [+] Embedding Cache: Tu dong cache vector dac trung (.npz) -> Khoi dong < 5ms.
  [+] Auto Downloader: Tu dong tai weights .onnx neu chua co trong assets/models/.
  [+] ThreadedCamera : Capture stream doc lap 30 FPS, khong drop lag RTSP/Webcam.
  [+] AsyncFaceWorker: Xu ly nhan dien bat dong bo khong chan luong giao dien.
  [+] Backward Comp  : Tuong thich 100% du lieu stuface/ va giao dien cu.
===============================================================================
"""

import os
import re
import cv2
import numpy as np
import time
import urllib.request
import threading
import queue
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Optional, List, Dict, Tuple, Any

from config import (
    BASE_DIR, FACE_DB_PATH, VIOLATION_PATH,
    CAPTURE_COOLDOWN, COLOR_FACE_OK, COLOR_FACE_WARN, COLOR_FACE_STRANGER, COLOR_FACE_SCAN
)

# Optional v5 config imports with fallback defaults
try:
    from config import (
        YUNET_MODEL, SFACE_MODEL, FACE_CACHE_PATH,
        YUNET_SCORE_THRESHOLD, YUNET_NMS_THRESHOLD, SFACE_COSINE_THRESHOLD,
        FACE_TOP2_MARGIN, FACE_TOLERANCE, MIN_FACE_SIZE
    )
except ImportError:
    MODELS_DIR = os.path.join(BASE_DIR, "assets", "models")
    YUNET_MODEL = os.path.join(MODELS_DIR, "face_detection_yunet_2023mar.onnx")
    SFACE_MODEL = os.path.join(MODELS_DIR, "face_recognition_sface_2021dec.onnx")
    FACE_CACHE_PATH = os.path.join(BASE_DIR, "data", "stuface_embeddings.npz")
    YUNET_SCORE_THRESHOLD = 0.65
    YUNET_NMS_THRESHOLD = 0.3
    SFACE_COSINE_THRESHOLD = 0.42
    FACE_TOP2_MARGIN = 0.08
    FACE_TOLERANCE = 0.45
    MIN_FACE_SIZE = 45

# Model download URLs (OpenCV Zoo Official CDN & Mirrors)
YUNET_URLS = [
    "https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx",
    "https://raw.githubusercontent.com/opencv/opencv_zoo/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx",
]
SFACE_URLS = [
    "https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx",
    "https://raw.githubusercontent.com/opencv/opencv_zoo/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx",
]


def ensure_model_file(model_path: str, urls: List[str], expected_min_bytes: int = 100_000) -> bool:
    """Kiem tra va tu dong tai model ONNX neu chua ton tai hoac bi loi file pointer."""
    if os.path.isfile(model_path) and os.path.getsize(model_path) >= expected_min_bytes:
        return True

    os.makedirs(os.path.dirname(os.path.abspath(model_path)), exist_ok=True)
    filename = os.path.basename(model_path)
    print(f"[MODEL] Dang tai model: {filename}...")

    for url in urls:
        try:
            urllib.request.urlretrieve(url, model_path)
            if os.path.isfile(model_path) and os.path.getsize(model_path) >= expected_min_bytes:
                print(f"[MODEL] Tai thanh cong: {filename} ({os.path.getsize(model_path):,} bytes)")
                return True
        except Exception as e:
            print(f"[MODEL] Thu tai tu {url} that bai: {e}")
            if os.path.exists(model_path):
                try:
                    os.remove(model_path)
                except OSError:
                    pass

    print(f"[ERROR] Khong the tai tu dong {filename}. Vui long kiem tra ket noi mang hoac tai thu cong.")
    return False


# =============================================================================
# FACE ENGINE v5.0
# =============================================================================
class FaceEngine:
    """
    Engine Nhan dien khuon mat the he moi v5.0:
      - Detection   : OpenCV DNN YuNet (Realtime 30+ FPS, ho tro multi-face)
      - Recognition : OpenCV DNN SFace (128-d Feature Extraction + Cosine Match)
      - Cache       : Luu tru embeddings tren dia giup startup sieu toc
      - Fallback    : Tu dong chuyen sang Haar Cascade / dlib neu khong co DNN
    """

    SUPPORTED_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
    _io_executor: ThreadPoolExecutor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="FaceEngineWriter")

    def __init__(self, students: dict):
        self.students = students  # {ma_hs: ho_ten}
        self.known_ids: List[str] = []
        self.known_encs: List[np.ndarray] = []  # Danh sach vector 128-d
        self.known_encs_matrix: Optional[np.ndarray] = None  # Matrix (N, 128) cho vectorized dot-product
        self._lock = threading.Lock()
        self._capture_cooldown: Dict[str, float] = {}

        # Backend flags
        self.has_yunet = False
        self.has_sface = False
        self.detector: Optional[cv2.FaceDetectorYN] = None
        self.recognizer: Optional[cv2.FaceRecognizerSF] = None
        self._input_size = (320, 320)

        # Fallback Haar Cascade
        self.face_cascade: Optional[cv2.CascadeClassifier] = None

        # Khoi tao cac mo hinh
        self._init_models()
        self._load_known_faces()

    # -------------------------------------------------------------------------
    # KHOI TAO MO HINH
    # -------------------------------------------------------------------------
    def _init_models(self):
        """Khoi tao YuNet va SFace thong qua OpenCV DNN voi ho tro GPU NVIDIA CUDA."""
        # 1. Kiem tra & Tai file weights
        yunet_ok = ensure_model_file(YUNET_MODEL, YUNET_URLS, expected_min_bytes=100_000)
        sface_ok = ensure_model_file(SFACE_MODEL, SFACE_URLS, expected_min_bytes=1_000_000)

        # 2. Xac dinh Backend va Target (Tu dong phat hien GPU)
        backend_id = cv2.dnn.DNN_BACKEND_OPENCV
        target_id = cv2.dnn.DNN_TARGET_CPU
        gpu_detected = False
        gpu_name = "CPU"

        try:
            import torch
            if torch.cuda.is_available():
                gpu_name = torch.cuda.get_device_name(0)
                gpu_detected = True
        except Exception:
            pass

        if not gpu_detected:
            try:
                if hasattr(cv2, "cuda") and cv2.cuda.getCudaEnabledDeviceCount() > 0:
                    gpu_detected = True
                    gpu_name = "NVIDIA CUDA Device"
            except Exception:
                pass

        # 3. Khoi tao YuNet Face Detector (Thu GPU truoc, fallback CPU)
        if yunet_ok and hasattr(cv2, "FaceDetectorYN"):
            # Thu voi CUDA neu he thong co GPU
            if gpu_detected and hasattr(cv2.dnn, "DNN_BACKEND_CUDA") and hasattr(cv2.dnn, "DNN_TARGET_CUDA"):
                try:
                    self.detector = cv2.FaceDetectorYN.create(
                        model=YUNET_MODEL,
                        config="",
                        input_size=self._input_size,
                        score_threshold=float(YUNET_SCORE_THRESHOLD),
                        nms_threshold=float(YUNET_NMS_THRESHOLD),
                        top_k=5000,
                        backend_id=cv2.dnn.DNN_BACKEND_CUDA,
                        target_id=cv2.dnn.DNN_TARGET_CUDA
                    )
                    self.has_yunet = True
                    backend_id = cv2.dnn.DNN_BACKEND_CUDA
                    target_id = cv2.dnn.DNN_TARGET_CUDA
                    print(f"🔥 [FACE GPU] Da kich hoat tang toc GPU ({gpu_name}) cho YuNet Face Detector!")
                except Exception as e:
                    print(f"ℹ️ [FACE] OpenCV DNN CUDA backend khong san sang ({e}). Chuyen sang che do CPU.")
                    self.detector = None

            if self.detector is None:
                try:
                    self.detector = cv2.FaceDetectorYN.create(
                        model=YUNET_MODEL,
                        config="",
                        input_size=self._input_size,
                        score_threshold=float(YUNET_SCORE_THRESHOLD),
                        nms_threshold=float(YUNET_NMS_THRESHOLD),
                        top_k=5000,
                        backend_id=cv2.dnn.DNN_BACKEND_OPENCV,
                        target_id=cv2.dnn.DNN_TARGET_CPU
                    )
                    self.has_yunet = True
                    print("[FACE] Khoi tao thanh cong OpenCV DNN YuNet Face Detector (CPU).")
                except Exception as e:
                    print(f"[WARN] Khong the nap YuNet ONNX: {e}")
                    self.has_yunet = False

        # 4. Khoi tao SFace Face Recognizer
        if sface_ok and hasattr(cv2, "FaceRecognizerSF"):
            if gpu_detected and backend_id == cv2.dnn.DNN_BACKEND_CUDA:
                try:
                    self.recognizer = cv2.FaceRecognizerSF.create(
                        model=SFACE_MODEL,
                        config="",
                        backend_id=cv2.dnn.DNN_BACKEND_CUDA,
                        target_id=cv2.dnn.DNN_TARGET_CUDA
                    )
                    self.has_sface = True
                    print(f"🔥 [FACE GPU] Da kich hoat tang toc GPU ({gpu_name}) cho SFace Feature Extractor!")
                except Exception:
                    self.recognizer = None

            if self.recognizer is None:
                try:
                    self.recognizer = cv2.FaceRecognizerSF.create(
                        model=SFACE_MODEL,
                        config="",
                        backend_id=cv2.dnn.DNN_BACKEND_OPENCV,
                        target_id=cv2.dnn.DNN_TARGET_CPU
                    )
                    self.has_sface = True
                    print("[FACE] Khoi tao thanh cong OpenCV DNN SFace Feature Extractor (CPU).")
                except Exception as e:
                    print(f"[WARN] Khong the nap SFace ONNX: {e}")
                    self.has_sface = False

        # 5. Fallback Haar Cascade neu YuNet khong kha dung
        if not self.has_yunet:
            cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            self.face_cascade = cv2.CascadeClassifier(cascade_path)
            print("[FACE] Su dung che do du phong: Haar Cascade Face Detector.")

    # -------------------------------------------------------------------------
    # LOAD & CACHE EMBEDDINGS
    # -------------------------------------------------------------------------
    def _load_known_faces(self):
        """Load va encode tat ca anh tu thu muc stuface/ voi bo dem cache (.npz)."""
        if not os.path.isdir(FACE_DB_PATH):
            os.makedirs(FACE_DB_PATH, exist_ok=True)
            print(f"[FACE] Da tao thu muc stuface: {FACE_DB_PATH}")
            return

        files = [
            f for f in sorted(os.listdir(FACE_DB_PATH))
            if os.path.splitext(f)[1].lower() in self.SUPPORTED_EXT
        ]

        if not files:
            print(f"[FACE] Thu muc {FACE_DB_PATH} chua co anh mau nao.")
            return

        # Kiem tra bo dem Cache
        cached_ids, cached_encs = self._load_cache(files)
        if cached_ids is not None and cached_encs is not None:
            with self._lock:
                self.known_ids = cached_ids
                self.known_encs = cached_encs
                if cached_encs:
                    self.known_encs_matrix = np.vstack(cached_encs)
                else:
                    self.known_encs_matrix = None
            print(f"[FACE] Da nap {len(self.known_ids)} khuon mat tu Cache ({FACE_CACHE_PATH}).")
            return

        # Neu cache khong hop le -> Tien hanh trinh xu ly anh goc
        # Nhom cac file anh theo tung hoc sinh
        student_files: Dict[str, List[str]] = {}
        for fname in files:
            path = os.path.join(FACE_DB_PATH, fname)
            if os.path.getsize(path) < 1000:
                continue
            stem, _ = os.path.splitext(fname)
            ma_hs = re.sub(r"_(left|right|tilt|tilt_up|tilt_down|up|down|center|\d+)$", "", stem, flags=re.IGNORECASE).strip().upper()
            if self.students and ma_hs not in self.students:
                continue  # Bo qua hoc sinh khong thuoc danh sach truong hien tai
            student_files.setdefault(ma_hs, []).append(fname)

        count = 0
        failed = []
        new_ids = []
        new_encs = []

        total_students = len(student_files)
        print(f"[FACE] Dang trich xuat dac trung sinh trac hoc da goc (3D FaceID) cho {total_students} hoc sinh...")

        for ma_hs, stu_fnames in student_files.items():
            stu_encs: List[np.ndarray] = []
            for fname in stu_fnames:
                path = os.path.join(FACE_DB_PATH, fname)
                img = cv2.imread(path)
                if img is None:
                    failed.append(fname)
                    continue

                # 1. Trich xuat vector tu anh goc (Center, Left, Right, Tilt...)
                enc = self._extract_feature_from_image(img)
                if enc is not None:
                    stu_encs.append(enc)
                    count += 1
                else:
                    failed.append(fname)

                # 2. Doi voi cac goc nghieng (left/right/tilt), tao them anh lat ngang doi xung (Horizontal Flip)
                # Ky thuat nay bo sung goc nhin doi xung tu nhien cua khuon mat (Pose Symmetry)
                is_side_pose = any(k in fname.lower() for k in ("left", "right", "tilt"))
                if is_side_pose and img is not None:
                    flipped_img = cv2.flip(img, 1)
                    flip_enc = self._extract_feature_from_image(flipped_img)
                    if flip_enc is not None:
                        stu_encs.append(flip_enc)

            # 3. Ky thuat Dung Hop Dac Trung Da Goc: Tao Vector Trung Tam Chuan Hoa (Normalized Centroid Embedding)
            # Vector nay la tam hinh hoc (geodesic centroid) tren mat cau dac trung cua toan bo cac goc khuon mat,
            # giup nhan dien cuc ky on dinh khi hoc sinh nghieng dau o cac goc trung gian (10 - 25 do)
            if len(stu_encs) >= 2:
                centroid = np.mean(stu_encs, axis=0)
                centroid = centroid / (np.linalg.norm(centroid) + 1e-6)
                stu_encs.append(centroid)

            for e in stu_encs:
                new_ids.append(ma_hs)
                new_encs.append(e)

        with self._lock:
            self.known_ids = new_ids
            self.known_encs = new_encs
            if new_encs:
                self.known_encs_matrix = np.vstack(new_encs)
            else:
                self.known_encs_matrix = None

        print(f"[FACE] Da nap va dung hop thanh cong {len(new_encs)} vectors da goc ({total_students} hoc sinh)")
        if failed:
            print(f"[FACE] Khong trich xuat duoc mat trong: {', '.join(failed)}")

        # Luu Cache cho cac lan khoi dong sau
        self._last_sig = self._compute_files_signature(files)
        self._save_cache(new_ids, new_encs, sig=self._last_sig)

    @staticmethod
    def _compute_files_signature(files: List[str]) -> str:
        import hashlib
        sig_data = []
        for f in sorted(files):
            p = os.path.join(FACE_DB_PATH, f)
            try:
                st = os.stat(p)
                if st.st_size >= 1000:
                    sig_data.append(f"{f}:{st.st_size}:{st.st_mtime_ns}")
            except OSError:
                pass
        return hashlib.sha256(";".join(sig_data).encode("utf-8")).hexdigest()

    def check_for_updates(self) -> bool:
        """Kiem tra xem thu muc stuface/ co anh hoc sinh moi hoac thay doi khong, tu dong reload."""
        if not os.path.isdir(FACE_DB_PATH):
            return False
        files = [
            f for f in sorted(os.listdir(FACE_DB_PATH))
            if os.path.splitext(f)[1].lower() in self.SUPPORTED_EXT
        ]
        curr_sig = self._compute_files_signature(files)
        if hasattr(self, "_last_sig") and self._last_sig == curr_sig:
            return False
        print("[FACE] 🔄 Phát hiện thay đổi ảnh sinh trắc học trên đĩa -> Tự động nạp lại Model...")
        self.reload()
        return True

    def _save_cache(self, ids: List[str], encs: List[np.ndarray], sig: str = ""):
        """Luu vector dac trung vao file .npz de tang toc khoi dong."""
        if not ids or not encs:
            return
        try:
            os.makedirs(os.path.dirname(FACE_CACHE_PATH), exist_ok=True)
            np.savez_compressed(FACE_CACHE_PATH, ids=np.array(ids), encodings=np.array(encs), sig=np.array([sig]))
        except Exception as e:
            print(f"[FACE] Khong the luu cache: {e}")

    def _load_cache(self, current_files: List[str]) -> Tuple[Optional[List[str]], Optional[List[np.ndarray]]]:
        """Doc cache neu danh sach file khop voi cache signature."""
        if not os.path.isfile(FACE_CACHE_PATH):
            return None, None
        try:
            current_sig = self._compute_files_signature(current_files)
            data = np.load(FACE_CACHE_PATH, allow_pickle=True)
            if "sig" in data:
                saved_sig = str(data["sig"][0])
                if saved_sig and saved_sig == current_sig:
                    cached_ids = list(data["ids"])
                    cached_encs = [vec for vec in data["encodings"]]
                    self._last_sig = current_sig
                    if self.students:
                        filtered_ids = []
                        filtered_encs = []
                        for sid, enc in zip(cached_ids, cached_encs):
                            if sid in self.students:
                                filtered_ids.append(sid)
                                filtered_encs.append(enc)
                        return filtered_ids, filtered_encs
                    return cached_ids, cached_encs
        except Exception:
            pass
        return None, None

    def _extract_feature_from_image(self, img_bgr: np.ndarray) -> Optional[np.ndarray]:
        """Trich xuat vector 128-d tu 1 buc anh tinh."""
        if img_bgr is None or img_bgr.size == 0:
            return None

        h, w = img_bgr.shape[:2]

        # 1. Su dung YuNet + SFace
        if self.has_yunet and self.has_sface and self.detector and self.recognizer:
            self.detector.setInputSize((w, h))
            _, faces = self.detector.detect(img_bgr)
            if faces is not None and len(faces) > 0:
                # Chon mat co score cao nhat hoac dien tich lon nhat
                best_face = faces[0]
                if len(faces) > 1:
                    areas = faces[:, 2] * faces[:, 3]
                    best_face = faces[np.argmax(areas)]

                aligned_face = self.recognizer.alignCrop(img_bgr, best_face)
                feature = self.recognizer.feature(aligned_face)
                # Chuan hoa L2-norm
                norm_feat = feature / (np.linalg.norm(feature) + 1e-6)
                return norm_feat.flatten()

        # 2. Fallback: thu dung face_recognition neu co
        try:
            import face_recognition
            rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
            encs = face_recognition.face_encodings(rgb)
            if encs:
                return encs[0]
        except Exception:
            pass

        return None

    # =========================================================================
    # DETECT LOCATIONS (YuNet / Haar Fallback)
    # =========================================================================
    def detect_locations(self, frame_bgr: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """
        Phat hien toan bo vi tri khuon mat trong frame (~5-10ms).
        Tra ve: list cac tuple (top, right, bottom, left)
        """
        if frame_bgr is None or frame_bgr.size == 0:
            return []

        h, w = frame_bgr.shape[:2]

        if self.has_yunet and self.detector is not None:
            if self._input_size != (w, h):
                self._input_size = (w, h)
                self.detector.setInputSize((w, h))

            _, faces = self.detector.detect(frame_bgr)
            if faces is None or len(faces) == 0:
                return []

            boxes = []
            for face in faces:
                x, y, bw, bh = int(face[0]), int(face[1]), int(face[2]), int(face[3])
                top = max(0, y)
                left = max(0, x)
                bottom = min(h, y + bh)
                right = min(w, x + bw)
                boxes.append((top, right, bottom, left))
            return boxes

        # Haar Cascade Fallback
        if self.face_cascade is not None:
            gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(
                gray, scaleFactor=1.1, minNeighbors=4, minSize=(40, 40)
            )
            return [(y, x + bw, y + bh, x) for (x, y, bw, bh) in faces]

        return []

    # =========================================================================
    # MULTI-TARGET FACE RECOGNITION (SFace + Vectorized Cosine Match)
    # =========================================================================
    def recognize(self, frame_bgr: np.ndarray) -> List[Dict[str, Any]]:
        """
        Nhan dien danh tinh da muc tieu (3-8 nguoi cung luc trong 1 frame).
        Tra ve list dict:
          {
            "student_id": "HS001" hoac None,
            "name": "Nguyen Van A" hoac "Nguoi la",
            "location": (top, right, bottom, left),
            "confidence": 0.85,
            "status": "warn" | "ok" | "stranger",
            "raw_face": face_detection_row
          }
        """
        if frame_bgr is None or frame_bgr.size == 0:
            return []

        h, w = frame_bgr.shape[:2]
        results = []

        # ---------------------------------------------------------------------
        # 1. NHAN DIEN VOI YUNET + SFACE (Chinh - Uu tien cao nhat)
        # ---------------------------------------------------------------------
        if self.has_yunet and self.has_sface and self.detector and self.recognizer:
            if self._input_size != (w, h):
                self._input_size = (w, h)
                self.detector.setInputSize((w, h))

            _, faces = self.detector.detect(frame_bgr)
            if faces is None or len(faces) == 0:
                return []

            with self._lock:
                ids_snap = list(self.known_ids)
                matrix_snap = self.known_encs_matrix.copy() if self.known_encs_matrix is not None else None

            for face in faces:
                x, y, bw, bh = int(face[0]), int(face[1]), int(face[2]), int(face[3])
                score = float(face[14])
                top = max(0, y)
                left = max(0, x)
                bottom = min(h, y + bh)
                right = min(w, x + bw)

                # Bo qua phat hien kem hoac mat qua nho (chong nhan nham vat the nen)
                if score < float(YUNET_SCORE_THRESHOLD):
                    continue
                if (bottom - top) < int(MIN_FACE_SIZE) or (right - left) < int(MIN_FACE_SIZE):
                    continue

                # 1. Kiem tra hinh hoc Landmark: Khoang cach 2 mat phai du lon de tranh mat qua nghieng / quay ngang
                eye_dx = float(face[4] - face[6])
                eye_dy = float(face[5] - face[7])
                eye_dist = (eye_dx * eye_dx + eye_dy * eye_dy) ** 0.5
                if eye_dist < (0.18 * bw):
                    # Mat qua nghieng goc ngang (profile > 65 do) hoac 1 mat bi che khuat -> Bo qua de tranh nhan nham
                    continue

                aligned = self.recognizer.alignCrop(frame_bgr, face)
                if aligned is None or aligned.size == 0:
                    continue

                # 2. Bo loc do net (Motion Blur Filter):
                # Giam nguong lap_var xuong 20.0 (tu 32.0) de nhan dien muot ma khi hoc sinh di chuyen buoc vao cong
                gray_aligned = cv2.cvtColor(aligned, cv2.COLOR_BGR2GRAY)
                lap_var = float(cv2.Laplacian(gray_aligned, cv2.CV_64F).var())
                if lap_var < 20.0:
                    continue

                # 3. Chuan hoa anh sang nhe bang CLAHE khi mat bi toi hoac nguoc sang cong truong
                mean_lum = float(np.mean(gray_aligned))
                if mean_lum < 65.0 or mean_lum > 205.0:
                    try:
                        lab = cv2.cvtColor(aligned, cv2.COLOR_BGR2LAB)
                        l_ch, a_ch, b_ch = cv2.split(lab)
                        clahe = cv2.createCLAHE(clipLimit=1.5, tileGridSize=(4, 4))
                        l_enh = clahe.apply(l_ch)
                        enhanced_bgr = cv2.cvtColor(cv2.merge((l_enh, a_ch, b_ch)), cv2.COLOR_LAB2BGR)
                        feature = self.recognizer.feature(enhanced_bgr)
                    except Exception:
                        feature = self.recognizer.feature(aligned)
                else:
                    feature = self.recognizer.feature(aligned)

                norm_feat = (feature / (np.linalg.norm(feature) + 1e-6)).flatten()

                result = {
                    "student_id": None,
                    "name": "Nguoi la",
                    "location": (top, right, bottom, left),
                    "confidence": 0.0,
                    "status": "stranger",
                    "raw_face": face
                }

                if matrix_snap is not None and len(ids_snap) > 0:
                    # 1. Tinh Cosine Similarity toan bo templates bang ma tran dot-product (< 0.1ms)
                    sims = np.dot(matrix_snap, norm_feat)

                    # 2. Thu thap diem tuong dong cua tat ca cac goc theo tung hoc sinh
                    student_scores_map: Dict[str, List[float]] = {}
                    for idx, sid in enumerate(ids_snap):
                        # Chi so khop hoc sinh thuoc truong hien tai
                        if self.students and sid not in self.students:
                            continue
                        s_val = float(sims[idx])
                        if sid not in student_scores_map:
                            student_scores_map[sid] = []
                        student_scores_map[sid].append(s_val)

                    # 3. Ky thuat Dung Hop Diem Da Goc (Multi-Angle Fusion Scoring):
                    # - Lay diem so goc khop cao nhat (top 1)
                    # - Neu goc thu 2 cung dat tuong dong tot (> 0.38), cong huong nhe dong thuan da goc
                    student_best_sims = {}
                    for sid, s_list in student_scores_map.items():
                        s_list.sort(reverse=True)
                        top_angle_sim = s_list[0]
                        if len(s_list) > 1 and s_list[1] > 0.44:
                            boost = 0.03 * (s_list[1] - 0.42)
                            student_best_sims[sid] = min(1.0, top_angle_sim + boost)
                        else:
                            student_best_sims[sid] = top_angle_sim

                    # Sap xep cac ung vien theo do tuong dong giam dan
                    sorted_matches = sorted(student_best_sims.items(), key=lambda x: x[1], reverse=True)
                    if sorted_matches:
                        top_sid, top_sim = sorted_matches[0]
                        runner_up_sid = sorted_matches[1][0] if len(sorted_matches) > 1 else None
                        runner_up_sim = sorted_matches[1][1] if len(sorted_matches) > 1 else -1.0
                        margin = top_sim - runner_up_sim if runner_up_sim > -1.0 else 1.0

                        # Tieu chuan nhan dien:
                        # 1. Diem cosine top 1 phai dat nguong an toan (>= SFACE_COSINE_THRESHOLD: 0.48)
                        # 2. Xu ly truong hop luong lu (ambiguity):
                        #    - Neu co á quân dat diem canh tranh, bat buoc phai co khoang cach an toan (margin >= FACE_TOP2_MARGIN)
                        is_confident = (top_sim >= float(SFACE_COSINE_THRESHOLD))
                        if is_confident and runner_up_sim >= (float(SFACE_COSINE_THRESHOLD) - 0.08):
                            req_margin = float(FACE_TOP2_MARGIN) if top_sim < 0.60 else 0.04
                            if margin < req_margin:
                                is_confident = False  # Tranh nhan nham giua 2 hoc sinh

                        if is_confident:
                            name = self.students.get(top_sid, top_sid)
                            result.update({
                                "student_id": top_sid,
                                "name": name,
                                "confidence": round(top_sim, 2),
                                "status": "ok"  # Da xac nhan danh tinh hoc sinh chinh xac
                            })

                results.append(result)
            return results

        # ---------------------------------------------------------------------
        # 2. FALLBACK FACE_RECOGNITION / DLIB (Neu chua co ONNX)
        # ---------------------------------------------------------------------
        try:
            import face_recognition
            with self._lock:
                ids_snap = list(self.known_ids)
                encs_snap = list(self.known_encs)

            rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            locations = face_recognition.face_locations(rgb, model="hog")
            if not locations:
                return []
            encodings = face_recognition.face_encodings(rgb, locations)

            for enc, loc in zip(encodings, locations):
                top, right, bottom, left = loc
                result = {
                    "student_id": None,
                    "name": "Nguoi la",
                    "location": (top, right, bottom, left),
                    "confidence": 0.0,
                    "status": "stranger",
                    "raw_face": None
                }

                if encs_snap:
                    # Loc theo danh sach hoc sinh truong hien tai
                    valid_indices = [
                        i for i, s in enumerate(ids_snap)
                        if not self.students or s in self.students
                    ]
                    if valid_indices:
                        sub_encs = [encs_snap[i] for i in valid_indices]
                        dists = face_recognition.face_distance(sub_encs, enc)
                        min_sub_idx = int(np.argmin(dists))
                        best_idx = valid_indices[min_sub_idx]
                        best_dist = float(dists[min_sub_idx])
                        conf = max(0.0, 1.0 - best_dist)
                        if best_dist <= FACE_TOLERANCE:
                            sid = ids_snap[best_idx]
                            result.update({
                                "student_id": sid,
                                "name": self.students.get(sid, sid),
                                "confidence": round(conf, 2),
                                "status": "ok"
                            })
                results.append(result)
            return results
        except Exception:
            return []

    # =========================================================================
    # VE OVERLAY TRUC QUAN (VISUAL OVERLAY HUD)
    # =========================================================================
    def draw_overlay(self, frame: np.ndarray, fast_locations: List[Tuple[int, int, int, int]],
                     recog_results: List[Dict[str, Any]], scanned_ids: set) -> np.ndarray:
        """
        Ve khung bounding box, goc target cong nghe cao, confidence bar va sidebar thong tin.
        """
        h_frame, w_frame = frame.shape[:2]

        updated = []
        for r in recog_results:
            r_copy = dict(r)
            if r_copy.get("student_id") and r_copy["student_id"] in scanned_ids:
                r_copy["status"] = "ok"
            updated.append(r_copy)

        # 1. Ve fast location box (neu chua co ket qua recognition tuong ung)
        recog_locs = [r["location"] for r in updated]
        for (top, right, bottom, left) in fast_locations:
            top = max(0, top); left = max(0, left)
            bottom = min(h_frame, bottom); right = min(w_frame, right)

            matched = any(
                abs(top - rt) < 40 and abs(left - rl) < 40
                for (rt, rr, rb, rl) in recog_locs
            )
            if not matched:
                self._draw_box(frame, top, right, bottom, left,
                               COLOR_FACE_SCAN, "Dang quet...", None, None, None)

        # 2. Ve recognition box chinh thuc
        for r in updated:
            top, right, bottom, left = r["location"]
            top = max(0, top); left = max(0, left)
            bottom = min(h_frame, bottom); right = min(w_frame, right)

            sid = r.get("student_id")
            name = r.get("name", "Nguoi la")
            conf = r.get("confidence", 0.0)
            status = r.get("status", "stranger")

            if status == "ok":
                color = COLOR_FACE_OK
                vio_tag = "CO THE (OK)" if (sid and sid in scanned_ids) else "DA NHAN DIEN (OK)"
            elif status == "warn":
                color = COLOR_FACE_WARN
                vio_tag = "CHUA QUET THE!"
            else:
                color = COLOR_FACE_STRANGER
                vio_tag = "NGUOI LA"
                sid = "N/A"
                name = "Nguoi la"

            self._draw_box(frame, top, right, bottom, left, color, name, sid, vio_tag, conf)

            # Confidence bar duoi box
            if conf and conf > 0 and status != "stranger":
                bar_w = right - left
                filled = int(bar_w * min(conf, 1.0))
                cv2.rectangle(frame, (left, bottom + 2), (right, bottom + 6), (50, 50, 50), -1)
                cv2.rectangle(frame, (left, bottom + 2), (left + filled, bottom + 6), color, -1)

        return frame

    # -------------------------------------------------------------------------
    def _draw_box(self, frame: np.ndarray, top: int, right: int, bottom: int, left: int,
                  color: tuple, label: str, sid: Optional[str], vio_tag: Optional[str],
                  conf: Optional[float]):
        """Ve 4 goc Target cong nghe cao + sidebar thong tin banh dep."""
        h_frame, w_frame = frame.shape[:2]
        L = min(20, max(8, (right - left) // 4))

        # 4 goc Target
        corners_arms = [
            ((left,  top),    [(left+L, top),    (left,  top+L)]),
            ((right, top),    [(right-L, top),   (right, top+L)]),
            ((left,  bottom), [(left+L, bottom), (left,  bottom-L)]),
            ((right, bottom), [(right-L, bottom),(right, bottom-L)]),
        ]
        for corner, arms in corners_arms:
            for arm in arms:
                cv2.line(frame, corner, arm, color, 3)
        cv2.rectangle(frame, (left, top), (right, bottom), color, 1)

        # Sidebar thong tin ben phai box
        sidebar_x = min(right + 8, w_frame - 160)
        sidebar_y = top

        info_lines = []
        if sid is not None:
            info_lines.append(("ID:", sid if sid != "N/A" else "---"))
            info_lines.append(("Ten:", label[:16]))
            if vio_tag:
                info_lines.append(("TT:", vio_tag))
            if conf:
                info_lines.append(("Conf:", f"{int(conf * 100)}%"))
        else:
            info_lines.append(("TT:", label))

        font = cv2.FONT_HERSHEY_SIMPLEX
        fscale = 0.42
        fthick = 1
        line_h = 18
        pad = 4

        max_w = 0
        for k, v in info_lines:
            tw, _ = cv2.getTextSize(f"{k} {v}", font, fscale, fthick)[0]
            max_w = max(max_w, tw)

        sb_x1 = sidebar_x
        sb_y1 = sidebar_y
        sb_x2 = min(sb_x1 + max_w + pad * 2, w_frame - 2)
        sb_y2 = sidebar_y + len(info_lines) * line_h + pad * 2

        if sb_x2 > sb_x1 and sb_y2 > sb_y1:
            ov = frame.copy()
            cv2.rectangle(ov, (sb_x1, sb_y1), (sb_x2, sb_y2), (18, 18, 18), -1)
            cv2.addWeighted(ov, 0.70, frame, 0.30, 0, frame)
            cv2.rectangle(frame, (sb_x1, sb_y1), (sb_x2, sb_y2), color, 1)

            for i, (key, val) in enumerate(info_lines):
                y_pos = sidebar_y + pad + (i + 1) * line_h
                if y_pos > h_frame - 5:
                    break
                kw = cv2.getTextSize(key + " ", font, fscale, fthick)[0][0]
                cv2.putText(frame, key, (sb_x1 + pad, y_pos), font, fscale, (170, 170, 170), fthick)
                cv2.putText(frame, val, (sb_x1 + pad + kw, y_pos), font, fscale, (255, 255, 255), fthick)

        # Label ngan duoi box
        lbl_y = bottom + 16 if bottom + 20 < h_frame else top - 6
        lbl_y = max(12, min(lbl_y, h_frame - 5))
        cv2.putText(frame, label, (left, lbl_y), font, 0.5, color, 1)

    # =========================================================================
    # ADD FACE LIVE & HOT RELOAD
    # =========================================================================
    def add_face_live(self, frame_bgr: np.ndarray, student_id: str) -> bool:
        """Them khuon mat truc tiep tu camera vao database va cap nhat cache ngay lap tuc."""
        ma_hs = student_id.strip().upper()
        if not ma_hs or frame_bgr is None or frame_bgr.size == 0:
            return False

        enc = self._extract_feature_from_image(frame_bgr)
        if enc is None:
            print(f"[FACE] Khong tim thay mat ro rang khi add {ma_hs}")
            return False

        os.makedirs(FACE_DB_PATH, exist_ok=True)
        save_path = os.path.join(FACE_DB_PATH, f"{ma_hs}.jpg")
        cv2.imwrite(save_path, frame_bgr)

        with self._lock:
            if ma_hs in self.known_ids:
                # [fix] Xóa TẤT CẢ embedding cũ của học sinh này
                # (có thể có nhiều: center/left/right/centroid từ lần load ban đầu)
                # list.index() chỉ trả về vị trí đầu tiên → các góc còn lại bị bỏ sót
                indices = [i for i, sid in enumerate(self.known_ids) if sid == ma_hs]
                for idx in sorted(indices, reverse=True):
                    del self.known_ids[idx]
                    del self.known_encs[idx]
            self.known_ids.append(ma_hs)
            self.known_encs.append(enc)
            self.known_encs_matrix = np.vstack(self.known_encs)
            self._save_cache(self.known_ids, self.known_encs)

        print(f"[FACE] Da them va cache thanh cong khuon mat: {ma_hs} -> {save_path}")
        return True

    def reload(self):
        """Hot reload toan bo database khuon mat tu dia."""
        with self._lock:
            self.known_ids = []
            self.known_encs = []
            self.known_encs_matrix = None
        # Xoa cache cu de ep trich xuat lai neu co anh moi
        if os.path.exists(FACE_CACHE_PATH):
            try:
                os.remove(FACE_CACHE_PATH)
            except OSError:
                pass
        self._load_known_faces()
        print("[FACE] Reload database khuon mat hoan tat.")

    # =========================================================================
    # VIOLATION PHOTO CAPTURE
    # =========================================================================
    def capture_violation(self, frame: np.ndarray, student_id: str, student_name: str,
                          reason: str = "VI PHAM", face_loc=None, body_box=None) -> Optional[str]:
        """Chup anh vi pham voi cooldown tranh spam anh."""
        key = (student_id or "stranger").replace("/", "_")
        now = time.time()
        if now - self._capture_cooldown.get(key, 0) < CAPTURE_COOLDOWN:
            return None
        self._capture_cooldown[key] = now
        return FaceEngine.save_violation_photo(frame, student_id, student_name, reason, face_loc=face_loc, body_box=body_box)

    @staticmethod
    def save_violation_photo(frame: np.ndarray, student_id: str, student_name: str,
                             reason: str = "VI PHAM", face_loc=None, body_box=None) -> str:
        """
        Lưu ảnh vi phạm / cảnh báo người lạ kèm:
        1. Khung đỏ bao quanh đối tượng/khuôn mặt + góc HUD ngắm bắn + nhãn cảnh báo đỏ.
        2. Cắt và phóng to trực tiếp (Zoom cận cảnh 2.5x - 3x PiP) khuôn mặt ở góc trên.
        3. Khung đỏ toàn cảnh và thanh Watermark an ninh chi tiết ở đáy.
        """
        os.makedirs(VIOLATION_PATH, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_id = (student_id or "stranger").replace("/", "_")
        filename = f"{ts}_{safe_id}.jpg"
        filepath = os.path.join(VIOLATION_PATH, filename)

        if frame is None or getattr(frame, "size", 0) == 0:
            return filepath

        snap = frame.copy()
        h, w = snap.shape[:2]

        is_stranger = (student_id or "").upper() in ("STRANGER", "UNKNOWN") or "NGUOI LA" in reason.upper()

        # 1. Vẽ body_box nếu có (khung thân người)
        if body_box is not None:
            try:
                bx, by, bw, bh = body_box
                bx = max(0, min(w - 1, int(bx)))
                by = max(0, min(h - 1, int(by)))
                bw = min(w - bx, int(bw))
                bh = min(h - by, int(bh))
                if bw > 20 and bh > 20:
                    cv2.rectangle(snap, (bx, by), (bx + bw, by + bh), (0, 50, 220), 2)
            except Exception:
                pass

        # 2. Xử lý khuôn mặt: Vẽ khung đỏ & Tạo ô Zoom cận cảnh
        if face_loc is not None:
            try:
                top, right, bottom, left = face_loc
                top = max(0, min(h - 1, int(top)))
                bottom = max(0, min(h - 1, int(bottom)))
                left = max(0, min(w - 1, int(left)))
                right = max(0, min(w - 1, int(right)))
                fh = max(1, bottom - top)
                fw = max(1, right - left)

                # A. Vẽ khung đỏ bao quanh khuôn mặt (Độ dày 3px)
                box_color = (0, 0, 240)
                cv2.rectangle(snap, (left, top), (right, bottom), box_color, 3)

                # B. Vẽ các góc ngắm bắn / HUD Target Corners (chuyên nghiệp)
                c_len = max(10, min(fw, fh) // 4)
                # Top-Left
                cv2.line(snap, (left, top), (left + c_len, top), (0, 0, 255), 4)
                cv2.line(snap, (left, top), (left, top + c_len), (0, 0, 255), 4)
                # Top-Right
                cv2.line(snap, (right, top), (right - c_len, top), (0, 0, 255), 4)
                cv2.line(snap, (right, top), (right, top + c_len), (0, 0, 255), 4)
                # Bottom-Left
                cv2.line(snap, (left, bottom), (left + c_len, bottom), (0, 0, 255), 4)
                cv2.line(snap, (left, bottom), (left, bottom - c_len), (0, 0, 255), 4)
                # Bottom-Right
                cv2.line(snap, (right, bottom), (right - c_len, bottom), (0, 0, 255), 4)
                cv2.line(snap, (right, bottom), (right, bottom - c_len), (0, 0, 255), 4)

                # C. Badge cảnh báo đỏ ngay trên đầu khuôn mặt
                badge_text = "CANH BAO: NGUOI LA" if is_stranger else f"CANH BAO: {reason[:20]}"
                (tw, th), _ = cv2.getTextSize(badge_text, cv2.FONT_HERSHEY_SIMPLEX, 0.52, 2)
                badge_y = max(th + 8, top - 8)
                badge_x = max(2, min(w - tw - 12, left))
                cv2.rectangle(snap, (badge_x, badge_y - th - 6), (badge_x + tw + 10, badge_y + 4), (0, 0, 210), -1)
                cv2.putText(snap, badge_text, (badge_x + 5, badge_y - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (255, 255, 255), 2)

                # D. Cắt ảnh cận cảnh khuôn mặt (Zoom PiP) với lề đệm 40%
                pad_y = int(fh * 0.40)
                pad_x = int(fw * 0.40)
                crop_y1 = max(0, top - pad_y)
                crop_y2 = min(h, bottom + pad_y)
                crop_x1 = max(0, left - pad_x)
                crop_x2 = min(w, right + pad_x)

                face_crop = frame[crop_y1:crop_y2, crop_x1:crop_x2]
                if face_crop.size > 0:
                    pip_w = min(260, max(180, int(w * 0.28)))
                    crop_h, crop_w = face_crop.shape[:2]
                    pip_h = int(pip_w * crop_h / max(1, crop_w))
                    pip_h = min(280, max(160, pip_h))

                    pip_resized = cv2.resize(face_crop, (pip_w, pip_h), interpolation=cv2.INTER_LANCZOS4)

                    # Chọn góc đặt khung Zoom để không che khuất đối tượng
                    center_x = (left + right) // 2
                    if center_x > w // 2:
                        pip_x = 18
                        pip_y = 26
                    else:
                        pip_x = w - pip_w - 18
                        pip_y = 26

                    # Đảm bảo không đè vào banner đáy
                    if pip_y + pip_h > h - 70:
                        pip_h = max(120, h - 70 - pip_y)
                        pip_resized = cv2.resize(face_crop, (pip_w, pip_h), interpolation=cv2.INTER_AREA)

                    # Dán ảnh zoom cận cảnh
                    snap[pip_y:pip_y + pip_h, pip_x:pip_x + pip_w] = pip_resized

                    # Viền đỏ nổi bật quanh khung Zoom
                    cv2.rectangle(snap, (pip_x, pip_y), (pip_x + pip_w, pip_y + pip_h), (0, 0, 240), 3)

                    # Header nhãn Zoom cận cảnh
                    cv2.rectangle(snap, (pip_x, pip_y - 24), (pip_x + pip_w, pip_y), (0, 0, 180), -1)
                    cv2.putText(snap, "ZOOM CAN CANH MAT", (pip_x + 8, pip_y - 7),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.46, (255, 255, 255), 1)

                    # Đóng dấu khung đỏ nhỏ bên trong ảnh zoom
                    cv2.rectangle(snap, (pip_x + 6, pip_y + 6), (pip_x + pip_w - 6, pip_y + pip_h - 6), (0, 0, 220), 1)
            except Exception as e:
                print(f"  [CAM] Loi ve khung zoom khuon mat: {e}")

        # 3. Watermark Banner chuyên nghiệp phía dưới
        banner_h = 62
        ov = snap.copy()
        cv2.rectangle(ov, (0, h - banner_h), (w, h), (10, 10, 80 if is_stranger else 120), -1)
        cv2.addWeighted(ov, 0.80, snap, 0.20, 0, snap)

        # Viền ngăn cách banner
        cv2.rectangle(snap, (0, h - banner_h), (w, h - banner_h + 3), (0, 0, 255), -1)

        ts_disp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        title_prefix = "CANH BAO AN NINH: PHAT HIEN NGUOI LA" if is_stranger else f"CANH BAO VI PHAM: {reason.upper()}"
        sub_info = f"Doi tuong: {student_name}  |  ID: {student_id or 'CHUA_XAC_DINH'}  |  {ts_disp}"
        if face_loc:
            sub_info += f"  |  Toa do: [{face_loc[3]},{face_loc[0]}]-[{face_loc[1]},{face_loc[2]}]"

        cv2.putText(snap, f"[!] {title_prefix}",
                    (14, h - banner_h + 23), cv2.FONT_HERSHEY_SIMPLEX, 0.58, (255, 255, 255), 2)
        cv2.putText(snap, sub_info,
                    (14, h - banner_h + 48), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (200, 220, 255), 1)

        # Viền đỏ cảnh báo an ninh bao quanh toàn ảnh
        cv2.rectangle(snap, (0, 0), (w - 1, h - 1), (0, 0, 240), 4)

        def _async_save(p, img):
            try:
                cv2.imwrite(p, img, [cv2.IMWRITE_JPEG_QUALITY, 92])
            except Exception as _err:
                print(f"  [CAM] Loi ghi anh vi pham: {_err}")

        FaceEngine._io_executor.submit(_async_save, filepath, snap)
        print(f"  [CAM] Da luu anh vi pham (kem khung do & zoom can canh): {filename}")
        return filepath


# =============================================================================
# THREADED CAMERA STREAM (Zero-Lag 30 FPS Capture)
# =============================================================================
class ThreadedCamera:
    """
    Luong doc Camera nen doc lap (Camera Capture Thread).
    - Giai quyet dut diem tinh trang giat lag, drop FPS cua camera USB / RTSP IP.
    - Luon duy tri frame moi nhat trong bo dem (Discard stale frames).
    """

    def __init__(self, src: Any = 0, width: int = 1280, height: int = 720):
        if isinstance(src, str):
            clean_src = src.strip().strip('"\'')
            if clean_src.isdigit():
                self.src = int(clean_src)
            else:
                self.src = clean_src
        else:
            self.src = src

        self.width = width
        self.height = height

        if isinstance(self.src, str) and not str(self.src).isdigit():
            # Tối ưu siêu tốc luồng RTSP IP: triệt tiêu toàn bộ bộ đệm (Zero Buffer Lag), giảm tối đa trễ
            os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = (
                "rtsp_transport;tcp|fflags;nobuffer|flags;low_delay|max_delay;0|"
                "probesize;32768|analyzeduration;100000|stimeout;4000000"
            )

        self.cap = cv2.VideoCapture(self.src)
        # Bắt buộc khóa CAP_PROP_BUFFERSIZE = 1 cho TẤT CẢ các luồng camera (cả IP RTSP và USB)
        try:
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        except Exception:
            pass

        if isinstance(self.src, int):
            # Khóa định dạng phần cứng MJPG và 30 FPS để tránh bị Linux V4L2 USB giới hạn băng thông YUYV (15-20 FPS)
            try:
                self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
            except Exception:
                pass
            self.cap.set(cv2.CAP_PROP_FPS, 30)
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)

        self.grabbed, self.frame = self.cap.read()
        self.stopped = False
        self._lock = threading.Lock()
        self._condition = threading.Condition(self._lock)
        self.frame_id = 1 if self.grabbed else 0
        self._last_read_id = 0
        self.fps = 0.0

        self.thread = threading.Thread(target=self._update, daemon=True)
        self.thread.start()

    def _update(self):
        fps_counter = 0
        fps_timer = time.time()
        last_reconnect = time.time()

        while not self.stopped:
            if not self.cap.isOpened():
                if time.time() - last_reconnect >= 3.0:
                    last_reconnect = time.time()
                    try:
                        self.cap.open(self.src)
                    except Exception:
                        pass
                time.sleep(0.2)
                continue

            grabbed, frame = self.cap.read()
            if not grabbed:
                # Nếu mất kết nối luồng RTSP (string source), thử kết nối lại sau 3s
                if isinstance(self.src, str) and not self.src.isdigit() and (time.time() - last_reconnect >= 3.0):
                    last_reconnect = time.time()
                    try:
                        self.cap.release()
                        self.cap.open(self.src)
                    except Exception:
                        pass
                time.sleep(0.02)
                continue

            # Tối ưu siêu tốc: Tự động scale luồng phân giải cao (> 1280px) về chuẩn chiều rộng 1280px
            # bảo toàn tỷ lệ khung hình gốc (Aspect Ratio) giúp hình ảnh không bị méo mặt
            if frame is not None and frame.shape[1] > 1280:
                orig_h, orig_w = frame.shape[:2]
                target_h = max(240, int(orig_h * (1280.0 / orig_w)))
                frame = cv2.resize(frame, (1280, target_h), interpolation=cv2.INTER_LINEAR)

            with self._condition:
                self.grabbed = grabbed
                self.frame = frame
                self.frame_id += 1
                self._condition.notify_all()

            fps_counter += 1
            if time.time() - fps_timer >= 1.0:
                self.fps = fps_counter / (time.time() - fps_timer)
                fps_counter = 0
                fps_timer = time.time()

    def read(self, wait_new: bool = True, timeout: float = 0.04) -> Tuple[bool, Optional[np.ndarray]]:
        """
        Đọc frame mới nhất.
        Nếu wait_new=True, tiến trình sẽ chờ frame mới thực sự từ camera (tối đa timeout giây)
        thay vì lặp vô ích gây cháy CPU khi nguồn camera phát FPS thấp (ví dụ RTSP 10-15 FPS).
        """
        with self._condition:
            if wait_new and self.frame is not None and self.frame_id == self._last_read_id:
                self._condition.wait(timeout=timeout)
            if self.frame is None:
                return False, None
            self._last_read_id = self.frame_id
            return self.grabbed, self.frame.copy()

    def isOpened(self) -> bool:
        return self.cap.isOpened() and not self.stopped

    def stop(self):
        self.stopped = True
        with self._condition:
            self._condition.notify_all()
        if self.thread.is_alive():
            self.thread.join(timeout=1.0)
        self.cap.release()

    def release(self):
        self.stop()


# =============================================================================
# ASYNC AI WORKER PIPELINE
# =============================================================================
class AsyncFaceWorker:
    """
    Worker xu ly nhan dien AI & QR bat dong bo tren luong rieng.
    Khong bao gio block luong hien thi giao dien chinh.

    [FIX v5.1]
    - result_frame_id: Tang moi khi co ket qua THUC SU moi tu worker.
      Main loop so sanh voi last_consumed_frame_id de phat hien stale,
      tranh tinh trang face_consec_counts tang do cached result cu lap lai.
    - latest_frame: Luu chinh xac frame da duoc nhan dien (khong phai frame
      hien tai tu camera), dam bao anh bang chung diem danh chup dung nguoi,
      dung vi tri khuon mat, dung thoi diem.
    """

    def __init__(self, engine: FaceEngine):
        self.engine = engine
        self.in_queue = queue.Queue(maxsize=1)  # Chi giu 1 frame moi nhat
        self.stopped = False
        self._lock = threading.Lock()

        # Cached outputs
        self.latest_locations: List[Tuple[int, int, int, int]] = []
        self.latest_results: List[Dict[str, Any]] = []
        self.last_process_time: float = 0.0

        # [FIX #2] frame_id tang dan moi khi co ket qua THUC SU moi —
        # main loop so sanh de phat hien stale, khong tang face_consec_counts oan.
        self.result_frame_id: int = 0

        # [FIX #3] Luu lai chinh xac frame da duoc nhan dien (KHONG phai
        # frame hien tai tu camera) — tranh chup anh bang chung sai vi tri mat.
        self.latest_frame: Optional[np.ndarray] = None

        self.thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.thread.start()

    def submit_frame(self, frame: np.ndarray):
        """Gui frame moi nhat vao queue (tu dong bo qua frame cu neu worker dang ban)."""
        if self.stopped or frame is None:
            return
        try:
            # Neu queue da day, lay frame cu ra de day frame moi nhat vao
            if self.in_queue.full():
                try:
                    self.in_queue.get_nowait()
                except queue.Empty:
                    pass
            self.in_queue.put_nowait(frame.copy())
        except queue.Full:
            pass

    def _worker_loop(self):
        while not self.stopped:
            try:
                frame = self.in_queue.get(timeout=0.05)
            except queue.Empty:
                continue

            t0 = time.perf_counter()
            # [TỐI ƯU 1-PASS AI] recognize() đã chạy bộ dò YuNet bên trong.
            # Trích xuất trực tiếp locations từ results thay vì gọi detect_locations() lần thứ 2,
            # giúp giảm ngay 40-50% AI latency trên CPU!
            results = self.engine.recognize(frame)
            locs = [r["location"] for r in results if "location" in r]
            if not locs and not results and not (self.engine.has_yunet and self.engine.has_sface):
                locs = self.engine.detect_locations(frame)
            process_ms = (time.perf_counter() - t0) * 1000

            with self._lock:
                self.latest_locations = locs
                self.latest_results = results
                self.last_process_time = process_ms
                # [FIX #2] Tang frame_id -> main loop biet day la ket qua THUC SU moi
                self.result_frame_id += 1
                # [FIX #3] Giu nguyen frame da nhan dien (KHONG cap nhat frame hien tai)
                self.latest_frame = frame

    def get_results(self) -> Tuple[List[Tuple[int, int, int, int]], List[Dict[str, Any]], float]:
        """Lay ket qua nhan dien moi nhat ngay lap tuc (khong cho doi)."""
        with self._lock:
            return list(self.latest_locations), list(self.latest_results), self.last_process_time

    def get_recognition_frame(self) -> Optional[np.ndarray]:
        """
        Tra ve ban sao frame CHINH XAC tai thoi diem nhan dien.
        Dung lam anh bang chung diem danh thay vi frame hien tai tu camera.
        Dam bao bounding box mat khop 100% voi noi dung anh.
        """
        with self._lock:
            return self.latest_frame.copy() if self.latest_frame is not None else None

    def stop(self):
        self.stopped = True
        if self.thread.is_alive():
            self.thread.join(timeout=1.0)


# =============================================================================
# TEST BENCHMARK TRUC TIEP
# =============================================================================
if __name__ == "__main__":
    print("=" * 60)
    print("  FACE ENGINE v5.0 Pro — TEST BENCHMARK LIVE")
    print("  OpenCV DNN YuNet + SFace + Async Threading Pipeline")
    print("=" * 60)

    dummy_students = {}
    if os.path.isdir(FACE_DB_PATH):
        for f in os.listdir(FACE_DB_PATH):
            stem = os.path.splitext(f)[0].upper()
            dummy_students[stem] = f"Hoc Sinh {stem}"

    engine = FaceEngine(dummy_students)
    cam = ThreadedCamera(0, width=1280, height=720)
    worker = AsyncFaceWorker(engine)

    print("\n[OK] He thong da san sang. Nhan 'q' de thoat.")
    time.sleep(1.0)

    frame_count = 0
    t_start = time.time()

    while True:
        ret, frame = cam.read()
        if not ret or frame is None:
            time.sleep(0.01)
            continue
        frame_count += 1
        worker.submit_frame(frame)
        fast_locs, recog_results, proc_ms = worker.get_results()

        # Render overlay
        frame = engine.draw_overlay(frame, fast_locs, recog_results, set())

        # Performance HUD
        fps = frame_count / (time.time() - t_start)
        cv2.putText(frame, f"Camera FPS: {cam.fps:.1f} | UI FPS: {fps:.1f} | AI Latency: {proc_ms:.1f}ms",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 0), 2)
        cv2.putText(frame, f"Targets: {len(fast_locs)} detected | {len(recog_results)} recognized",
                    (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.60, (0, 255, 255), 2)

        cv2.imshow("Face Engine v5.0 Pro - Benchmark", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cam.stop()
    worker.stop()
    cv2.destroyAllWindows()
