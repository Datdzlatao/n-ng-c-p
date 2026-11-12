"""
app/services/cleanup_service.py — Rolling Data Retention & Cleanup Service
Tự động dọn dẹp ảnh bằng chứng camera và dữ liệu điểm danh cũ sau N ngày (mặc định 8 ngày).
Giải quyết triệt để nút thắt tràn bộ nhớ ổ cứng của trạm và máy chủ.
"""
import os
import logging
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any

from app.config import UPLOAD_DIR, RETENTION_DAYS, CLEANUP_DELETE_RECORDS
from app.database import get_db

log = logging.getLogger("stem.cleanup")

_cleanup_task: Optional[asyncio.Task] = None


def _resolve_upload_file_path(url_or_path: str) -> Optional[Path]:
    """Chuyển đổi URL hoặc đường dẫn tương đối thành Path tuyệt đối trong UPLOAD_DIR an toàn."""
    if not url_or_path:
        return None
    
    # Chuẩn hóa nếu là URL đầy đủ: loại bỏ protocol và domain
    clean_path = url_or_path.split("?")[0]
    if "/uploads/" in clean_path:
        clean_path = clean_path.split("/uploads/", 1)[1]
    elif clean_path.startswith("uploads/"):
        clean_path = clean_path[len("uploads/"):]
    elif clean_path.startswith("/"):
        clean_path = clean_path.lstrip("/")

    target_file = (UPLOAD_DIR / clean_path).resolve()
    # Chống Path Traversal
    if UPLOAD_DIR.resolve() in target_file.parents or target_file == UPLOAD_DIR.resolve():
        return target_file if target_file.exists() and target_file.is_file() else None
    return None


