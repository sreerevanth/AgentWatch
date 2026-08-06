"""FastAPI middleware for request correlation ID propagation.

Extracts or generates a correlation ID for each incoming request,
injects it into the logging context, and returns it in the response
headers for client-side tracing.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from agentwatch.core.logging import set_correlation_id, get_correlation_id

logger = logging.getLogger(__name__)

CORRELATION_ID_HEADER = "X-Correlation-ID"
DEFAULT_ID_LENGTH = 16


def generate_request_id() -> str:
    return uuid.uuid4().hex[:DEFAULT_ID_LENGTH]


class CorrelationMiddleware(BaseHTTPMiddleware):
    """Middleware that attaches a correlation ID to every request.

    - Extracts X-Correlation-ID from the incoming request header.
    - Generates a new one if not provided.
    - Sets it in the logging context (contextvars).
    - Returns it in the response header.
    """

    def __init__(self, app: Any, header_name: str = CORRELATION_ID_HEADER) -> None:
        super().__init__(app)
        self.header_name = header_name

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        cid = request.headers.get(self.header_name) or generate_request_id()
        set_correlation_id(cid)
        request.state.correlation_id = cid

        response = await call_next(request)
        response.headers[self.header_name] = cid

        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware that logs request start and completion with timing."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        import time
        start = time.monotonic()
        cid = getattr(request.state, "correlation_id", "")
        method = request.method
        path = request.url.path

        logger.info("Request started: %s %s (cid=%s)", method, path, cid)

        try:
            response = await call_next(request)
            elapsed = (time.monotonic() - start) * 1000
            logger.info(
                "Request completed: %s %s -> %d (%.1fms, cid=%s)",
                method, path, response.status_code, elapsed, cid,
            )
            response.headers["X-Response-Time"] = f"{elapsed:.1f}ms"
            return response
        except Exception as exc:
            elapsed = (time.monotonic() - start) * 1000
            logger.error(
                "Request failed: %s %s -> 500 (%.1fms, cid=%s): %s",
                method, path, elapsed, cid, exc,
            )
            raise


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Lightweight middleware that only adds a request ID header.

    For cases where full correlation context is not needed but a
    unique request identifier is still useful for support tickets.
    """

    def __init__(self, app: Any, header_name: str = "X-Request-ID") -> None:
        super().__init__(app)
        self.header_name = header_name

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get(self.header_name) or generate_request_id()
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers[self.header_name] = request_id
        return response
