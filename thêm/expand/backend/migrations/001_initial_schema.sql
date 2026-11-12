-- ================================================================
-- STEM Attendance Platform — PostgreSQL Production Schema
-- Version: 1.0.0 | Run on: initial deploy
-- SQLite dev version lives in app/database.py
-- ================================================================

-- Enable UUID extension (PostgreSQL)
-- CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Platform Admins
CREATE TABLE IF NOT EXISTS platform_admins (
    id          SERIAL PRIMARY KEY,
    email       TEXT UNIQUE NOT NULL,
    full_name   TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    salt        TEXT NOT NULL,
    is_active   BOOLEAN DEFAULT TRUE,
    created_at  TIMESTAMP DEFAULT NOW()
);

-- Schools (each = one tenant "server")
CREATE TABLE IF NOT EXISTS schools (
    id              SERIAL PRIMARY KEY,
    school_code     TEXT UNIQUE NOT NULL,
    name            TEXT NOT NULL,
    short_name      TEXT,
    logo_url        TEXT,
    address         TEXT,
    province_city   TEXT,
    academic_year   TEXT DEFAULT '2025-2026',
    owner_user_id   INTEGER,
    status          TEXT DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE','SUSPENDED','PENDING')),
    rules_config    JSONB DEFAULT '{}',
    form_config     JSONB DEFAULT '{}',
    teacher_invite_code   TEXT,
    inspector_invite_code TEXT,
    bgh_invite_code       TEXT,
    created_at  TIMESTAMP DEFAULT NOW(),
    updated_at  TIMESTAMP DEFAULT NOW()
);

-- Users (multi-tenant via school_id)
CREATE TABLE IF NOT EXISTS users (
    id              SERIAL PRIMARY KEY,
    school_id       INTEGER NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
    username        TEXT NOT NULL,
    email           TEXT,
    phone           TEXT,
    password_hash   TEXT NOT NULL,
    salt            TEXT NOT NULL,
    full_name       TEXT NOT NULL,
    dob             DATE,
    gender          TEXT,
    avatar_url      TEXT,
    role            TEXT NOT NULL CHECK (role IN ('HEADMASTER','TEACHER','INSPECTOR','STUDENT','PARENT')),
    status          TEXT DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE','SUSPENDED','PENDING_APPROVAL')),
    verified_status       TEXT DEFAULT 'UNVERIFIED' CHECK (verified_status IN ('UNVERIFIED','PENDING_REVIEW','VERIFIED','REJECTED')),
    verification_method   TEXT,
    verification_doc_url  TEXT,
    verification_note     TEXT,
    verified_at           TIMESTAMP,
    student_code    TEXT,
    class_name      TEXT,
    grade_level     SMALLINT,
    last_login_at   TIMESTAMP,
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW(),
    UNIQUE(school_id, username),
    UNIQUE(school_id, phone)
);

-- Row Level Security for users
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
-- CREATE POLICY user_school_isolation ON users USING (school_id = current_setting('app.school_id')::int);

-- Classes
CREATE TABLE IF NOT EXISTS classes (
    id                  SERIAL PRIMARY KEY,
    school_id           INTEGER NOT NULL REFERENCES schools(id),
    name                TEXT NOT NULL,
    grade_level         SMALLINT,
    homeroom_teacher_id INTEGER REFERENCES users(id),
    academic_year       TEXT DEFAULT '2025-2026',
    invite_code         TEXT UNIQUE,
    qr_code_url         TEXT,
    is_active           BOOLEAN DEFAULT TRUE,
    created_at          TIMESTAMP DEFAULT NOW()
);

-- Students
CREATE TABLE IF NOT EXISTS students (
    id                  SERIAL PRIMARY KEY,
    user_id             INTEGER REFERENCES users(id),
    class_id            INTEGER REFERENCES classes(id),
    school_id           INTEGER NOT NULL REFERENCES schools(id),
    student_code        TEXT NOT NULL,
    full_name           TEXT NOT NULL,
    dob                 DATE,
    gender              TEXT,
    parent_phone        TEXT,
    parent_name         TEXT,
    parent_relation     TEXT DEFAULT 'Phụ huynh',
    face_embedding_blob BYTEA,
    face_photo_url      TEXT,
    face_approved       TEXT DEFAULT 'PENDING' CHECK (face_approved IN ('PENDING','APPROVED','REJECTED')),
    face_approved_by    INTEGER REFERENCES users(id),
    qr_token            TEXT UNIQUE,
    current_points      SMALLINT DEFAULT 100,
    is_active           BOOLEAN DEFAULT TRUE,
    created_at          TIMESTAMP DEFAULT NOW(),
    updated_at          TIMESTAMP DEFAULT NOW(),
    UNIQUE(school_id, student_code)
);

-- Parent-Student Links
CREATE TABLE IF NOT EXISTS parent_student_links (
    id              SERIAL PRIMARY KEY,
    parent_user_id  INTEGER NOT NULL REFERENCES users(id),
    student_id      INTEGER NOT NULL REFERENCES students(id),
    school_id       INTEGER NOT NULL REFERENCES schools(id),
    relation_name   TEXT DEFAULT 'Phụ huynh',
    verified_status TEXT DEFAULT 'PENDING' CHECK (verified_status IN ('PENDING','VERIFIED')),
    verified_at     TIMESTAMP,
    created_at      TIMESTAMP DEFAULT NOW(),
    UNIQUE(parent_user_id, student_id)
);

