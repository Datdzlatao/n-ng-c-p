"""
=============================================================================
  INIT_DB.PY — KHỞI TẠO VÀ MIGRATE DATABASE ĐA TRƯỜNG HỌC (STEM v5.2)
=============================================================================
Đặc tả nâng cấp v5.2 Real-Life Auth & Verified Accounts:
  1. Xác thực người dùng thực tế: Đăng ký, Đăng nhập, Mật khẩu băm an toàn PBKDF2-SHA256.
  2. Hệ thống Tài khoản Xác Minh (Verified Account):
     - VERIFIED (Tích Xanh ✅): Đã đối chiếu danh bộ nhà trường, khớp SĐT/CCCD hoặc GVCN duyệt.
     - PENDING_REVIEW (Chờ duyệt ⏳): Đã nộp giấy tờ CCCD/Thẻ HS, chờ GVCN/BGH đối soát.
     - UNVERIFIED (Chưa xác minh ⚠️): Mới đăng ký, chưa xác thực OTP hoặc danh tính.
     - REJECTED (Bị từ chối ❌).
  3. Bảng mã OTP xác thực: verification_otps (Hỗ trợ SMS/Zalo ZNS/Email).
  4. Kiến trúc Multi-Tenant & RBAC 5 vai trò.

Cách dùng:
    python init_db.py
    python init_db.py --reset
    python init_db.py --summary
=============================================================================
"""

import sqlite3
import os
import csv
import argparse
import hashlib
import secrets
from datetime import datetime

from config import DB_PATH

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "students.csv")
STUFACE_DIR = os.path.join(BASE_DIR, "data", "stuface")

os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
os.makedirs(STUFACE_DIR, exist_ok=True)


def hash_password(password: str, salt: str = None) -> tuple[str, str]:
    """Băm mật khẩu an toàn chuẩn PBKDF2-HMAC-SHA256 (NIST standard)."""
    if not salt:
        salt = secrets.token_hex(16)
    pwd_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000).hex()
    return pwd_hash, salt


