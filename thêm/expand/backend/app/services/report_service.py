"""
app/services/report_service.py — Async Report Generator
Xuat bao cao Excel/CSV chuyen can — chay background, khong block API.
"""
import csv
import io
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from app.database import get_db
from app.config import UPLOAD_DIR

log = logging.getLogger("stem.report")


async def generate_attendance_csv(
    school_id: int,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    time_from: Optional[str] = None,
    time_to: Optional[str] = None,
    time_mode: Optional[str] = "daily",
    class_id: Optional[int] = None,
    status: Optional[str] = None,
    uniform_status: Optional[str] = None,
) -> str:
    """
    Xuat bao cao chuyen can CSV theo khoang ngay, khung gio va bo loc chi tiet.
    Tra ve duong dan tuong doi file CSV de tai ve.
    """
    if not date_from:
        date_from = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    if not date_to:
        date_to = datetime.now().strftime("%Y-%m-%d")

    conn = get_db()
    try:
        sql = """
            SELECT a.date_only, a.timestamp, s.student_code, s.full_name,
                   c.name as class_name, a.status, a.check_type, a.uniform_status,
                   a.violation_details
            FROM attendance_logs a
            JOIN students s ON a.student_id = s.id
            LEFT JOIN classes c ON s.class_id = c.id
            WHERE a.school_id=? AND a.date_only BETWEEN ? AND ?
        """
        params = [school_id, date_from, date_to]

        if time_mode == "continuous" and date_from and date_to:
            tf = f"{time_from or '00:00'}:00"
            tt = f"{time_to or '23:59'}:59"
            sql += " AND replace(a.timestamp, ' ', 'T') >= ? AND replace(a.timestamp, ' ', 'T') <= ?"
            params += [f"{date_from}T{tf}", f"{date_to}T{tt}"]
        else:
            if time_from:
                sql += " AND strftime('%H:%M', replace(a.timestamp, ' ', 'T')) >= ?"
                params.append(time_from)
            if time_to:
                sql += " AND strftime('%H:%M', replace(a.timestamp, ' ', 'T')) <= ?"
                params.append(time_to)

        if class_id:
            sql += " AND s.class_id=?"
            params.append(class_id)
        if status:
            sql += " AND a.status=?"
            params.append(status)
        if uniform_status:
            sql += " AND a.uniform_status=?"
            params.append(uniform_status)

        sql += " ORDER BY a.date_only DESC, a.timestamp DESC, s.student_code"
        rows = conn.execute(sql, params).fetchall()
    finally:
        conn.close()

    # Write CSV to uploads directory
    reports_dir = UPLOAD_DIR / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    filename = f"attendance_{school_id}_{date_from}_{date_to}_{datetime.now().strftime('%H%M%S')}.csv"
    filepath = reports_dir / filename

    status_map = {
        "ON_TIME": "Đúng Giờ",
        "LATE": "Đi Trễ",
        "ABSENT": "Vắng Không Phép",
        "EXCUSED": "Nghỉ Có Phép"
    }
    uniform_map = {
        "OK": "Chuẩn Đồng Phục",
        "VIOLATION": "Vi Phạm Đồng Phục",
        "UNKNOWN": "Chưa Xác Định"
    }

    with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["Ngày", "Thời Gian", "Mã HS", "Họ Và Tên", "Lớp", "Trạng Thái", "Phương Thức", "Đồng Phục", "Ghi Chú"])
        for r in rows:
            st = status_map.get(r["status"], r["status"] or "")
            uf = uniform_map.get(r["uniform_status"], r["uniform_status"] or "")
            note = r["violation_details"] or ""
            writer.writerow([r["date_only"], r["timestamp"], r["student_code"],
                             r["full_name"], r["class_name"] or "",
                             st, r["check_type"], uf, note])

    log.info(f"[REPORT] Da xuat bao cao {len(rows)} dong -> {filename}")
    return f"/uploads/reports/{filename}"
