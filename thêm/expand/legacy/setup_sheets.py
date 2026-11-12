"""
=================================================
  SETUP_SHEETS.PY — KHOI TAO GOOGLE SHEETS
=================================================
BUG FIX:
  - import_students: khong xu ly truong hop CSV co BOM ky tu
  - Khong kiem tra sheet da co data truoc khi import -> tranh trung lap

MOI:
  - Tao them sheet TongKet (bao cao tong hop theo ngay)
  - Kiem tra va cap nhat header neu cu (thieu cot moi)
  - Hien URL de mo truc tiep sau khi hoan tat

Cach dung:
    python setup_sheets.py
"""

import gspread
from oauth2client.service_account import ServiceAccountCredentials
import csv
import os
import sys

from config import (
    SPREADSHEET_NAME, SHEET_LOG, SHEET_STUDENTS, SHEET_VIOLATIONS, SHEET_SUMMARY,
    CREDENTIALS_FILE, SPREADSHEET_ID
)

SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

HEADER_LOG = ["Thoi Gian", "Ma HS", "Ho Ten", "Trang Thai (Vao/Ra)"]
HEADER_STU = ["MaHS", "HoTen", "Lop"]
HEADER_VIO = ["Thoi Gian", "Ma HS", "Ho Ten", "Mo Ta", "Ten File Anh", "Duong Dan Anh"]
HEADER_SUM = ["Ngay", "Tong HS", "Co Mat", "Vang Mat", "Vi Pham", "Gio Bat Dau", "Gio Ket Thuc", "Ghi Chu"]


def connect():
    try:
        creds  = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, SCOPE)
        client = gspread.authorize(creds)
        print("[OK] Da xac thuc credentials.")
        return client
    except FileNotFoundError:
        print(f"[!!] Khong tim thay '{CREDENTIALS_FILE}'.")
        print("     Xem README.md de biet cach tai file nay tu Google Cloud Console.")
        sys.exit(1)


def get_or_create_spreadsheet(client):
    if SPREADSHEET_ID:
        try:
            ss = client.open_by_key(SPREADSHEET_ID)
            print(f"[OK] Da mo bang tinh bang ID: '{ss.title}'")
            return ss
        except gspread.SpreadsheetNotFound:
            print(f"[!!] Khong tim thay Sheets voi ID '{SPREADSHEET_ID}'.")
            sys.exit(1)

    try:
        ss = client.open(SPREADSHEET_NAME)
        print(f"[OK] Mo bang tinh hien co: '{SPREADSHEET_NAME}'")
    except gspread.SpreadsheetNotFound:
        ss = client.create(SPREADSHEET_NAME)
        print(f"[OK] Da tao bang tinh moi: '{SPREADSHEET_NAME}'")
        ss.share(None, perm_type="anyone", role="reader")
    return ss


def _setup_generic_sheet(ss, title, header, rows, cols, header_format):
    """Tao sheet neu chua co, them header, tra ve worksheet."""
    try:
        ws = ss.worksheet(title)
        print(f"  -> Sheet '{title}' da ton tai.")
        # [MOI] Kiem tra header co day du cot khong
        existing = ws.row_values(1)
        if existing != header:
            ws.insert_row(header, 1)
            ws.format(f"A1:{chr(64 + len(header))}1", header_format)
            print(f"     Da cap nhat header sheet '{title}'.")
    except gspread.WorksheetNotFound:
        ws = ss.add_worksheet(title=title, rows=rows, cols=cols)
        ws.append_row(header)
        ws.format(f"A1:{chr(64 + len(header))}1", header_format)
        print(f"  [OK] Da tao sheet '{title}'.")
    return ws


def setup_sheet_log(ss):
    fmt = {
        "backgroundColor": {"red": 0.12, "green": 0.39, "blue": 0.78},
        "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}},
        "horizontalAlignment": "CENTER"
    }
    ws = _setup_generic_sheet(ss, SHEET_LOG, HEADER_LOG, 3000, 6, fmt)
    set_column_width(ws, 0, 185)
    set_column_width(ws, 1, 100)
    set_column_width(ws, 2, 210)
    set_column_width(ws, 3, 150)
    return ws


