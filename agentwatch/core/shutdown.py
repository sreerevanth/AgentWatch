"""Graceful shutdown handler with ordered cleanup hooks.

Provides a signal-safe shutdown coordinator that runs registered
cleanup handlers in priority order when SIGTERM/SIGINT is received.
Ensures in-flight operations complete before resources are released.
"""

from __future__ import annotations

import asyncio
import enum
import logging
import signal
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Awaitable

logger = logging.getLogger(__name__)


class ShutdownPriority(enum.IntEnum):
    """Cleanup hook priority. Lower values run first."""
    CRITICAL = 0
    HIGH = 10
    NORMAL = 50
    LOW = 100
    BACKGROUND = 200


class ShutdownState(enum.Enum):
    RUNNING = "running"
    SHUTTING_DOWN = "shutting_down"
    COMPLETED = "completed"
    TIMED_OUT = "timed_out"
    FAILED = "failed"


@dataclass
class CleanupHook:
    name: str
    handler: Callable[[], Awaitable[None]]
    priority: ShutdownPriority = ShutdownPriority.NORMAL
    timeout: float = 10.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class CleanupResult:
    hook_name: str
    success: bool
    duration_ms: float
    error: str = ""


@dataclass
class ShutdownReport:
    state: ShutdownState
    results: list[CleanupResult]
    total_duration_ms: float
    triggered_by: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "state": self.state.value,
            "triggered_by": self.triggered_by,
            "total_duration_ms": self.total_duration_ms,
            "results": [
                {
                    "hook_name": r.hook_name,
                    "success": r.success,
                    "duration_ms": r.duration_ms,
                    "error": r.error,
                }
                for r in self.results
            ],
        }