# =============================================================================
# SCHEMA DEFINITIONS (v5.2 Real-Life Multi-Tenant Auth)
# =============================================================================
SCHEMA_SQL = """
-- 1. Bảng Trường Học (Multi-Tenant)
CREATE TABLE IF NOT EXISTS schools (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL,
    school_code   TEXT UNIQUE NOT NULL,
    logo_url      TEXT,
    academic_year TEXT DEFAULT '2025-2026',
    rules_config  TEXT,
    form_config   TEXT,
    owner_id      INTEGER,
    created_at    TEXT DEFAULT (datetime('now','localtime'))
);

-- 2. Bảng Người Dùng & Phân Quyền Xác Minh Thực Tế (Users & Verified Account)
CREATE TABLE IF NOT EXISTS users (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    school_id            INTEGER DEFAULT 1,
    username             TEXT UNIQUE NOT NULL,
    email                TEXT UNIQUE,
    phone                TEXT,
    password_hash        TEXT NOT NULL,
    salt                 TEXT NOT NULL,
    full_name            TEXT NOT NULL,
    role                 TEXT NOT NULL CHECK(role IN ('HEADMASTER', 'VICE_HEADMASTER', 'TEACHER', 'INSPECTOR', 'STUDENT', 'PARENT')),
    verified_status      TEXT DEFAULT 'UNVERIFIED' CHECK(verified_status IN ('UNVERIFIED', 'PENDING_REVIEW', 'VERIFIED', 'REJECTED')),
    verification_method  TEXT DEFAULT 'AUTO_MATCH' CHECK(verification_method IN ('AUTO_MATCH', 'OTP_PHONE', 'OTP_EMAIL', 'TEACHER_APPROVED', 'ID_CARD', 'HEADMASTER_INVITE')),
    verification_doc_url TEXT,
    verification_note    TEXT,
    verified_at          TEXT,
    student_code         TEXT,
    class_name           TEXT,
    status               TEXT DEFAULT 'ACTIVE' CHECK(status IN ('ACTIVE', 'BANNED', 'SUSPENDED')),
    avatar_url           TEXT,
    created_at           TEXT DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (school_id) REFERENCES schools(id)
);

-- 3. Bảng Mã Xác Thực OTP (SMS / Zalo ZNS / Email)
CREATE TABLE IF NOT EXISTS verification_otps (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER,
    target      TEXT NOT NULL,
    otp_code    TEXT NOT NULL,
    otp_type    TEXT DEFAULT 'PHONE_REGISTER' CHECK(otp_type IN ('PHONE_REGISTER', 'EMAIL_REGISTER', 'PARENT_LINK', 'RESET_PASSWORD')),
    expires_at  TEXT NOT NULL,
    is_used     INTEGER DEFAULT 0,
    created_at  TEXT DEFAULT (datetime('now','localtime'))
);

-- 4. Bảng Lớp Học (Classes)
CREATE TABLE IF NOT EXISTS classes (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    school_id    INTEGER DEFAULT 1,
    name         TEXT UNIQUE NOT NULL,
    grade        TEXT,
    teacher_id   INTEGER,
    teacher_name TEXT,
    invite_code  TEXT,
    qr_code_url  TEXT,
    created_at   TEXT DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (school_id) REFERENCES schools(id)
);

-- 5. Bảng Học Sinh (HocSinh / Students)
CREATE TABLE IF NOT EXISTS HocSinh (
    ma_hs          TEXT PRIMARY KEY,
    ho_ten         TEXT NOT NULL,
    lop            TEXT,
    school_id      INTEGER DEFAULT 1,
    ngay_sinh      TEXT,
    sdt_phu_huynh  TEXT,
    ten_phu_huynh  TEXT,
    photo_url      TEXT,
    status         TEXT DEFAULT 'APPROVED' CHECK(status IN ('PENDING', 'APPROVED', 'REJECTED')),
    face_embedding TEXT,
    qr_token       TEXT,
    current_points INTEGER DEFAULT 100,
    is_active      INTEGER DEFAULT 1,
    tao_luc        TEXT DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (school_id) REFERENCES schools(id)
);

-- 6. Bảng Liên Kết Phụ Huynh - Học Sinh (Parent Links)
CREATE TABLE IF NOT EXISTS parent_student_links (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    school_id       INTEGER DEFAULT 1,
    parent_user_id  INTEGER,
    parent_name     TEXT NOT NULL,
    parent_phone    TEXT NOT NULL,
    student_id      TEXT NOT NULL,
    relation_name   TEXT DEFAULT 'Phụ huynh',
    verified_status TEXT DEFAULT 'VERIFIED' CHECK(verified_status IN ('PENDING', 'VERIFIED', 'REJECTED')),
    verified_at     TEXT DEFAULT (datetime('now','localtime')),
    created_at      TEXT DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (student_id) REFERENCES HocSinh(ma_hs)
);

-- 7. Bảng Quản Lý Trạm Camera AI (Camera Stations - Chỉ Hiệu Trưởng quản lý)
CREATE TABLE IF NOT EXISTS camera_stations (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    school_id   INTEGER DEFAULT 1,
    name        TEXT NOT NULL,
    location    TEXT NOT NULL,
    stream_url  TEXT,
    secret_key  TEXT UNIQUE,
    status      TEXT DEFAULT 'ONLINE' CHECK(status IN ('ONLINE', 'OFFLINE', 'MAINTENANCE')),
    last_ping   TEXT DEFAULT (datetime('now','localtime')),
    is_active   INTEGER DEFAULT 1,
    created_at  TEXT DEFAULT (datetime('now','localtime'))
);

-- 8. Bảng Nhật Ký Điểm Danh Cục Bộ (offline_log / DiemDanh)
CREATE TABLE IF NOT EXISTS offline_log (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    school_id         INTEGER DEFAULT 1,
    camera_station_id INTEGER DEFAULT 1,
    thoi_gian         TEXT NOT NULL,
    ma_hs             TEXT NOT NULL,
    ho_ten            TEXT,
    lop               TEXT,
    trang_thai        TEXT DEFAULT 'Vao',
    attendance_status TEXT DEFAULT 'ON_TIME' CHECK(attendance_status IN ('ON_TIME', 'LATE', 'ABSENT')),
    uniform_status    TEXT DEFAULT 'VALID',
    proof_image_url   TEXT,
    synced            INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS DiemDanh (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    thoi_gian   TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    ma_hs       TEXT NOT NULL,
    ho_ten      TEXT,
    trang_thai  TEXT CHECK(trang_thai IN ('Vao','Ra')),
    da_sync     INTEGER DEFAULT 1,
    FOREIGN KEY (ma_hs) REFERENCES HocSinh(ma_hs)
);

-- 9. Bảng Vi Phạm (offline_violation)
CREATE TABLE IF NOT EXISTS offline_violation (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    school_id   INTEGER DEFAULT 1,
    thoi_gian   TEXT NOT NULL,
    ma_hs       TEXT NOT NULL,
    ho_ten      TEXT,
    lop         TEXT,
    mo_ta       TEXT,
    ten_file    TEXT,
    duong_dan   TEXT,
    synced      INTEGER DEFAULT 0
);

-- 10. Bảng Khiếu Nại 2 Cấp (Disputes: Cấp 1 GVCN -> Cấp 2 Giám Thị)
CREATE TABLE IF NOT EXISTS disputes (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    school_id         INTEGER DEFAULT 1,
    attendance_log_id INTEGER,
    ma_hs             TEXT NOT NULL,
    ho_ten            TEXT,
    lop               TEXT,
    level             TEXT DEFAULT 'LEVEL_1_TEACHER' CHECK(level IN ('LEVEL_1_TEACHER', 'LEVEL_2_INSPECTOR')),
    reason            TEXT NOT NULL,
    proof_image_url   TEXT,
    student_evidence  TEXT,
    status            TEXT DEFAULT 'PENDING' CHECK(status IN ('PENDING', 'APPROVED', 'REJECTED', 'ESCALATED')),
    resolution_note   TEXT,
    resolver_id       INTEGER,
    resolver_name     TEXT,
    points_reimbursed INTEGER DEFAULT 0,
    created_at        TEXT DEFAULT (datetime('now','localtime')),
    resolved_at       TEXT
);

-- 11. Bảng Đơn Xin Nghỉ Phép (Leave Requests - Chỉ GVCN duyệt)
CREATE TABLE IF NOT EXISTS leave_requests (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    school_id    INTEGER DEFAULT 1,
    ma_hs        TEXT NOT NULL,
    ho_ten       TEXT,
    lop          TEXT,
    parent_name  TEXT,
    parent_phone TEXT,
    start_date   TEXT NOT NULL,
    end_date     TEXT,
    reason       TEXT NOT NULL,
    status       TEXT DEFAULT 'PENDING' CHECK(status IN ('PENDING', 'APPROVED', 'REJECTED')),
    approved_by  TEXT,
    note         TEXT,
    created_at   TEXT DEFAULT (datetime('now','localtime'))
);

-- 12. Bảng Chấm Điểm Thi Đua Các Lớp (Class Discipline Scores - Giám Thị chấm, Hiệu Trưởng duyệt)
CREATE TABLE IF NOT EXISTS class_discipline_scores (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    school_id           INTEGER DEFAULT 1,
    class_name          TEXT NOT NULL,
    week_number         INTEGER NOT NULL,
    month_number        INTEGER NOT NULL,
    year                INTEGER DEFAULT 2026,
    attendance_score    REAL DEFAULT 100.0,
    uniform_score       REAL DEFAULT 100.0,
    discipline_score    REAL DEFAULT 100.0,
    bonus_points        REAL DEFAULT 0.0,
    total_points        REAL DEFAULT 100.0,
    rank                INTEGER,
    inspector_notes     TEXT,
    inspector_name      TEXT DEFAULT 'Giám Thị',
    inspector_status    TEXT DEFAULT 'SUBMITTED' CHECK(inspector_status IN ('DRAFT', 'SUBMITTED')),
    headmaster_approval TEXT DEFAULT 'PENDING' CHECK(headmaster_approval IN ('PENDING', 'APPROVED', 'REJECTED')),
    approved_by         TEXT,
    approved_at         TEXT,
    created_at          TEXT DEFAULT (datetime('now','localtime'))
);

-- 13. Bảng Tổng Kết Ngày (TongKet)
CREATE TABLE IF NOT EXISTS TongKet (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    school_id    INTEGER DEFAULT 1,
    ngay         TEXT UNIQUE,
    tong_hs      INTEGER DEFAULT 0,
    co_mat       INTEGER DEFAULT 0,
    vang_mat     INTEGER DEFAULT 0,
    vi_pham      INTEGER DEFAULT 0,
    gio_bat_dau  TEXT,
    gio_ket_thuc TEXT,
    ghi_chu      TEXT
);
"""

