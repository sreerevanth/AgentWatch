"""Tests for per-IP rate limiting on the AgentWatch API."""

import os

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def rate_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """Fresh limiter with a low write cap so 429 is reachable quickly."""
    monkeypatch.setenv("API_RATE_LIMIT_WRITE", "10")
    monkeypatch.setenv("API_RATE_LIMIT_READ", "1000")
    monkeypatch.delenv("AGENTWATCH_API_KEY", raising=False)
    monkeypatch.delenv("AGENTWATCH_ENV", raising=False)

    import agentwatch.api.server as server

    server.RATE_WRITE = int(os.getenv("API_RATE_LIMIT_WRITE", "10"))
    server.RATE_READ = int(os.getenv("API_RATE_LIMIT_READ", "1000"))
    server.reset_rate_limiter_for_tests()

    return TestClient(server.app, raise_server_exceptions=False)


def test_read_endpoint_returns_rate_limit_headers(rate_client: TestClient) -> None:
    r = rate_client.get("/health")
    assert r.status_code == 200, r.text
    assert "X-RateLimit-Limit" in r.headers
    assert "X-RateLimit-Remaining" in r.headers


def test_write_endpoint_returns_429_after_limit(rate_client: TestClient) -> None:
    last_status = None
    for i in range(25):
        r = rate_client.post(
            "/api/v1/sessions",
            json={
                "session_id": f"test-{i}",
                "agent_id": "agent-1",
                "agent_name": "Test",
                "framework": "claude_code",
                "status": "running",
            },
        )
        last_status = r.status_code
        if r.status_code == 429:
            break
    assert last_status == 429, (
        f"Expected 429 after exceeding write limit, last status was {last_status}"
    )


def test_429_body_matches_spec(rate_client: TestClient) -> None:
    last = None
    for i in range(25):
        last = rate_client.post(
            "/api/v1/sessions",
            json={
                "session_id": f"spec-{i}",
                "agent_id": "agent-1",
                "agent_name": "Test",
                "framework": "claude_code",
                "status": "running",
            },
        )
        if last.status_code == 429:
            break
    assert last is not None, "No responses received from write endpoint"
    assert last.status_code == 429, "Expected a 429 response but none was returned"
    assert last.json() == {"error": "rate_limit_exceeded"}
    assert "Retry-After" in last.headers


def test_client_ip_prefers_forwarded_for() -> None:
    import agentwatch.api.server as server

    class _Request:
        client = None
        headers = {"x-forwarded-for": "203.0.113.9, 70.41.3.18"}

    assert server._client_ip(_Request()) == "203.0.113.9"  # type: ignore[arg-type]


def test_limiter_prunes_stale_buckets() -> None:
    import time

    import agentwatch.api.server as server

    server.reset_rate_limiter_for_tests()
    server._limiter._buckets["stale-ip:w"] = {
        "count": 1,
        "start": time.time() - server.RATE_BUCKET_TTL_SEC - 1,
    }
    server._limiter._prune_stale(time.time())
    assert "stale-ip:w" not in server._limiter._buckets
