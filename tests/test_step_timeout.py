"""Tests for step timeout detector."""

from __future__ import annotations

import asyncio
import time

import pytest

from agentwatch.reasoning.step_timeout import (
    StepTimeoutConfig,
    StepTimeoutDetector,
    StepTiming,
    TimeoutAlert,
    TimeoutSeverity,
)


def test_step_timing_elapsed():
    t = StepTiming(step_index=0, event_id="evt", timeout_seconds=10.0)
    assert t.elapsed_seconds >= 0
    assert t.is_overdue is False
    assert t.progress >= 0


def test_step_timing_completed():
    t = StepTiming(step_index=0, event_id="evt", timeout_seconds=1.0)
    t.started_at = time.monotonic() - 2.0
    t.ended_at = time.monotonic()
    assert t.elapsed_seconds >= 1.9
    assert t.is_overdue is True


def test_step_timing_progress_capped():
    t = StepTiming(step_index=0, event_id="evt", timeout_seconds=1.0)
    t.started_at = time.monotonic() - 100.0
    assert t.progress == 1.0


def test_start_step():
    det = StepTimeoutDetector(StepTimeoutConfig(default_timeout_seconds=15.0))
    timing = det.start_step(0, "evt-1", tool_name="search")
    assert timing.step_index == 0
    assert timing.event_id == "evt-1"
    assert timing.tool_name == "search"
    assert timing.timeout_seconds == 15.0
    assert len(det.get_active_steps()) == 1


def test_start_step_with_tool_override():
    det = StepTimeoutDetector(
        StepTimeoutConfig(per_tool_overrides={"slow_tool": 60.0})
    )
    timing = det.start_step(0, "evt", tool_name="slow_tool")
    assert timing.timeout_seconds == 60.0


def test_start_step_with_timeout_override():
    det = StepTimeoutDetector()
    timing = det.start_step(0, "evt", timeout_override=45.0)
    assert timing.timeout_seconds == 45.0


def test_end_step():
    det = StepTimeoutDetector()
    det.start_step(0, "evt-1")
    time.sleep(0.01)
    timing = det.end_step(0)
    assert timing is not None
    assert timing.ended_at is not None
    assert len(det.get_completed_steps()) == 1
    assert len(det.get_active_steps()) == 0


def test_end_step_nonexistent():
    det = StepTimeoutDetector()
    result = det.end_step(999)
    assert result is None


def test_check_timeouts_fires_critical():
    det = StepTimeoutDetector(StepTimeoutConfig(default_timeout_seconds=0.01))
    det.start_step(0, "evt", timeout_override=0.01)
    time.sleep(0.05)
    alerts = det.check_timeouts()
    assert len(alerts) >= 1
    assert alerts[0].severity == TimeoutSeverity.CRITICAL


def test_check_timeouts_fires_warning():
    det = StepTimeoutDetector(
        StepTimeoutConfig(default_timeout_seconds=0.1, warning_threshold=0.5)
    )
    det.start_step(0, "evt", timeout_override=0.1)
    time.sleep(0.06)
    alerts = det.check_timeouts()
    assert any(a.severity == TimeoutSeverity.WARNING for a in alerts)


def test_check_timeouts_no_false_positive():
    det = StepTimeoutDetector(StepTimeoutConfig(default_timeout_seconds=10.0))
    det.start_step(0, "evt")
    alerts = det.check_timeouts()
    assert len(alerts) == 0


def test_get_alerts_filtered():
    det = StepTimeoutDetector(StepTimeoutConfig(default_timeout_seconds=0.01))
    det.start_step(0, "evt", timeout_override=0.01)
    time.sleep(0.05)
    det.check_timeouts()
    critical = det.get_alerts(severity=TimeoutSeverity.CRITICAL)
    warning = det.get_alerts(severity=TimeoutSeverity.WARNING)
    all_alerts = det.get_alerts()
    assert len(all_alerts) >= 1
    assert len(critical) + len(warning) == len(all_alerts)


def test_get_slowest_steps():
    det = StepTimeoutDetector()
    for i in range(5):
        det.start_step(i, f"evt-{i}")
        time.sleep(0.001)
        det.end_step(i)
    slowest = det.get_slowest_steps(n=3)
    assert len(slowest) == 3
    assert slowest[0].elapsed_seconds >= slowest[1].elapsed_seconds


def test_get_step_stats():
    det = StepTimeoutDetector(StepTimeoutConfig(default_timeout_seconds=0.01))
    for i in range(3):
        det.start_step(i, f"evt-{i}", timeout_override=0.01)
        time.sleep(0.02)
        det.end_step(i)
    stats = det.get_step_stats()
    assert stats["total_steps"] == 3
    assert stats["avg_duration_seconds"] > 0
    assert stats["max_duration_seconds"] > 0
    assert stats["timed_out_count"] >= 0


def test_get_step_stats_empty():
    det = StepTimeoutDetector()
    stats = det.get_step_stats()
    assert stats["total_steps"] == 0


def test_clear():
    det = StepTimeoutDetector()
    det.start_step(0, "evt")
    det.end_step(0)
    det.clear()
    assert len(det.get_completed_steps()) == 0
    assert len(det.get_alerts()) == 0


def test_alert_to_dict():
    alert = TimeoutAlert(
        step_index=1,
        event_id="evt",
        tool_name="search",
        elapsed_seconds=5.0,
        timeout_seconds=3.0,
        severity=TimeoutSeverity.CRITICAL,
        message="timeout exceeded",
    )
    d = alert.to_dict()
    assert d["step_index"] == 1
    assert d["severity"] == "critical"
    assert d["elapsed_seconds"] == 5.0


def test_overwrite_active_step():
    det = StepTimeoutDetector()
    det.start_step(0, "evt-1")
    det.start_step(0, "evt-2")
    assert len(det.get_active_steps()) == 1
    assert det.get_active_steps()[0].event_id == "evt-2"


@pytest.mark.asyncio
async def test_periodic_check():
    det = StepTimeoutDetector(StepTimeoutConfig(default_timeout_seconds=0.01))
    det.start_step(0, "evt", timeout_override=0.01)
    await det.start_periodic_check(interval=0.01)
    await asyncio.sleep(0.1)
    await det.stop_periodic_check()
    alerts = det.get_alerts(severity=TimeoutSeverity.CRITICAL)
    assert len(alerts) >= 1


@pytest.mark.asyncio
async def test_stop_periodic_check_idempotent():
    det = StepTimeoutDetector()
    await det.start_periodic_check()
    await det.stop_periodic_check()
    await det.stop_periodic_check()


def test_tool_overrides_in_config():
    config = StepTimeoutConfig(
        per_tool_overrides={"db_query": 5.0, "file_upload": 120.0}
    )
    det = StepTimeoutDetector(config)
    t1 = det.start_step(0, "e1", tool_name="db_query")
    t2 = det.start_step(1, "e2", tool_name="file_upload")
    t3 = det.start_step(2, "e3", tool_name="unknown")
    assert t1.timeout_seconds == 5.0
    assert t2.timeout_seconds == 120.0
    assert t3.timeout_seconds == config.default_timeout_seconds