INDEX_SQL = [
    "CREATE INDEX IF NOT EXISTS idx_usr_user        ON users(username)",
    "CREATE INDEX IF NOT EXISTS idx_usr_role        ON users(role)",
    "CREATE INDEX IF NOT EXISTS idx_usr_ver         ON users(verified_status)",
    "CREATE INDEX IF NOT EXISTS idx_hs_school       ON HocSinh(school_id)",
    "CREATE INDEX IF NOT EXISTS idx_hs_lop          ON HocSinh(lop)",
    "CREATE INDEX IF NOT EXISTS idx_off_ma_hs       ON offline_log(ma_hs)",
    "CREATE INDEX IF NOT EXISTS idx_off_thoi_gian   ON offline_log(thoi_gian)",
    "CREATE INDEX IF NOT EXISTS idx_disputes_level  ON disputes(level, status)",
    "CREATE INDEX IF NOT EXISTS idx_leave_status    ON leave_requests(status)",
    "CREATE INDEX IF NOT EXISTS idx_scores_week     ON class_discipline_scores(class_name, week_number, year)",
]


# =============================================================================
# DATABASE INITIALIZATION & MIGRATION
# =============================================================================
def init_database(conn: sqlite3.Connection):
    cur = conn.cursor()
    cur.executescript(SCHEMA_SQL)
    conn.commit()
    migrate_schema(conn)
    for sql in INDEX_SQL:
        try:
            cur.execute(sql)
        except Exception:
            pass
    conn.commit()
    print("[OK] Đã tạo và kiểm tra cấu trúc Database Multi-Tenant Auth v5.2.")


