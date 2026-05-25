"""
Integration tests — verify live connectivity to Postgres and Redis.

These run in CI against real service containers (see ci.yml services block).
They are skipped automatically when DATABASE_URL / REDIS_URL are not set so
they never block local development without the backing services.
"""

from __future__ import annotations

import os

import pytest


@pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="DATABASE_URL not set")
@pytest.mark.asyncio
async def test_postgres_connectivity() -> None:
    """Open an asyncpg connection and run a trivial query."""
    import asyncpg  # type: ignore[import]

    url = os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://")
    conn = await asyncpg.connect(url)
    try:
        result = await conn.fetchval("SELECT 1")
        assert result == 1
    finally:
        await conn.close()


@pytest.mark.skipif(not os.getenv("REDIS_URL"), reason="REDIS_URL not set")
@pytest.mark.asyncio
async def test_redis_connectivity() -> None:
    """Ping the Redis server and verify it responds."""
    import redis.asyncio as aioredis  # type: ignore[import]

    client = aioredis.from_url(os.environ["REDIS_URL"])
    try:
        pong = await client.ping()
        assert pong is True
    finally:
        await client.aclose()
