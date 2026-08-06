"""Tests for structured logging with correlation ID context propagation."""

from __future__ import annotations

import asyncio
import json
import logging
import io

from agentwatch.core.logging import (
    CorrelationContextFilter,
    StructuredFormatter,
    HumanReadableFormatter,
    generate_correlation_id,
    get_correlation_id,
    set_correlation_id,
    get_session_id,
    set_session_id,
    get_agent_id,
    set_agent_id,
    get_step_number,
    set_step_number,
    setup_structured_logging,
    get_logger,
)


def test_generate_correlation_id_returns_hex_string():
    cid = generate_correlation_id()
    assert isinstance(cid, str)
    assert len(cid) == 16
    assert all(c in "0123456789abcdef" for c in cid)


def test_correlation_id_roundtrip():
    set_correlation_id("test-cid-123")
    assert get_correlation_id() == "test-cid-123"
    set_correlation_id(None)
    assert get_correlation_id() is None


def test_session_id_roundtrip():
    set_session_id("sess-abc")
    assert get_session_id() == "sess-abc"
    set_session_id(None)
    assert get_session_id() is None


def test_agent_id_roundtrip():
    set_agent_id("agent-xyz")
    assert get_agent_id() == "agent-xyz"
    set_agent_id(None)
    assert get_agent_id() is None


def test_step_number_roundtrip():
    set_step_number(42)
    assert get_step_number() == 42
    set_step_number(None)
    assert get_step_number() is None


def test_correlation_filter_adds_fields():
    filt = CorrelationContextFilter()
    record = logging.LogRecord("test", logging.INFO, "", 0, "msg", (), None)
    set_correlation_id("cid-1")
    set_session_id("sid-2")
    set_agent_id("aid-3")
    set_step_number(5)
    result = filt.filter(record)
    assert result is True
    assert record.correlation_id == "cid-1"
    assert record.session_id == "sid-2"
    assert record.agent_id == "aid-3"
    assert record.step_number == 5
    set_correlation_id(None)
    set_session_id(None)
    set_agent_id(None)
    set_step_number(None)


def test_correlation_filter_defaults_empty():
    filt = CorrelationContextFilter()
    record = logging.LogRecord("test", logging.INFO, "", 0, "msg", (), None)
    set_correlation_id(None)
    set_session_id(None)
    set_agent_id(None)
    set_step_number(None)
    filt.filter(record)
    assert record.correlation_id == ""
    assert record.session_id == ""
    assert record.agent_id == ""
    assert record.step_number == ""


def test_structured_formatter_outputs_json():
    formatter = StructuredFormatter()
    record = logging.LogRecord(
        "agentwatch.test", logging.INFO, "test.py", 10, "hello world", (), None
    )
    record.correlation_id = "cid-abc"
    record.session_id = "sid-xyz"
    record.agent_id = "agent-1"
    record.step_number = 3
    output = formatter.format(record)
    parsed = json.loads(output)
    assert parsed["level"] == "INFO"
    assert parsed["logger"] == "agentwatch.test"
    assert parsed["message"] == "hello world"
    assert parsed["correlation_id"] == "cid-abc"
    assert parsed["session_id"] == "sid-xyz"
    assert parsed["agent_id"] == "agent-1"
    assert parsed["step_number"] == 3
    assert "timestamp" in parsed


def test_structured_formatter_includes_exception():
    formatter = StructuredFormatter()
    try:
        raise ValueError("boom")
    except ValueError:
        import sys
        record = logging.LogRecord(
            "test", logging.ERROR, "t.py", 1, "error", None, sys.exc_info()
        )
        record.correlation_id = ""
        record.session_id = ""
        record.agent_id = ""
        record.step_number = ""
    output = formatter.format(record)
    parsed = json.loads(output)
    assert "exception" in parsed
    assert "ValueError" in parsed["exception"]


def test_human_readable_formatter_outputs_prefix():
    formatter = HumanReadableFormatter()
    record = logging.LogRecord(
        "agentwatch.test", logging.INFO, "test.py", 10, "hello", (), None
    )
    record.correlation_id = "cid-1"
    record.session_id = "sid-2"
    record.agent_id = ""
    record.step_number = 7
    output = formatter.format(record)
    assert "[cid=cid-1 sid=sid-2 step=7]" in output
    assert "hello" in output


def test_human_readable_no_prefix_when_empty():
    formatter = HumanReadableFormatter()
    record = logging.LogRecord(
        "agentwatch.test", logging.WARNING, "t.py", 1, "warn", (), None
    )
    record.correlation_id = ""
    record.session_id = ""
    record.agent_id = ""
    record.step_number = ""
    output = formatter.format(record)
    assert output.startswith("WARNING")


def test_setup_structured_logging_json():
    stream = io.StringIO()
    setup_structured_logging(level=logging.DEBUG, fmt="json", stream=stream)
    logger = get_logger("agentwatch.test.setup")
    logger.info("test message")
    output = stream.getvalue()
    parsed = json.loads(output.strip())
    assert parsed["message"] == "test message"
    assert parsed["level"] == "INFO"


def test_setup_structured_logging_human():
    stream = io.StringIO()
    setup_structured_logging(level=logging.DEBUG, fmt="human", stream=stream)
    logger = get_logger("agentwatch.test.human")
    logger.info("test human")
    output = stream.getvalue()
    assert "test human" in output


def test_correlation_id_propagates_through_contextvars():
    async def _inner():
        set_correlation_id("async-cid")
        await asyncio.sleep(0)
        assert get_correlation_id() == "async-cid"

    asyncio.run(_inner())


def test_context_isolation_between_tasks():
    results = {}

    async def _task(name: str, cid: str):
        set_correlation_id(cid)
        await asyncio.sleep(0.01)
        results[name] = get_correlation_id()

    async def _main():
        await asyncio.gather(_task("a", "cid-a"), _task("b", "cid-b"))

    asyncio.run(_main())
    assert results["a"] == "cid-a"
    assert results["b"] == "cid-b"
