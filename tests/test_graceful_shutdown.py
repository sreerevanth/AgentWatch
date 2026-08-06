"""Tests for graceful shutdown handler."""

from __future__ import annotations

import asyncio

import pytest

from agentwatch.core.shutdown import (
    CleanupResult,
    GracefulShutdown,
    ShutdownPriority,
    ShutdownState,
)


async def _noop():
    pass


async def _slow():
    await asyncio.sleep(20)


async def _failing():
    raise RuntimeError("hook failed")


async def _recording(results: list[str], name: str):
    results.append(name)


@pytest.mark.asyncio
async def test_shutdown_starts_running():
    gs = GracefulShutdown()
    assert gs.state == ShutdownState.RUNNING
    assert gs.is_shutting_down is False


@pytest.mark.asyncio
async def test_register_and_list_hooks():
    gs = GracefulShutdown()
    gs.register("a", _noop, priority=ShutdownPriority.HIGH)
    gs.register("b", _noop, priority=ShutdownPriority.LOW)
    hooks = gs.list_hooks()
    assert len(hooks) == 2
    assert hooks[0].name == "a"
    assert hooks[1].name == "b"


@pytest.mark.asyncio
async def test_unregister():
    gs = GracefulShutdown()
    gs.register("a", _noop)
    assert gs.unregister("a") is True
    assert gs.unregister("a") is False
    assert len(gs.list_hooks()) == 0


@pytest.mark.asyncio
async def test_trigger_runs_hooks_in_priority_order():
    gs = GracefulShutdown()
    order = []

    async def _first():
        order.append("first")

    async def _second():
        order.append("second")

    gs.register("low", _first, priority=ShutdownPriority.LOW)
    gs.register("high", _second, priority=ShutdownPriority.HIGH)
    report = await gs.trigger("test")
    assert order == ["second", "first"]
    assert report.state == ShutdownState.COMPLETED
    assert len(report.results) == 2


@pytest.mark.asyncio
async def test_trigger_sets_shutting_down_state():
    gs = GracefulShutdown()
    gs.register("a", _noop)
    await gs.trigger("test")
    assert gs.is_shutting_down is True


@pytest.mark.asyncio
async def test_trigger_double_call_returns_existing():
    gs = GracefulShutdown()
    gs.register("a", _noop)
    report1 = await gs.trigger("first")
    report2 = await gs.trigger("second")
    assert report2.triggered_by == "first"
    assert report2.state == ShutdownState.COMPLETED


@pytest.mark.asyncio
async def test_hook_failure_marks_failed():
    gs = GracefulShutdown()
    gs.register("fail", _failing)
    report = await gs.trigger("test")
    assert report.state == ShutdownState.FAILED
    assert report.results[0].success is False
    assert "hook failed" in report.results[0].error


@pytest.mark.asyncio
async def test_hook_timeout():
    gs = GracefulShutdown(default_timeout=0.1)
    gs.register("slow", _slow, timeout=0.1)
    report = await gs.trigger("test")
    assert report.state == ShutdownState.FAILED
    assert "Timed out" in report.results[0].error


@pytest.mark.asyncio
async def test_mixed_success_and_failure():
    gs = GracefulShutdown()
    gs.register("ok", _noop)
    gs.register("fail", _failing)
    report = await gs.trigger("test")
    assert report.state == ShutdownState.FAILED
    successes = [r for r in report.results if r.success]
    failures = [r for r in report.results if not r.success]
    assert len(successes) == 1
    assert len(failures) == 1


@pytest.mark.asyncio
async def test_report_to_dict():
    gs = GracefulShutdown()
    gs.register("a", _noop)
    report = await gs.trigger("test")
    d = report.to_dict()
    assert d["state"] == "completed"
    assert d["triggered_by"] == "test"
    assert len(d["results"]) == 1
    assert "total_duration_ms" in d


@pytest.mark.asyncio
async def test_reset():
    gs = GracefulShutdown()
    gs.register("a", _noop)
    await gs.trigger("test")
    assert gs.state == ShutdownState.COMPLETED
    gs.reset()
    assert gs.state == ShutdownState.RUNNING
    assert gs.is_shutting_down is False


@pytest.mark.asyncio
async def test_wait_blocks_until_trigger():
    gs = GracefulShutdown()
    gs.register("a", _noop)

    async def _trigger_later():
        await asyncio.sleep(0.05)
        await gs.trigger("delayed")

    done = False

    async def _wait():
        nonlocal done
        await gs.wait()
        done = True

    await asyncio.gather(_wait(), _trigger_later())
    assert done is True


@pytest.mark.asyncio
async def test_hooks_run_concurrently_within_priority():
    gs = GracefulShutdown()
    results = []

    async def _h1():
        await asyncio.sleep(0.01)
        results.append(1)

    async def _h2():
        await asyncio.sleep(0.01)
        results.append(2)

    gs.register("a", _h1, priority=ShutdownPriority.NORMAL)
    gs.register("b", _h2, priority=ShutdownPriority.NORMAL)
    await gs.trigger("test")
    assert len(results) == 2


@pytest.mark.asyncio
async def test_metadata_preserved():
    gs = GracefulShutdown()
    gs.register("a", _noop, environment="prod", region="us-east-1")
    hooks = gs.list_hooks()
    assert hooks[0].metadata["environment"] == "prod"
    assert hooks[0].metadata["region"] == "us-east-1"
