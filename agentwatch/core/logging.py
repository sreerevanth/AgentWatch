"""Structured logging with correlation ID context propagation.

Provides a logging system that automatically attaches correlation IDs,
session IDs, and agent IDs to all log records within a request scope.
Uses Python's contextvars for thread-safe, async-safe context propagation.
"""

from __future__ import annotations

import logging
import sys
import uuid
from contextvars import ContextVar
from typing import Any

_correlation_id: ContextVar[str | None] = ContextVar("correlation_id", default=None)
_session_id: ContextVar[str | None] = ContextVar("session_id", default=None)
_agent_id: ContextVar[str | None] = ContextVar("agent_id", default=None)
_step_number: ContextVar[int | None] = ContextVar("step_number", default=None)


def generate_correlation_id() -> str:
    return uuid.uuid4().hex[:16]


def get_correlation_id() -> str | None:
    return _correlation_id.get()


def set_correlation_id(cid: str | None) -> None:
    _correlation_id.set(cid)


def get_session_id() -> str | None:
    return _session_id.get()


def set_session_id(sid: str | None) -> None:
    _session_id.set(sid)


def get_agent_id() -> str | None:
    return _agent_id.get()


def set_agent_id(aid: str | None) -> None:
    _agent_id.set(aid)


def get_step_number() -> int | None:
    return _step_number.get()


def set_step_number(step: int | None) -> None:
    _step_number.set(step)


class CorrelationContextFilter(logging.Filter):
    """Logging filter that injects correlation context into every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = get_correlation_id() or ""
        record.session_id = get_session_id() or ""
        record.agent_id = get_agent_id() or ""
        step = get_step_number()
        record.step_number = step if step is not None else ""
        return True


class StructuredFormatter(logging.Formatter):
    """JSON-structured log formatter with correlation context.

    Output format:
    {"timestamp":"...","level":"INFO","logger":"...","correlation_id":"...","session_id":"...","agent_id":"...","step_number":"","message":"..."}
    """

    def format(self, record: logging.LogRecord) -> str:
        import json
        from datetime import datetime, timezone

        log_entry: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "correlation_id": getattr(record, "correlation_id", ""),
            "session_id": getattr(record, "session_id", ""),
            "agent_id": getattr(record, "agent_id", ""),
            "step_number": getattr(record, "step_number", ""),
            "message": record.getMessage(),
        }
        if record.exc_info and record.exc_info[0] is not None:
            log_entry["exception"] = self.formatException(record.exc_info)
        if hasattr(record, "extra_data"):
            log_entry["extra"] = record.extra_data
        return json.dumps(log_entry, default=str)


class HumanReadableFormatter(logging.Formatter):
    """Human-readable formatter with correlation context prefix."""

    def format(self, record: logging.LogRecord) -> str:
        cid = getattr(record, "correlation_id", "")
        sid = getattr(record, "session_id", "")
        prefix_parts = []
        if cid:
            prefix_parts.append(f"cid={cid}")
        if sid:
            prefix_parts.append(f"sid={sid}")
        step = getattr(record, "step_number", "")
        if step != "":
            prefix_parts.append(f"step={step}")
        prefix = f"[{' '.join(prefix_parts)}] " if prefix_parts else ""
        base = f"{record.levelname:8s} {record.name}: {record.getMessage()}"
        msg = f"{prefix}{base}"
        if record.exc_info and record.exc_info[0] is not None:
            msg = f"{msg}\n{self.formatException(record.exc_info)}"
        return msg


def setup_structured_logging(
    level: int = logging.INFO,
    fmt: str = "json",
    stream: Any = None,
) -> None:
    """Configure the root logger with correlation context propagation.

    Args:
        level: Logging level (default: INFO).
        fmt: Format type - "json" for structured, "human" for readable.
        stream: Output stream (default: stderr).
    """
    root = logging.getLogger()
    root.setLevel(level)

    for handler in root.handlers[:]:
        root.removeHandler(handler)

    if stream is None:
        stream = sys.stderr

    handler = logging.StreamHandler(stream)
    handler.setLevel(level)

    if fmt == "json":
        handler.setFormatter(StructuredFormatter())
    else:
        handler.setFormatter(HumanReadableFormatter())

    handler.addFilter(CorrelationContextFilter())
    root.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    """Get a named logger. Correlation context is automatically attached."""
    return logging.getLogger(name)
