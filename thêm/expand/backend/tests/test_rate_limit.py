"""
tests/test_rate_limit.py — Rate limiting unit tests
"""
import os
import pytest
from fastapi import HTTPException
from app.core.rate_limit import check_rate_limit

def test_rate_limiter_allows_under_limit():
    key = "test_ip_allow"
    # Should allow 3 calls with limit 3
    check_rate_limit(key, max_calls=3, window_seconds=10)
    check_rate_limit(key, max_calls=3, window_seconds=10)
    check_rate_limit(key, max_calls=3, window_seconds=10)

def test_rate_limiter_blocks_over_limit():
    key = "test_ip_block"
    # Temporarily ensure rate limiting is enabled
    old_val = os.environ.get("DISABLE_RATE_LIMIT")
    os.environ["DISABLE_RATE_LIMIT"] = "false"
    try:
        check_rate_limit(key, max_calls=2, window_seconds=10)
        check_rate_limit(key, max_calls=2, window_seconds=10)
        with pytest.raises(HTTPException) as exc_info:
            check_rate_limit(key, max_calls=2, window_seconds=10)
        assert exc_info.value.status_code == 429
    finally:
        if old_val is not None:
            os.environ["DISABLE_RATE_LIMIT"] = old_val
        else:
            os.environ.pop("DISABLE_RATE_LIMIT", None)
