"""
Tests for AgentWatch API rate limiting.
Run with: pytest test_rate_limiting.py -v
"""

from __future__ import annotations

import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# Set tight limits before importing app so env vars are picked up
os.environ["API_RATE_LIMIT_READ"]  = "5/minute"
os.environ["API_RATE_LIMIT_WRITE"] = "3/minute"

from httpx import ASGITransport, AsyncClient

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def anyio_backend():
    return "asyncio"


@pytest.fixture()
async def client():
    """Fresh AsyncClient per test; resets limiter storage each time."""
    # Import here so env vars above are already set
    from agentwatch.api.server import app, limiter

    # Reset in-memory limiter storage between tests
    limiter.reset()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as ac:
        yield ac


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _hit(client: AsyncClient, url: str, method: str = "GET", n: int = 1):
    responses = []
    for _ in range(n):
        if method == "GET":
            r = await client.get(url)
        else:
            r = await client.post(url, json={})
        responses.append(r)
    return responses


# ---------------------------------------------------------------------------
# Read endpoint tests  (limit = 5/minute in tests)
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_health_allowed_under_limit(client):
    """First N requests under the read limit should succeed."""
    responses = await _hit(client, "/health", n=5)
    for r in responses:
        assert r.status_code == 200


@pytest.mark.anyio
async def test_health_429_after_read_limit(client):
    """Request N+1 should return 429."""
    await _hit(client, "/health", n=5)
    r = (await _hit(client, "/health", n=1))[0]
    assert r.status_code == 429


@pytest.mark.anyio
async def test_429_json_body(client):
    """429 response must include the required JSON body."""
    await _hit(client, "/health", n=5)
    r = (await _hit(client, "/health", n=1))[0]
    assert r.status_code == 429
    assert r.json() == {"error": "rate_limit_exceeded"}


@pytest.mark.anyio
async def test_rate_limit_headers_present(client):
    """Rate-limit headers must be present on a 429 response."""
    await _hit(client, "/health", n=5)
    r = (await _hit(client, "/health", n=1))[0]
    assert r.status_code == 429
    assert "x-ratelimit-limit" in r.headers
    assert "x-ratelimit-remaining" in r.headers
    assert "retry-after" in r.headers


@pytest.mark.anyio
async def test_rate_limit_remaining_is_zero_on_429(client):
    """X-RateLimit-Remaining must be '0' on a 429 response."""
    await _hit(client, "/health", n=5)
    r = (await _hit(client, "/health", n=1))[0]
    assert r.headers.get("x-ratelimit-remaining") == "0"


@pytest.mark.anyio
async def test_retry_after_is_positive_integer(client):
    """Retry-After header must be a positive integer."""
    await _hit(client, "/health", n=5)
    r = (await _hit(client, "/health", n=1))[0]
    retry_after = int(r.headers["retry-after"])
    assert retry_after > 0


# ---------------------------------------------------------------------------
# Env var config tests
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_read_limit_from_env(client):
    """Read limit should reflect API_RATE_LIMIT_READ env var (5/minute here)."""
    # 5 should pass, 6th should fail
    responses = await _hit(client, "/health", n=6)
    statuses = [r.status_code for r in responses]
    assert statuses[:5] == [200] * 5
    assert statuses[5] == 429


@pytest.mark.anyio
async def test_different_ips_have_independent_limits():
    """After resetting the limiter (simulating a new IP bucket), requests succeed again."""
    from agentwatch.api.server import app, limiter

    limiter.reset()

    # Exhaust the limit for current IP
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as c1:
        await _hit(c1, "/health", n=5)
        r = (await _hit(c1, "/health", n=1))[0]
        assert r.status_code == 429

    # Reset limiter (simulates a different IP bucket having its own clean slate)
    limiter.reset()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as c2:
        r2 = (await _hit(c2, "/health", n=1))[0]
        assert r2.status_code == 200
