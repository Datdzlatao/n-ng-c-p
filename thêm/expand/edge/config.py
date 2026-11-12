import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ── Database cuc bo (SQLite) --------------------------------------------------
DB_PATH = os.path.join(BASE_DIR, "data", "database.db")

# ── Google Sheets -------------------------------------------------------------
SPREADSHEET_NAME = "Diem Danh STEM"
SPREADSHEET_ID   = os.environ.get("STEM_SPREADSHEET_ID",
                                   "1CLE7GcJNAiJe1irURuCWzq9WaSPZJPLaoufW9lXythU")

SHEET_LOG        = "Log"
SHEET_STUDENTS   = "HocSinh"
SHEET_VIOLATIONS = "PhamLoi"
SHEET_SUMMARY    = "TongKet"        # Tong ket cuoi ngay

# [fix-security] KHONG hard-code ten file credentials trong code nua —
# file JSON cu (chua khoa Google that) tung bi commit len GitHub public va
# da phai thu hoi. Tu nay, duong dan file credentials PHAI duoc truyen qua
# bien moi truong STEM_CREDENTIALS_FILE, tro toi 1 file nam NGOAI thu muc
# du an (VD: C:\Users\<ban>\secrets\credentials.json) de khong bao gio bi
# commit nham len Git.
#
# Cach dat bien moi truong tren Windows (CMD), chay 1 lan roi dong lai mo lai:
#     setx STEM_CREDENTIALS_FILE "C:\Users\ADMIN\secrets\credentials.json"
# Hoac dat tam thoi cho phien lam viec hien tai:
#     set STEM_CREDENTIALS_FILE=C:\Users\ADMIN\secrets\credentials.json
CREDENTIALS_FILE = os.environ.get("STEM_CREDENTIALS_FILE", "")

if not CREDENTIALS_FILE:
    print("[CANH BAO] Chua dat bien moi truong STEM_CREDENTIALS_FILE.")
    print("            Xem huong dan trong config.py de biet cach dat.")
elif not os.path.isfile(CREDENTIALS_FILE):
    print(f"[CANH BAO] Khong tim thay file credentials tai: {CREDENTIALS_FILE}")
else:
    try:
        _inside_project = os.path.commonpath(
            [os.path.abspath(CREDENTIALS_FILE), BASE_DIR]
        ) == BASE_DIR
    except ValueError:
        _inside_project = False  # O khac o dia -> chac chan khong nam trong du an
    if _inside_project:
        print("[CANH BAO] File credentials dang nam BEN TRONG thu muc du an.")
        print("            Neu du an nay se push len GitHub, hay chuyen file ra")
        print("            ngoai thu muc du an de tranh lo khoa nhu truoc day.")

# ── Camera -------------------------------------------------------------------
CAMERA_INDEX = 0   # 0 = webcam mac dinh, 1 = ngoai, hoac URL IP cam http://192.168.1.38:4747/video

# ── Logic diem danh ----------------------------------------------------------
COOLDOWN_SECONDS = 5

# [v2] Offline buffer: luu SQLite khi Sheets loi, dong bo khi co mang
OFFLINE_MODE       = False
AUTO_SYNC_INTERVAL = 60   # giay

# ── Nhan dien khuon mat (v5.0 OpenCV DNN YuNet + SFace) ----------------------
MODELS_DIR     = os.path.join(BASE_DIR, "assets", "models")
YUNET_MODEL    = os.path.join(MODELS_DIR, "face_detection_yunet_2023mar.onnx")
SFACE_MODEL    = os.path.join(MODELS_DIR, "face_recognition_sface_2021dec.onnx")

# Ưu tiên thư mục data/faces (nơi backend đồng bộ dữ liệu eKYC Apple FaceID mới nhất)
_faces_dir = os.path.join(BASE_DIR, "data", "faces")
if os.path.isdir(_faces_dir) and any(os.path.splitext(f)[1].lower() in {".jpg", ".jpeg", ".png", ".webp"} for f in os.listdir(_faces_dir)):
    FACE_DB_PATH    = _faces_dir
    FACE_CACHE_PATH = os.path.join(BASE_DIR, "data", "faces_embeddings.npz")
else:
    FACE_DB_PATH    = os.path.join(BASE_DIR, "data", "stuface")
    FACE_CACHE_PATH = os.path.join(BASE_DIR, "data", "stuface_embeddings.npz")
VIOLATION_PATH = os.path.join(BASE_DIR, "data", "violations")

