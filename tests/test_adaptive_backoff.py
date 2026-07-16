"""Tests for client-side adaptive backoff and rate-limiting policy (Issue #527)."""
from __future__ import annotations

import time
import asyncio
import pytest

from agentwatch.core.rate_limiter import AdaptiveBackoffHandler, RateLimitPolicy


# ---------------------------------------------------------------------------
# RateLimitPolicy construction
# ---------------------------------------------------------------------------

def test_policy_defaults():
    policy = RateLimitPolicy()
    assert policy.max_calls == 60
    assert policy.window_seconds == 60.0
    assert policy.base_backoff == 1.0
    assert policy.max_backoff == 32.0
    assert policy.backoff_factor == 2.0
    assert policy.jitter is True
    assert policy.enabled is True


def test_policy_custom_values():
    policy = RateLimitPolicy(max_calls=10, window_seconds=5.0, base_backoff=0.1, max_backoff=2.0)
    assert policy.max_calls == 10
    assert policy.window_seconds == 5.0


def test_policy_invalid_max_calls():
    with pytest.raises(ValueError, match="max_calls"):
        RateLimitPolicy(max_calls=0)


def test_policy_invalid_window():
    with pytest.raises(ValueError, match="window_seconds"):
        RateLimitPolicy(window_seconds=-1.0)


def test_policy_invalid_max_backoff():
    with pytest.raises(ValueError, match="max_backoff"):
        RateLimitPolicy(base_backoff=5.0, max_backoff=1.0)


def test_policy_invalid_backoff_factor():
    with pytest.raises(ValueError, match="backoff_factor"):
        RateLimitPolicy(backoff_factor=0.5)


def test_policy_from_env(monkeypatch):
    monkeypatch.setenv("AGENTWATCH_RL_MAX_CALLS", "20")
    monkeypatch.setenv("AGENTWATCH_RL_WINDOW_SECONDS", "30.0")
    monkeypatch.setenv("AGENTWATCH_RL_MAX_BACKOFF", "16.0")
    monkeypatch.setenv("AGENTWATCH_RL_ENABLED", "true")
    policy = RateLimitPolicy.from_env()
    assert policy.max_calls == 20
    assert policy.window_seconds == 30.0
    assert policy.max_backoff == 16.0
    assert policy.enabled is True


def test_policy_from_env_disabled(monkeypatch):
    monkeypatch.setenv("AGENTWATCH_RL_ENABLED", "false")
    policy = RateLimitPolicy.from_env()
    assert policy.enabled is False


# ---------------------------------------------------------------------------
# AdaptiveBackoffHandler — basic tracking
# ---------------------------------------------------------------------------

def test_handler_tracks_call_count():
    policy = RateLimitPolicy(max_calls=5, window_seconds=10.0, base_backoff=0.0, max_backoff=0.0, jitter=False)
    handler = AdaptiveBackoffHandler(policy)
    for _ in range(3):
        handler.check_sync("test_tool")
    assert handler.current_call_count == 3


def test_handler_no_block_under_limit():
    """Calls under the limit should complete without sleeping."""
    policy = RateLimitPolicy(max_calls=10, window_seconds=60.0, base_backoff=0.0, max_backoff=0.0, jitter=False)
    handler = AdaptiveBackoffHandler(policy)
    start = time.monotonic()
    for _ in range(5):
        handler.check_sync("fast_tool")
    elapsed = time.monotonic() - start
    assert elapsed < 0.5, f"Should not block, but took {elapsed:.2f}s"


def test_handler_disabled_policy_is_noop():
    """Disabled policy should never block regardless of call volume."""
    policy = RateLimitPolicy(max_calls=1, window_seconds=60.0, base_backoff=10.0, max_backoff=10.0, enabled=False)
    handler = AdaptiveBackoffHandler(policy)
    start = time.monotonic()
    for _ in range(20):
        handler.check_sync("noop_tool")
    elapsed = time.monotonic() - start
    assert elapsed < 0.5, "Disabled policy should never sleep"


def test_handler_reset_clears_state():
    policy = RateLimitPolicy(max_calls=5, window_seconds=60.0, base_backoff=0.0, max_backoff=0.0, jitter=False)
    handler = AdaptiveBackoffHandler(policy)
    for _ in range(4):
        handler.check_sync("tool")
    assert handler.current_call_count == 4
    handler.reset()
    assert handler.current_call_count == 0
    assert handler.consecutive_hits == 0


