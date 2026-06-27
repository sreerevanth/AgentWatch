"""
Tests for Active Circuit Breaker - Issue #483
Run: pytest tests/test_circuit_breaker.py -v
"""

from __future__ import annotations

import time
from typing import Any, Dict
from unittest.mock import MagicMock

import pytest

from core.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerResult,
    CircuitState,
    ComplianceEvent,
    SessionCheckpoint,
)
from core.circuit_breaker_registry import CircuitBreakerRegistry


@pytest.fixture
def config() -> CircuitBreakerConfig:
    return CircuitBreakerConfig(
        error_threshold=3,
        error_window_seconds=60,
        max_tokens_per_session=1000,
        hallucination_threshold=0.8,
        hallucination_consecutive=2,
        half_open_max_calls=1,
        recovery_timeout_seconds=300,
        pause_requires_manual_resume=True,
    )


@pytest.fixture
def cb(config) -> CircuitBreaker:
    return CircuitBreaker(session_id="test-session", config=config)


AGENT_STATE: Dict[str, Any] = {"step": 1, "context": "test"}


class TestInitialState:
    def test_starts_closed(self, cb):
        assert cb.state == CircuitState.CLOSED

    def test_allows_calls_when_closed(self, cb):
        result = cb.call(AGENT_STATE)
        assert result.allowed is True
        assert result.state == CircuitState.CLOSED


class TestErrorThreshold:
    def test_trips_on_error_threshold(self, cb, config):
        for _ in range(config.error_threshold):
            cb.call(AGENT_STATE, metrics={"error": True})
        assert cb.state == CircuitState.PAUSED

    def test_blocks_when_open(self, cb, config):
        for _ in range(config.error_threshold):
            cb.call(AGENT_STATE, metrics={"error": True})
        result = cb.call(AGENT_STATE)
        assert result.allowed is False

    def test_error_window_pruning(self, cb, config):
        now = time.time()
        old_ts = now - config.error_window_seconds - 1
        cb._error_timestamps = [old_ts] * (config.error_threshold - 1)
        cb._error_count = config.error_threshold - 1
        result = cb.call(AGENT_STATE, metrics={"error": True})
        assert cb.state == CircuitState.CLOSED

    def test_reason_in_result(self, cb, config):
        for _ in range(config.error_threshold):
            result = cb.call(AGENT_STATE, metrics={"error": True})
        assert "Error threshold" in result.reason


class TestTokenThreshold:
    def test_trips_on_token_budget(self, cb, config):
        cb.call(AGENT_STATE, metrics={"tokens_used": config.max_tokens_per_session})
        assert cb.state == CircuitState.PAUSED

    def test_token_count_accumulates(self, cb):
        cb.call(AGENT_STATE, metrics={"tokens_used": 100})
        cb.call(AGENT_STATE, metrics={"tokens_used": 200})
        assert cb._token_count == 300

    def test_token_reason_in_result(self, cb, config):
        result = cb.call(AGENT_STATE, metrics={"tokens_used": config.max_tokens_per_session})
        assert "Token budget" in result.reason


class TestHallucinationThreshold:
    def test_trips_on_consecutive_hallucinations(self, cb, config):
        for _ in range(config.hallucination_consecutive):
            cb.call(AGENT_STATE, metrics={"hallucination_risk": 0.9})
        assert cb.state == CircuitState.PAUSED

    def test_resets_on_safe_step(self, cb, config):
        cb.call(AGENT_STATE, metrics={"hallucination_risk": 0.9})
        assert cb._hallucination_consecutive == 1
        cb.call(AGENT_STATE, metrics={"hallucination_risk": 0.1})
        assert cb._hallucination_consecutive == 0

    def test_hallucination_reason_in_result(self, cb, config):
        for _ in range(config.hallucination_consecutive):
            result = cb.call(AGENT_STATE, metrics={"hallucination_risk": 0.9})
        assert "hallucination" in result.reason.lower()