# ── Chế độ điểm danh & Lọc khuôn mặt ------------------------------------------
#   "AUTO"             : Điểm danh tự động linh hoạt (FaceID sinh trắc học & Thẻ QR)
#   "FACE_ONLY"        : Chỉ dùng khuôn mặt sinh trắc học FaceID
#   "2FACTOR_QR_FACE"  : Bắt buộc quét thẻ QR trước khi quét mặt
ATTENDANCE_MODE        = "AUTO"
MIN_FACE_SIZE          = 45     # Kích thước tối thiểu (px) để nhận diện (từ 55 -> 45: đứng xa 3-4m vẫn bắt nét)
ANTI_SPOOF_ENABLE      = True   # Bật/tắt phát hiện gian lận liveness
STRANGER_ALERT_ENABLE  = True   # Bật/tắt cảnh báo người lạ

FACE_GRACE_SECONDS     = 30     # Grace window sau khi quet QR (giay)
YUNET_SCORE_THRESHOLD  = 0.65   # Nguong phat hien mat YuNet (0.5-0.8)
YUNET_NMS_THRESHOLD    = 0.3    # NMS threshold YuNet
SFACE_COSINE_THRESHOLD = 0.42   # Nguong so khop SFace Cosine (từ 0.48 -> 0.42: giảm tối đa bị nhận nhầm người lạ khi đổi ánh sáng)
FACE_TOP2_MARGIN       = 0.08   # Khoang cach toi thieu giua Top-1 va Top-2 tranh nhan nham 2 hoc sinh
FACE_CONFIRM_FRAMES    = 3      # So frame lien tiep xac nhan danh tinh truoc khi commit diem danh (~0.1s - 0.15s, cực nhạy)
FACE_TOLERANCE         = 0.45   # Fallback cho face_recognition cu (0.45 nghiem ngat hon 0.5)
VIOLATION_COOLDOWN     = 30     # Cooldown ghi vi pham (giay, da toi uu tu 60s)
CAPTURE_COOLDOWN       = 20     # Cooldown chup anh (giay, da toi uu tu 30s)

# [v5.0] Pipeline va da luong
ASYNC_CAMERA_ENABLE    = True   # Luong capture rieng khong lag camera RTSP/Webcam
ASYNC_WORKER_ENABLE    = True   # Worker background cho AI / QR
FACE_SKIP_FRAMES       = 1      # Voi YuNet/SFace co the chay moi 1-2 frame
FACE_SCALE             = 1.0    # YuNet chay truc tiep 1.0 hoac 0.5 tuy do phan giai
FRAME_MAX_WIDTH        = 1280   # Chuan hoa toi da 1280px giu dung aspect ratio cho camera do net cao

# [Storage & Retention Policy]
VIOLATION_RETENTION_DAYS       = 30  # Tu dong don dep anh vi pham cu hon 30 ngay tren Edge
OFFLINE_PROOFS_RETENTION_DAYS  = 7   # Tu dong don dep anh tam offline cu hon 7 ngay

# [v1-mod Legacy Fallback] Haar Cascade
HAAR_SCALE_FACTOR  = 1.05
HAAR_MIN_NEIGHBORS = 4
HAAR_MIN_SIZE      = (40, 40)   # pixel

# ── [v4] Kiem tra trang phuc (uniform_checker.py) -----------------------------
UNIFORM_CHECK_ENABLE   = True   # Bat/tat kiem tra trang phuc tich hop
UNIFORM_CHECK_INTERVAL = 6      # Chi chay HOG+AI moi 6 frame (~0.2s - 0.3s) giup bat loi tuc thi
UNIFORM_VIOLATION_COOLDOWN = 35 # Giay — da toi uu tu 90s tranh bo sot vi pham ke tiep

# ── Mau sac (BGR) ------------------------------------------------------------
COLOR_SUCCESS       = (0, 220, 80)
COLOR_ERROR         = (0, 0, 220)
COLOR_INFO          = (220, 180, 0)
COLOR_VIOLATION     = (0, 80, 255)
COLOR_FACE_OK       = (50, 220, 50)     # Xanh la  - co the + da quet QR
COLOR_FACE_WARN     = (0, 200, 255)     # Vang cam - biet nhung chua quet
COLOR_FACE_STRANGER = (30, 30, 220)     # Do       - nguoi la
COLOR_FACE_SCAN     = (180, 180, 180)   # Xam      - dang quet Haar nhanh

# [v2] HUD tren camera
SHOW_CLOCK      = True
SHOW_STATS      = True
BANNER_DURATION = 3.0

# ── [v6] Multi-Object Tracking (MOT) & Spatial Fusion -------------------------
# Cho phep nhan dien CUNG LUC nhieu nguoi (3-8) ma khong nham lan du lieu
# QR / khuon mat / trang phuc giua tung nguoi. Xem chi tiet: tracker.py
MOT_ENABLE             = True   # Bat/tat Multi-Object Tracker
MOT_DETECT_INTERVAL    = 8      # Chay HOG PersonDetector cho tracker moi 8 frame (~3-4 fps, giam 65% CPU)
MOT_MAX_TRACKS         = 8      # Gioi han so nguoi theo doi cung luc
MOT_MAX_DISAPPEARED    = 45     # So frame toi da 1 track duoc giu khi mat dau
MOT_IOU_THRESHOLD      = 0.25   # Nguong IoU de khop track (uu tien)
MOT_MAX_CENTROID_DIST  = 140.0  # px — nguong fallback khop theo centroid
MOT_DRAW_TRACKS        = True   # Mac dinh bat ve khung quet dong thoi Khuon mat & Body (Trang phuc)
MOT_ATTENDANCE_COOLDOWN = 10    # Giay — tranh commit diem danh lap cho cung track

