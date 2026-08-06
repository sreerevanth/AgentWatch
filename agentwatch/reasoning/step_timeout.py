"""Step timeout detector for reasoning steps.

Monitors the duration of each reasoning step and fires alerts when
a step exceeds its expected time budget. Detects hung reasoning loops,
stuck tool calls, and runaway LLM invocations.
"""

from __future__ import annotations

import asyncio
import enum
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Awaitable

logger = logging.getLogger(__name__)


class TimeoutSeverity(enum.Enum):
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class StepTimeoutConfig:
    """Configuration for step timeout detection."""
    default_timeout_seconds: float = 30.0
    warning_threshold: float = 0.8
    critical_timeout_seconds: float = 120.0
    per_tool_overrides: dict[str, float] = field(default_factory=dict)
    enabled: bool = True


@dataclass
class StepTiming:
    """Tracks timing for a single reasoning step."""
    step_index: int
    event_id: str
    tool_name: str | None = None
    started_at: float = field(default_factory=time.monotonic)
    ended_at: float | None = None
    timeout_seconds: float = 30.0
    warning_fired: bool = False
    timed_out: bool = False

    @property
    def elapsed_seconds(self) -> float:
        if self.ended_at is not None:
            return self.ended_at - self.started_at
        return time.monotonic() - self.started_at

    @property
    def is_overdue(self) -> bool:
        return self.elapsed_seconds > self.timeout_seconds

    @property
    def progress(self) -> float:
        if self.timeout_seconds <= 0:
            return 1.0
        return min(self.elapsed_seconds / self.timeout_seconds, 1.0)


@dataclass
class TimeoutAlert:
    """Alert fired when a step exceeds its time budget."""
    step_index: int
    event_id: str
    tool_name: str | None
    elapsed_seconds: float
    timeout_seconds: float
    severity: TimeoutSeverity
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_index": self.step_index,
            "event_id": self.event_id,
            "tool_name": self.tool_name,
            "elapsed_seconds": round(self.elapsed_seconds, 3),
            "timeout_seconds": self.timeout_seconds,
            "severity": self.severity.value,
            "message": self.message,
        }


class StepTimeoutDetector:
    """Monitors reasoning step durations and fires timeout alerts.

    Usage:
        detector = StepTimeoutDetector(config)
        detector.start_step(0, "evt-1", tool_name="search")
        # ... step executes ...
        detector.end_step(0)

        alerts = detector.get_alerts()
    """

    def __init__(self, config: StepTimeoutConfig | None = None) -> None:
        self._config = config or StepTimeoutConfig()
        self._active: dict[int, StepTiming] = {}
        self._completed: list[StepTiming] = []
        self._alerts: list[TimeoutAlert] = []
        self._check_task: asyncio.Task | None = None

    @property
    def config(self) -> StepTimeoutConfig:
        return self._config

    def start_step(
        self,
        step_index: int,
        event_id: str,
        tool_name: str | None = None,
        timeout_override: float | None = None,
    ) -> StepTiming:
        if step_index in self._active:
            logger.warning("Step %d already active, overwriting", step_index)

        timeout = timeout_override or self._config.per_tool_overrides.get(
            tool_name or "", self._config.default_timeout_seconds
        )
        timing = StepTiming(
            step_index=step_index,
            event_id=event_id,
            tool_name=tool_name,
            timeout_seconds=timeout,
        )
        self._active[step_index] = timing
        return timing

    def end_step(self, step_index: int) -> StepTiming | None:
        timing = self._active.pop(step_index, None)
        if timing is not None:
            timing.ended_at = time.monotonic()
            self._completed.append(timing)
            if timing.is_overdue:
                self._fire_alert(timing, TimeoutSeverity.CRITICAL)
            elif timing.progress >= self._config.warning_threshold and not timing.warning_fired:
                self._fire_alert(timing, TimeoutSeverity.WARNING)
        return timing

    def check_timeouts(self) -> list[TimeoutAlert]:
        new_alerts: list[TimeoutAlert] = []
        now = time.monotonic()
        for step_index, timing in list(self._active.items()):
            elapsed = now - timing.started_at
            if elapsed > timing.timeout_seconds and not timing.timed_out:
                timing.timed_out = True
                alert = self._fire_alert(timing, TimeoutSeverity.CRITICAL)
                new_alerts.append(alert)
            elif (
                elapsed >= timing.timeout_seconds * self._config.warning_threshold
                and not timing.warning_fired
            ):
                alert = self._fire_alert(timing, TimeoutSeverity.WARNING)
                new_alerts.append(alert)
        return new_alerts

    def _fire_alert(self, timing: StepTiming, severity: TimeoutSeverity) -> TimeoutAlert:
        elapsed = timing.elapsed_seconds
        if severity == TimeoutSeverity.WARNING:
            timing.warning_fired = True
            msg = (
                f"Step {timing.step_index} approaching timeout: "
                f"{elapsed:.1f}s / {timing.timeout_seconds:.1f}s"
            )
        else:
            timing.timed_out = True
            msg = (
                f"Step {timing.step_index} exceeded timeout: "
                f"{elapsed:.1f}s > {timing.timeout_seconds:.1f}s"
            )
            if timing.tool_name:
                msg += f" (tool: {timing.tool_name})"

        alert = TimeoutAlert(
            step_index=timing.step_index,
            event_id=timing.event_id,
            tool_name=timing.tool_name,
            elapsed_seconds=elapsed,
            timeout_seconds=timing.timeout_seconds,
            severity=severity,
            message=msg,
        )
        self._alerts.append(alert)
        logger.warning("Step timeout alert: %s", msg)
        return alert

    def get_alerts(self, severity: TimeoutSeverity | None = None) -> list[TimeoutAlert]:
        if severity:
            return [a for a in self._alerts if a.severity == severity]
        return list(self._alerts)

    def get_active_steps(self) -> list[StepTiming]:
        return list(self._active.values())

    def get_completed_steps(self) -> list[StepTiming]:
        return list(self._completed)

    def get_slowest_steps(self, n: int = 5) -> list[StepTiming]:
        all_steps = self._completed + list(self._active.values())
        return sorted(all_steps, key=lambda s: s.elapsed_seconds, reverse=True)[:n]

    def get_step_stats(self) -> dict[str, Any]:
        completed = self._completed
        if not completed:
            return {
                "total_steps": 0,
                "avg_duration_seconds": 0.0,
                "max_duration_seconds": 0.0,
                "timed_out_count": 0,
                "warning_count": 0,
            }
        durations = [s.elapsed_seconds for s in completed]
        return {
            "total_steps": len(completed),
            "avg_duration_seconds": sum(durations) / len(durations),
            "max_duration_seconds": max(durations),
            "min_duration_seconds": min(durations),
            "timed_out_count": sum(1 for s in completed if s.timed_out),
            "warning_count": sum(1 for s in completed if s.warning_fired),
        }

    async def start_periodic_check(self, interval: float = 1.0) -> None:
        if self._check_task is not None:
            return

        async def _loop():
            while True:
                await asyncio.sleep(interval)
                self.check_timeouts()

        self._check_task = asyncio.create_task(_loop())

    async def stop_periodic_check(self) -> None:
        if self._check_task is not None:
            self._check_task.cancel()
            try:
                await self._check_task
            except asyncio.CancelledError:
                pass
            self._check_task = None

    def clear(self) -> None:
        self._active.clear()
        self._completed.clear()
        self._alerts.clear()