def migrate_schema(conn: sqlite3.Connection):
    """Bổ sung các cột mới vào các bảng cũ an toàn."""
    cur = conn.cursor()

    # Migrate users table
    cols_usr = [r[1] for r in cur.execute("PRAGMA table_info(users)").fetchall()]
    needed_usr = [
        ("username", "TEXT"),
        ("password_hash", "TEXT"),
        ("salt", "TEXT"),
        ("verified_status", "TEXT DEFAULT 'UNVERIFIED'"),
        ("verification_method", "TEXT DEFAULT 'AUTO_MATCH'"),
        ("verification_doc_url", "TEXT"),
        ("verification_note", "TEXT"),
        ("verified_at", "TEXT"),
        ("student_code", "TEXT"),
        ("class_name", "TEXT"),
    ]
    for col, col_type in needed_usr:
        if col not in cols_usr:
            try:
                cur.execute(f"ALTER TABLE users ADD COLUMN {col} {col_type}")
                print(f"  [MIGRATE] Đã thêm cột '{col}' vào users.")
            except Exception:
                pass

    conn.commit()


# =============================================================================
# SEED DEFAULT SAMPLE DATA
# =============================================================================
def seed_default_data(conn: sqlite3.Connection):
    """Nạp dữ liệu mẫu ban đầu kèm mật khẩu đã hash và trạng thái Verified."""
    cur = conn.cursor()

    # 1. Trường học mẫu
    cur.execute("SELECT COUNT(*) FROM schools")
    if cur.fetchone()[0] == 0:
        cur.execute(
            """
            INSERT INTO schools (id, name, school_code, logo_url, academic_year, rules_config)
            VALUES (1, 'Trường THPT Chuyên STEM Pro', 'STEM_HIGH_01', '/static/icons/icon-192.png', '2025-2026', 
                    '{"on_time_limit": "07:00", "strict_uniform_days": ["Monday", "Friday"]}')
            """
        )
        print("  [SEED] Đã tạo trường học: THPT Chuyên STEM Pro.")

    # 2. Người dùng mẫu (5 vai trò, có password hash & Verified badge)
    pwd_default = "123456"
    pwd_hash, salt = hash_password(pwd_default)
    now_str = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    users = [
        (1, 'hieutruong', 'hieutruong@stem.edu.vn', '0901234567', pwd_hash, salt, 'Thầy Nguyễn Văn Hiệu (Hiệu Trưởng)', 'HEADMASTER', 'VERIFIED', 'HEADMASTER_INVITE', now_str, None, None),
        (1, 'phohieutruong', 'phohieutruong@stem.edu.vn', '0901234568', pwd_hash, salt, 'Cô Trần Thị Thu (Phó Hiệu Trưởng)', 'VICE_HEADMASTER', 'VERIFIED', 'HEADMASTER_INVITE', now_str, None, None),
        (1, 'giamthi', 'giamthi@stem.edu.vn', '0902345678', pwd_hash, salt, 'Thầy Lê Quốc Dũng (Trưởng Ban Giám Thị)', 'INSPECTOR', 'VERIFIED', 'HEADMASTER_INVITE', now_str, None, None),
        (1, 'gvcn10a1', 'gvcn10a1@stem.edu.vn', '0903456789', pwd_hash, salt, 'Cô Nguyễn Mai Hương (GVCN 10A1)', 'TEACHER', 'VERIFIED', 'HEADMASTER_INVITE', now_str, None, '10A1'),
        (1, 'gvcn10a2', 'gvcn10a2@stem.edu.vn', '0903456790', pwd_hash, salt, 'Thầy Trần Văn Bình (GVCN 10A2)', 'TEACHER', 'VERIFIED', 'HEADMASTER_INVITE', now_str, None, '10A2'),
        (1, 'hocsinh01', 'an.nm@stem.edu.vn', '0904567890', pwd_hash, salt, 'Nguyễn Minh An (Học Sinh 10A1)', 'STUDENT', 'VERIFIED', 'AUTO_MATCH', now_str, 'HS001', '10A1'),
        (1, 'phuhuynh01', 'phuhuynh.an@gmail.com', '0912345678', pwd_hash, salt, 'Nguyễn Văn Ba (Phụ Huynh em An)', 'PARENT', 'VERIFIED', 'AUTO_MATCH', now_str, 'HS001', '10A1'),
        # Tài khoản chờ duyệt (PENDING_REVIEW)
        (1, 'hocsinh_moi', 'chi.vm@stem.edu.vn', '0904567899', pwd_hash, salt, 'Vũ Mai Chi (Học Sinh Mới)', 'STUDENT', 'PENDING_REVIEW', 'ID_CARD', None, 'HS011', '10A1'),
        # Tài khoản chưa xác minh (UNVERIFIED)
        (1, 'phuhuynh_moi', 'phuhuynh.tung@gmail.com', '0912345699', pwd_hash, salt, 'Phan Văn Hải (Phụ Huynh Mới)', 'PARENT', 'UNVERIFIED', 'OTP_PHONE', None, 'HS012', '10A1'),
    ]
    for s_id, uname, email, phone, phash, psalt, fname, role, v_stat, v_meth, v_at, s_code, c_name in users:
        # Check if exists by username or email
        cur.execute("SELECT id FROM users WHERE username = ? OR email = ?", (uname, email))
        row = cur.fetchone()
        if row:
            cur.execute(
                """
                UPDATE users 
                SET username = ?, email = ?, phone = ?, password_hash = ?, salt = ?, full_name = ?, role = ?, 
                    verified_status = ?, verification_method = ?, verified_at = ?, student_code = ?, class_name = ?
                WHERE id = ?
                """,
                (uname, email, phone, phash, psalt, fname, role, v_stat, v_meth, v_at, s_code, c_name, row[0])
            )
        else:
            cur.execute(
                """
                INSERT INTO users 
                (school_id, username, email, phone, password_hash, salt, full_name, role, verified_status, verification_method, verified_at, student_code, class_name)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (s_id, uname, email, phone, phash, psalt, fname, role, v_stat, v_meth, v_at, s_code, c_name)
            )
    print(f"  [SEED] Đã đồng bộ {len(users)} tài khoản người dùng thực tế kèm mật khẩu '123456' & Verified Status.")

    # 3. Lớp học mẫu
    cur.execute("SELECT COUNT(*) FROM classes")
    if cur.fetchone()[0] == 0:
        classes = [
            (1, '10A1', '10', 'Cô Nguyễn Mai Hương', 'INV-10A1'),
            (1, '10A2', '10', 'Thầy Trần Văn Bình', 'INV-10A2'),
            (1, '10A3', '10', 'Cô Lê Thu Hà', 'INV-10A3'),
            (1, '11A1', '11', 'Thầy Phạm Đức Minh', 'INV-11A1'),
            (1, '11A2', '11', 'Cô Hoàng Lan Anh', 'INV-11A2'),
            (1, '12A1', '12', 'Thầy Vũ Quốc Hùng', 'INV-12A1'),
        ]
        for s_id, name, grade, t_name, inv in classes:
            cur.execute(
                "INSERT INTO classes (school_id, name, grade, teacher_name, invite_code) VALUES (?, ?, ?, ?, ?)",
                (s_id, name, grade, t_name, inv)
            )
        print(f"  [SEED] Đã tạo {len(classes)} lớp học mẫu.")

    # 4. Trạm Camera AI mẫu
    cur.execute("SELECT COUNT(*) FROM camera_stations")
    if cur.fetchone()[0] == 0:
        stations = [
            (1, 'Trạm 01 - Cổng Chính', 'Cổng chính (Trục đường chính)', 'http://192.168.1.101:8080/stream', 'STATION_KEY_GATE01', 'ONLINE'),
            (1, 'Trạm 02 - Cổng Phụ Tây', 'Cổng phụ (Bãi đỗ xe giáo viên)', 'http://192.168.1.102:8080/stream', 'STATION_KEY_GATE02', 'ONLINE'),
            (1, 'Trạm 03 - Ký Túc Xá', 'Khu KTX Học Sinh Nội Trú', 'http://192.168.1.103:8080/stream', 'STATION_KEY_KTX01', 'ONLINE'),
            (1, 'Trạm 04 - Căng Tin & Sân Thể Thao', 'Nhà ăn tập thể trường', 'http://192.168.1.104:8080/stream', 'STATION_KEY_CANTIN', 'ONLINE'),
        ]
        for s_id, name, loc, url, key, st in stations:
            cur.execute(
                "INSERT INTO camera_stations (school_id, name, location, stream_url, secret_key, status) VALUES (?, ?, ?, ?, ?, ?)",
                (s_id, name, loc, url, key, st)
            )
        print(f"  [SEED] Đã tạo {len(stations)} trạm Camera AI.")

    # 5. Học sinh mẫu
    cur.execute("SELECT COUNT(*) FROM HocSinh")
    if cur.fetchone()[0] == 0:
        default_students = [
            ('HS001', 'Nguyễn Minh An', '10A1', '15/05/2010', '0912345678', 'Nguyễn Văn Ba', '/stuface/HS011.jpg', 'APPROVED', 100),
            ('HS002', 'Trần Bảo Ngọc', '10A1', '20/08/2010', '0912345679', 'Trần Văn Long', '/stuface/HS012.jpg', 'APPROVED', 98),
            ('HS003', 'Lê Hoàng Nam', '10A1', '10/02/2010', '0912345680', 'Lê Đình Toàn', None, 'APPROVED', 95),
            ('HS004', 'Phạm Quỳnh Anh', '10A1', '14/11/2010', '0912345681', 'Phạm Văn Hùng', None, 'APPROVED', 100),
            ('HS005', 'Vũ Đức Duy', '10A2', '03/07/2010', '0912345682', 'Vũ Quốc Tuấn', None, 'APPROVED', 92),
            ('HS006', 'Hoàng Thùy Linh', '10A2', '18/09/2010', '0912345683', 'Hoàng Văn Sơn', None, 'APPROVED', 100),
            ('HS007', 'Đặng Quốc Bảo', '10A2', '25/12/2010', '0912345684', 'Đặng Minh Trí', None, 'APPROVED', 88),
            ('HS008', 'Bùi Mai Phương', '11A1', '08/04/2009', '0912345685', 'Bùi Văn Hậu', None, 'APPROVED', 100),
            ('HS009', 'Ngô Kiến Huy', '11A1', '19/10/2009', '0912345686', 'Ngô Văn Thành', None, 'APPROVED', 96),
            ('HS010', 'Đỗ Gia Huy', '12A1', '05/01/2008', '0912345687', 'Đỗ Đức Thắng', None, 'APPROVED', 100),
            ('HS011', 'Vũ Mai Chi', '10A1', '12/03/2010', '0912345688', 'Vũ Văn Khang', None, 'PENDING', 100),
            ('HS012', 'Phan Thanh Tùng', '10A1', '22/06/2010', '0912345689', 'Phan Văn Hải', None, 'PENDING', 100),
        ]
        for ma, ten, lop, dob, sdt, ten_ph, photo, st, pts in default_students:
            cur.execute(
                """
                INSERT OR REPLACE INTO HocSinh 
                (ma_hs, ho_ten, lop, school_id, ngay_sinh, sdt_phu_huynh, ten_phu_huynh, photo_url, status, current_points)
                VALUES (?, ?, ?, 1, ?, ?, ?, ?, ?, ?)
                """,
                (ma, ten, lop, dob, sdt, ten_ph, photo, st, pts)
            )
        print(f"  [SEED] Đã tạo {len(default_students)} học sinh mẫu.")

    # 6. Đơn xin nghỉ phép mẫu
    cur.execute("SELECT COUNT(*) FROM leave_requests")
    if cur.fetchone()[0] == 0:
        today_str = datetime.now().strftime("%d/%m/%Y")
        leave_samples = [
            (1, 'HS003', 'Lê Hoàng Nam', '10A1', 'Lê Đình Toàn', '0912345680', today_str, today_str, 'Cháu bị sốt nhẹ xin nghỉ 1 ngày ở nhà theo dõi.', 'PENDING', None),
            (1, 'HS007', 'Đặng Quốc Bảo', '10A2', 'Đặng Minh Trí', '0912345684', today_str, today_str, 'Gia đình có việc hiếu ở quê xin phép nghỉ.', 'APPROVED', 'Thầy Trần Văn Bình'),
        ]
        for s_id, ma, ten, lop, ph_name, ph_phone, s_date, e_date, reason, st, app in leave_samples:
            cur.execute(
                """
                INSERT INTO leave_requests 
                (school_id, ma_hs, ho_ten, lop, parent_name, parent_phone, start_date, end_date, reason, status, approved_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (s_id, ma, ten, lop, ph_name, ph_phone, s_date, e_date, reason, st, app)
            )
        print("  [SEED] Đã tạo đơn xin nghỉ phép mẫu.")

    # 7. Khiếu nại nề nếp 2 cấp mẫu
    cur.execute("SELECT COUNT(*) FROM disputes")
    if cur.fetchone()[0] == 0:
        disputes_samples = [
            (1, 101, 'HS001', 'Nguyễn Minh An', '10A1', 'LEVEL_1_TEACHER', 
             'Em có mặc áo khoác đồng phục mùa đông của trường nhưng AI nhận diện nhầm là sai đồng phục.', 
             '/violations/sample_uniform_01.jpg', 'PENDING', None, None, 0),
            (1, 102, 'HS005', 'Vũ Đức Duy', '10A2', 'LEVEL_2_INSPECTOR', 
             'Học sinh khiếu nại trừ điểm đi trễ do xe buýt trường đón muộn. GVCN chuyển Ban Giám Thị xác minh.', 
             '/violations/sample_late_01.jpg', 'PENDING', None, None, 0),
        ]
        for s_id, log_id, ma, ten, lop, lvl, reason, proof, st, note, r_name, pts in disputes_samples:
            cur.execute(
                """
                INSERT INTO disputes 
                (school_id, attendance_log_id, ma_hs, ho_ten, lop, level, reason, proof_image_url, status, resolution_note, resolver_name, points_reimbursed)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (s_id, log_id, ma, ten, lop, lvl, reason, proof, st, note, r_name, pts)
            )
        print("  [SEED] Đã tạo dữ liệu khiếu nại nề nếp 2 cấp mẫu.")

    # 8. Bảng chấm điểm thi đua các lớp mẫu
    cur.execute("SELECT COUNT(*) FROM class_discipline_scores")
    if cur.fetchone()[0] == 0:
        current_week = 35
        current_month = 8
        scores_samples = [
            (1, '10A1', current_week, current_month, 2026, 98.5, 96.0, 99.0, 5.0, 99.6, 1, 'Lớp chuyên cần tốt, phong trào sôi nổi.', 'SUBMITTED', 'PENDING'),
            (1, '10A2', current_week, current_month, 2026, 94.0, 91.5, 95.0, 0.0, 93.5, 4, 'Còn 2 học sinh đi trễ thứ 3.', 'SUBMITTED', 'PENDING'),
            (1, '10A3', current_week, current_month, 2026, 96.0, 95.0, 97.0, 2.0, 96.5, 3, 'Nề nếp ổn định.', 'SUBMITTED', 'PENDING'),
            (1, '11A1', current_week, current_month, 2026, 99.0, 98.0, 98.5, 3.0, 99.1, 2, 'Xuất sắc không có vi phạm.', 'SUBMITTED', 'PENDING'),
            (1, '11A2', current_week, current_month, 2026, 92.0, 90.0, 91.0, 0.0, 91.0, 5, 'Cần chấn chỉnh đồng phục thứ 2.', 'SUBMITTED', 'PENDING'),
        ]
        for s_id, c_name, wk, mo, yr, a_sc, u_sc, d_sc, bon, tot, rk, notes, i_st, hm_st in scores_samples:
            cur.execute(
                """
                INSERT INTO class_discipline_scores 
                (school_id, class_name, week_number, month_number, year, attendance_score, uniform_score, discipline_score, bonus_points, total_points, rank, inspector_notes, inspector_status, headmaster_approval)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (s_id, c_name, wk, mo, yr, a_sc, u_sc, d_sc, bon, tot, rk, notes, i_st, hm_st)
            )
        print("  [SEED] Đã tạo bảng chấm điểm thi đua mẫu cho các lớp.")

    conn.commit()


def show_summary(conn: sqlite3.Connection):
    cur = conn.cursor()
    n_sch  = cur.execute("SELECT COUNT(*) FROM schools").fetchone()[0]
    n_usr  = cur.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    n_v_ok = cur.execute("SELECT COUNT(*) FROM users WHERE verified_status='VERIFIED'").fetchone()[0]
    n_v_pe = cur.execute("SELECT COUNT(*) FROM users WHERE verified_status='PENDING_REVIEW'").fetchone()[0]
    n_cls  = cur.execute("SELECT COUNT(*) FROM classes").fetchone()[0]
    n_cam  = cur.execute("SELECT COUNT(*) FROM camera_stations").fetchone()[0]
    n_hs   = cur.execute("SELECT COUNT(*) FROM HocSinh").fetchone()[0]
    n_disp = cur.execute("SELECT COUNT(*) FROM disputes WHERE status='PENDING'").fetchone()[0]
    n_lev  = cur.execute("SELECT COUNT(*) FROM leave_requests WHERE status='PENDING'").fetchone()[0]

    print("\n" + "=" * 65)
    print("  📊 BÁO CÁO DATABASE AUTH & VERIFIED ACCOUNTS — STEM v5.2")
    print("=" * 65)
    print(f"  • Trường học (Schools)       : {n_sch}")
    print(f"  • Tổng Người Dùng (Users)    : {n_usr}")
    print(f"    - Đã xác minh (VERIFIED ✅) : {n_v_ok}")
    print(f"    - Chờ duyệt (PENDING ⏳)   : {n_v_pe}")
    print(f"  • Lớp học (Classes)          : {n_cls}")
    print(f"  • Trạm Camera AI (Stations)  : {n_cam}")
    print(f"  • Tổng Học Sinh              : {n_hs}")
    print(f"  • Khiếu Nại Chờ Duyệt (C1/C2): {n_disp}")
    print(f"  • Đơn Nghỉ Phép Chờ Duyệt    : {n_lev}")
    print(f"  • File Cơ Sở Dữ Liệu         : {DB_PATH}")
    print("=" * 65)
    print("  🔑 Tài khoản mẫu: hieutruong, giamthi, gvcn10a1, hocsinh01, phuhuynh01")
    print("  🔑 Mật khẩu mặc định: 123456")
    print("=" * 65)


def reset_database():
    confirm = input(
        "\n[!!] CẢNH BÁO: Bạn chuẩn bị xóa TOÀN BỘ dữ liệu database!\n"
        "     Nhập 'XAC NHAN' để tiếp tục: "
    ).strip()
    if confirm != "XAC NHAN":
        print("[OK] Hủy bỏ thao tác xóa database.")
        return False
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print(f"[OK] Đã xóa file: {DB_PATH}")
    return True


# =============================================================================
# MAIN ENTRYPOINT
# =============================================================================
def main():
    parser = argparse.ArgumentParser(description="Khởi tạo database hệ thống Điểm danh STEM v5.2")
    parser.add_argument("--reset",   action="store_true", help="Xóa sạch và tạo lại toàn bộ database")
    parser.add_argument("--summary", action="store_true", help="Chỉ in báo cáo thống kê hiện tại")
    args = parser.parse_args()

    print("=" * 65)
    print("  KHỞI TẠO DATABASE REAL-LIFE AUTH & VERIFIED ACCOUNTS — STEM v5.2")
    print("=" * 65)

    if args.reset:
        if not reset_database():
            return

    conn = sqlite3.connect(DB_PATH)
    try:
        init_database(conn)
        migrate_schema(conn)
        seed_default_data(conn)
        show_summary(conn)
    finally:
        conn.close()

    print("\n  [Hoàn Tất] Database sẵn sàng phục vụ đăng ký, đăng nhập và xác minh tài khoản!\n")


if __name__ == "__main__":
    main()
