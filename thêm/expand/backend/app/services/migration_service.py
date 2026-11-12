"""
app/services/migration_service.py — Ensures schema columns exist for cameras, students, and face datasets.
"""
import sqlite3, os
from pathlib import Path
from app.config import DB_PATH, UPLOAD_DIR, BASE_DIR

def run_migrations():
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    (UPLOAD_DIR / "faces").mkdir(parents=True, exist_ok=True)
    
    # Ensure edge faces directory exists too (if edge directory is present)
    edge_faces_dir = BASE_DIR.parent / "edge" / "data" / "faces"
    if (BASE_DIR.parent / "edge").exists():
        edge_faces_dir.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    
    # Check camera_stations columns
    c.execute("PRAGMA table_info(camera_stations)")
    cam_cols = [r[1] for r in c.fetchall()]
    
    if "stream_type" not in cam_cols:
        c.execute("ALTER TABLE camera_stations ADD COLUMN stream_type TEXT DEFAULT 'WEBCAM'")
    if "stream_url" not in cam_cols:
        c.execute("ALTER TABLE camera_stations ADD COLUMN stream_url TEXT DEFAULT '0'")
    if "camera_num" not in cam_cols:
        c.execute("ALTER TABLE camera_stations ADD COLUMN camera_num INTEGER DEFAULT 1")

    # Check students columns
    c.execute("PRAGMA table_info(students)")
    stu_cols = [r[1] for r in c.fetchall()]
    if "qr_token" not in stu_cols:
        c.execute("ALTER TABLE students ADD COLUMN qr_token TEXT")

    # Check users school_id nullable migration
    c.execute("PRAGMA table_info(users)")
    user_cols = c.fetchall()
    school_id_col = next((r for r in user_cols if r[1] == 'school_id'), None)
    if school_id_col and school_id_col[3] == 1:
        c.execute("PRAGMA foreign_keys=OFF")
        c.execute("""
            CREATE TABLE users_migrated (
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
                role            TEXT NOT NULL,
                status          TEXT DEFAULT 'ACTIVE',
                verified_status       TEXT DEFAULT 'UNVERIFIED',
                verification_method   TEXT,
                verification_doc_url  TEXT,
                verification_note     TEXT,
                verified_at           TEXT,
                student_code    TEXT,
                class_name      TEXT,
                grade_level     INTEGER,
                last_login_at   TEXT,
                created_at      TEXT DEFAULT (datetime('now','localtime')),
                updated_at      TEXT DEFAULT (datetime('now','localtime')),
                user_code       TEXT
            )
        """)
        c.execute("""
            INSERT INTO users_migrated (id, school_id, username, email, phone, password_hash, salt, full_name, dob, gender, avatar_url, role, status, verified_status, verification_method, verification_doc_url, verification_note, verified_at, student_code, class_name, grade_level, last_login_at, created_at, updated_at, user_code)
            SELECT id, school_id, username, email, phone, password_hash, salt, full_name, dob, gender, avatar_url, role, status, verified_status, verification_method, verification_doc_url, verification_note, verified_at, student_code, class_name, grade_level, last_login_at, created_at, updated_at, user_code FROM users
        """)
        c.execute("DROP TABLE users")
        c.execute("ALTER TABLE users_migrated RENAME TO users")
        c.execute("CREATE INDEX IF NOT EXISTS idx_usr_school ON users (school_id, username)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_usr_code ON users (school_id, user_code)")
        c.execute("PRAGMA foreign_keys=ON")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    run_migrations()
    print("Migrations complete.")
