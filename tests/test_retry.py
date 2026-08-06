"""Tests for retry decorator with exponential backoff."""

from __future__ import annotations

import asyncio
import time

import pytest

from agentwatch.core.retry import (
    RetryExhausted,
    RetryStats,
    _compute_delay,
    retry,
    retry_async,
)


def test_compute_delay_basic():
    d = _compute_delay(1, 1.0, 60.0, 2.0, jitter=False)
    assert d == 1.0


def test_compute_delay_exponential():
    d1 = _compute_delay(1, 1.0, 60.0, 2.0, jitter=False)
    d2 = _compute_delay(2, 1.0, 60.0, 2.0, jitter=False)
    d3 = _compute_delay(3, 1.0, 60.0, 2.0, jitter=False)
    assert d1 == 1.0
    assert d2 == 2.0
    assert d3 == 4.0


def test_compute_delay_capped_at_max():
    d = _compute_delay(10, 1.0, 5.0, 2.0, jitter=False)
    assert d == 5.0


def test_compute_delay_jitter_range():
    delays = [_compute_delay(1, 1.0, 60.0, 2.0, jitter=True) for _ in range(100)]
    assert all(0.5 <= d <= 1.0 for d in delays)


def test_retry_max_attempts_must_be_positive():
    with pytest.raises(ValueError):
        retry(max_attempts=0)


# --- Sync tests ---


def test_sync_no_retry_needed():
    call_count = 0

    @retry(max_attempts=3, base_delay=0.01)
    def _ok():
        nonlocal call_count
        call_count += 1
        return "ok"

    result = _ok()
    assert result == "ok"
    assert call_count == 1


def test_sync_retries_on_exception():
    call_count = 0

    @retry(max_attempts=3, base_delay=0.01, jitter=False)
    def _fail_twice():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ValueError("not yet")
        return "done"

    result = _fail_twice()
    assert result == "done"
    assert call_count == 3


def test_sync_exhausted():
    @retry(max_attempts=2, base_delay=0.01, jitter=False)
    def _always_fail():
        raise RuntimeError("always")

    with pytest.raises(RetryExhausted) as exc_info:
        _always_fail()
    assert exc_info.value.attempts == 2
    assert isinstance(exc_info.value.last_exception, RuntimeError)


def test_sync_selective_retryable_exceptions():
    call_count = 0

    @retry(
        max_attempts=3,
        base_delay=0.01,
        jitter=False,
        retryable_exceptions=(ValueError,),
    )
    def _type_error():
        nonlocal call_count
        call_count += 1
        raise TypeError("not retryable")

    with pytest.raises(TypeError):
        _type_error()
    assert call_count == 1


def test_sync_on_retry_callback():
    retry_log = []

    @retry(max_attempts=3, base_delay=0.01, jitter=False, on_retry=lambda a, e, d: retry_log.append((a, str(e), d)))
    def _fail_once():
        if len(retry_log) == 0:
            raise ValueError("first")
        return "ok"

    result = _fail_once()
    assert result == "ok"
    assert len(retry_log) == 1
    assert retry_log[0][0] == 1
    assert "first" in retry_log[0][1]


# --- Async tests ---


@pytest.mark.asyncio
async def test_async_no_retry_needed():
    call_count = 0

    @retry(max_attempts=3, base_delay=0.01)
    async def _ok():
        nonlocal call_count
        call_count += 1
        return "ok"

    result = await _ok()
    assert result == "ok"
    assert call_count == 1


@pytest.mark.asyncio
async def test_async_retries_on_exception():
    call_count = 0

    @retry(max_attempts=3, base_delay=0.01, jitter=False)
    async def _fail_twice():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ValueError("not yet")
        return "done"

    result = await _fail_twice()
    assert result == "done"
    assert call_count == 3


@pytest.mark.asyncio
async def test_async_exhausted():
    @retry(max_attempts=2, base_delay=0.01, jitter=False)
    async def _always_fail():
        raise RuntimeError("always")

    with pytest.raises(RetryExhausted) as exc_info:
        await _always_fail()
    assert exc_info.value.attempts == 2


@pytest.mark.asyncio
async def test_async_on_retry_callback():
    retry_log = []

    @retry(
        max_attempts=3,
        base_delay=0.01,
        jitter=False,
        on_retry=lambda a, e, d: retry_log.append((a, str(e), d)),
    )
    async def _fail_once():
        if len(retry_log) == 0:
            raise ValueError("first")
        return "ok"

    result = await _fail_once()
    assert result == "ok"
    assert len(retry_log) == 1


# --- retry_async programmatic ---


@pytest.mark.asyncio
async def test_retry_async_programmatic():
    call_count = 0

    async def _func():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ValueError("nope")
        return 42

    result = await retry_async(_func, max_attempts=3, base_delay=0.01, jitter=False)
    assert result == 42
    assert call_count == 3


@pytest.mark.asyncio
async def test_retry_async_programmatic_exhausted():
    async def _fail():
        raise RuntimeError("nope")

    with pytest.raises(RetryExhausted):
        await retry_async(_fail, max_attempts=2, base_delay=0.01, jitter=False)


def test_retry_async_max_attempts_validation():
    with pytest.raises(ValueError):
        asyncio.run(retry_async(lambda: None, max_attempts=0))


# --- Stats ---


def test_retry_stats_defaults():
    s = RetryStats()
    assert s.attempts == 0
    assert s.total_delay_ms == 0.0
    assert s.exceptions == []
    assert s.succeeded is False
