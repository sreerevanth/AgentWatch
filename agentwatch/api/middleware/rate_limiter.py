"""Rate Limiting Middleware

Per-user and global rate limiting to prevent denial of service attacks
on API endpoints.
"""

from __future__ import annotations

import time
from collections import defaultdict
from typing import Any


class RateLimiter:
    """Per-user and global rate limiting."""

    def __init__(self, user_limit: int = 100, window_sec: int = 3600) -> None:
        """Initialize rate limiter with configurable limits.

        Args:
            user_limit: Maximum requests per user per window (default: 100)
            window_sec: Time window in seconds (default: 3600 / 1 hour)
        """
        self.user_limit = user_limit
        self.window_sec = window_sec
        self.user_buckets: dict[str, dict[str, Any]] = defaultdict(
            lambda: {"count": 0, "start": time.time()}
        )
        self.global_bucket: dict[str, Any] = {"count": 0, "start": time.time()}

    def check_rate_limit(self, user_id: str) -> bool:
        """Check if user has exceeded rate limit.

        Args:
            user_id: The user identifier

        Returns:
            True if under limit, False if limit exceeded
        """
        now = time.time()
        bucket = self.user_buckets[user_id]

        if now - bucket["start"] > self.window_sec:
            bucket["count"] = 0
            bucket["start"] = now

        bucket["count"] += 1
        return bucket["count"] <= self.user_limit
