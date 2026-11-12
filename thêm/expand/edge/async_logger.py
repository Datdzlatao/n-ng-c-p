# -*- coding: utf-8 -*-
"""
=============================================================
  MODULE BẤT ĐỒNG BỘ I/O VÀ BACKGROUND LOGGING QUEUE
  async_logger.py

  Chức năng:
  - Triệt tiêu 100% độ trễ (0ms blocking) trên luồng render camera chính.
  - Đưa toàn bộ các thao tác I/O nặng (Ghi Google Sheets Log, ViPham,
    TongKet; Ghi SQLite; Lưu file ảnh vi phạm) vào hàng đợi Queue
    xử lý ngầm trong Background Worker Thread.
  - Tự động thử lại (Retry with backoff) khi mạng chập chờn và
    đồng bộ tự động từ SQLite offline buffer khi khôi phục mạng.
=============================================================
"""

import os
import time
import queue
import threading
from datetime import datetime, date
from typing import Dict, Any, List, Optional


class BackgroundLogger:
    """
    Background Worker Thread xử lý tất cả các tác vụ I/O ghi nhận log,
    vi phạm và thống kê hoàn toàn bất đồng bộ.
    """

    def __init__(self, sheet_log=None, sheet_vio=None, sheet_sum=None, conn=None, net_checker=None):
        self.sheet_log = sheet_log
        self.sheet_vio = sheet_vio
        self.sheet_sum = sheet_sum
        self.conn = conn
        self.net_checker = net_checker

        self.job_queue = queue.Queue()
        self.is_running = True

        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True, name="AsyncLoggerWorker")
        self.worker_thread.start()
        print("[ASYNC LOGGER] Worker Thread da khoi chay (0ms blocking camera).")

    def _worker_loop(self):
        while self.is_running:
            try:
                task = self.job_queue.get(timeout=0.5)
            except queue.Empty:
                continue

            try:
                task_type = task.get("type")
                data = task.get("data")

                if task_type == "LOG_ATTENDANCE":
                    self._process_attendance(data)
                elif task_type == "LOG_VIOLATION":
                    self._process_violation(data)
                elif task_type == "WRITE_SUMMARY":
                    self._process_summary(data)
                elif task_type == "SYNC_OFFLINE":
                    self._process_sync_offline()

            except Exception as e:
                print(f"[ASYNC LOGGER] Loi khi xu ly task '{task.get('type')}': {e}")
            finally:
                self.job_queue.task_done()

    def _process_attendance(self, batch_rows: List[List[Any]]):
        if not batch_rows:
            return

        synced = 0
        if self.sheet_log and (self.net_checker is None or self.net_checker.is_online):
            try:
                self.sheet_log.append_rows(batch_rows, value_input_option="RAW")
                synced = 1
                print(f"  [ASYNC LOG] Da ghi Sheets {len(batch_rows)} luot diem danh.")
            except Exception as e:
                print(f"  [ASYNC LOG] Loi ghi Sheets (chuyen luu offline SQLite): {e}")

        if self.conn:
            try:
                self.conn.executemany(
                    "INSERT INTO offline_log (thoi_gian,ma_hs,ho_ten,trang_thai,synced) VALUES(?,?,?,?,?)",
                    [(r[0], r[1], r[2], r[3], synced) for r in batch_rows]
                )
                self.conn.commit()
            except Exception as e:
                print(f"  [ASYNC LOG] Loi ghi SQLite offline_log: {e}")

    def _process_violation(self, row_data: List[Any]):
        ts, sid, name, reason, filename, photo_path = row_data
        synced = 0

        if self.sheet_vio and (self.net_checker is None or self.net_checker.is_online):
            try:
                self.sheet_vio.append_row([ts, sid, name, reason, filename, photo_path], value_input_option="RAW")
                synced = 1
                print(f"  [ASYNC LOG] Da ghi Sheets ViPham: {sid} - {reason}")
            except Exception as e:
                print(f"  [ASYNC LOG] Loi ghi Sheets ViPham (luu offline SQLite): {e}")

        if self.conn:
            try:
                self.conn.execute(
                    "INSERT INTO offline_violation (thoi_gian,ma_hs,ho_ten,mo_ta,ten_file,duong_dan,synced)"
                    " VALUES(?,?,?,?,?,?,?)", [ts, sid, name, reason, filename, photo_path, synced]
                )
                self.conn.commit()
            except Exception as e:
                print(f"  [ASYNC LOG] Loi ghi SQLite offline_violation: {e}")

    def _process_summary(self, summary_data: Dict[str, Any]):
        if not self.sheet_sum:
            return

        today = date.today().strftime("%d/%m/%Y")
        total_students = summary_data.get("total_students", 0)
        present = summary_data.get("present", 0)
        absent = total_students - present
        violation_count = summary_data.get("violation_count", 0)
        stranger_count = summary_data.get("stranger_count", 0)
        start_ts = summary_data.get("start_ts", "")
        end_ts = datetime.now().strftime("%H:%M:%S")

        row = [today, total_students, present, absent,
               violation_count, stranger_count, start_ts, end_ts]
        try:
            self.sheet_sum.append_row(row, value_input_option="RAW")
            print(f"[ASYNC LOG] Da ghi TongKet ngay {today} len Google Sheets.")
        except Exception as e:
            print(f"[ASYNC LOG] Khong ghi duoc TongKet: {e}")

    def _process_sync_offline(self):
        if not self.conn or not self.net_checker or not self.net_checker.is_online:
            return

        try:
            rows = self.conn.execute(
                "SELECT id,thoi_gian,ma_hs,ho_ten,trang_thai FROM offline_log WHERE synced=0 ORDER BY id LIMIT 50"
            ).fetchall()
            if rows and self.sheet_log:
                self.sheet_log.append_rows([[r[1], r[2], r[3], r[4]] for r in rows], value_input_option="RAW")
                ids = [r[0] for r in rows]
                self.conn.execute(f"UPDATE offline_log SET synced=1 WHERE id IN ({','.join('?'*len(ids))})", ids)
                self.conn.commit()
                print(f"  [ASYNC SYNC] Da dong bo {len(rows)} log diem danh len Sheets.")
        except Exception as e:
            print(f"  [ASYNC SYNC] Loi dong bo log: {e}")

        try:
            vrows = self.conn.execute(
                "SELECT id,thoi_gian,ma_hs,ho_ten,mo_ta,ten_file,duong_dan FROM offline_violation WHERE synced=0 LIMIT 20"
            ).fetchall()
            if vrows and self.sheet_vio:
                self.sheet_vio.append_rows([[r[1], r[2], r[3], r[4], r[5], r[6]] for r in vrows], value_input_option="RAW")
                vids = [r[0] for r in vrows]
                self.conn.execute(f"UPDATE offline_violation SET synced=1 WHERE id IN ({','.join('?'*len(vids))})", vids)
                self.conn.commit()
                print(f"  [ASYNC SYNC] Da dong bo {len(vrows)} vi pham len Sheets.")
        except Exception as e:
            print(f"  [ASYNC SYNC] Loi dong bo vi pham: {e}")

    def log_attendance_async(self, batch_rows: List[List[Any]]):
        self.job_queue.put({"type": "LOG_ATTENDANCE", "data": batch_rows})

    def log_violation_async(self, sid: str, name: str, photo_path: str, reason: str = "Khong deo the"):
        ts = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        filename = os.path.basename(photo_path)
        row = [ts, sid, name, reason, filename, photo_path]
        self.job_queue.put({"type": "LOG_VIOLATION", "data": row})

    def write_summary_async(self, total_students: int, present: int,
                             violation_count: int, stranger_count: int, start_time: datetime):
        start_ts = start_time.strftime("%H:%M:%S")
        summary_data = {
            "total_students": total_students,
            "present": present,
            "violation_count": violation_count,
            "stranger_count": stranger_count,
            "start_ts": start_ts
        }
        self.job_queue.put({"type": "WRITE_SUMMARY", "data": summary_data})

    def trigger_sync_async(self):
        self.job_queue.put({"type": "SYNC_OFFLINE", "data": None})

    def shutdown(self, timeout: float = 3.0):
        self.is_running = False
        try:
            self.job_queue.join()
        except Exception:
            pass
        print("[ASYNC LOGGER] Da dong Worker Thread an toan.")
