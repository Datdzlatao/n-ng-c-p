"""
app/core/rate_limit.py — In-memory Token Bucket Rate Limiter
Không cần Redis — dùng collections.deque cho mỗi IP+endpoint key.
Rate limits:
  - POST /api/v1/auth/login           → 5 req / 60s
  - POST /api/v1/s/*/attendance/sync  → 200 req / 60s
  - Default mọi API khác              → 120 req / 60s
"""
import time
import os
import threading
from collections import deque
from fastapi import Request, HTTPException

_lock   = threading.Lock()
_buckets: dict[str, deque] = {}


def _get_bucket(key: str) -> deque:
    with _lock:
        if key not in _buckets:
            _buckets[key] = deque()
        return _buckets[key]


def check_rate_limit(key: str, max_calls: int, window_seconds: int = 60) -> None:
    """Raise HTTP 429 if the key exceeds max_calls within window_seconds."""
    if os.getenv("DISABLE_RATE_LIMIT", "false").lower() == "true":
        return
    now    = time.time()
    bucket = _get_bucket(key)
    with _lock:
        # Evict old timestamps
        while bucket and bucket[0] < now - window_seconds:
            bucket.popleft()
        if len(bucket) >= max_calls:
            raise HTTPException(
                status_code=429,
                detail=f"Quá nhiều yêu cầu. Vui lòng thử lại sau {window_seconds} giây."
            )
        bucket.append(now)


def get_client_ip(request: Request) -> str:
    """Extract real client IP, respecting X-Forwarded-For from Nginx."""
    xff = request.headers.get("X-Forwarded-For")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
