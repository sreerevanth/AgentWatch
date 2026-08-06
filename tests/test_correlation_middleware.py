"""Tests for request correlation ID middleware."""

from __future__ import annotations

import pytest
from httpx import AsyncClient, ASGITransport

from agentwatch.api.middleware.correlation import (
    CORRELATION_ID_HEADER,
    CorrelationMiddleware,
    RequestIDMiddleware,
    RequestLoggingMiddleware,
    generate_request_id,
)
from agentwatch.core.logging import get_correlation_id, set_correlation_id
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route


async def _root(request):
    return JSONResponse({"status": "ok"})


async def _echo_correlation(request):
    cid = getattr(request.state, "correlation_id", None)
    return JSONResponse({"correlation_id": cid})


async def _echo_headers(request):
    return JSONResponse({
        "correlation": request.headers.get(CORRELATION_ID_HEADER),
        "request_id": request.headers.get("X-Request-ID"),
    })


def _make_app(middlewares=None):
    middlewares = middlewares or []
    app = Starlette(
        routes=[
            Route("/", _root),
            Route("/echo", _echo_correlation),
            Route("/headers", _echo_headers),
        ],
    )
    for mw in reversed(middlewares):
        app.add_middleware(mw)
    return app


def test_generate_request_id():
    rid = generate_request_id()
    assert isinstance(rid, str)
    assert len(rid) == 16
    assert all(c in "0123456789abcdef" for c in rid)


@pytest.mark.asyncio
async def test_correlation_middleware_generates_id():
    app = _make_app([CorrelationMiddleware])
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/echo")
    assert resp.status_code == 200
    data = resp.json()
    assert data["correlation_id"] is not None
    assert len(data["correlation_id"]) == 16
    assert CORRELATION_ID_HEADER in resp.headers


@pytest.mark.asyncio
async def test_correlation_middleware_preserves_existing():
    app = _make_app([CorrelationMiddleware])
    transport = ASGITransport(app=app)
    custom_id = "my-custom-cid-abc"
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/echo", headers={CORRELATION_ID_HEADER: custom_id})
    data = resp.json()
    assert data["correlation_id"] == custom_id
    assert resp.headers[CORRELATION_ID_HEADER] == custom_id


@pytest.mark.asyncio
async def test_correlation_middleware_returns_header():
    app = _make_app([CorrelationMiddleware])
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/")
    assert CORRELATION_ID_HEADER in resp.headers
    assert len(resp.headers[CORRELATION_ID_HEADER]) == 16


@pytest.mark.asyncio
async def test_request_logging_middleware():
    app = _make_app([CorrelationMiddleware, RequestLoggingMiddleware])
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/")
    assert "X-Response-Time" in resp.headers
    assert resp.headers["X-Response-Time"].endswith("ms")


@pytest.mark.asyncio
async def test_request_id_middleware_generates():
    app = _make_app([RequestIDMiddleware])
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/headers")
    data = resp.json()
    assert data["request_id"] is not None
    assert len(data["request_id"]) == 16
    assert "X-Request-ID" in resp.headers


@pytest.mark.asyncio
async def test_request_id_middleware_preserves():
    app = _make_app([RequestIDMiddleware])
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/headers", headers={"X-Request-ID": "my-req-id"})
    data = resp.json()
    assert data["request_id"] == "my-req-id"
    assert resp.headers["X-Request-ID"] == "my-req-id"


@pytest.mark.asyncio
async def test_multiple_requests_different_ids():
    app = _make_app([CorrelationMiddleware])
    transport = ASGITransport(app=app)
    ids = set()
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for _ in range(10):
            resp = await client.get("/echo")
            ids.add(resp.json()["correlation_id"])
    assert len(ids) == 10


@pytest.mark.asyncio
async def test_correlation_context_available_in_handler():
    app = _make_app([CorrelationMiddleware])
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/echo", headers={CORRELATION_ID_HEADER: "ctx-test"})
    assert resp.json()["correlation_id"] == "ctx-test"


@pytest.mark.asyncio
async def test_request_id_not_overwritten_by_correlation():
    app = _make_app([CorrelationMiddleware, RequestIDMiddleware])
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/headers", headers={
            CORRELATION_ID_HEADER: "corr-123",
            "X-Request-ID": "req-456",
        })
    data = resp.json()
    assert data["correlation"] == "corr-123"
    assert data["request_id"] == "req-456"
