"""
SAF-006 — Client-Side Adaptive Backoff and Rate-Limiting Policy.

Configurable rate-limiting and exponential backoff for the watch() wrapper.
Prevents AI agents in high-frequency tool loops from triggering API
rate-limit blocks or flooding target backends.

Usage::

    from agentwatch import watch
    from agentwatch.core.rate_limiter import RateLimitPolicy

    policy = RateLimitPolicy(max_calls=10, window_seconds=60, max_backoff=32.0)
    agent = watch(agent, rate_limit_policy=policy)

Or via environment variables::

    AGENTWATCH_RL_MAX_CALLS=10
    AGENTWATCH_RL_WINDOW_SECONDS=60
    AGENTWATCH_RL_MAX_BACKOFF=32.0
    AGENTWATCH_RL_ENABLED=true
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from dataclasses import dataclass, field
from threading import Lock
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class RateLimitPolicy:
    """
    Configurable client-side rate-limiting policy for the watch() wrapper.

    Attributes:
        max_calls:        Maximum tool calls allowed within ``window_seconds``.
        window_seconds:   Sliding window duration in seconds.
        base_backoff:     Initial backoff delay in seconds when rate limit is hit.
        max_backoff:      Maximum backoff cap in seconds (exponential growth is capped here).
        backoff_factor:   Multiplier applied on each consecutive backoff (default: 2.0).
        jitter:           If True, adds random jitter to backoff to prevent thundering herd.
        enabled:          If False, policy is a no-op (useful for testing/disabling at runtime).
    """

    max_calls: int = 60
    window_seconds: float = 60.0
    base_backoff: float = 1.0
    max_backoff: float = 32.0
    backoff_factor: float = 2.0
    jitter: bool = True
    enabled: bool = True

    @classmethod
    def from_env(cls) -> RateLimitPolicy:
        """Build a RateLimitPolicy from environment variables."""
        return cls(
            max_calls=int(os.getenv("AGENTWATCH_RL_MAX_CALLS", "60")),
            window_seconds=float(os.getenv("AGENTWATCH_RL_WINDOW_SECONDS", "60.0")),
            base_backoff=float(os.getenv("AGENTWATCH_RL_BASE_BACKOFF", "1.0")),
            max_backoff=float(os.getenv("AGENTWATCH_RL_MAX_BACKOFF", "32.0")),
            backoff_factor=float(os.getenv("AGENTWATCH_RL_BACKOFF_FACTOR", "2.0")),
            jitter=os.getenv("AGENTWATCH_RL_JITTER", "true").lower() == "true",
            enabled=os.getenv("AGENTWATCH_RL_ENABLED", "true").lower() == "true",
        )

    def __post_init__(self) -> None:
        if self.max_calls <= 0:
            raise ValueError("max_calls must be > 0")
        if self.window_seconds <= 0:
            raise ValueError("window_seconds must be > 0")
        if self.base_backoff < 0:
            raise ValueError("base_backoff must be >= 0")
        if self.max_backoff < self.base_backoff:
            raise ValueError("max_backoff must be >= base_backoff")
        if self.backoff_factor < 1.0:
            raise ValueError("backoff_factor must be >= 1.0")


class AdaptiveBackoffHandler:
    """
    Thread-safe sliding-window rate limiter with exponential backoff.

    - Tracks call timestamps in a sliding window.
    - When the window is full, computes backoff delay and either sleeps
      (sync) or awaits (async) before allowing the call through.
    - Backoff grows exponentially on consecutive limit hits, capped at
      ``policy.max_backoff``.
    - Optional jitter prevents thundering-herd when multiple agents share
      the same policy instance.
    """

    def __init__(self, policy: RateLimitPolicy) -> None:
        self.policy = policy
        self._lock = Lock()
        self._call_timestamps: list[float] = []
        self._consecutive_hits: int = 0

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _prune_window(self, now: float) -> None:
        """Remove timestamps outside the current sliding window."""
        cutoff = now - self.policy.window_seconds
        self._call_timestamps = [t for t in self._call_timestamps if t >= cutoff]

    def _compute_backoff(self) -> float:
        """Return the current backoff delay in seconds."""
        import random

        delay = min(
            self.policy.base_backoff * (self.policy.backoff_factor ** self._consecutive_hits),
            self.policy.max_backoff,
        )
        if self.policy.jitter:
            delay *= 0.5 + random.random() * 0.5  # uniform [0.5*delay, delay]
        return delay

    def _record_call(self, now: float) -> None:
        """Register a successful (non-blocked) call."""
        self._call_timestamps.append(now)

    def _is_limited(self, now: float) -> bool:
        """Return True if the call should be rate-limited right now."""
        self._prune_window(now)
        return len(self._call_timestamps) >= self.policy.max_calls

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def check_sync(self, tool_name: str = "") -> None:
        """
        Synchronous rate-limit check.  Blocks (sleeps) if rate limit is hit.
        Call this before every tool invocation in sync wrapped methods.
        """
        if not self.policy.enabled:
            return

        with self._lock:
            now = time.monotonic()
            if self._is_limited(now):
                delay = self._compute_backoff()
                self._consecutive_hits += 1
                logger.warning(
                    "AgentWatch rate limit hit for tool %r — backing off %.2fs "
                    "(consecutive hits: %d)",
                    tool_name,
                    delay,
                    self._consecutive_hits,
                )
            else:
                self._consecutive_hits = 0
                delay = 0.0

            self._record_call(now)

        if delay > 0:
            time.sleep(delay)

    async def check_async(self, tool_name: str = "") -> None:
        """
        Async rate-limit check.  Awaits (non-blocking sleep) if rate limit is hit.
        Call this before every tool invocation in async wrapped methods.
        """
        if not self.policy.enabled:
            return

        with self._lock:
            now = time.monotonic()
            if self._is_limited(now):
                delay = self._compute_backoff()
                self._consecutive_hits += 1
                logger.warning(
                    "AgentWatch rate limit hit for tool %r — backing off %.2fs "
                    "(consecutive hits: %d)",
                    tool_name,
                    delay,
                    self._consecutive_hits,
                )
            else:
                self._consecutive_hits = 0
                delay = 0.0

            self._record_call(now)

        if delay > 0:
            await asyncio.sleep(delay)

    def reset(self) -> None:
        """Reset internal state — useful for testing."""
        with self._lock:
            self._call_timestamps.clear()
            self._consecutive_hits = 0

    @property
    def current_call_count(self) -> int:
        """Number of calls recorded in the current window (thread-safe read)."""
        with self._lock:
            self._prune_window(time.monotonic())
            return len(self._call_timestamps)

    @property
    def consecutive_hits(self) -> int:
        """Number of consecutive rate-limit hits (resets on a non-limited call)."""
        with self._lock:
            return self._consecutive_hits


__all__ = ["RateLimitPolicy", "AdaptiveBackoffHandler"]
