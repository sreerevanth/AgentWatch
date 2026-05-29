"""
AgentWatch API Server
FastAPI-based REST API for observability dashboard, CLI, integrations.
"""

from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, AsyncContextManager, Callable

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from agentwatch.core.event_bus import get_event_bus
from agentwatch.core.schema import AgentEvent

logger = logging.getLogger(__name__)

_RATE_READ  = os.getenv("API_RATE_LIMIT_READ",  "1000/minute")
_RATE_WRITE = os.getenv("API_RATE_LIMIT_WRITE", "200/minute")

limiter = Limiter(key_func=get_remote_address, default_limits=[_RATE_READ])

def _rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Return a JSON 429 with standard rate-limit headers."""
    retry_after = getattr(exc, "retry_after", 60)
    limit       = getattr(exc, "limit", None)
    limit_value = str(limit.limit) if limit else _RATE_READ

    response = JSONResponse(
        status_code=429,
        content={"error": "rate_limit_exceeded"},
    )
    response.headers["Retry-After"]          = str(retry_after)
    response.headers["X-RateLimit-Limit"]    = limit_value
    response.headers["X-RateLimit-Remaining"] = "0"
    return response

SessionFactory = Callable[[], AsyncContextManager[Any]]
_db_session_factory: SessionFactory | None = None

_DB_HEALTH_TTL = 10

@dataclass
class DbHealthCache:
    status: str = "unknown"
    checked_at: datetime | None = None

_db_health = DbHealthCache()

def set_session_factory(factory: SessionFactory) -> None:
    """Wire up the DB session factory at startup (e.g. from lifespan or tests)."""
    global _db_session_factory
    _db_session_factory = factory

def _event_to_pg(event: AgentEvent) -> dict[str, Any]:
    data: dict[str, Any] = {
        "event_id": event.event_id,
        "session_id": event.session_id,
        "agent_id": event.agent_id,
        "framework": event.framework.value,
        "event_type": event.event_type.value,
        "status": event.status.value,
        "step_number": event.step_number,
        "timestamp": event.timestamp,
        "goal": event.goal,
        "duration_ms": event.duration_ms,
        "task_id": event.task_id,
        "trace_id": event.trace_id,
        "parent_event_id": event.parent_event_id,
        "prompt_preview": event.prompt_preview,
        "planner_output_preview": event.planner_output_preview,
        "event_metadata": event.metadata or {},
        "tags": list(event.tags) if event.tags else [],
    }

    if event.tool_call:
        data["tool_name"] = event.tool_call.tool_name
        data["tool_raw_command"] = event.tool_call.raw_command
        data["tool_arguments"] = dict(event.tool_call.arguments or {})

    if event.tool_result:
        data["tool_output"] = event.tool_result.output
        data["tool_error"] = event.tool_result.error

    if event.safety:
        data["risk_level"] = str(event.safety.risk_level)
        data["risk_score"] = event.safety.risk_score
        data["safety_blocked"] = event.safety.blocked
        data["safety_reasons"] = list(event.safety.reasons or [])

    if event.token_usage:
        data["prompt_tokens"] = event.token_usage.prompt_tokens
        data["completion_tokens"] = event.token_usage.completion_tokens
        data["total_tokens"] = event.token_usage.total_tokens
        data["estimated_cost_usd"] = event.token_usage.estimated_cost_usd

    if event.confidence:
        data["confidence_score"] = event.confidence.overall_score
        data["anomaly_flags"] = list(event.confidence.anomaly_flags or [])

    return data

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("AgentWatch API starting up")
    yield
    logger.info("AgentWatch API shutting down")

app = FastAPI(
    title="AgentWatch API",
    version="0.1.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

@app.get("/health")
@limiter.limit(_RATE_READ)
async def health(request: Request) -> dict[str, Any]:
    now = datetime.now(UTC)

    stale = (
        _db_health.checked_at is None
        or (now - _db_health.checked_at).total_seconds() > _DB_HEALTH_TTL
    )

    if _db_session_factory is None:
        _db_health.status = "in-memory"
    elif stale:
        try:
            async with _db_session_factory() as db:
                await db.execute(text("SELECT 1"))
            _db_health.status = "ok"
        except SQLAlchemyError:
            _db_health.status = "error"

    _db_health.checked_at = now

    return {
        "status": "ok",
        "version": "0.1.0",
        "timestamp": now.isoformat(),
        "db": _db_health.status,
    }

_ws_clients: set[WebSocket] = set()
_ws_lock = asyncio.Lock()

async def _safe_ws_remove(ws: WebSocket) -> None:
    async with _ws_lock:
        _ws_clients.discard(ws)

@app.websocket("/ws/events")
async def ws_events(ws: WebSocket) -> None:
    await ws.accept()

    async with _ws_lock:
        _ws_clients.add(ws)

    bus = get_event_bus()
    handler_id = f"ws-{id(ws)}"
    subscribed = False

    async def forward(event: AgentEvent) -> None:
        try:
            await ws.send_json(event.model_dump_for_storage())
        except Exception:
            await _safe_ws_remove(ws)
            if subscribed:
                try:
                    bus.unsubscribe(handler_id)
                except Exception:
                    pass

    try:
        bus.subscribe_fn(forward, handler_id=handler_id)
        subscribed = True

        while True:
            try:
                await asyncio.wait_for(ws.receive_text(), timeout=60)
            except asyncio.TimeoutError:
                continue

    except WebSocketDisconnect:
        pass

    finally:
        if subscribed:
            try:
                bus.unsubscribe(handler_id)
            except Exception:
                pass
        await _safe_ws_remove(ws)

def create_app() -> FastAPI:
    return app
