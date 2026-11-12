"""
app/database.py — SQLite database setup, full multi-tenant schema & seed data.
Schema design: every table carries school_id for tenant isolation.
"""
import sqlite3, json, logging, secrets
from pathlib import Path
from app.config import DB_PATH
from app.core.security import generate_salt, hash_password

log = logging.getLogger("stem.db")


def get_db():
    """
    Return a SQLite connection (row_factory=sqlite3.Row).

    SQLite tuning tạm thời để giảm lỗi 'database is locked' khi nhiều
    camera station đồng thời gửi attendance sync (giờ cao điểm):
      - WAL mode: cho phép nhiều readers song song với 1 writer.
      - busy_timeout=5000ms: chờ tối đa 5 giây nếu DB đang bị lock.

    TODO [ARCHITECTURAL DEBT]: Migrate sang PostgreSQL cho production
    đa trường lớn. Set: DATABASE_URL=postgresql+asyncpg://user:pass@host/db
    """
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), timeout=5.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")       # Multi-reader / single-writer mode
    conn.execute("PRAGMA busy_timeout=5000")      # Tránh lỗi "database is locked"
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA synchronous=NORMAL")      # Tốc độ tốt hơn với WAL mode
    return conn



def init_db():
    """Create all tables and seed initial data."""
    conn = get_db()
    c = conn.cursor()

    # ─── PLATFORM LEVEL ──────────────────────────────────────────────────────

    c.executescript("""
    -- Platform super-admins (manage all schools)
    CREATE TABLE IF NOT EXISTS platform_admins (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        email       TEXT UNIQUE NOT NULL,
        full_name   TEXT NOT NULL,
        password_hash TEXT NOT NULL,
        salt        TEXT NOT NULL,
        is_active   INTEGER DEFAULT 1,
        created_at  TEXT DEFAULT (datetime('now','localtime'))
    );

    -- Schools (each = one independent "server")
    CREATE TABLE IF NOT EXISTS schools (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        school_code     TEXT UNIQUE NOT NULL,   -- slug: thpt-nguyen-hue
        name            TEXT NOT NULL,
        short_name      TEXT,
        logo_url        TEXT,
        address         TEXT,
        province_city   TEXT,
        academic_year   TEXT DEFAULT '2025-2026',
        owner_user_id   INTEGER,                -- Headmaster who created this school
        status          TEXT DEFAULT 'ACTIVE',  -- ACTIVE | SUSPENDED | PENDING
        -- Configurable school rules (JSON)
        rules_config    TEXT DEFAULT '{}',
        -- Configurable join form fields (JSON)
        form_config     TEXT DEFAULT '{}',
        -- Role invite codes
        teacher_invite_code   TEXT,
        inspector_invite_code TEXT,
        bgh_invite_code       TEXT,
        created_at  TEXT DEFAULT (datetime('now','localtime')),
        updated_at  TEXT DEFAULT (datetime('now','localtime'))
    );

    -- ─── AUTH & USERS ─────────────────────────────────────────────────────

    CREATE TABLE IF NOT EXISTS users (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        school_id       INTEGER REFERENCES schools(id),
        username        TEXT NOT NULL UNIQUE,
        email           TEXT,
        phone           TEXT,
        password_hash   TEXT NOT NULL,
        salt            TEXT NOT NULL,
        full_name       TEXT NOT NULL,
        dob             TEXT,
        gender          TEXT,
        avatar_url      TEXT,
        role            TEXT NOT NULL,   -- HEADMASTER|TEACHER|INSPECTOR|STUDENT|PARENT
        status          TEXT DEFAULT 'ACTIVE',  -- ACTIVE|SUSPENDED|PENDING_APPROVAL
        -- Verified badge
        verified_status       TEXT DEFAULT 'UNVERIFIED',
        verification_method   TEXT,
        verification_doc_url  TEXT,
        verification_note     TEXT,
        verified_at           TEXT,
        -- Student / User extras
        user_code       TEXT,
        student_code    TEXT,
        class_name      TEXT,
        grade_level     INTEGER,
        -- Timestamps
        last_login_at   TEXT,
        created_at      TEXT DEFAULT (datetime('now','localtime')),
        updated_at      TEXT DEFAULT (datetime('now','localtime')),
        UNIQUE(school_id, phone)
    );

    CREATE TABLE IF NOT EXISTS verification_otps (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id     INTEGER REFERENCES users(id),
        school_id   INTEGER NOT NULL REFERENCES schools(id),
        target      TEXT NOT NULL,   -- phone or email
        otp_code    TEXT NOT NULL,
        otp_type    TEXT NOT NULL,   -- PHONE_REGISTER | EMAIL_REGISTER
        expires_at  TEXT NOT NULL,
        used_at     TEXT,
        created_at  TEXT DEFAULT (datetime('now','localtime'))
    );

    -- ─── SCHOOL STRUCTURE ─────────────────────────────────────────────────

    CREATE TABLE IF NOT EXISTS classes (
        id                    INTEGER PRIMARY KEY AUTOINCREMENT,
        school_id             INTEGER NOT NULL REFERENCES schools(id),
        name                  TEXT NOT NULL,           -- "10A1"
        grade_level           INTEGER,                 -- 10, 11, 12
        homeroom_teacher_id   INTEGER REFERENCES users(id),
        academic_year         TEXT DEFAULT '2025-2026',
        invite_code           TEXT UNIQUE,
        qr_code_url           TEXT,
        is_active             INTEGER DEFAULT 1,
        created_at            TEXT DEFAULT (datetime('now','localtime'))
    );

    CREATE TABLE IF NOT EXISTS students (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id             INTEGER REFERENCES users(id),
        class_id            INTEGER REFERENCES classes(id),
        school_id           INTEGER NOT NULL REFERENCES schools(id),
        student_code        TEXT NOT NULL,
        full_name           TEXT NOT NULL,
        dob                 TEXT,
        gender              TEXT,
        parent_phone        TEXT,
        parent_name         TEXT,
        parent_relation     TEXT DEFAULT 'Phụ huynh',
        face_embedding_blob BLOB,          -- binary: 128D float array
        face_photo_url      TEXT,          -- thumbnail for display
        face_approved       TEXT DEFAULT 'PENDING',  -- PENDING|APPROVED|REJECTED
        face_approved_by    INTEGER REFERENCES users(id),
        qr_token            TEXT UNIQUE,
        parent_invite_code  TEXT UNIQUE,
        current_points      INTEGER DEFAULT 100,
        is_active           INTEGER DEFAULT 1,
        created_at          TEXT DEFAULT (datetime('now','localtime')),
        updated_at          TEXT DEFAULT (datetime('now','localtime')),
        UNIQUE(school_id, student_code)
    );

    CREATE TABLE IF NOT EXISTS parent_student_links (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        parent_user_id  INTEGER NOT NULL REFERENCES users(id),
        student_id      INTEGER NOT NULL REFERENCES students(id),
        school_id       INTEGER NOT NULL REFERENCES schools(id),
        relation_name   TEXT DEFAULT 'Phụ huynh',
        verified_status TEXT DEFAULT 'PENDING',   -- PENDING | VERIFIED
        verified_at     TEXT,
        created_at      TEXT DEFAULT (datetime('now','localtime')),
        UNIQUE(parent_user_id, student_id)
    );

    -- ─── DEVICES ──────────────────────────────────────────────────────────

    CREATE TABLE IF NOT EXISTS camera_stations (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        school_id       INTEGER NOT NULL REFERENCES schools(id),
        camera_num      INTEGER DEFAULT 1,
        name            TEXT NOT NULL,
        location        TEXT,
        stream_type     TEXT DEFAULT 'WEBCAM',    -- WEBCAM | RTSP | HTTP_CAM
        stream_url      TEXT DEFAULT '0',         -- index (0,1) or rtsp:// or http://
        secret_key      TEXT UNIQUE NOT NULL,
        status          TEXT DEFAULT 'OFFLINE',   -- ONLINE | OFFLINE | ERROR
        uniform_check   INTEGER DEFAULT 1,        -- 1 = Bật nhận diện trang phục | 0 = Tắt
        occlusion_check INTEGER DEFAULT 1,        -- 1 = Bật cảnh báo che khuất ống kính (Tamper Detection >= 60%) | 0 = Tắt
        direction       TEXT DEFAULT 'IN',        -- IN | OUT | BIDIRECTIONAL
        public_stream_url TEXT,                   -- HTTPS public stream link via Tailscale Funnel
        tailscale_enabled INTEGER DEFAULT 1,      -- 1 = Tự động xuất bản Tailscale HTTPS
        last_ping_at    TEXT,
        created_at      TEXT DEFAULT (datetime('now','localtime'))
    );

    -- ─── ATTENDANCE ───────────────────────────────────────────────────────

    CREATE TABLE IF NOT EXISTS attendance_logs (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id          INTEGER NOT NULL REFERENCES students(id),
        camera_station_id   INTEGER REFERENCES camera_stations(id),
        school_id           INTEGER NOT NULL REFERENCES schools(id),
        timestamp           TEXT NOT NULL,
        date_only           TEXT NOT NULL,     -- "2025-09-01" for daily grouping
        direction           TEXT DEFAULT 'IN', -- IN (Check-in / Vào) | OUT (Check-out / Ra)
        check_type          TEXT DEFAULT 'FACE_AI',   -- FACE_AI|QR_SCAN|MANUAL
        status              TEXT DEFAULT 'ON_TIME',   -- ON_TIME|LATE|ABSENT|EXCUSED
        uniform_status      TEXT DEFAULT 'UNKNOWN',   -- OK|VIOLATION|UNKNOWN
        spoof_status        TEXT DEFAULT 'SKIPPED',   -- PASSED|FAILED|SKIPPED
        confidence_score    REAL DEFAULT 0.0,
        proof_image_url     TEXT,
        violation_details   TEXT,
        is_disputed         INTEGER DEFAULT 0,
        created_at          TEXT DEFAULT (datetime('now','localtime'))
    );

    -- ─── DISPUTES ─────────────────────────────────────────────────────────

    CREATE TABLE IF NOT EXISTS disputes (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        attendance_log_id   INTEGER REFERENCES attendance_logs(id),
        student_id          INTEGER NOT NULL REFERENCES students(id),
        school_id           INTEGER NOT NULL REFERENCES schools(id),
        level               TEXT DEFAULT 'LEVEL_1_TEACHER',   -- LEVEL_1_TEACHER|LEVEL_2_INSPECTOR
        reason              TEXT NOT NULL,
        proof_image_url     TEXT,
        status              TEXT DEFAULT 'PENDING',   -- PENDING|APPROVED|REJECTED|ESCALATED
        resolver_id         INTEGER REFERENCES users(id),
        resolution_note     TEXT,
        created_at          TEXT DEFAULT (datetime('now','localtime')),
        updated_at          TEXT DEFAULT (datetime('now','localtime'))
    );

    -- ─── LEAVE REQUESTS ───────────────────────────────────────────────────

    CREATE TABLE IF NOT EXISTS leave_requests (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id      INTEGER NOT NULL REFERENCES students(id),
        parent_user_id  INTEGER REFERENCES users(id),
        school_id       INTEGER NOT NULL REFERENCES schools(id),
        start_date      TEXT NOT NULL,
        end_date        TEXT NOT NULL,
        reason          TEXT NOT NULL,
        status          TEXT DEFAULT 'PENDING',   -- PENDING|APPROVED|REJECTED
        approved_by     INTEGER REFERENCES users(id),
        approved_at     TEXT,
        created_at      TEXT DEFAULT (datetime('now','localtime'))
    );

    -- ─── DISCIPLINE SCORES ────────────────────────────────────────────────

    CREATE TABLE IF NOT EXISTS discipline_scores (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        class_id            INTEGER NOT NULL REFERENCES classes(id),
        school_id           INTEGER NOT NULL REFERENCES schools(id),
        week_number         INTEGER NOT NULL,
        year                INTEGER NOT NULL,
        attendance_score    REAL DEFAULT 0,
        uniform_score       REAL DEFAULT 0,
        discipline_score    REAL DEFAULT 0,
        bonus_points        REAL DEFAULT 0,
        total_points        REAL DEFAULT 0,
        inspector_id        INTEGER REFERENCES users(id),
        inspector_notes     TEXT,
        headmaster_approval TEXT DEFAULT 'PENDING',   -- PENDING|APPROVED
        approved_at         TEXT,
        created_at          TEXT DEFAULT (datetime('now','localtime'))
    );

    -- ─── SECURITY: REFRESH TOKENS & BLACKLIST ─────────────────────────────
    CREATE TABLE IF NOT EXISTS user_refresh_tokens (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id     INTEGER NOT NULL,
        jti         TEXT UNIQUE NOT NULL,
        expires_at  TEXT NOT NULL,
        revoked_at  TEXT,
        device_info TEXT,
        created_at  TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS token_blacklist (
        jti        TEXT PRIMARY KEY,
        expires_at TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    -- ─── BIOMETRIC COMPLIANCE (Nghị định 13/2023/NĐ-CP) ──────────────────────
    CREATE TABLE IF NOT EXISTS biometric_consent_records (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id      INTEGER NOT NULL REFERENCES students(id),
        school_id       INTEGER NOT NULL REFERENCES schools(id),
        parent_user_id  INTEGER,
        consent_status  TEXT NOT NULL DEFAULT 'CONSENTED',  -- CONSENTED | REVOKED
        consent_version TEXT DEFAULT '1.0',
        purpose         TEXT DEFAULT 'FACE_ATTENDANCE',
        signed_at       TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        revoked_at      TEXT,
        ip_address      TEXT,
        device_info     TEXT,
        user_agent      TEXT,
        created_at      TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS student_face_samples (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id    INTEGER NOT NULL REFERENCES students(id),
        school_id     INTEGER NOT NULL REFERENCES schools(id),
        sample_index  INTEGER NOT NULL,
        angle_type    TEXT DEFAULT 'CENTER',
        yaw_angle     REAL,
        pitch_angle   REAL,
        image_url     TEXT NOT NULL,
        quality_score REAL DEFAULT 1.0,
        created_at    TEXT DEFAULT CURRENT_TIMESTAMP
    );

    -- ─── POSTS & FEED (BẢNG TIN TRƯỜNG HỌC & THẢO LUẬN LỚP) ────────────────
    CREATE TABLE IF NOT EXISTS posts (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        school_id       INTEGER,
        class_id        INTEGER REFERENCES classes(id),
        category        TEXT DEFAULT 'DISCUSSION',
        is_pinned       INTEGER DEFAULT 0,
        author_id       INTEGER,
        author_name     TEXT NOT NULL,
        author_role     TEXT NOT NULL,
        content         TEXT NOT NULL,
        likes_count     INTEGER DEFAULT 0,
        comments_count  INTEGER DEFAULT 0,
        created_at      TEXT DEFAULT (datetime('now','localtime'))
    );

    CREATE TABLE IF NOT EXISTS post_likes (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        post_id     INTEGER NOT NULL,
        user_id     INTEGER NOT NULL,
        created_at  TEXT DEFAULT (datetime('now','localtime')),
        UNIQUE(post_id, user_id)
    );

    CREATE TABLE IF NOT EXISTS post_comments (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        post_id     INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
        school_id   INTEGER NOT NULL REFERENCES schools(id),
        user_id     INTEGER NOT NULL REFERENCES users(id),
        author_name TEXT NOT NULL,
        author_role TEXT NOT NULL,
        content     TEXT NOT NULL,
        created_at  TEXT DEFAULT (datetime('now','localtime'))
    );

    CREATE TABLE IF NOT EXISTS security_alerts (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        school_id           INTEGER NOT NULL REFERENCES schools(id),
        camera_station_id   INTEGER REFERENCES camera_stations(id),
        alert_type          TEXT DEFAULT 'STRANGER',
        title               TEXT NOT NULL,
        description         TEXT,
        direction           TEXT DEFAULT 'IN',
        proof_image_url     TEXT,
        timestamp           TEXT NOT NULL,
        date_only           TEXT NOT NULL,
        status              TEXT DEFAULT 'UNRESOLVED',
        created_at          TEXT DEFAULT (datetime('now','localtime'))
    );
    """)

    # ── Performance Indexes (safe to run multiple times) ─────────────────────
    index_statements = [
        "CREATE INDEX IF NOT EXISTS idx_att_school_date ON attendance_logs (school_id, date_only)",
        "CREATE INDEX IF NOT EXISTS idx_att_student     ON attendance_logs (student_id)",
        "CREATE INDEX IF NOT EXISTS idx_att_timestamp   ON attendance_logs (timestamp DESC)",
        "CREATE INDEX IF NOT EXISTS idx_att_direction   ON attendance_logs (school_id, date_only, direction)",
        "CREATE INDEX IF NOT EXISTS idx_cam_school      ON camera_stations (school_id)",
        "CREATE INDEX IF NOT EXISTS idx_sec_school_date ON security_alerts (school_id, date_only)",
        "CREATE INDEX IF NOT EXISTS idx_sec_type        ON security_alerts (school_id, alert_type)",
        "CREATE INDEX IF NOT EXISTS idx_stu_school      ON students (school_id, is_deleted)",
        "CREATE INDEX IF NOT EXISTS idx_stu_code        ON students (school_id, student_code)",
        "CREATE INDEX IF NOT EXISTS idx_usr_school      ON users (school_id, username)",
        "CREATE INDEX IF NOT EXISTS idx_usr_code        ON users (school_id, user_code)",
        "CREATE INDEX IF NOT EXISTS idx_leave_school    ON leave_requests (school_id, status)",
        "CREATE INDEX IF NOT EXISTS idx_dispute_school  ON disputes (school_id, status)",
        "CREATE INDEX IF NOT EXISTS idx_samples_student ON student_face_samples (student_id, school_id)",
        "CREATE INDEX IF NOT EXISTS idx_posts_school    ON posts (school_id, created_at DESC)",
        "CREATE INDEX IF NOT EXISTS idx_posts_class     ON posts (class_id, created_at DESC)",
        "CREATE INDEX IF NOT EXISTS idx_post_likes      ON post_likes (post_id, user_id)",
        "CREATE INDEX IF NOT EXISTS idx_post_comments   ON post_comments (post_id, created_at ASC)",
        "CREATE INDEX IF NOT EXISTS idx_stu_parent_invite ON students (parent_invite_code)",
    ]
    for stmt in index_statements:
        try:
            conn.execute(stmt)
        except Exception:
            pass
    conn.commit()

    # Soft-delete & column migrations — safe to run multiple times
    for col_sql in [
        "ALTER TABLE users ADD COLUMN user_code TEXT",
        "ALTER TABLE students ADD COLUMN is_deleted INTEGER DEFAULT 0",
        "ALTER TABLE students ADD COLUMN deleted_at TEXT",
        "ALTER TABLE students ADD COLUMN parent_invite_code TEXT",
        "ALTER TABLE biometric_consent_records ADD COLUMN consent_version TEXT DEFAULT '1.0'",
        "ALTER TABLE biometric_consent_records ADD COLUMN user_agent TEXT",
        "ALTER TABLE attendance_logs ADD COLUMN violation_details TEXT",
        "ALTER TABLE attendance_logs ADD COLUMN direction TEXT DEFAULT 'IN'",
        "ALTER TABLE camera_stations ADD COLUMN direction TEXT DEFAULT 'IN'",
        "ALTER TABLE posts ADD COLUMN class_id INTEGER REFERENCES classes(id)",
        "ALTER TABLE posts ADD COLUMN category TEXT DEFAULT 'DISCUSSION'",
        "ALTER TABLE posts ADD COLUMN is_pinned INTEGER DEFAULT 0",
        "ALTER TABLE camera_stations ADD COLUMN uniform_check INTEGER DEFAULT 1",
        "ALTER TABLE camera_stations ADD COLUMN occlusion_check INTEGER DEFAULT 1",
        "ALTER TABLE camera_stations ADD COLUMN public_stream_url TEXT",
        "ALTER TABLE camera_stations ADD COLUMN tailscale_enabled INTEGER DEFAULT 1",
    ]:
        try:
            conn.execute(col_sql)
            conn.commit()
        except Exception:
            pass  # column already exists

    try:
        conn.execute("UPDATE users SET user_code = student_code WHERE (user_code IS NULL OR user_code='') AND student_code IS NOT NULL")
        conn.commit()
    except Exception:
        pass

    try:
        # Populate parent_invite_code for any students that don't have one yet
        missing_stus = conn.execute("SELECT id FROM students WHERE parent_invite_code IS NULL OR parent_invite_code=''").fetchall()
        for s in missing_stus:
            p_code = f"PH-{secrets.token_hex(3).upper()}"
            conn.execute("UPDATE students SET parent_invite_code=? WHERE id=?", (p_code, s["id"]))
        # Populate invite_code for any classes that don't have one yet
        missing_classes = conn.execute("SELECT id, name FROM classes WHERE invite_code IS NULL OR invite_code=''").fetchall()
        for c_row in missing_classes:
            clean_name = (c_row["name"] or "CLASS").replace(" ", "").upper()
            c_code = f"INVITE_{clean_name}_{secrets.token_hex(4).upper()}"
            conn.execute("UPDATE classes SET invite_code=? WHERE id=?", (c_code, c_row["id"]))
        conn.commit()
    except Exception:
        pass

    log.info("[DB] Schema initialized.")
    _seed_data(conn)
    conn.close()
    log.info("[DB] Database ready.")