class GracefulShutdown:
    """Coordinates orderly shutdown with prioritized cleanup hooks.

    Usage:
        shutdown = GracefulShutdown()
        shutdown.register("db_pool", close_db_pool, priority=ShutdownPriority.HIGH)
        shutdown.register("cache", flush_cache, priority=ShutdownPriority.LOW)

        # Install signal handlers (async context)
        await shutdown.install_signals()

        # Or trigger manually
        await shutdown.trigger("manual")
    """

    def __init__(self, default_timeout: float = 30.0) -> None:
        self._hooks: list[CleanupHook] = []
        self._state = ShutdownState.RUNNING
        self._default_timeout = default_timeout
        self._shutdown_event = asyncio.Event()
        self._results: list[CleanupResult] = []
        self._triggered_by: str = ""
        self._start_time: float = 0.0
        self._original_sigterm: Any = None
        self._original_sigint: Any = None

    @property
    def state(self) -> ShutdownState:
        return self._state

    @property
    def is_shutting_down(self) -> bool:
        return self._state in (ShutdownState.SHUTTING_DOWN, ShutdownState.COMPLETED, ShutdownState.TIMED_OUT, ShutdownState.FAILED)

    def register(
        self,
        name: str,
        handler: Callable[[], Awaitable[None]],
        priority: ShutdownPriority = ShutdownPriority.NORMAL,
        timeout: float | None = None,
        **metadata: Any,
    ) -> None:
        hook = CleanupHook(
            name=name,
            handler=handler,
            priority=priority,
            timeout=timeout or self._default_timeout,
            metadata=metadata,
        )
        self._hooks.append(hook)
        logger.debug("Registered cleanup hook: %s (priority=%s)", name, priority.name)

    def unregister(self, name: str) -> bool:
        before = len(self._hooks)
        self._hooks = [h for h in self._hooks if h.name != name]
        return len(self._hooks) < before

    def list_hooks(self) -> list[CleanupHook]:
        return sorted(self._hooks, key=lambda h: h.priority.value)

    async def install_signals(self) -> None:
        loop = asyncio.get_running_loop()
        try:
            self._original_sigterm = loop.remove_signal_handler(signal.SIGTERM)
        except (NotImplementedError, AttributeError):
            pass
        try:
            self._original_sigint = loop.remove_signal_handler(signal.SIGINT)
        except (NotImplementedError, AttributeError):
            pass

        loop.add_signal_handler(signal.SIGTERM, lambda: asyncio.create_task(self.trigger("SIGTERM")))
        loop.add_signal_handler(signal.SIGINT, lambda: asyncio.create_task(self.trigger("SIGINT")))
        logger.info("Installed graceful shutdown signal handlers")

    async def uninstall_signals(self) -> None:
        loop = asyncio.get_running_loop()
        try:
            loop.remove_signal_handler(signal.SIGTERM)
            loop.remove_signal_handler(signal.SIGINT)
        except (NotImplementedError, AttributeError):
            pass
        if self._original_sigterm is not None:
            try:
                loop.add_signal_handler(signal.SIGTERM, self._original_sigterm)
            except (NotImplementedError, AttributeError):
                pass
        if self._original_sigint is not None:
            try:
                loop.add_signal_handler(signal.SIGINT, self._original_sigint)
            except (NotImplementedError, AttributeError):
                pass

    async def trigger(self, reason: str = "manual") -> ShutdownReport:
        if self._state != ShutdownState.RUNNING:
            logger.warning("Shutdown already in progress (state=%s)", self._state.value)
            return ShutdownReport(
                state=self._state,
                results=self._results,
                total_duration_ms=0.0,
                triggered_by=self._triggered_by,
            )

        self._state = ShutdownState.SHUTTING_DOWN
        self._triggered_by = reason
        self._start_time = time.monotonic()
        self._results = []
        self._shutdown_event.set()

        logger.info("Shutdown triggered by: %s", reason)

        sorted_hooks = self.list_hooks()
        all_success = True

        for hook in sorted_hooks:
            if self._state == ShutdownState.TIMED_OUT:
                break
            result = await self._run_hook(hook)
            self._results.append(result)
            if not result.success:
                all_success = False

        total_ms = (time.monotonic() - self._start_time) * 1000
        if self._state == ShutdownState.SHUTTING_DOWN:
            self._state = ShutdownState.COMPLETED if all_success else ShutdownState.FAILED

        report = ShutdownReport(
            state=self._state,
            results=self._results,
            total_duration_ms=total_ms,
            triggered_by=self._triggered_by,
        )

        logger.info(
            "Shutdown completed: state=%s, hooks=%d, duration=%.1fms",
            self._state.value,
            len(self._results),
            total_ms,
        )
        return report

    async def _run_hook(self, hook: CleanupHook) -> CleanupResult:
        start = time.monotonic()
        try:
            logger.info("Running cleanup hook: %s (timeout=%.1fs)", hook.name, hook.timeout)
            await asyncio.wait_for(hook.handler(), timeout=hook.timeout)
            elapsed = (time.monotonic() - start) * 1000
            logger.info("Cleanup hook '%s' completed in %.1fms", hook.name, elapsed)
            return CleanupResult(hook_name=hook.name, success=True, duration_ms=elapsed)
        except asyncio.TimeoutError:
            elapsed = (time.monotonic() - start) * 1000
            logger.warning("Cleanup hook '%s' timed out after %.1fs", hook.name, hook.timeout)
            return CleanupResult(
                hook_name=hook.name,
                success=False,
                duration_ms=elapsed,
                error=f"Timed out after {hook.timeout}s",
            )
        except Exception as exc:
            elapsed = (time.monotonic() - start) * 1000
            logger.error("Cleanup hook '%s' failed: %s", hook.name, exc)
            return CleanupResult(
                hook_name=hook.name,
                success=False,
                duration_ms=elapsed,
                error=str(exc),
            )

    async def wait(self) -> None:
        await self._shutdown_event.wait()

    def reset(self) -> None:
        self._state = ShutdownState.RUNNING
        self._results = []
        self._triggered_by = ""
        self._start_time = 0.0
        self._shutdown_event.clear()