def setup_sheet_students(ss):
    fmt = {
        "backgroundColor": {"red": 0.12, "green": 0.39, "blue": 0.78},
        "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}},
        "horizontalAlignment": "CENTER"
    }
    ws = _setup_generic_sheet(ss, SHEET_STUDENTS, HEADER_STU, 500, 4, fmt)
    set_column_width(ws, 0, 100)
    set_column_width(ws, 1, 220)
    set_column_width(ws, 2, 100)
    return ws


def setup_sheet_violations(ss):
    fmt = {
        "backgroundColor": {"red": 0.8, "green": 0.1, "blue": 0.1},
        "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}},
        "horizontalAlignment": "CENTER"
    }
    ws = _setup_generic_sheet(ss, SHEET_VIOLATIONS, HEADER_VIO, 2000, 7, fmt)
    for i, w in enumerate([185, 100, 210, 200, 200, 320]):
        set_column_width(ws, i, w)
    return ws


def setup_sheet_summary(ss):
    """[MOI] Sheet TongKet bao cao theo ngay."""
    fmt = {
        "backgroundColor": {"red": 0.0, "green": 0.55, "blue": 0.35},
        "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}},
        "horizontalAlignment": "CENTER"
    }
    ws = _setup_generic_sheet(ss, SHEET_SUMMARY, HEADER_SUM, 500, 8, fmt)
    for i, w in enumerate([120, 100, 100, 100, 100, 130, 130, 200]):
        set_column_width(ws, i, w)
    return ws


def import_students(ws):
    """
    [BUG FIX] Import hoc sinh tu students.csv, tranh trung lap.
    """
    csv_candidates = ["students.csv", os.path.join(os.path.dirname(__file__), "students.csv")]
    csv_path = next((p for p in csv_candidates if os.path.exists(p)), None)

    if not csv_path:
        print("  [!] Khong tim thay 'students.csv' — bo qua import.")
        print("      Ban co the nhap tay vao sheet hoac chay lai sau khi co file CSV.")
        return

    # [BUG FIX] Doc BOM-safe, strip khoang trang
    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows   = []
        for r in reader:
            ma   = r.get("MaHS", "").strip()
            ten  = r.get("HoTen", "").strip()
            lop  = r.get("Lop", "").strip()
            if ma and ten:
                rows.append([ma, ten, lop])

    if not rows:
        print("  [!] File CSV rong hoac sai dinh dang cot (can: MaHS, HoTen, Lop).")
        return

    # [BUG FIX] Lay danh sach MaHS da co trong sheet tranh trung lap
    existing_ids = set()
    existing = ws.get_all_values()
    for row in existing[1:]:
        if row and row[0].strip():
            existing_ids.add(row[0].strip())

    new_rows = [r for r in rows if r[0] not in existing_ids]
    if new_rows:
        ws.append_rows(new_rows, value_input_option="RAW")
        print(f"  [OK] Da import {len(new_rows)} hoc sinh moi vao sheet '{SHEET_STUDENTS}'.")
    else:
        print(f"  [OK] Tat ca {len(rows)} hoc sinh da co trong sheet — bo qua import.")


def set_column_width(ws, col_index: int, width_px: int):
    """Dat do rong cot."""
    try:
        ws.spreadsheet.batch_update({
            "requests": [{
                "updateDimensionProperties": {
                    "range": {
                        "sheetId":    ws.id,
                        "dimension":  "COLUMNS",
                        "startIndex": col_index,
                        "endIndex":   col_index + 1,
                    },
                    "properties": {"pixelSize": width_px},
                    "fields": "pixelSize"
                }
            }]
        })
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────────────
def main():
    print("=" * 58)
    print("  SETUP GOOGLE SHEETS — HE THONG DIEM DANH QR  v2.0")
    print("=" * 58)

    client = connect()
    ss     = get_or_create_spreadsheet(client)

    print("\n[->] Thiet lap cac sheet:")
    setup_sheet_log(ss)
    ws_stu = setup_sheet_students(ss)
    setup_sheet_violations(ss)
    setup_sheet_summary(ss)     # [MOI]

    print("\n[->] Import hoc sinh:")
    import_students(ws_stu)

    url = f"https://docs.google.com/spreadsheets/d/{ss.id}"
    print(f"\n{'=' * 58}")
    print(f"  [OK] Hoan thanh! Mo bang tinh tai:")
    print(f"  {url}")
    print(f"{'=' * 58}")


if __name__ == "__main__":
    main()