-- Camera Stations
CREATE TABLE IF NOT EXISTS camera_stations (
    id              SERIAL PRIMARY KEY,
    school_id       INTEGER NOT NULL REFERENCES schools(id),
    name            TEXT NOT NULL,
    location        TEXT,
    secret_key      TEXT UNIQUE NOT NULL,
    status          TEXT DEFAULT 'OFFLINE' CHECK (status IN ('ONLINE','OFFLINE','ERROR')),
    last_ping_at    TIMESTAMP,
    created_at      TIMESTAMP DEFAULT NOW()
);

-- Attendance Logs
CREATE TABLE IF NOT EXISTS attendance_logs (
    id                  SERIAL PRIMARY KEY,
    student_id          INTEGER NOT NULL REFERENCES students(id),
    camera_station_id   INTEGER REFERENCES camera_stations(id),
    school_id           INTEGER NOT NULL REFERENCES schools(id),
    timestamp           TIMESTAMP NOT NULL,
    date_only           DATE NOT NULL,
    check_type          TEXT DEFAULT 'FACE_AI' CHECK (check_type IN ('FACE_AI','QR_SCAN','MANUAL')),
    status              TEXT DEFAULT 'ON_TIME' CHECK (status IN ('ON_TIME','LATE','ABSENT','EXCUSED')),
    uniform_status      TEXT DEFAULT 'UNKNOWN' CHECK (uniform_status IN ('OK','VIOLATION','UNKNOWN')),
    spoof_status        TEXT DEFAULT 'SKIPPED' CHECK (spoof_status IN ('PASSED','FAILED','SKIPPED')),
    confidence_score    REAL DEFAULT 0,
    proof_image_url     TEXT,
    is_disputed         BOOLEAN DEFAULT FALSE,
    created_at          TIMESTAMP DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_attendance_school_date ON attendance_logs(school_id, date_only);
CREATE INDEX IF NOT EXISTS idx_attendance_student ON attendance_logs(student_id, date_only);
CREATE INDEX IF NOT EXISTS idx_students_school ON students(school_id);
CREATE INDEX IF NOT EXISTS idx_users_school ON users(school_id, username);

-- Disputes
CREATE TABLE IF NOT EXISTS disputes (
    id                  SERIAL PRIMARY KEY,
    attendance_log_id   INTEGER REFERENCES attendance_logs(id),
    student_id          INTEGER NOT NULL REFERENCES students(id),
    school_id           INTEGER NOT NULL REFERENCES schools(id),
    level               TEXT DEFAULT 'LEVEL_1_TEACHER',
    reason              TEXT NOT NULL,
    proof_image_url     TEXT,
    status              TEXT DEFAULT 'PENDING',
    resolver_id         INTEGER REFERENCES users(id),
    resolution_note     TEXT,
    created_at          TIMESTAMP DEFAULT NOW(),
    updated_at          TIMESTAMP DEFAULT NOW()
);

-- Leave Requests
CREATE TABLE IF NOT EXISTS leave_requests (
    id              SERIAL PRIMARY KEY,
    student_id      INTEGER NOT NULL REFERENCES students(id),
    parent_user_id  INTEGER REFERENCES users(id),
    school_id       INTEGER NOT NULL REFERENCES schools(id),
    start_date      DATE NOT NULL,
    end_date        DATE NOT NULL,
    reason          TEXT NOT NULL,
    status          TEXT DEFAULT 'PENDING',
    approved_by     INTEGER REFERENCES users(id),
    approved_at     TIMESTAMP,
    created_at      TIMESTAMP DEFAULT NOW()
);

-- Verification OTPs
CREATE TABLE IF NOT EXISTS verification_otps (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER REFERENCES users(id),
    school_id   INTEGER NOT NULL REFERENCES schools(id),
    target      TEXT NOT NULL,
    otp_code    TEXT NOT NULL,
    otp_type    TEXT NOT NULL,
    expires_at  TIMESTAMP NOT NULL,
    used_at     TIMESTAMP,
    created_at  TIMESTAMP DEFAULT NOW()
);

-- Discipline Scores
CREATE TABLE IF NOT EXISTS discipline_scores (
    id                  SERIAL PRIMARY KEY,
    class_id            INTEGER NOT NULL REFERENCES classes(id),
    school_id           INTEGER NOT NULL REFERENCES schools(id),
    week_number         SMALLINT NOT NULL,
    year                SMALLINT NOT NULL,
    attendance_score    REAL DEFAULT 0,
    uniform_score       REAL DEFAULT 0,
    discipline_score    REAL DEFAULT 0,
    bonus_points        REAL DEFAULT 0,
    total_points        REAL DEFAULT 0,
    inspector_id        INTEGER REFERENCES users(id),
    inspector_notes     TEXT,
    headmaster_approval TEXT DEFAULT 'PENDING',
    approved_at         TIMESTAMP,
    created_at          TIMESTAMP DEFAULT NOW()
);
