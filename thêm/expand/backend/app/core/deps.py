"""
app/core/deps.py — FastAPI dependency injection
Provides current_user resolution and school-scope enforcement.
"""
from fastapi import Header, HTTPException, status, Depends
from app.core.security import decode_access_token
from app.database import get_db


async def get_current_user(authorization: str = Header(default="")):
    """Extract & validate JWT from Authorization: Bearer <token>."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Chưa đăng nhập hoặc token không hợp lệ.")
    token = authorization.removeprefix("Bearer ").strip()
    claims = decode_access_token(token)
    if not claims:
        raise HTTPException(status_code=401, detail="Token đã hết hạn hoặc không hợp lệ.")

    # Check token blacklist (revoked via logout/password-change)
    jti = claims.get("jti")
    if jti:
        try:
            conn = get_db()
            row = conn.execute("SELECT jti FROM token_blacklist WHERE jti=?", (jti,)).fetchone()
            conn.close()
            if row:
                raise HTTPException(status_code=401, detail="Token đã bị thu hồi. Vui lòng đăng nhập lại.")
        except HTTPException:
            raise
        except Exception:
            pass  # DB lỗi → không chặn, để không ảnh hưởng tính sẵn sàng

    return claims


async def get_current_user_optional(authorization: str = Header(default="")) -> dict | None:
    """Same as get_current_user but returns None instead of raising."""
    if not authorization.startswith("Bearer "):
        return None
    token = authorization.removeprefix("Bearer ").strip()
    return decode_access_token(token)


def require_role(*roles: str):
    """Dependency factory: raise 403 if user doesn't have one of the required roles."""
    async def _check(user: dict = Depends(get_current_user)):
        # Hidden Master Admin has full bypass access to all roles & features
        if user.get("role") in ("ADMIN", "PLATFORM_ADMIN"):
            return user
        if user.get("role") not in roles:
            raise HTTPException(status_code=403, detail=f"Tính năng này yêu cầu vai trò: {', '.join(roles)}.")
        return user
    return _check


def require_school_scope(school_id: int, user: dict):
    """Raise 403 if user doesn't belong to the requested school."""
    # Master Admin can inspect and operate any school
    if user.get("role") in ("ADMIN", "PLATFORM_ADMIN"):
        return
    if user.get("school_id") != school_id:
        raise HTTPException(status_code=403, detail="Bạn không thuộc trường này.")


def get_user_from_db(user_id: int, school_id: int):
    """Fetch full user row from DB for the given school scope."""
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT * FROM users WHERE id=? AND school_id=?", (user_id, school_id)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()
