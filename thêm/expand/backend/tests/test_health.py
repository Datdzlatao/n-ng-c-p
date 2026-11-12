"""
tests/test_health.py — Health check endpoints
"""

def test_liveness(client):
    res = client.get("/health/live")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "alive"
    assert "uptime_seconds" in data

def test_readiness_ok(client):
    res = client.get("/health/ready")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ready"
    assert data["checks"]["database"] == "ok"

def test_root_returns_api_info(client):
    res = client.get("/")
    assert res.status_code == 200
    assert "version" in res.json()