class TestPauseResume:
    def test_manual_pause(self, cb):
        checkpoint = cb.pause(AGENT_STATE, reason="manual test")
        assert cb.state == CircuitState.PAUSED
        assert isinstance(checkpoint, SessionCheckpoint)
        assert checkpoint.trigger_reason == "manual test"

    def test_checkpoint_saved(self, cb):
        cp = cb.pause(AGENT_STATE)
        assert cb.get_checkpoint(cp.checkpoint_id) is not None

    def test_latest_checkpoint(self, cb):
        cp1 = cb.pause(AGENT_STATE, reason="first")
        cb._state = CircuitState.CLOSED
        time.sleep(0.01)
        cp2 = cb.pause(AGENT_STATE, reason="second")
        assert cb.get_latest_checkpoint().checkpoint_id == cp2.checkpoint_id

    def test_resume_from_paused(self, cb):
        cb.pause(AGENT_STATE)
        cp = cb.resume(operator_id="alice")
        assert cb.state == CircuitState.HALF_OPEN
        assert isinstance(cp, SessionCheckpoint)

    def test_resume_not_paused_raises(self, cb):
        with pytest.raises(RuntimeError, match="not PAUSED"):
            cb.resume(operator_id="alice")

    def test_resume_no_checkpoint_raises(self, cb):
        cb._state = CircuitState.PAUSED
        with pytest.raises(RuntimeError, match="No valid checkpoint"):
            cb.resume(operator_id="alice")

    def test_resume_with_updated_state(self, cb):
        cb.pause(AGENT_STATE)
        new_state = {"step": 99, "context": "updated"}
        cp = cb.resume(operator_id="bob", agent_state=new_state)
        assert cp.state_snapshot == new_state

    def test_blocked_while_paused(self, cb):
        cb.pause(AGENT_STATE)
        result = cb.call(AGENT_STATE)
        assert result.allowed is False
        assert "PAUSED" in result.reason


class TestHalfOpen:
    def _force_half_open(self, cb):
        cb._state = CircuitState.HALF_OPEN
        cb._half_open_calls = 0

    def test_allows_probe(self, cb):
        self._force_half_open(cb)
        result = cb.call(AGENT_STATE)
        assert result.allowed is True

    def test_blocks_after_probe_quota(self, cb, config):
        self._force_half_open(cb)
        for _ in range(config.half_open_max_calls):
            cb.call(AGENT_STATE)
        result = cb.call(AGENT_STATE)
        assert result.allowed is False

    def test_record_success_closes_circuit(self, cb):
        self._force_half_open(cb)
        cb.record_success()
        assert cb.state == CircuitState.CLOSED

    def test_record_failure_reopens_circuit(self, cb):
        self._force_half_open(cb)
        cb._checkpoints["fake"] = SessionCheckpoint(
            checkpoint_id="fake", session_id="test-session", timestamp=time.time(),
            state_snapshot={}, circuit_state=CircuitState.HALF_OPEN,
            error_count=0, token_count=0, hallucination_consecutive=0, trigger_reason="",
        )
        cb._latest_checkpoint_id = "fake"
        cb.record_failure(AGENT_STATE, reason="probe failed")
        assert cb.state == CircuitState.PAUSED

    def test_success_resets_counters(self, cb):
        self._force_half_open(cb)
        cb._error_count = 5
        cb.record_success()
        assert cb._error_count == 0


class TestAutoTransition:
    def test_auto_open_to_half_open(self, cb, config):
        cb._state = CircuitState.OPEN
        cb._last_open_time = time.time() - config.recovery_timeout_seconds - 1
        _ = cb.state
        assert cb.state == CircuitState.HALF_OPEN

    def test_no_auto_transition_before_timeout(self, cb, config):
        cb._state = CircuitState.OPEN
        cb._last_open_time = time.time()
        _ = cb.state
        assert cb.state == CircuitState.OPEN

    def test_auto_resume_when_not_manual(self, config):
        config.pause_requires_manual_resume = False
        config.auto_resume_timeout_seconds = 0
        cb = CircuitBreaker(session_id="auto-resume", config=config)
        cb._state = CircuitState.PAUSED
        cb._last_pause_time = time.time() - 1
        _ = cb.state
        assert cb.state == CircuitState.HALF_OPEN


class TestResolve:
    def test_resolve(self, cb):
        cb.resolve(operator_id="admin", notes="all good")
        assert cb.state == CircuitState.RESOLVED

    def test_resolved_allows_calls(self, cb):
        cb.resolve(operator_id="admin")
        result = cb.call(AGENT_STATE)
        assert result.allowed is True


