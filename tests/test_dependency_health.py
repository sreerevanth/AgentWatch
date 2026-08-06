"""Tests for dependency health checks with circuit breaker."""

from __future__ import annotations

import asyncio
import time

import pytest

from agentwatch.core.health import (
    CircuitState,
    DependencyHealthChecker,
    DependencyHealthReport,
    HealthCheckResult,
    HealthStatus,
    ServiceCircuitBreaker,
)


def _healthy_result(name: str = "test") -> HealthCheckResult:
    return HealthCheckResult(name=name, status=HealthStatus.HEALTHY, latency_ms=1.0)


def _unhealthy_result(name: str = "test", msg: str = "fail") -> HealthCheckResult:
    return HealthCheckResult(name=name, status=HealthStatus.UNHEALTHY, latency_ms=0.0, message=msg)


# --- ServiceCircuitBreaker tests ---


def test_circuit_breaker_starts_closed():
    cb = ServiceCircuitBreaker("svc")
    assert cb.state == CircuitState.CLOSED
    assert cb.allow_request() is True


def test_circuit_breaker_opens_after_threshold():
    cb = ServiceCircuitBreaker("svc", failure_threshold=3)
    cb.record_failure()
    cb.record_failure()
    assert cb.state == CircuitState.CLOSED
    cb.record_failure()
    assert cb.state == CircuitState.OPEN
    assert cb.allow_request() is False


def test_circuit_breaker_transitions_to_half_open_after_timeout():
    cb = ServiceCircuitBreaker("svc", failure_threshold=2, recovery_timeout=0.1)
    cb.record_failure()
    cb.record_failure()
    assert cb.state == CircuitState.OPEN
    time.sleep(0.15)
    assert cb.state == CircuitState.HALF_OPEN
    assert cb.allow_request() is True


def test_circuit_breaker_closes_from_half_open_on_success():
    cb = ServiceCircuitBreaker("svc", failure_threshold=2, recovery_timeout=0.05)
    cb.record_failure()
    cb.record_failure()
    time.sleep(0.1)
    assert cb.state == CircuitState.HALF_OPEN
    cb.record_success()
    assert cb.state == CircuitState.CLOSED


def test_circuit_breaker_reopens_from_half_open_on_failure():
    cb = ServiceCircuitBreaker("svc", failure_threshold=2, recovery_timeout=0.05)
    cb.record_failure()
    cb.record_failure()
    time.sleep(0.1)
    assert cb.state == CircuitState.HALF_OPEN
    cb.record_failure()
    assert cb.state == CircuitState.OPEN


def test_circuit_breaker_success_decrements_failures():
    cb = ServiceCircuitBreaker("svc", failure_threshold=3)
    cb.record_failure()
    cb.record_failure()
    cb.record_success()
    assert cb._failure_count == 1


def test_circuit_breaker_reset():
    cb = ServiceCircuitBreaker("svc", failure_threshold=2)
    cb.record_failure()
    cb.record_failure()
    assert cb.state == CircuitState.OPEN
    cb.reset()
    assert cb.state == CircuitState.CLOSED
    assert cb.allow_request() is True


# --- DependencyHealthChecker tests ---


@pytest.mark.asyncio
async def test_check_one_healthy():
    checker = DependencyHealthChecker()

    async def _check():
        return _healthy_result("svc")

    checker.register("svc", _check)
    result = await checker.check_one("svc")
    assert result.status == HealthStatus.HEALTHY


@pytest.mark.asyncio
async def test_check_one_unregistered():
    checker = DependencyHealthChecker()
    result = await checker.check_one("missing")
    assert result.status == HealthStatus.UNHEALTHY
    assert "No check registered" in result.message


@pytest.mark.asyncio
async def test_check_one_circuit_open():
    checker = DependencyHealthChecker()

    async def _check():
        return _healthy_result()

    checker.register("svc", _check)
    breaker = checker._breakers["svc"]
    breaker._failure_count = 5
    breaker._state = CircuitState.OPEN
    breaker._last_failure_time = time.time()
    result = await checker.check_one("svc")
    assert result.status == HealthStatus.UNHEALTHY
    assert "Circuit breaker OPEN" in result.message


