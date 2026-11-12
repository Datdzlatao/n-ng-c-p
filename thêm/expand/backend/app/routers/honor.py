"""
app/routers/honor.py — Honor Board & Attendance Flame Streaks API
Cung cấp dữ liệu Bảng Vinh Danh, Chuỗi Lửa Chuyên Cần & Xếp Hạng Lớp Học.
"""
import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query

from app.database import get_db
from app.core.deps import get_current_user_optional

router = APIRouter(prefix="/api/v1/s/{school_id}/honor", tags=["Honor Board & Streaks"])
log    = logging.getLogger("stem.honor")


def get_flame_tier(streak: int) -> Dict[str, Any]:
    """
    Xác định cấp độ ngọn lửa dựa trên số ngày chuyên cần đúng giờ liên tiếp:
    - 0 ngày: Chưa có lửa (Chưa kích hoạt)
    - 1 - 2 ngày: Lửa Mầm (Xanh lơ)
    - 3 - 6 ngày: Lửa Xanh Lá (Emerald Flame)
    - 7 - 13 ngày: Lửa Cam (Amber Flame)
    - 14 - 29 ngày: Lửa Đỏ (Crimson Inferno)
    - 30+ ngày: Lửa Tím Tối Thượng (Cosmic Amethyst)
    """
    if streak >= 30:
        return {
            "tier": "PURPLE",
            "tier_name": "Lửa Tím Tối Thượng",
            "title": "Huyền Thoại Chuyên Cần",
            "color": "purple",
            "gradient": "from-purple-500 via-fuchsia-500 to-indigo-500",
            "badge_color": "bg-purple-500/20 text-purple-300 border-purple-500/40",
            "glow": "shadow-lg shadow-purple-500/40",
            "badge_icon": "🟣🔥",
            "min_days": 30,
            "next_target": None,
            "days_left": 0
        }
    elif streak >= 14:
        return {
            "tier": "RED",
            "tier_name": "Lửa Đỏ Rực",
            "title": "Chiến Thần Đúng Giờ",
            "color": "red",
            "gradient": "from-red-500 via-rose-500 to-orange-600",
            "badge_color": "bg-red-500/20 text-red-300 border-red-500/40",
            "glow": "shadow-lg shadow-red-500/40",
            "badge_icon": "🔴🔥",
            "min_days": 14,
            "next_target": 30,
            "days_left": 30 - streak
        }
    elif streak >= 7:
        return {
            "tier": "ORANGE",
            "tier_name": "Lửa Cam Nhiệt Huyết",
            "title": "Tinh Hoa Chuyên Cần",
            "color": "orange",
            "gradient": "from-orange-500 via-amber-500 to-yellow-500",
            "badge_color": "bg-amber-500/20 text-amber-300 border-amber-500/40",
            "glow": "shadow-lg shadow-orange-500/30",
            "badge_icon": "🟠🔥",
            "min_days": 7,
            "next_target": 14,
            "days_left": 14 - streak
        }
    elif streak >= 3:
        return {
            "tier": "GREEN",
            "tier_name": "Lửa Xanh Lá",
            "title": "Bền Bỉ Vươn Lên",
            "color": "green",
            "gradient": "from-emerald-500 via-green-500 to-teal-500",
            "badge_color": "bg-emerald-500/20 text-emerald-300 border-emerald-500/40",
            "glow": "shadow-lg shadow-emerald-500/30",
            "badge_icon": "🟢🔥",
            "min_days": 3,
            "next_target": 7,
            "days_left": 7 - streak
        }
    elif streak >= 1:
        return {
            "tier": "BLUE",
            "tier_name": "Lửa Mầm",
            "title": "Khởi Đầu Tích Cực",
            "color": "blue",
            "gradient": "from-sky-500 to-blue-600",
            "badge_color": "bg-blue-500/20 text-blue-300 border-blue-500/30",
            "glow": "shadow-md shadow-blue-500/20",
            "badge_icon": "🕯️",
            "min_days": 1,
            "next_target": 3,
            "days_left": 3 - streak
        }
    else:
        return {
            "tier": "NONE",
            "tier_name": "Chưa Có Lửa",
            "title": "Hãy Đi Học Đúng Giờ",
            "color": "gray",
            "gradient": "from-gray-600 to-slate-700",
            "badge_color": "bg-white/5 text-gray-400 border-white/10",
            "glow": "",
            "badge_icon": "❄️",
            "min_days": 0,
            "next_target": 3,
            "days_left": 3
        }


