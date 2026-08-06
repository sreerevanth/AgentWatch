"""Sliding window rate limiter algorithm.

Provides a more accurate rate limiting approach compared to the existing
fixed-window implementation in api/middleware/rate_limiter.py. The sliding
window algorithm prevents burst traffic at window boundaries by counting
requests across a rolling time window.
"""

from __future__ import annotations

import collections
import threading
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SlidingWindowConfig:
    window_seconds: float = 60.0
    max_requests: int = 100
    burst_allowance: int = 0
    cleanup_interval: float = 30.0


@dataclass
class RateLimitResult:
    allowed: bool
    current_count: int
    max_requests: int
    window_seconds: float
    retry_after_seconds: float = 0.0
    remaining: int = 0
    reset_at: float = 0.0

    def to_headers(self) -> dict[str, str]:
        headers = {
            "X-RateLimit-Limit": str(self.max_requests),
            "X-RateLimit-Remaining": str(max(0, self.remaining)),
            "X-RateLimit-Reset": str(int(self.reset_at)),
        }
        if not self.allowed:
            headers["Retry-After"] = str(int(self.retry_after_seconds) + 1)
        return headers

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "current_count": self.current_count,
            "max_requests": self.max_requests,
            "window_seconds": self.window_seconds,
            "retry_after_seconds": self.retry_after_seconds,
            "remaining": self.remaining,
            "reset_at": self.reset_at,
        }


class SlidingWindowCounter:
    """Sliding window counter using a circular buffer of timestamps.

    Tracks request timestamps within a rolling window and counts
    requests that fall within the current window period.
    """

    def __init__(self, window_seconds: float, max_requests: int) -> None:
        self.window_seconds = window_seconds
        self.max_requests = max_requests
        self._timestamps: collections.deque[float] = collections.deque()
        self._lock = threading.Lock()

    def _cleanup(self, now: float) -> None:
        cutoff = now - self.window_seconds
        while self._timestamps and self._timestamps[0] <= cutoff:
            self._timestamps.popleft()

    def record(self, now: float | None = None) -> RateLimitResult:
        now = now or time.time()
        with self._lock:
            self._cleanup(now)
            current_count = len(self._timestamps)
            if current_count >= self.max_requests:
                oldest = self._timestamps[0]
                retry_after = oldest + self.window_seconds - now
                return RateLimitResult(
                    allowed=False,
                    current_count=current_count,
                    max_requests=self.max_requests,
                    window_seconds=self.window_seconds,
                    retry_after_seconds=max(0.0, retry_after),
                    remaining=0,
                    reset_at=oldest + self.window_seconds,
                )
            self._timestamps.append(now)
            remaining = self.max_requests - current_count - 1
            return RateLimitResult(
                allowed=True,
                current_count=current_count + 1,
                max_requests=self.max_requests,
                window_seconds=self.window_seconds,
                remaining=remaining,
                reset_at=now + self.window_seconds,
            )

    def count(self, now: float | None = None) -> int:
        now = now or time.time()
        with self._lock:
            self._cleanup(now)
            return len(self._timestamps)

    def reset(self) -> None:
        with self._lock:
            self._timestamps.clear()

    @property
    def is_empty(self) -> bool:
        return len(self._timestamps) == 0


class SlidingWindowRateLimiter:
    """Per-key sliding window rate limiter.

    Tracks rate limits independently for each key (e.g., IP address,
    user ID, API key). Supports both in-memory and pluggable backends.
    """

    def __init__(self, config: SlidingWindowConfig | None = None) -> None:
        self._config = config or SlidingWindowConfig()
        self._windows: dict[str, SlidingWindowCounter] = {}
        self._lock = threading.Lock()
        self._last_cleanup = time.time()

    @property
    def config(self) -> SlidingWindowConfig:
        return self._config

    def _get_window(self, key: str) -> SlidingWindowCounter:
        if key not in self._windows:
            self._windows[key] = SlidingWindowCounter(
                window_seconds=self._config.window_seconds,
                max_requests=self._config.max_requests,
            )
        return self._windows[key]

    def check(self, key: str) -> RateLimitResult:
        self._maybe_cleanup()
        with self._lock:
            window = self._get_window(key)
        return window.record()

    def count(self, key: str) -> int:
        self._maybe_cleanup()
        with self._lock:
            if key not in self._windows:
                return 0
            return self._windows[key].count()

    def reset(self, key: str | None = None) -> None:
        with self._lock:
            if key:
                if key in self._windows:
                    self._windows[key].reset()
            else:
                self._windows.clear()

    def _maybe_cleanup(self) -> None:
        now = time.time()
        if now - self._last_cleanup < self._config.cleanup_interval:
            return
        with self._lock:
            self._last_cleanup = now
            empty_keys = [
                k for k, w in self._windows.items() if w.is_empty
            ]
            for k in empty_keys:
                del self._windows[k]

    def get_stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "total_keys": len(self._windows),
                "config": {
                    "window_seconds": self._config.window_seconds,
                    "max_requests": self._config.max_requests,
                },
            }

    def list_keys(self) -> list[str]:
        with self._lock:
            return list(self._windows.keys())


class SlidingWindowRateLimitMiddleware:
    """ASGI middleware for sliding window rate limiting.

    Integrates with FastAPI/Starlette applications.
    """

    def __init__(
        self,
        app: Any,
        limiter: SlidingWindowRateLimiter | None = None,
        key_func: Any = None,
        exempt_paths: list[str] | None = None,
    ) -> None:
        self.app = app
        self.limiter = limiter or SlidingWindowRateLimiter()
        self.key_func = key_func
        self.exempt_paths = exempt_paths or []

    async def __call__(self, scope: dict, receive: Any, send: Any) -> None:
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if any(path.startswith(ep) for ep in self.exempt_paths):
            await self.app(scope, receive, send)
            return

        client = scope.get("client")
        key = "unknown"
        if client:
            key = client[0]
        if self.key_func:
            key = self.key_func(scope)

        result = self.limiter.check(key)

        if not result.allowed:
            from starlette.responses import JSONResponse
            response = JSONResponse(
                status_code=429,
                content={"error": "Rate limit exceeded", "retry_after": result.retry_after_seconds},
                headers=result.to_headers(),
            )
            await response(scope, receive, send)
            return

        scope["state"] = scope.get("state", {})
        scope["state"]["rate_limit"] = result.to_dict()

        await self.app(scope, receive, send)