def test_handler_consecutive_hits_increments():
    """consecutive_hits should increment each time the window is full."""
    policy = RateLimitPolicy(
        max_calls=2, window_seconds=60.0,
        base_backoff=0.0, max_backoff=0.0,
        jitter=False
    )
    handler = AdaptiveBackoffHandler(policy)
    # Fill the window
    handler.check_sync("t")
    handler.check_sync("t")
    assert handler.consecutive_hits == 0
    # Next call hits limit
    handler.check_sync("t")
    assert handler.consecutive_hits == 1
    handler.check_sync("t")
    assert handler.consecutive_hits == 2


def test_handler_consecutive_hits_resets_after_window_clears():
    """consecutive_hits resets when a call goes through without hitting limit."""
    policy = RateLimitPolicy(
        max_calls=2, window_seconds=0.1,  # very short window
        base_backoff=0.0, max_backoff=0.0,
        jitter=False
    )
    handler = AdaptiveBackoffHandler(policy)
    handler.check_sync("t")
    handler.check_sync("t")
    handler.check_sync("t")  # hits limit, consecutive_hits = 1
    assert handler.consecutive_hits == 1
    time.sleep(0.15)          # let window expire
    handler.check_sync("t")  # should NOT hit limit now
    assert handler.consecutive_hits == 0


# ---------------------------------------------------------------------------
# AdaptiveBackoffHandler — async path
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_handler_async_no_block_under_limit():
    policy = RateLimitPolicy(max_calls=10, window_seconds=60.0, base_backoff=0.0, max_backoff=0.0, jitter=False)
    handler = AdaptiveBackoffHandler(policy)
    start = time.monotonic()
    for _ in range(5):
        await handler.check_async("async_tool")
    elapsed = time.monotonic() - start
    assert elapsed < 0.5


@pytest.mark.asyncio
async def test_handler_async_disabled_is_noop():
    policy = RateLimitPolicy(max_calls=1, window_seconds=60.0, base_backoff=10.0, max_backoff=10.0, enabled=False)
    handler = AdaptiveBackoffHandler(policy)
    start = time.monotonic()
    for _ in range(10):
        await handler.check_async("noop")
    elapsed = time.monotonic() - start
    assert elapsed < 0.5


@pytest.mark.asyncio
async def test_handler_async_tracks_same_state_as_sync():
    """Async and sync paths share the same internal state."""
    policy = RateLimitPolicy(max_calls=5, window_seconds=60.0, base_backoff=0.0, max_backoff=0.0, jitter=False)
    handler = AdaptiveBackoffHandler(policy)
    handler.check_sync("t")
    await handler.check_async("t")
    handler.check_sync("t")
    assert handler.current_call_count == 3


# ---------------------------------------------------------------------------
# Integration: watch() accepts rate_limit_policy
# ---------------------------------------------------------------------------

def test_watch_accepts_rate_limit_policy():
    """watch() should accept and apply a RateLimitPolicy without errors."""
    from agentwatch import watch
    from agentwatch.core.rate_limiter import RateLimitPolicy

    class DummyAgent:
        def run(self, task):
            return f"done: {task}"

    policy = RateLimitPolicy(max_calls=100, window_seconds=60.0, base_backoff=0.0, max_backoff=0.0)
    agent = watch(DummyAgent(), rate_limit_policy=policy)
    result = agent.run("hello")
    assert result == "done: hello"


def test_watch_rate_limiter_attached_to_adapter():
    """GenericAdapter should have _rate_limiter attribute after watch()."""
    from agentwatch import watch
    from agentwatch.core.rate_limiter import RateLimitPolicy, AdaptiveBackoffHandler

    class DummyAgent:
        def run(self, task):
            return task

    policy = RateLimitPolicy(max_calls=5, window_seconds=10.0, base_backoff=0.0, max_backoff=0.0)
    agent = watch(DummyAgent(), rate_limit_policy=policy)
    adapter = getattr(agent, "_agentwatch_adapter", None)
    assert adapter is not None, "_agentwatch_adapter not attached"
    assert hasattr(adapter, "_rate_limiter")
    assert isinstance(adapter._rate_limiter, AdaptiveBackoffHandler)