def _calculate_streak(conn, student_id: int, school_id: int) -> int:
    """
    Tính số ngày chuyên cần đúng giờ liên tục gần nhất theo tiêu chuẩn:
    NGUYÊN CẢ 1 NGÀY HỢP LỆ (Whole Day Validity):
    1. Trong ngày đó phải có mặt đúng giờ (ít nhất 1 log ON_TIME).
    2. CẢ NGÀY KHÔNG ĐƯỢC CÓ BẤT KỲ LỖI NÀO:
       - Không có log LATE (đi muộn dù chỉ 1 lần/1 tiết).
       - Không có log ABSENT (vắng mặt/trốn tiết).
       - Không có vi phạm đồng phục (uniform_status == 'VIOLATION').
       - Không có cảnh báo giả mạo (spoof_status == 'FAILED').
    3. Nếu trong ngày đó có DÙ CHỈ 1 VI PHẠM -> CẢ NGÀY KHÔNG HỢP LỆ -> Chuỗi lửa bị dập tắt!
    4. Nếu cả ngày học sinh nghỉ có phép hợp lệ (tất cả logs là EXCUSED) -> Bảo lưu chuỗi, không bị dập tắt.
    """
    distinct_dates = conn.execute("""
        SELECT DISTINCT date_only
        FROM attendance_logs
        WHERE student_id=? AND school_id=?
        ORDER BY date_only DESC
        LIMIT 90
    """, (student_id, school_id)).fetchall()

    streak = 0
    for row in distinct_dates:
        d = row["date_only"]
        day_logs = conn.execute("""
            SELECT status, uniform_status, spoof_status
            FROM attendance_logs
            WHERE student_id=? AND school_id=? AND date_only=?
        """, (student_id, school_id, d)).fetchall()

        if not day_logs:
            continue

        # Kiểm tra tính trọn vẹn của cả ngày học
        has_late = any(r["status"] == "LATE" for r in day_logs)
        has_absent = any(r["status"] == "ABSENT" for r in day_logs)
        has_uniform_violation = any(r["uniform_status"] == "VIOLATION" for r in day_logs)
        has_spoof_failed = any(r["spoof_status"] == "FAILED" for r in day_logs)
        has_on_time = any(r["status"] == "ON_TIME" for r in day_logs)
        all_excused = all(r["status"] == "EXCUSED" for r in day_logs)

        # 1. Nếu có bất kỳ vi phạm nào trong ngày -> CẢ NGÀY BỊ HUỶ HỢP LỆ -> Dập tắt chuỗi!
        if has_late or has_absent or has_uniform_violation or has_spoof_failed:
            break

        # 2. Nếu cả ngày là nghỉ có phép -> Bảo lưu chuỗi (không dập tắt, tiếp tục ngày trước)
        if all_excused:
            continue

        # 3. Cả ngày đúng giờ và nề nếp tuyệt đối -> +1 ngày chuỗi lửa!
        if has_on_time:
            streak += 1
        else:
            break

    return streak