def _seed_data(conn: sqlite3.Connection):
    """Insert default platform admin + demo school + users if not already present."""
    c = conn.cursor()

    # ── Platform Admin ──────────────────────────────────────────
    from app.config import PLATFORM_ADMIN_EMAIL, PLATFORM_ADMIN_PASSWORD
    c.execute("SELECT id FROM platform_admins WHERE email=?", (PLATFORM_ADMIN_EMAIL,))
    if not c.fetchone():
        salt = generate_salt()
        pw   = hash_password(PLATFORM_ADMIN_PASSWORD, salt)
        c.execute(
            "INSERT INTO platform_admins (email, full_name, password_hash, salt) VALUES (?,?,?,?)",
            (PLATFORM_ADMIN_EMAIL, "Platform Admin", pw, salt)
        )
        log.info(f"[SEED] Platform admin created: {PLATFORM_ADMIN_EMAIL}")

    # ── Demo School (Only seed if explicitly requested) ────────
    import os
    if os.getenv("SEED_DEMO_DATA", "false").lower() != "true":
        conn.commit()
        return

    c.execute("SELECT id FROM schools WHERE school_code=?", ("thpt-nguyen-hue",))
    school_row = c.fetchone()
    if not school_row:
        default_rules = json.dumps({
            "checkin_from":  "06:00",
            "checkin_on_time_until": "07:15",
            "checkin_late_until":    "07:30",
            "uniform_check": True,
            "min_points_warning": 80
        })
        default_form = json.dumps({
            "student": {
                "require_student_code": False,  # User requested: auto-assigned by system per role
                "require_phone":        True,
                "require_face_photo":   True,
                "require_dob":          True
            },
            "parent": {
                "require_phone":  True,
                "require_student_link": True
            },
            "teacher": {
                "require_invite_code": True
            }
        })
        c.execute("""
            INSERT INTO schools (
                school_code, name, short_name, address, province_city,
                academic_year, status, rules_config, form_config,
                teacher_invite_code, inspector_invite_code, bgh_invite_code
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            "thpt-nguyen-hue",
            "Trường THPT Nguyễn Huệ (Demo)",
            "THPT Nguyễn Huệ",
            "123 Đường Lê Lợi, Quận 1",
            "TP. Hồ Chí Minh",
            "2025-2026",
            "ACTIVE",
            default_rules,
            default_form,
            "GV_NGUYEN_HUE_2026",
            "GT_NGUYEN_HUE_2026",
            "BGH_NGUYEN_HUE_2026"
        ))
        school_id = c.lastrowid
        log.info(f"[SEED] Demo school created: id={school_id}")
    else:
        school_id = school_row["id"]

    # ── Demo Users ──────────────────────────────────────────────
    demo_users = [
        ("hieutruong",  "hieutruong@nguyen-hue.edu.vn", "0901000001", "HEADMASTER",  "Thầy Nguyễn Văn Hiệu (Hiệu Trưởng)"),
        ("phohieutruong","pho.hieu@nguyen-hue.edu.vn",  "0901000002", "HEADMASTER",  "Cô Trần Thị Phương (Phó Hiệu Trưởng)"),
        ("giamthi01",   "giamthi01@nguyen-hue.edu.vn",  "0901000003", "INSPECTOR",   "Thầy Lê Văn Giám (Giám Thị)"),
        ("gvcn10a1",    "gvcn10a1@nguyen-hue.edu.vn",   "0901000004", "TEACHER",     "Cô Nguyễn Mai Hương (GVCN 10A1)"),
        ("gvcn10a2",    "gvcn10a2@nguyen-hue.edu.vn",   "0901000005", "TEACHER",     "Thầy Phạm Văn Dũng (GVCN 10A2)"),
        ("phuhuynh01",  "phuhuynh01@gmail.com",         "0901000006", "PARENT",      "Chị Trần Thị Mai (Phụ Huynh)"),
        ("phuhuynh02",  "phuhuynh02@gmail.com",         "0901000007", "PARENT",      "Anh Nguyễn Văn Nam (Phụ Huynh)"),
        ("hocsinh01",   None,                           "0901000008", "STUDENT",     "Nguyễn Văn An (HS 10A1)"),
        ("hocsinh02",   None,                           "0901000009", "STUDENT",     "Trần Thị Bình (HS 10A1)"),
    ]

    for username, email, phone, role, full_name in demo_users:
        c.execute("SELECT id FROM users WHERE school_id=? AND username=?", (school_id, username))
        if not c.fetchone():
            salt = generate_salt()
            pw   = hash_password("123456", salt)
            c.execute("""
                INSERT INTO users (
                    school_id, username, email, phone, password_hash, salt,
                    full_name, role, status, verified_status, verification_method, verification_note
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                school_id, username, email, phone, pw, salt,
                full_name, role,
                "ACTIVE", "VERIFIED", "SEED_DATA",
                "Tài khoản demo — đã được xác minh sẵn"
            ))

    # ── Demo Classes ────────────────────────────────────────────
    c.execute("SELECT id FROM users WHERE school_id=? AND username='gvcn10a1'", (school_id,))
    teacher_row = c.fetchone()
    teacher_id  = teacher_row["id"] if teacher_row else None

    classes_data = [
        ("10A1", 10, "INVITE_10A1_2026", teacher_id),
        ("10A2", 10, "INVITE_10A2_2026", None),
        ("11A1", 11, "INVITE_11A1_2026", None),
        ("12A1", 12, "INVITE_12A1_2026", None),
    ]
    for cname, grade, invite, tid in classes_data:
        c.execute("SELECT id FROM classes WHERE school_id=? AND name=?", (school_id, cname))
        if not c.fetchone():
            c.execute("""
                INSERT INTO classes (school_id, name, grade_level, homeroom_teacher_id, invite_code)
                VALUES (?,?,?,?,?)
            """, (school_id, cname, grade, tid, invite))

    # ── Demo Students ──────────────────────────────────────────
    import secrets as sec
    c.execute("SELECT id FROM classes WHERE school_id=? AND name='10A1'", (school_id,))
    cls_row = c.fetchone()
    cls_id  = cls_row["id"] if cls_row else None

    c.execute("SELECT id FROM users WHERE school_id=? AND username='hocsinh01'", (school_id,))
    hs_row = c.fetchone()

    c.execute("SELECT id FROM students WHERE school_id=? AND student_code='HS001'", (school_id,))
    if not c.fetchone() and hs_row and cls_id:
        c.execute("""
            INSERT INTO students (
                user_id, class_id, school_id, student_code, full_name,
                dob, parent_phone, parent_name, qr_token, current_points
            ) VALUES (?,?,?,?,?,?,?,?,?,?)
        """, (
            hs_row["id"], cls_id, school_id, "HS001", "Nguyễn Văn An",
            "2008-05-15", "0901000006", "Chị Trần Thị Mai",
            sec.token_urlsafe(16), 95
        ))

    # ── Demo Camera Station ─────────────────────────────────────
    c.execute("SELECT id FROM camera_stations WHERE school_id=?", (school_id,))
    if not c.fetchone():
        c.execute("""
            INSERT INTO camera_stations (school_id, name, location, secret_key, status)
            VALUES (?,?,?,?,?)
        """, (school_id, "Cổng Chính", "Cổng trường chính phía Đông", sec.token_urlsafe(24), "ONLINE"))
        c.execute("""
            INSERT INTO camera_stations (school_id, name, location, secret_key, status)
            VALUES (?,?,?,?,?)
        """, (school_id, "Cổng Phụ", "Cổng phụ phía Tây", sec.token_urlsafe(24), "OFFLINE"))

    conn.commit()
    log.info("[SEED] Seed data complete.")


def cleanup_expired_tokens():
    """Remove expired tokens from token_blacklist to prevent unbounded table growth."""
    conn = get_db()
    try:
        cur = conn.execute("DELETE FROM token_blacklist WHERE expires_at < datetime('now')")
        deleted = cur.rowcount
        conn.commit()
        if deleted > 0:
            log.info(f"[DB] Cleaned up {deleted} expired blacklisted token(s).")
    except Exception as e:
        log.warning(f"[DB] Failed to cleanup expired tokens: {e}")
    finally:
        conn.close()
