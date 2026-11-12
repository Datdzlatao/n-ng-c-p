"""
backend/app/core/code_generator.py — Role-based unique user & student code generator.

Standardizes code generation across all roles:
- STUDENT:    HS{school_id:02d}-{seq:04d}   (Học Sinh)
- TEACHER:    GV{school_id:02d}-{seq:04d}   (Giáo Viên)
- PARENT:     PH{school_id:02d}-{seq:04d}   (Phụ Huynh)
- INSPECTOR:  GT{school_id:02d}-{seq:04d}   (Giám Thị)
- HEADMASTER: HT{school_id:02d}-{seq:04d}   (Hiệu Trưởng / Ban Giám Hiệu)
- ADMIN:      QT{school_id:02d}-{seq:04d}   (Quản Trị Viên)
"""

import sqlite3
import logging

log = logging.getLogger("code_generator")

ROLE_PREFIXES = {
    "STUDENT": "HS",
    "TEACHER": "GV",
    "PARENT": "PH",
    "INSPECTOR": "GT",
    "HEADMASTER": "HT",
    "ADMIN": "QT",
}


def get_role_prefix(role: str) -> str:
    """Return 2-letter uppercase prefix for a role."""
    return ROLE_PREFIXES.get((role or "STUDENT").strip().upper(), "ND")


def generate_role_code(conn: sqlite3.Connection, school_id: int | None, role: str) -> str:
    """
    Generate an incremental, collision-free code for a user based on their role and school.
    Example: HS01-0001, GV01-0001, PH01-0001, HT01-0001.
    If school_id is None or 0, uses 00 (e.g. HS00-0001) until the user joins a school.
    """
    role_upper = (role or "STUDENT").strip().upper()
    prefix = get_role_prefix(role_upper)
    sid = school_id or 0
    pattern = f"{prefix}{sid:02d}-%"

    # 1. Inspect existing users table for the highest assigned number
    rows_users = conn.execute(
        "SELECT user_code, student_code FROM users WHERE (school_id=? OR (school_id IS NULL AND ?=0)) AND (user_code LIKE ? OR student_code LIKE ?)",
        (sid, sid, pattern, pattern)
    ).fetchall()

    existing_nums = []
    for r in rows_users:
        for val in (r["user_code"], r["student_code"]):
            if val and val.startswith(f"{prefix}{sid:02d}-"):
                suffix = val.split("-")[-1]
                if suffix.isdigit():
                    existing_nums.append(int(suffix))

    # 2. If student, also inspect students table
    if role_upper == "STUDENT":
        rows_stu = conn.execute(
            "SELECT student_code FROM students WHERE (school_id=? OR (school_id IS NULL AND ?=0)) AND student_code LIKE ?",
            (sid, sid, pattern)
        ).fetchall()
        for r in rows_stu:
            val = r["student_code"]
            if val and val.startswith(f"{prefix}{sid:02d}-"):
                suffix = val.split("-")[-1]
                if suffix.isdigit():
                    existing_nums.append(int(suffix))

    next_num = (max(existing_nums) + 1) if existing_nums else 1
    code = f"{prefix}{sid:02d}-{next_num:04d}"

    # 3. Collision guard: ensure code is genuinely free in both users and students
    while True:
        dup_user = conn.execute(
            "SELECT id FROM users WHERE (school_id=? OR (school_id IS NULL AND ?=0)) AND (user_code=? OR student_code=?)",
            (sid, sid, code, code)
        ).fetchone()
        dup_stu = conn.execute(
            "SELECT id FROM students WHERE (school_id=? OR (school_id IS NULL AND ?=0)) AND student_code=?",
            (sid, sid, code)
        ).fetchone() if role_upper == "STUDENT" else None

        if not dup_user and not dup_stu:
            break
        next_num += 1
        code = f"{prefix}{sid:02d}-{next_num:04d}"

    return code
