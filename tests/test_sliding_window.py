"""Tests for sliding window rate limiter."""

from __future__ import annotations

import time

import pytest

from agentwatch.security.sliding_window import (
    RateLimitResult,
    SlidingWindowConfig,
    SlidingWindowCounter,
    SlidingWindowRateLimiter,
)


def test_sliding_window_counter_allows_within_limit():
    counter = SlidingWindowCounter(window_seconds=1.0, max_requests=5)
    for i in range(5):
        result = counter.record(now=1000.0 + i * 0.1)
        assert result.allowed is True
        assert result.current_count == i + 1


def test_sliding_window_counter_blocks_at_limit():
    counter = SlidingWindowCounter(window_seconds=1.0, max_requests=3)
    counter.record(now=1000.0)
    counter.record(now=1000.1)
    result = counter.record(now=1000.2)
    assert result.allowed is True
    result = counter.record(now=1000.3)
    assert result.allowed is False
    assert result.retry_after_seconds > 0


def test_sliding_window_counter_window_expiry():
    counter = SlidingWindowCounter(window_seconds=1.0, max_requests=2)
    counter.record(now=1000.0)
    counter.record(now=1000.5)
    result = counter.record(now=1000.3)
    assert result.allowed is False
    result = counter.record(now=1001.1)
    assert result.allowed is True


def test_sliding_window_counter_remaining():
    counter = SlidingWindowCounter(window_seconds=1.0, max_requests=5)
    result = counter.record(now=1000.0)
    assert result.remaining == 4


def test_sliding_window_counter_reset():
    counter = SlidingWindowCounter(window_seconds=1.0, max_requests=2)
    counter.record(now=1000.0)
    counter.record(now=1000.1)
    result = counter.record(now=1000.2)
    assert result.allowed is False
    counter.reset()
    assert counter.count(now=1000.2) == 0
    result = counter.record(now=1000.2)
    assert result.allowed is True


def test_sliding_window_counter_count():
    counter = SlidingWindowCounter(window_seconds=1.0, max_requests=10)
    counter.record(now=1000.0)
    counter.record(now=1000.5)
    assert counter.count(now=1000.5) == 2
    assert counter.count(now=1001.1) == 0


def test_sliding_window_counter_is_empty():
    counter = SlidingWindowCounter(window_seconds=1.0, max_requests=5)
    assert counter.is_empty is True
    counter.record(now=1000.0)
    assert counter.is_empty is False


# --- SlidingWindowRateLimiter tests ---


def test_rate_limiter_per_key():
    limiter = SlidingWindowRateLimiter(SlidingWindowConfig(window_seconds=1.0, max_requests=2))
    r1 = limiter.check("ip-1")
    r2 = limiter.check("ip-1")
    r3 = limiter.check("ip-1")
    assert r1.allowed is True
    assert r2.allowed is True
    assert r3.allowed is False
    r_other = limiter.check("ip-2")
    assert r_other.allowed is True


def test_rate_limiter_reset_key():
    limiter = SlidingWindowRateLimiter(SlidingWindowConfig(window_seconds=1.0, max_requests=1))
    limiter.check("k")
    result = limiter.check("k")
    assert result.allowed is False
    limiter.reset("k")
    result = limiter.check("k")
    assert result.allowed is True


def test_rate_limiter_reset_all():
    limiter = SlidingWindowRateLimiter(SlidingWindowConfig(window_seconds=1.0, max_requests=1))
    limiter.check("a")
    limiter.check("b")
    limiter.reset()
    assert limiter.count("a") == 0
    assert limiter.count("b") == 0


def test_rate_limiter_get_stats():
    limiter = SlidingWindowRateLimiter(SlidingWindowConfig(window_seconds=60.0, max_requests=100))
    limiter.check("x")
    stats = limiter.get_stats()
    assert stats["total_keys"] == 1
    assert stats["config"]["window_seconds"] == 60.0


def test_rate_limiter_list_keys():
    limiter = SlidingWindowRateLimiter()
    limiter.check("a")
    limiter.check("b")
    keys = limiter.list_keys()
    assert "a" in keys
    assert "b" in keys


# --- RateLimitResult tests ---


def test_result_to_headers():
    result = RateLimitResult(
        allowed=True, current_count=5, max_requests=10,
        window_seconds=60.0, remaining=5, reset_at=1000.0,
    )
    headers = result.to_headers()
    assert headers["X-RateLimit-Limit"] == "10"
    assert headers["X-RateLimit-Remaining"] == "5"


def test_result_to_headers_blocked():
    result = RateLimitResult(
        allowed=False, current_count=10, max_requests=10,
        window_seconds=60.0, retry_after_seconds=5.5, remaining=0,
        reset_at=1000.0,
    )
    headers = result.to_headers()
    assert "Retry-After" in headers
    assert headers["Retry-After"] == "6"


def test_result_to_dict():
    result = RateLimitResult(
        allowed=True, current_count=1, max_requests=10,
        window_seconds=60.0, remaining=9, reset_at=1000.0,
    )
    d = result.to_dict()
    assert d["allowed"] is True
    assert d["current_count"] == 1
    assert d["remaining"] == 9


# --- Cleanup tests ---


def test_cleanup_removes_old_keys():
    limiter = SlidingWindowRateLimiter(
        SlidingWindowConfig(window_seconds=1.0, max_requests=10, cleanup_interval=0.0)
    )
    limiter.check("expired")
    assert limiter.count("expired") == 1
    limiter._maybe_cleanup()
    assert limiter.count("expired") == 0


# --- Window expiry boundary ---


def test_boundary_no_double_counting():
    counter = SlidingWindowCounter(window_seconds=1.0, max_requests=3)
    counter.record(now=1000.0)
    counter.record(now=1000.99)
    counter.record(now=1001.01)
    assert counter.count(now=1001.01) == 2