@router.get("")
async def get_honor_board(
    school_id: int,
    current: Optional[dict] = Depends(get_current_user_optional)
):
    """
    Lấy toàn bộ dữ liệu Bảng Vinh Danh:
    1. my_streak: Chuỗi lửa của học sinh đang đăng nhập.
    2. streak_leaders: Top học sinh chuỗi lửa dài nhất toàn trường.
    3. points_leaders: Top học sinh điểm nề nếp rèn luyện cao nhất (100đ).
    4. class_rankings: Bảng xếp hạng thi đua tuần giữa các lớp.
    """
    conn = get_db()
    try:
        user_id = current.get("user_id") if current else None
        role = current.get("role") if current else None

        # ── 1. Thành tích chuỗi lửa cá nhân (Nếu là học sinh) ──
        my_streak_info = None
        if user_id and role == "STUDENT":
            stu = conn.execute("""
                SELECT s.id, s.student_code, s.full_name, s.current_points, c.name as class_name
                FROM students s
                LEFT JOIN classes c ON s.class_id = c.id
                WHERE s.user_id=? AND s.school_id=?
            """, (user_id, school_id)).fetchone()

            if stu:
                # Tính tổng ngày học hoàn hảo (nguyên ngày đúng giờ, không vi phạm)
                perfect_days = 0
                all_stu_dates = conn.execute("""
                    SELECT DISTINCT date_only FROM attendance_logs
                    WHERE student_id=? AND school_id=?
                """, (stu["id"], school_id)).fetchall()
                for r_d in all_stu_dates:
                    d_logs = conn.execute("""
                        SELECT status, uniform_status, spoof_status FROM attendance_logs
                        WHERE student_id=? AND school_id=? AND date_only=?
                    """, (stu["id"], school_id, r_d["date_only"])).fetchall()
                    if any(r["status"] == "ON_TIME" for r in d_logs) and not any(
                        r["status"] in ("LATE", "ABSENT") or r["uniform_status"] == "VIOLATION" or r["spoof_status"] == "FAILED"
                        for r in d_logs
                    ):
                        perfect_days += 1

                cur_streak = _calculate_streak(conn, stu["id"], school_id)
                tier_info = get_flame_tier(cur_streak)
                my_streak_info = {
                    "student_id": stu["id"],
                    "student_code": stu["student_code"],
                    "full_name": stu["full_name"],
                    "class_name": stu["class_name"] or "Chưa xếp lớp",
                    "current_points": stu["current_points"],
                    "current_streak": cur_streak,
                    "total_on_time_days": perfect_days,
                    "flame": tier_info
                }

        # ── 2. Top Học Sinh Chuỗi Lửa Cao Nhất Toàn Trường ──
        all_students = conn.execute("""
            SELECT s.id, s.student_code, s.full_name, s.current_points, c.name as class_name
            FROM students s
            LEFT JOIN classes c ON s.class_id = c.id
            WHERE s.school_id=? AND s.is_active=1 AND s.is_deleted=0
            LIMIT 100
        """, (school_id,)).fetchall()

        streak_list = []
        for s in all_students:
            strk = _calculate_streak(conn, s["id"], school_id)
            tier = get_flame_tier(strk)
            streak_list.append({
                "student_id": s["id"],
                "student_code": s["student_code"],
                "full_name": s["full_name"],
                "class_name": s["class_name"] or "—",
                "current_points": s["current_points"],
                "streak": strk,
                "flame": tier
            })

        # Sắp xếp giảm dần theo streak, sau đó theo điểm rèn luyện
        streak_list.sort(key=lambda x: (x["streak"], x["current_points"]), reverse=True)
        streak_leaders = streak_list[:10]

        # ── 3. Top Học Sinh Điểm Nề Nếp Cao Nhất ──
        points_leaders_rows = conn.execute("""
            SELECT s.id, s.student_code, s.full_name, s.current_points, c.name as class_name
            FROM students s
            LEFT JOIN classes c ON s.class_id = c.id
            WHERE s.school_id=? AND s.is_active=1 AND s.is_deleted=0
            ORDER BY s.current_points DESC, s.full_name ASC
            LIMIT 10
        """, (school_id,)).fetchall()

        points_leaders = [
            {
                "student_id": r["id"],
                "student_code": r["student_code"],
                "full_name": r["full_name"],
                "class_name": r["class_name"] or "—",
                "current_points": r["current_points"],
            }
            for r in points_leaders_rows
        ]

        # ── 4. Xếp Hạng Thi Đua Giữa Các Lớp (Tập Thể) ──
        # Lấy điểm thi đua tuần gần nhất nếu có, hoặc tính trung bình điểm nề nếp của lớp
        class_rows = conn.execute("""
            SELECT c.id, c.name, c.grade_level, u.full_name as teacher_name,
                   (SELECT COUNT(*) FROM students s WHERE s.class_id=c.id AND s.is_active=1) as student_count,
                   (SELECT AVG(s.current_points) FROM students s WHERE s.class_id=c.id AND s.is_active=1) as avg_points,
                   (SELECT total_points FROM discipline_scores ds WHERE ds.class_id=c.id AND ds.school_id=c.school_id ORDER BY year DESC, week_number DESC LIMIT 1) as latest_score
            FROM classes c
            LEFT JOIN users u ON c.homeroom_teacher_id = u.id
            WHERE c.school_id=? AND c.is_active=1
            ORDER BY latest_score DESC, avg_points DESC
        """, (school_id,)).fetchall()

        class_rankings = []
        for rank, c in enumerate(class_rows, 1):
            score = c["latest_score"] if c["latest_score"] is not None else (round(c["avg_points"] or 100, 1))
            class_rankings.append({
                "rank": rank,
                "class_id": c["id"],
                "class_name": c["name"],
                "grade_level": c["grade_level"],
                "teacher_name": c["teacher_name"] or "Chưa phân công",
                "student_count": c["student_count"],
                "score": score
            })

        return {
            "status": "success",
            "data": {
                "my_streak": my_streak_info,
                "streak_leaders": streak_leaders,
                "points_leaders": points_leaders,
                "class_rankings": class_rankings,
            }
        }
    finally:
        conn.close()
