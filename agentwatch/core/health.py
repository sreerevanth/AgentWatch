"""Dependency health checks with circuit breaker pattern.

Provides proactive health monitoring for PostgreSQL, Redis, and other
service dependencies. Includes a lightweight circuit breaker that
prevents cascading failures when dependencies are unhealthy.
"""

from __future__ import annotations

import asyncio
import enum
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Awaitable, Protocol

logger = logging.getLogger(__name__)


class HealthStatus(enum.Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class CircuitState(enum.Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class HealthCheckResult:
    name: str
    status: HealthStatus
    latency_ms: float
    message: str = ""
    checked_at: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class DependencyHealthReport:
    overall: HealthStatus
    checks: list[HealthCheckResult]
    circuit_states: dict[str, CircuitState]
    checked_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "overall": self.overall.value,
            "checks": [
                {
                    "name": c.name,
                    "status": c.status.value,
                    "latency_ms": c.latency_ms,
                    "message": c.message,
                    "checked_at": c.checked_at,
                    "metadata": c.metadata,
                }
                for c in self.checks
            ],
            "circuit_states": {k: v.value for k, v in self.circuit_states.items()},
            "checked_at": self.checked_at,
        }


class HealthCheckFn(Protocol):
    async def __call__(self) -> HealthCheckResult: ...


class ServiceCircuitBreaker:
    """Lightweight circuit breaker for a single dependency.

    States:
        CLOSED: Normal operation. Failures are counted.
        OPEN: Dependency is unhealthy. All checks fail fast.
        HALF_OPEN: Probing recovery. One success closes, one failure reopens.
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 3,
        recovery_timeout: float = 30.0,
        half_open_max_probes: int = 1,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_probes = half_open_max_probes
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: float = 0.0
        self._last_state_change: float = time.time()

    @property
    def state(self) -> CircuitState:
        if self._state == CircuitState.OPEN:
            elapsed = time.time() - self._last_failure_time
            if elapsed >= self.recovery_timeout:
                self._transition(CircuitState.HALF_OPEN)
        return self._state

    def _transition(self, new_state: CircuitState) -> None:
        old = self._state
        self._state = new_state
        self._last_state_change = time.time()
        if new_state == CircuitState.HALF_OPEN:
            self._success_count = 0
        elif new_state == CircuitState.CLOSED:
            self._failure_count = 0
            self._success_count = 0
        logger.info("Circuit breaker '%s': %s -> %s", self.name, old.value, new_state.value)

    def record_success(self) -> None:
        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self.half_open_max_probes:
                self._transition(CircuitState.CLOSED)
        elif self._state == CircuitState.CLOSED:
            self._failure_count = max(0, self._failure_count - 1)

    def record_failure(self) -> None:
        self._failure_count += 1
        self._last_failure_time = time.time()
        if self._state == CircuitState.HALF_OPEN:
            self._transition(CircuitState.OPEN)
        elif self._state == CircuitState.CLOSED:
            if self._failure_count >= self.failure_threshold:
                self._transition(CircuitState.OPEN)

    def allow_request(self) -> bool:
        if self._state == CircuitState.OPEN:
            return False
        return True

    def reset(self) -> None:
        self._failure_count = 0
        self._success_count = 0
        self._transition(CircuitState.CLOSED)


class DependencyHealthChecker:
    """Orchestrates health checks across all registered dependencies.

    Each dependency gets its own circuit breaker. When the circuit is OPEN,
    the health check is skipped and returns UNHEALTHY immediately.
    """

    def __init__(self) -> None:
        self._checks: dict[str, HealthCheckFn] = {}
        self._breakers: dict[str, ServiceCircuitBreaker] = {}

    def register(
        self,
        name: str,
        check_fn: HealthCheckFn,
        failure_threshold: int = 3,
        recovery_timeout: float = 30.0,
    ) -> None:
        self._checks[name] = check_fn
        self._breakers[name] = ServiceCircuitBreaker(
            name=name,
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
        )

    def unregister(self, name: str) -> None:
        self._checks.pop(name, None)
        self._breakers.pop(name, None)

    async def check_one(self, name: str) -> HealthCheckResult:
        if name not in self._checks:
            return HealthCheckResult(
                name=name,
                status=HealthStatus.UNHEALTHY,
                latency_ms=0.0,
                message=f"No check registered for '{name}'",
            )
        breaker = self._breakers[name]
        if not breaker.allow_request():
            return HealthCheckResult(
                name=name,
                status=HealthStatus.UNHEALTHY,
                latency_ms=0.0,
                message=f"Circuit breaker OPEN for '{name}'",
                metadata={"circuit_state": "open"},
            )
        start = time.monotonic()
        try:
            result = await asyncio.wait_for(self._checks[name](), timeout=10.0)
            elapsed_ms = (time.monotonic() - start) * 1000
            result.latency_ms = elapsed_ms
            if result.status == HealthStatus.HEALTHY:
                breaker.record_success()
            else:
                breaker.record_failure()
            return result
        except asyncio.TimeoutError:
            elapsed_ms = (time.monotonic() - start) * 1000
            breaker.record_failure()
            return HealthCheckResult(
                name=name,
                status=HealthStatus.UNHEALTHY,
                latency_ms=elapsed_ms,
                message=f"Health check timed out after 10s",
            )
        except Exception as exc:
            elapsed_ms = (time.monotonic() - start) * 1000
            breaker.record_failure()
            return HealthCheckResult(
                name=name,
                status=HealthStatus.UNHEALTHY,
                latency_ms=elapsed_ms,
                message=f"Check failed: {exc}",
            )

    async def check_all(self) -> DependencyHealthReport:
        results = await asyncio.gather(
            *[self.check_one(name) for name in self._checks],
            return_exceptions=False,
        )
        statuses = [r.status for r in results]
        if all(s == HealthStatus.HEALTHY for s in statuses):
            overall = HealthStatus.HEALTHY
        elif any(s == HealthStatus.UNHEALTHY for s in statuses):
            overall = HealthStatus.UNHEALTHY
        else:
            overall = HealthStatus.DEGRADED
        return DependencyHealthReport(
            overall=overall,
            checks=list(results),
            circuit_states={name: b.state for name, b in self._breakers.items()},
        )

    def get_circuit_state(self, name: str) -> CircuitState | None:
        if name in self._breakers:
            return self._breakers[name].state
        return None

    def reset_circuit(self, name: str) -> bool:
        if name in self._breakers:
            self._breakers[name].reset()
            return True
        return False


async def check_postgres_health(database_url: str) -> HealthCheckResult:
    """Check PostgreSQL connectivity via asyncpg."""
    try:
        import asyncpg
        conn = await asyncpg.connect(database_url, timeout=5)
        start = time.monotonic()
        await conn.execute("SELECT 1")
        latency = (time.monotonic() - start) * 1000
        await conn.close()
        return HealthCheckResult(
            name="postgresql",
            status=HealthStatus.HEALTHY,
            latency_ms=latency,
            message="Connection successful",
        )
    except Exception as exc:
        return HealthCheckResult(
            name="postgresql",
            status=HealthStatus.UNHEALTHY,
            latency_ms=0.0,
            message=f"PostgreSQL check failed: {exc}",
        )


async def check_redis_health(redis_url: str) -> HealthCheckResult:
    """Check Redis connectivity via aioredis."""
    try:
        import redis.asyncio as aioredis
        client = aioredis.from_url(redis_url, socket_timeout=5)
        start = time.monotonic()
        pong = await client.ping()
        latency = (time.monotonic() - start) * 1000
        await client.aclose()
        if pong:
            return HealthCheckResult(
                name="redis",
                status=HealthStatus.HEALTHY,
                latency_ms=latency,
                message="Connection successful",
            )
        return HealthCheckResult(
            name="redis",
            status=HealthStatus.DEGRADED,
            latency_ms=latency,
            message="Redis responded but ping returned false",
        )
    except Exception as exc:
        return HealthCheckResult(
            name="redis",
            status=HealthStatus.UNHEALTHY,
            latency_ms=0.0,
            message=f"Redis check failed: {exc}",
        )


def create_default_health_checker(
    database_url: str | None = None,
    redis_url: str | None = None,
) -> DependencyHealthChecker:
    """Create a health checker with PostgreSQL and Redis checks registered."""
    checker = DependencyHealthChecker()
    if database_url:
        checker.register(
            "postgresql",
            lambda: check_postgres_health(database_url),
            failure_threshold=3,
            recovery_timeout=30.0,
        )
    if redis_url:
        checker.register(
            "redis",
            lambda: check_redis_health(redis_url),
            failure_threshold=3,
            recovery_timeout=30.0,
        )
    return checker
