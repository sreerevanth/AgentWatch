"""Rate Limiting Middleware

Per-user and global rate limiting to prevent denial of service attacks
on API endpoints.
"""

from __future__ import annotations

import time
from collections import defaultdict
from typing import Any

from fastapi import Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class RateLimiter:
    """Per-user and global rate limiting."""

    def __init__(
        self, user_limit: int = 100, global_limit: int = 10000, window_sec: int = 3600
    ) -> None:
        """Initialize rate limiter with configurable limits.

        Args:
            user_limit: Maximum requests per user per window (default: 100)
            global_limit: Maximum requests globally per window (default: 10000)
            window_sec: Time window in seconds (default: 3600 / 1 hour)
        """
        self.user_limit = user_limit
        self.global_limit = global_limit
        self.window_sec = window_sec
        self.user_buckets: dict[str, dict[str, Any]] = defaultdict(
            lambda: {"count": 0, "start": time.time()}
        )
        self.global_bucket: dict[str, Any] = {"count": 0, "start": time.time()}

    def check_rate_limit(self, user_id: str) -> tuple[bool, dict[str, int]]:
        """Check if user and global limits are not exceeded.

        Args:
            user_id: The user identifier

        Returns:
            Tuple of (is_allowed, quota_info) where quota_info contains:
            - user_limit, user_remaining, global_limit, global_remaining
        """
        now = time.time()

        # Reset global bucket if window expired
        if now - self.global_bucket["start"] > self.window_sec:
            self.global_bucket["count"] = 0
            self.global_bucket["start"] = now

        # Reset user bucket if window expired
        user_bucket = self.user_buckets[user_id]
        if now - user_bucket["start"] > self.window_sec:
            user_bucket["count"] = 0
            user_bucket["start"] = now

        # Increment counters
        self.global_bucket["count"] += 1
        user_bucket["count"] += 1

        # Check limits
        user_allowed = user_bucket["count"] <= self.user_limit
        global_allowed = self.global_bucket["count"] <= self.global_limit

        quota_info = {
            "user_limit": self.user_limit,
            "user_remaining": max(0, self.user_limit - user_bucket["count"]),
            "global_limit": self.global_limit,
            "global_remaining": max(0, self.global_limit - self.global_bucket["count"]),
        }

        return user_allowed and global_allowed, quota_info

    def get_remaining_quota(self, user_id: str) -> dict[str, int]:
        """Get current remaining quota for user without incrementing.

        Args:
            user_id: The user identifier

        Returns:
            Dictionary with user and global remaining quota
        """
        now = time.time()

        # Check if buckets need reset (but don't actually reset)
        user_bucket = self.user_buckets[user_id]
        global_count = (
            0
            if now - self.global_bucket["start"] > self.window_sec
            else self.global_bucket["count"]
        )
        user_count = 0 if now - user_bucket["start"] > self.window_sec else user_bucket["count"]

        return {
            "user_limit": self.user_limit,
            "user_remaining": max(0, self.user_limit - user_count),
            "global_limit": self.global_limit,
            "global_remaining": max(0, self.global_limit - global_count),
        }


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce rate limits on API requests."""

    def __init__(self, app, limiter: RateLimiter) -> None:
        """Initialize middleware with rate limiter instance.

        Args:
            app: FastAPI application
            limiter: RateLimiter instance to use for all requests
        """
        super().__init__(app)
        self.limiter = limiter

    async def dispatch(self, request: Request, call_next):
        """Process request and enforce rate limits.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler in chain

        Returns:
            Response with rate limit headers, or 429 if limit exceeded
        """
        # Extract user ID from request (from Authorization header or IP)
        user_id = self._extract_user_id(request)

        # Check rate limits
        allowed, quota = self.limiter.check_rate_limit(user_id)

        # Store quota info in request state for response headers
        request.state.rate_limit_quota = quota
        request.state.rate_limit_allowed = allowed

        if not allowed:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"error": "rate_limit_exceeded"},
                headers=self._build_rate_limit_headers(quota),
            )

        # Continue with request
        response = await call_next(request)

        # Add rate limit headers to response
        response.headers.update(self._build_rate_limit_headers(quota))

        return response

    def _extract_user_id(self, request: Request) -> str:
        """Extract user ID from request.

        Args:
            request: HTTP request object

        Returns:
            User ID string (from Authorization header or IP address)
        """
        # Try to get from Authorization header first
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            return auth_header[7:]

        # Fall back to client IP address
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()

        if request.client:
            return request.client.host

        return "unknown"

    def _build_rate_limit_headers(self, quota: dict[str, int]) -> dict[str, str]:
        """Build HTTP headers with rate limit info.

        Args:
            quota: Rate limit quota dictionary from limiter

        Returns:
            Dictionary of rate limit headers
        """
        return {
            "X-RateLimit-User-Limit": str(quota["user_limit"]),
            "X-RateLimit-User-Remaining": str(quota["user_remaining"]),
            "X-RateLimit-Global-Limit": str(quota["global_limit"]),
            "X-RateLimit-Global-Remaining": str(quota["global_remaining"]),
        }
