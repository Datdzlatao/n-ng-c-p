"""
tests/conftest.py — Shared pytest fixtures
"""
import pytest
import sqlite3
from pathlib import Path
from fastapi.testclient import TestClient

# Use isolated DB for tests
import os
TEST_DB_PATH = Path(__file__).parent / "test_stem.db"
os.environ["DATABASE_PATH"] = str(TEST_DB_PATH)
os.environ["DATABASE_URL"] = ""
os.environ["JWT_SECRET"] = "test_secret_key_for_pytest_only_must_be_32_bytes!"
os.environ["DEBUG"] = "false"
os.environ["OTP_DEV_MODE"] = "true"
os.environ["DISABLE_RATE_LIMIT"] = "true"

from app.main import app
from app.database import init_db, get_db

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """Initialize schema once for the test session and ensure test school #1 exists."""
    init_db()
    conn = get_db()
    school = conn.execute("SELECT id FROM schools WHERE id=1").fetchone()
    if not school:
        conn.execute("""
            INSERT OR REPLACE INTO schools (id, school_code, name, province_city, status)
            VALUES (1, 'thpt-test-school', 'Trường THPT Thử Nghiệm Số 1', 'Hà Nội', 'ACTIVE')
        """)
        conn.execute("""
            INSERT OR REPLACE INTO users (id, school_id, username, password_hash, salt, full_name, role, status)
            VALUES (1, 1, 'admin', 'hash', 'salt', 'Admin User', 'ADMIN', 'ACTIVE')
        """)
        conn.commit()

    # Seed test platform admin with valid PBKDF2 hash
    from app.core.security import generate_salt, hash_password
    salt = generate_salt()
    pw   = hash_password("TestAdmin@2026!", salt)
    conn.execute("DELETE FROM platform_admins WHERE email='admin@stemapp.vn'")
    cur = conn.execute(
        "INSERT INTO platform_admins (email, full_name, password_hash, salt) VALUES (?,?,?,?)",
        ("admin@stemapp.vn", "Platform Admin", pw, salt)
    )
    existing_admin = conn.execute("SELECT id FROM users WHERE username='admin' AND school_id=1").fetchone()
    if existing_admin:
        conn.execute("""
            UPDATE users SET password_hash=?, salt=?, full_name='Admin User', role='ADMIN', status='ACTIVE'
            WHERE id=?
        """, (pw, salt, existing_admin["id"]))
    else:
        conn.execute("""
            INSERT INTO users (school_id, username, password_hash, salt, full_name, role, status)
            VALUES (1, 'admin', ?, ?, 'Admin User', 'ADMIN', 'ACTIVE')
        """, (pw, salt))
    conn.commit()
    yield
    # Cleanup test db after test session
    conn_t = get_db()
    try:
        conn_t.execute("PRAGMA foreign_keys = OFF")
        conn_t.execute("DELETE FROM schools WHERE id=1")
        conn_t.execute("DELETE FROM platform_admins WHERE email='admin@stemapp.vn'")
        conn_t.execute("DELETE FROM users WHERE school_id=1")
        conn_t.commit()
    finally:
        conn_t.close()
    for f in [TEST_DB_PATH, TEST_DB_PATH.with_suffix(".db-wal"), TEST_DB_PATH.with_suffix(".db-shm")]:
        if f.exists():
            try:
                f.unlink()
            except Exception:
                pass

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

@pytest.fixture
def admin_token(client):
    res = client.post("/api/v1/auth/login", json={
        "username_or_phone": "admin",
        "password": "TestAdmin@2026!"
    })
    assert res.status_code == 200
    return res.json()["access_token"]

@pytest.fixture
def auth_header(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}