class TestComplianceReport:
    def test_report_structure(self, cb):
        report = cb.compliance_report()
        assert report["report_type"] == "EU_AI_ACT_ARTICLE_12"
        assert "session_id" in report
        assert "event_log" in report
        assert "checkpoints" in report
        assert "summary" in report
        assert "thresholds" in report

    def test_report_counts_events(self, cb, config):
        for _ in range(config.error_threshold):
            cb.call(AGENT_STATE, metrics={"error": True})
        report = cb.compliance_report()
        assert report["summary"]["times_tripped"] >= 1
        assert report["summary"]["times_paused"] >= 1

    def test_report_includes_checkpoints(self, cb, config):
        for _ in range(config.error_threshold):
            cb.call(AGENT_STATE, metrics={"error": True})
        report = cb.compliance_report()
        assert len(report["checkpoints"]) >= 1

    def test_report_session_id(self, cb):
        report = cb.compliance_report()
        assert report["session_id"] == "test-session"


class TestCallbacks:
    def test_state_change_callback_called(self, config):
        callback = MagicMock()
        cb = CircuitBreaker(session_id="cb-cb", config=config, on_state_change=callback)
        for _ in range(config.error_threshold):
            cb.call(AGENT_STATE, metrics={"error": True})
        assert callback.called

    def test_compliance_event_callback_called(self, config):
        callback = MagicMock()
        cb = CircuitBreaker(session_id="cb-ce", config=config, on_compliance_event=callback)
        for _ in range(config.error_threshold):
            cb.call(AGENT_STATE, metrics={"error": True})
        assert callback.called

    def test_callback_exception_does_not_propagate(self, config):
        def bad_callback(*args, **kwargs):
            raise ValueError("boom")
        cb = CircuitBreaker(session_id="bad-cb", config=config, on_state_change=bad_callback)
        for _ in range(config.error_threshold):
            cb.call(AGENT_STATE, metrics={"error": True})


class TestSerialisation:
    def test_round_trip(self, cb, config):
        for _ in range(2):
            cb.call(AGENT_STATE, metrics={"error": True})
        cb.call(AGENT_STATE, metrics={"tokens_used": 200})
        d = cb.to_dict()
        cb2 = CircuitBreaker.from_dict(d)
        assert cb2.session_id == cb.session_id
        assert cb2._token_count == cb._token_count
        assert cb2._error_count == cb._error_count
        assert cb2.state == cb.state

    def test_checkpoint_round_trip(self, cb):
        cp = cb.pause(AGENT_STATE, reason="test checkpoint")
        d = cp.to_dict()
        cp2 = SessionCheckpoint.from_dict(d)
        assert cp2.checkpoint_id == cp.checkpoint_id
        assert cp2.trigger_reason == cp.trigger_reason

    def test_serialise_with_compliance_log(self, cb, config):
        for _ in range(config.error_threshold):
            cb.call(AGENT_STATE, metrics={"error": True})
        d = cb.to_dict()
        cb2 = CircuitBreaker.from_dict(d)
        assert len(cb2._compliance_log) == len(cb._compliance_log)


class TestRegistry:
    def test_get_or_create(self):
        reg = CircuitBreakerRegistry()
        cb = reg.get_or_create("session-1")
        assert cb is not None
        cb2 = reg.get_or_create("session-1")
        assert cb is cb2

    def test_get_missing(self):
        reg = CircuitBreakerRegistry()
        assert reg.get("nonexistent") is None

    def test_remove(self):
        reg = CircuitBreakerRegistry()
        reg.get_or_create("session-2")
        reg.remove("session-2")
        assert reg.get("session-2") is None

    def test_all_sessions(self):
        reg = CircuitBreakerRegistry()
        reg.get_or_create("s1")
        reg.get_or_create("s2")
        sessions = reg.all_sessions()
        assert "s1" in sessions
        assert "s2" in sessions


class TestListCheckpoints:
    def test_list_ordered_by_time(self, cb):
        cp1 = cb.pause(AGENT_STATE, reason="first")
        cb._state = CircuitState.CLOSED
        time.sleep(0.01)
        cp2 = cb.pause(AGENT_STATE, reason="second")
        cps = cb.list_checkpoints()
        assert cps[0].checkpoint_id == cp1.checkpoint_id
        assert cps[1].checkpoint_id == cp2.checkpoint_id

    def test_empty_list(self, cb):
        assert cb.list_checkpoints() == []