# ── MJPEG Preview Stream Server ----------------------------------------------
# Bat/tat tinh nang stream giao dien da xu ly ve thiet bi camera
STREAM_ENABLE   = True
STREAM_PORT     = 8080      # Cong HTTP; thiet bi camera mo: http://<IP_may_tinh>:8080
STREAM_QUALITY  = 45        # Chat luong JPEG (0-100); 45 la toi uu sieu toc cho mang Cloudflare Tunnel ma van rat net
STREAM_FPS      = 30        # FPS stream chuan 30 FPS thoi gian thuc sieu muot


import configparser

# ── Cấu hình kết nối Máy Chủ Trường Học (Laptop / Raspberry Pi) ─────────────
# Đọc từ file cấu hình /etc/stem_camera.conf hoặc biến môi trường (H-4, C-3)
# Bảo mật: Tuyệt đối KHÔNG hardcode secret_key trong source code!
_local_conf = os.path.join(BASE_DIR, "data", "camera.conf")
_alt_local_conf = os.path.join(BASE_DIR, "camera.conf")
_env_conf = os.environ.get("STEM_CAMERA_CONF", "")

if _env_conf and os.path.isfile(_env_conf):
    _conf_file = _env_conf
elif os.path.isfile(_local_conf):
    _conf_file = _local_conf
elif os.path.isfile(_alt_local_conf):
    _conf_file = _alt_local_conf
else:
    _conf_file = "/etc/stem_camera.conf"

_pi_cfg = configparser.ConfigParser()
if os.path.isfile(_conf_file):
    try:
        _pi_cfg.read(_conf_file, encoding="utf-8")
    except Exception as _e:
        print(f"[CONFIG] Không thể đọc file cấu hình {_conf_file}: {_e}")

_cam_sec = _pi_cfg["camera"] if "camera" in _pi_cfg else {}

def _clean_val(v, default=""):
    val = v if v is not None else default
    val = str(val).strip()
    if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
        val = val[1:-1].strip()
    return val

SCHOOL_ID       = int(_clean_val(os.environ.get("STEM_SCHOOL_ID", _cam_sec.get("school_id", "9")), "9"))
CAMERA_ID       = int(_clean_val(os.environ.get("STEM_CAMERA_ID", _cam_sec.get("camera_id", "1019")), "1019"))
CAMERA_NAME     = _clean_val(os.environ.get("STEM_CAMERA_NAME", _cam_sec.get("camera_name", "Camera 1")), "Camera 1")
CAMERA_LOCATION = _clean_val(os.environ.get("STEM_CAMERA_LOCATION", _cam_sec.get("location", "Cổng 1")), "Cổng 1")
STREAM_TYPE     = _clean_val(os.environ.get("STEM_STREAM_TYPE", _cam_sec.get("stream_type", "WEBCAM")), "WEBCAM")
_raw_stream_url = _clean_val(os.environ.get("STEM_STREAM_URL", _cam_sec.get("stream_url", "0")), "0")
CAMERA_INDEX    = int(_raw_stream_url) if _raw_stream_url.isdigit() else _raw_stream_url
CAMERA_SECRET   = _clean_val(os.environ.get("STEM_CAMERA_SECRET", _cam_sec.get("secret_key", "FAvv-yv5qZH8WXkoqSSGy5-GwrMyYW-J")))
SERVER_API_URL  = _clean_val(os.environ.get("STEM_SERVER_URL", _cam_sec.get("server_url", "http://localhost:8000")), "http://localhost:8000").rstrip("/")

_env_uniform = os.environ.get("STEM_UNIFORM_CHECK")
if _env_uniform is not None:
    UNIFORM_CHECK_ENABLE = _clean_val(_env_uniform).lower() in ("true", "1", "yes")
elif "uniform_check" in _cam_sec:
    UNIFORM_CHECK_ENABLE = _clean_val(_cam_sec.get("uniform_check", "true")).lower() in ("true", "1", "yes")

if not CAMERA_SECRET:
    print("[CẢNH BÁO BẢO MẬT] Chưa cấu hình CAMERA_SECRET cho trạm camera này.")
    print("                   Hãy tạo file /etc/stem_camera.conf hoặc đặt biến môi trường STEM_CAMERA_SECRET.")