def cleanup_old_attendance_data(
    retention_days: Optional[int] = None,
    delete_records: Optional[bool] = None
) -> Dict[str, Any]:
    """
    Dọn dẹp dữ liệu điểm danh cũ hơn retention_days (mặc định 8 ngày):
    1. Xóa vĩnh viễn các file ảnh bằng chứng camera (proof_image_url) cũ hơn N ngày.
    2. Cập nhật proof_image_url = NULL (hoặc xóa cả bản ghi nếu delete_records=True).
    3. Quét dọn các file ảnh mồ côi cũ hơn N ngày trong thư mục uploads.
    """
    days = retention_days if retention_days is not None else RETENTION_DAYS
    del_records = delete_records if delete_records is not None else CLEANUP_DELETE_RECORDS
    
    # Ngày mốc: những bản ghi có date_only <= cutoff_date sẽ được dọn dẹp
    cutoff_dt = datetime.now() - timedelta(days=days)
    cutoff_date = cutoff_dt.strftime("%Y-%m-%d")

    log.info(f"[Cleanup] Bắt đầu dọn dẹp dữ liệu cũ trước hoặc bằng ngày: {cutoff_date} (Giới hạn: {days} ngày)")

    deleted_photos = 0
    freed_bytes = 0
    records_affected = 0

    conn = get_db()
    try:
        # 1. Tìm các bản ghi attendance_logs cũ có ảnh bằng chứng
        cursor = conn.execute(
            """
            SELECT id, proof_image_url 
            FROM attendance_logs 
            WHERE date_only <= ? AND proof_image_url IS NOT NULL AND proof_image_url != ''
            """,
            (cutoff_date,)
        )
        old_logs = cursor.fetchall()

        for row in old_logs:
            file_path = _resolve_upload_file_path(row["proof_image_url"])
            if file_path and file_path.exists():
                try:
                    size = file_path.stat().st_size
                    file_path.unlink()
                    deleted_photos += 1
                    freed_bytes += size
                except Exception as e:
                    log.warning(f"[Cleanup] Không thể xóa file {file_path}: {e}")

        # 2. Tìm ảnh trong bảng disputes cũ
        cursor_disputes = conn.execute(
            """
            SELECT id, proof_image_url 
            FROM disputes 
            WHERE created_at <= ? AND proof_image_url IS NOT NULL AND proof_image_url != ''
            """,
            (cutoff_date + " 23:59:59",)
        )
        for row in cursor_disputes.fetchall():
            file_path = _resolve_upload_file_path(row["proof_image_url"])
            if file_path and file_path.exists():
                try:
                    size = file_path.stat().st_size
                    file_path.unlink()
                    deleted_photos += 1
                    freed_bytes += size
                except Exception as e:
                    log.warning(f"[Cleanup] Không thể xóa file tranh chấp {file_path}: {e}")

        # 3. Tìm ảnh trong bảng security_alerts cũ (ảnh người lạ / cảnh báo an ninh)
        cursor_alerts = conn.execute(
            """
            SELECT id, proof_image_url 
            FROM security_alerts 
            WHERE date_only <= ? AND proof_image_url IS NOT NULL AND proof_image_url != ''
            """,
            (cutoff_date,)
        )
        for row in cursor_alerts.fetchall():
            file_path = _resolve_upload_file_path(row["proof_image_url"])
            if file_path and file_path.exists():
                try:
                    size = file_path.stat().st_size
                    file_path.unlink()
                    deleted_photos += 1
                    freed_bytes += size
                except Exception as e:
                    log.warning(f"[Cleanup] Không thể xóa file cảnh báo an ninh {file_path}: {e}")

        # 4. Cập nhật Database
        if del_records:
            # Xóa sạch cả dòng lịch sử điểm danh và cảnh báo an ninh cũ
            res = conn.execute("DELETE FROM attendance_logs WHERE date_only <= ?", (cutoff_date,))
            records_affected = res.rowcount
            conn.execute("DELETE FROM security_alerts WHERE date_only <= ?", (cutoff_date,))
        else:
            # Chỉ xóa link ảnh, giữ nguyên dữ liệu text để xuất báo cáo
            res = conn.execute(
                "UPDATE attendance_logs SET proof_image_url = NULL WHERE date_only <= ? AND proof_image_url IS NOT NULL",
                (cutoff_date,)
            )
            records_affected = res.rowcount
            conn.execute(
                "UPDATE security_alerts SET proof_image_url = NULL WHERE date_only <= ? AND proof_image_url IS NOT NULL",
                (cutoff_date,)
            )

        conn.commit()

        # 4. Quét dọn file mồ côi trong UPLOAD_DIR có mtime > days (ví dụ uploads/attendance, uploads/proofs)
        orphaned_deleted = 0
        if UPLOAD_DIR.exists():
            cutoff_timestamp = cutoff_dt.timestamp()
            for root, _, files in os.walk(UPLOAD_DIR):
                for f in files:
                    fp = Path(root) / f
                    try:
                        # Bỏ qua ảnh đại diện học sinh và logo trường
                        if "avatar" in fp.name or "logo" in fp.name or "face_" in fp.name:
                            continue
                        stat = fp.stat()
                        if stat.st_mtime < cutoff_timestamp:
                            size = stat.st_size
                            fp.unlink()
                            orphaned_deleted += 1
                            freed_bytes += size
                    except Exception:
                        pass

        deleted_photos += orphaned_deleted

        log.info(
            f"[Cleanup] Hoàn tất dọn dẹp: Đã xóa {deleted_photos} ảnh, "
            f"giải phóng {freed_bytes / (1024 * 1024):.2f} MB, "
            f"cập nhật {records_affected} bản ghi."
        )

        return {
            "status": "success",
            "retention_days": days,
            "cutoff_date": cutoff_date,
            "deleted_photos": deleted_photos,
            "freed_bytes": freed_bytes,
            "freed_mb": round(freed_bytes / (1024 * 1024), 2),
            "records_affected": records_affected,
            "records_deleted": del_records,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        log.error(f"[Cleanup] Lỗi trong quá trình dọn dẹp: {e}", exc_info=True)
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
    finally:
        conn.close()


def get_storage_stats() -> Dict[str, Any]:
    """Lấy thống kê dung lượng thư mục uploads và tình trạng dữ liệu điểm danh."""
    total_size = 0
    total_files = 0
    photo_files = 0

    if UPLOAD_DIR.exists():
        for root, _, files in os.walk(UPLOAD_DIR):
            for f in files:
                fp = Path(root) / f
                try:
                    total_size += fp.stat().st_size
                    total_files += 1
                    if fp.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"):
                        photo_files += 1
                except Exception:
                    pass

    conn = get_db()
    try:
        row_count = conn.execute("SELECT COUNT(*) FROM attendance_logs").fetchone()[0]
        row_with_photo = conn.execute(
            "SELECT COUNT(*) FROM attendance_logs WHERE proof_image_url IS NOT NULL AND proof_image_url != ''"
        ).fetchone()[0]
        oldest_date = conn.execute("SELECT MIN(date_only) FROM attendance_logs").fetchone()[0]
        newest_date = conn.execute("SELECT MAX(date_only) FROM attendance_logs").fetchone()[0]

        cutoff_date = (datetime.now() - timedelta(days=RETENTION_DAYS)).strftime("%Y-%m-%d")
        eligible_for_cleanup = conn.execute(
            "SELECT COUNT(*) FROM attendance_logs WHERE date_only <= ? AND proof_image_url IS NOT NULL",
            (cutoff_date,)
        ).fetchone()[0]

        return {
            "upload_dir": str(UPLOAD_DIR),
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "total_files": total_files,
            "photo_files": photo_files,
            "retention_policy_days": RETENTION_DAYS,
            "current_cutoff_date": cutoff_date,
            "total_attendance_records": row_count,
            "records_with_photo": row_with_photo,
            "records_eligible_for_cleanup": eligible_for_cleanup,
            "oldest_record_date": oldest_date,
            "newest_record_date": newest_date,
        }
    finally:
        conn.close()


async def _periodic_cleanup_loop():
    """Background task chạy định kỳ mỗi 24 giờ."""
    log.info(f"[CleanupService] Worker dọn dẹp định kỳ đã kích hoạt. Chu kỳ: {RETENTION_DAYS} ngày.")
    # Chờ 10 giây sau khi server khởi động rồi quét phiên đầu tiên
    await asyncio.sleep(10)
    while True:
        try:
            log.info("[CleanupService] Bắt đầu phiên quét dọn dẹp hàng ngày...")
            result = cleanup_old_attendance_data()
            log.info(f"[CleanupService] Kết quả phiên dọn dẹp: {result}")
        except asyncio.CancelledError:
            log.info("[CleanupService] Worker dọn dẹp nhận lệnh dừng (shutdown).")
            break
        except Exception as e:
            log.error(f"[CleanupService] Lỗi trong phiên dọn dẹp hàng ngày: {e}", exc_info=True)
        
        # Chờ 24 giờ (86400s) cho phiên tiếp theo
        try:
            await asyncio.sleep(86400)
        except asyncio.CancelledError:
            break


def start_cleanup_scheduler():
    """Kích hoạt tiến trình dọn dẹp nền trong asyncio event loop."""
    global _cleanup_task
    if _cleanup_task is None or _cleanup_task.done():
        loop = asyncio.get_event_loop()
        _cleanup_task = loop.create_task(_periodic_cleanup_loop())
        log.info("[CleanupService] Đã lập lịch dọn dẹp nền.")


def stop_cleanup_scheduler():
    """Dừng tiến trình dọn dẹp nền khi tắt app."""
    global _cleanup_task
    if _cleanup_task and not _cleanup_task.done():
        _cleanup_task.cancel()
        log.info("[CleanupService] Đã hủy lịch dọn dẹp nền.")
