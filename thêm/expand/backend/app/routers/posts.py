"""
app/routers/posts.py — School Feed, Class Discussions & Comments API
Provides endpoints for creating, retrieving, liking, and commenting on posts.
Supports school-wide announcements as well as class-specific discussions.
"""
import logging
from typing import Optional, List, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, field_validator

from app.database import get_db
from app.core.deps import get_current_user, get_current_user_optional

router = APIRouter(prefix="/api/v1/posts", tags=["Posts & Feed"])
log    = logging.getLogger("stem.posts")


class CreatePostRequest(BaseModel):
    content: Any
    school_id: Optional[int] = None
    class_id: Optional[int] = None
    category: Optional[str] = "DISCUSSION"
    is_urgent: Optional[bool] = False

    @field_validator("content", mode="before")
    @classmethod
    def validate_content(cls, v: Any) -> str:
        if isinstance(v, dict):
            return str(v.get("content", "") or "")
        return str(v or "")


class CreateCommentRequest(BaseModel):
    content: str


def _format_time_ago(created_str: str, scope_suffix: str = "Toàn trường") -> str:
    """Format timestamp into human-readable relative or date string."""
    try:
        dt = datetime.strptime(created_str, "%Y-%m-%d %H:%M:%S")
        diff = (datetime.now() - dt).total_seconds()
        suffix = f" · {scope_suffix}" if scope_suffix else ""
        if diff < 60:
            return f"Vừa xong{suffix}"
        elif diff < 3600:
            minutes = max(1, int(diff // 60))
            return f"{minutes} phút trước{suffix}"
        elif diff < 86400:
            hours = int(diff // 3600)
            return f"{hours} giờ trước{suffix}"
        elif diff < 86400 * 7:
            days = int(diff // 86400)
            return f"{days} ngày trước{suffix}"
        else:
            return dt.strftime("%d/%m/%Y %H:%M") + suffix
    except Exception:
        suffix = f" · {scope_suffix}" if scope_suffix else ""
        return created_str + suffix


@router.get("")
async def get_posts(
    school_id: Optional[int] = Query(None),
    class_id: Optional[int] = Query(None),
    category: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current: Optional[dict] = Depends(get_current_user_optional)
):
    """
    Retrieve posts:
    - If class_id is given: returns discussions for that specific class.
    - If class_id is omitted: returns school-wide announcements.
    """
    user_id = current.get("user_id") if current else None
    user_school_id = current.get("school_id") if current else None
    effective_school_id = school_id or user_school_id

    conn = get_db()
    try:
        where_clauses = []
        params = [user_id, user_id]

        if effective_school_id:
            where_clauses.append("(p.school_id = ? OR p.school_id IS NULL)")
            params.append(effective_school_id)

        if class_id is not None:
            where_clauses.append("p.class_id = ?")
            params.append(class_id)
        else:
            where_clauses.append("p.class_id IS NULL")

        if category:
            where_clauses.append("p.category = ?")
            params.append(category)

        where_sql = " AND ".join(where_clauses)
        if where_sql:
            where_sql = "WHERE " + where_sql

        sql = f"""
            SELECT p.*, c.name as class_name,
                   (SELECT COUNT(*) FROM post_likes pl WHERE pl.post_id = p.id) AS real_likes_count,
                   (SELECT COUNT(*) FROM post_comments pc WHERE pc.post_id = p.id) AS real_comments_count,
                   CASE WHEN ? IS NOT NULL AND EXISTS(
                       SELECT 1 FROM post_likes pl WHERE pl.post_id = p.id AND pl.user_id = ?
                   ) THEN 1 ELSE 0 END AS user_liked
            FROM posts p
            LEFT JOIN classes c ON p.class_id = c.id
            {where_sql}
            ORDER BY p.is_pinned DESC, p.id DESC
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])

        rows = conn.execute(sql, params).fetchall()

        posts = []
        for r in rows:
            d = dict(r)
            author_name = d.get("author_name") or "Người dùng"
            class_name = d.get("class_name")
            scope_suffix = f"Lớp {class_name}" if class_name else "Toàn trường"

            posts.append({
                "id": d["id"],
                "schoolId": d.get("school_id"),
                "classId": d.get("class_id"),
                "className": class_name,
                "category": d.get("category") or "DISCUSSION",
                "isPinned": bool(d.get("is_pinned", 0)),
                "author": author_name,
                "authorId": d.get("author_id"),
                "roleTag": d.get("author_role") or "THÀNH VIÊN",
                "avatarText": author_name[:2].upper(),
                "timeText": _format_time_ago(d.get("created_at", ""), scope_suffix),
                "content": d.get("content", ""),
                "likes": d.get("real_likes_count", 0),
                "liked": bool(d.get("user_liked", 0)),
                "commentsCount": d.get("real_comments_count", 0),
                "createdAt": d.get("created_at"),
            })

        return {"status": "success", "data": posts}
    finally:
        conn.close()


@router.post("")
async def create_post(req: CreatePostRequest, current: dict = Depends(get_current_user)):
    """
    Create a new post:
    - If class_id is set: Class discussion. Students of that class and teachers/admins can post.
    - If class_id is None: School-wide announcement. Only teachers/admins can post.
    """
    content = req.content.strip()
    if not content:
        raise HTTPException(status_code=400, detail="Nội dung bài viết không được để trống.")

    if req.is_urgent and not content.startswith("🚨 [KHẨN CẤP]"):
        content = f"🚨 [KHẨN CẤP] {content}"

    role = current.get("role", "STUDENT")
    school_id = req.school_id or current.get("school_id")
    user_id = current.get("user_id") or current.get("id")
    author_name = current.get("full_name") or current.get("username") or "Người dùng"
    author_role = role
    category = (req.category or "DISCUSSION").upper()

    conn = get_db()
    try:
        class_name = None
        if req.class_id:
            # Kiểm tra lớp có tồn tại trong trường không
            cls = conn.execute("SELECT id, name FROM classes WHERE id=? AND school_id=?", (req.class_id, school_id)).fetchone()
            if not cls:
                raise HTTPException(404, "Lớp học không tồn tại trong trường.")
            class_name = cls["name"]

            # Nếu là STUDENT, kiểm tra xem có thuộc lớp này không
            if role == "STUDENT":
                stu = conn.execute(
                    "SELECT id FROM students WHERE user_id=? AND class_id=? AND school_id=? AND is_active=1",
                    (user_id, req.class_id, school_id)
                ).fetchone()
                if not stu:
                    raise HTTPException(403, "Bạn không thuộc lớp này để đăng thảo luận.")
        else:
            # Thông báo toàn trường
            allowed_roles = {"TEACHER", "SCHOOL_ADMIN", "HEADMASTER", "ADMIN", "PLATFORM_ADMIN", "INSPECTOR"}
            if role not in allowed_roles:
                raise HTTPException(status_code=403, detail="Chỉ giáo viên hoặc ban quản trị mới có quyền đăng thông báo toàn trường.")

        cursor = conn.execute(
            """
            INSERT INTO posts (school_id, class_id, category, author_id, author_name, author_role, content, likes_count, comments_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, 0, 0)
            """,
            (school_id, req.class_id, category, user_id, author_name, author_role, content)
        )
        post_id = cursor.lastrowid
        conn.commit()

        created_row = conn.execute("SELECT * FROM posts WHERE id=?", (post_id,)).fetchone()
        d = dict(created_row)

        scope_suffix = f"Lớp {class_name}" if class_name else "Toàn trường"

        created_post = {
            "id": d["id"],
            "schoolId": d.get("school_id"),
            "classId": d.get("class_id"),
            "className": class_name,
            "category": d.get("category"),
            "isPinned": bool(d.get("is_pinned", 0)),
            "author": d.get("author_name"),
            "authorId": d.get("author_id"),
            "roleTag": d.get("author_role"),
            "avatarText": (d.get("author_name") or "ND")[:2].upper(),
            "timeText": f"Vừa xong · {scope_suffix}",
            "content": d.get("content"),
            "likes": 0,
            "liked": False,
            "commentsCount": 0,
            "createdAt": d.get("created_at"),
        }

        log.info(f"[POSTS] Created post id={post_id} (class_id={req.class_id}) by user {user_id} ({author_name})")
        return {"status": "success", "data": created_post}
    finally:
        conn.close()


@router.post("/{post_id}/like")
async def toggle_like(post_id: int, current: dict = Depends(get_current_user)):
    """Toggle like for the current user on a post."""
    user_id = current.get("user_id") or current.get("id")
    conn = get_db()
    try:
        post = conn.execute("SELECT id FROM posts WHERE id=?", (post_id,)).fetchone()
        if not post:
            raise HTTPException(status_code=404, detail="Bài viết không tồn tại.")

        existing = conn.execute(
            "SELECT id FROM post_likes WHERE post_id=? AND user_id=?",
            (post_id, user_id)
        ).fetchone()

        if existing:
            conn.execute("DELETE FROM post_likes WHERE post_id=? AND user_id=?", (post_id, user_id))
            liked = False
        else:
            conn.execute("INSERT INTO post_likes (post_id, user_id) VALUES (?, ?)", (post_id, user_id))
            liked = True

        conn.execute("""
            UPDATE posts
            SET likes_count = (SELECT COUNT(*) FROM post_likes WHERE post_id = posts.id)
            WHERE id = ?
        """, (post_id,))
        conn.commit()

        likes_count = conn.execute(
            "SELECT COUNT(*) FROM post_likes WHERE post_id=?", (post_id,)
        ).fetchone()[0]

        return {"status": "success", "liked": liked, "likes": likes_count}
    finally:
        conn.close()


@router.delete("/{post_id}")
async def delete_post(post_id: int, current: dict = Depends(get_current_user)):
    """Delete a post. Can only be done by the author or an admin."""
    user_id = current.get("user_id") or current.get("id")
    role = current.get("role", "")
    conn = get_db()
    try:
        post = conn.execute("SELECT * FROM posts WHERE id=?", (post_id,)).fetchone()
        if not post:
            raise HTTPException(status_code=404, detail="Bài viết không tồn tại.")

        is_admin = role in ("ADMIN", "PLATFORM_ADMIN", "HEADMASTER")
        is_author = (post["author_id"] == user_id)

        if not (is_admin or is_author):
            raise HTTPException(status_code=403, detail="Bạn không có quyền xóa bài viết này.")

        conn.execute("DELETE FROM post_likes WHERE post_id=?", (post_id,))
        conn.execute("DELETE FROM post_comments WHERE post_id=?", (post_id,))
        conn.execute("DELETE FROM posts WHERE id=?", (post_id,))
        conn.commit()

        log.info(f"[POSTS] Deleted post id={post_id} by user {user_id}")
        return {"status": "success", "message": "Đã xóa bài viết thành công."}
    finally:
        conn.close()


# ─── COMMENTS API ─────────────────────────────────────────────────────────────

@router.get("/{post_id}/comments")
async def get_comments(
    post_id: int,
    limit: int = Query(100, ge=1, le=200),
    current: Optional[dict] = Depends(get_current_user_optional)
):
    """Retrieve all comments for a post in chronological order."""
    conn = get_db()
    try:
        post = conn.execute("SELECT id FROM posts WHERE id=?", (post_id,)).fetchone()
        if not post:
            raise HTTPException(404, "Bài viết không tồn tại.")

        rows = conn.execute("""
            SELECT pc.*, u.avatar_url
            FROM post_comments pc
            LEFT JOIN users u ON pc.user_id = u.id
            WHERE pc.post_id=?
            ORDER BY pc.id ASC
            LIMIT ?
        """, (post_id, limit)).fetchall()

        comments = []
        for r in rows:
            d = dict(r)
            author = d.get("author_name") or "Người dùng"
            comments.append({
                "id": d["id"],
                "postId": d["post_id"],
                "userId": d["user_id"],
                "author": author,
                "authorRole": d.get("author_role") or "STUDENT",
                "avatarText": author[:2].upper(),
                "avatarUrl": d.get("avatar_url"),
                "content": d.get("content"),
                "timeText": _format_time_ago(d.get("created_at", ""), ""),
                "createdAt": d.get("created_at"),
            })

        return {"status": "success", "data": comments}
    finally:
        conn.close()


@router.post("/{post_id}/comments")
async def add_comment(
    post_id: int,
    req: CreateCommentRequest,
    current: dict = Depends(get_current_user)
):
    """Add a new comment/reply to a post."""
    content = req.content.strip()
    if not content:
        raise HTTPException(400, "Nội dung bình luận không được để trống.")

    user_id = current.get("user_id") or current.get("id")
    author_name = current.get("full_name") or current.get("username") or "Người dùng"
    author_role = current.get("role", "STUDENT")
    school_id = current.get("school_id")

    conn = get_db()
    try:
        post = conn.execute("SELECT id, school_id FROM posts WHERE id=?", (post_id,)).fetchone()
        if not post:
            raise HTTPException(404, "Bài viết không tồn tại.")

        cursor = conn.execute("""
            INSERT INTO post_comments (post_id, school_id, user_id, author_name, author_role, content)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (post_id, school_id or post["school_id"], user_id, author_name, author_role, content))
        comment_id = cursor.lastrowid

        # Update comments_count in posts table
        conn.execute("""
            UPDATE posts
            SET comments_count = (SELECT COUNT(*) FROM post_comments WHERE post_id = posts.id)
            WHERE id = ?
        """, (post_id,))
        conn.commit()

        new_comment = {
            "id": comment_id,
            "postId": post_id,
            "userId": user_id,
            "author": author_name,
            "authorRole": author_role,
            "avatarText": author_name[:2].upper(),
            "content": content,
            "timeText": "Vừa xong",
            "createdAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        return {"status": "success", "data": new_comment}
    finally:
        conn.close()


@router.delete("/comments/{comment_id}")
async def delete_comment(comment_id: int, current: dict = Depends(get_current_user)):
    """Delete a comment."""
    user_id = current.get("user_id") or current.get("id")
    role = current.get("role", "")
    conn = get_db()
    try:
        comm = conn.execute("SELECT * FROM post_comments WHERE id=?", (comment_id,)).fetchone()
        if not comm:
            raise HTTPException(404, "Bình luận không tồn tại.")

        is_admin = role in ("ADMIN", "PLATFORM_ADMIN", "HEADMASTER", "TEACHER")
        is_author = (comm["user_id"] == user_id)

        if not (is_admin or is_author):
            raise HTTPException(403, "Bạn không có quyền xóa bình luận này.")

        post_id = comm["post_id"]
        conn.execute("DELETE FROM post_comments WHERE id=?", (comment_id,))
        conn.execute("""
            UPDATE posts
            SET comments_count = (SELECT COUNT(*) FROM post_comments WHERE post_id = posts.id)
            WHERE id = ?
        """, (post_id,))
        conn.commit()

        return {"status": "success", "message": "Đã xóa bình luận thành công."}
    finally:
        conn.close()
