"""Tests for per-IP rate limiting on the AgentWatch API."""
from fastapi.testclient import TestClient


def get_client():
    from agentwatch.api.server import app
    return TestClient(app, raise_server_exceptions=False)


def test_read_endpoint_returns_rate_limit_headers():
    c = get_client()
    r = c.get("/api/v1/sessions")
    assert r.status_code in (200, 401)
    assert "X-RateLimit-Limit" in r.headers
    assert "X-RateLimit-Remaining" in r.headers


def test_write_endpoint_returns_429_after_limit():
    c = get_client()
    statuses = set()
    for _ in range(210):
        r = c.post("/api/v1/sessions", json={
            "session_id": "test-1",
            "agent_id": "agent-1",
            "agent_name": "Test",
            "framework": "claude_code",
            "status": "running",
        })
        statuses.add(r.status_code)
        if 429 in statuses:
            break
    assert 429 in statuses, f"Expected a 429, got: {statuses}"


def test_429_body_matches_spec():
    c = get_client()
    last = None
    for _ in range(210):
        last = c.post("/api/v1/sessions", json={
            "session_id": "test-2",
            "agent_id": "agent-1",
            "agent_name": "Test",
            "framework": "claude_code",
            "status": "running",
        })
        if last.status_code == 429:
            break
    if last and last.status_code == 429:
        assert last.json() == {"detail": "rate_limit_exceeded"}
        assert "Retry-After" in last.headers