@pytest.mark.asyncio
async def test_check_one_timeout():
    checker = DependencyHealthChecker()

    async def _slow():
        await asyncio.sleep(20)
        return _healthy_result()

    checker.register("slow", _slow)
    result = await checker.check_one("slow")
    assert result.status == HealthStatus.UNHEALTHY
    assert "timed out" in result.message


@pytest.mark.asyncio
async def test_check_one_exception():
    checker = DependencyHealthChecker()

    async def _fail():
        raise RuntimeError("db down")

    checker.register("fail", _fail)
    result = await checker.check_one("fail")
    assert result.status == HealthStatus.UNHEALTHY
    assert "db down" in result.message


@pytest.mark.asyncio
async def test_check_all_healthy():
    checker = DependencyHealthChecker()

    async def _check_a():
        return _healthy_result("a")

    async def _check_b():
        return _healthy_result("b")

    checker.register("a", _check_a)
    checker.register("b", _check_b)
    report = await checker.check_all()
    assert report.overall == HealthStatus.HEALTHY
    assert len(report.checks) == 2


@pytest.mark.asyncio
async def test_check_all_degraded():
    checker = DependencyHealthChecker()

    async def _check_a():
        return _healthy_result("a")

    async def _check_b():
        return HealthCheckResult(name="b", status=HealthStatus.DEGRADED, latency_ms=50.0)

    checker.register("a", _check_a)
    checker.register("b", _check_b)
    report = await checker.check_all()
    assert report.overall == HealthStatus.DEGRADED


@pytest.mark.asyncio
async def test_check_all_unhealthy():
    checker = DependencyHealthChecker()

    async def _check_a():
        return _unhealthy_result("a")

    async def _check_b():
        return _unhealthy_result("b")

    checker.register("a", _check_a)
    checker.register("b", _check_b)
    report = await checker.check_all()
    assert report.overall == HealthStatus.UNHEALTHY


@pytest.mark.asyncio
async def test_unhealthy_check_trips_circuit():
    checker = DependencyHealthChecker()

    async def _check():
        return _unhealthy_result("svc")

    checker.register("svc", _check)
    for _ in range(3):
        await checker.check_one("svc")
    assert checker.get_circuit_state("svc") == CircuitState.OPEN


@pytest.mark.asyncio
async def test_unregister():
    checker = DependencyHealthChecker()

    async def _check():
        return _healthy_result("svc")

    checker.register("svc", _check)
    checker.unregister("svc")
    result = await checker.check_one("svc")
    assert "No check registered" in result.message


@pytest.mark.asyncio
async def test_reset_circuit():
    checker = DependencyHealthChecker()

    async def _check():
        return _healthy_result("svc")

    checker.register("svc", _check)
    checker._breakers["svc"]._state = CircuitState.OPEN
    assert checker.reset_circuit("svc") is True
    assert checker.get_circuit_state("svc") == CircuitState.CLOSED


def test_reset_circuit_unknown():
    checker = DependencyHealthChecker()
    assert checker.reset_circuit("nope") is False


def test_health_report_to_dict():
    report = DependencyHealthReport(
        overall=HealthStatus.HEALTHY,
        checks=[
            HealthCheckResult(name="db", status=HealthStatus.HEALTHY, latency_ms=2.5),
        ],
        circuit_states={"db": CircuitState.CLOSED},
    )
    d = report.to_dict()
    assert d["overall"] == "healthy"
    assert len(d["checks"]) == 1
    assert d["checks"][0]["name"] == "db"
    assert d["circuit_states"]["db"] == "closed"


@pytest.mark.asyncio
async def test_circuit_breaker_opens_on_timeout():
    checker = DependencyHealthChecker()

    async def _slow():
        await asyncio.sleep(20)
        return _healthy_result()

    checker.register("slow", _slow)
    for _ in range(3):
        await checker.check_one("slow")
    assert checker.get_circuit_state("slow") == CircuitState.OPEN


@pytest.mark.asyncio
async def test_concurrent_check_all():
    checker = DependencyHealthChecker()
    for i in range(5):
        name = f"svc_{i}"

        async def _check(n=name):
            return _healthy_result(n)

        checker.register(name, _check)
    report = await checker.check_all()
    assert report.overall == HealthStatus.HEALTHY
    assert len(report.checks) == 5
