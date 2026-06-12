"""
Agent Execution Logging

Comprehensive structured logging for agent execution lifecycle, including
parameter tracking, API calls, responses, and error context.
"""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)


class ExecutionLogger:
    """Structured logging for agent task execution."""

    def __init__(self, agent_id: str, session_id: str, task_id: str) -> None:
        """Initialize execution logger with context."""
        self.agent_id = agent_id
        self.session_id = session_id
        self.task_id = task_id
        self.context = {
            "agent_id": agent_id,
            "session_id": session_id,
            "task_id": task_id,
            "started_at": datetime.now(UTC).isoformat(),
        }

    def _format_log(self, level: str, message: str, **kwargs: Any) -> dict[str, Any]:
        """Format log entry with context and metadata."""
        return {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": level,
            "message": message,
            **self.context,
            **kwargs,
        }

    def log_step(self, step_name: str, details: dict[str, Any] | None = None) -> None:
        """Log an execution step."""
        logger.info(
            json.dumps(
                self._format_log(
                    "INFO",
                    f"Execution step: {step_name}",
                    step=step_name,
                    details=details or {},
                )
            )
        )

    def log_api_call(
        self,
        endpoint: str,
        method: str,
        parameters: dict[str, Any],
        headers: dict[str, Any],
    ) -> None:
        """Log API call with parameters."""
        logger.info(
            json.dumps(
                self._format_log(
                    "INFO",
                    f"API call: {method} {endpoint}",
                    api_endpoint=endpoint,
                    api_method=method,
                    api_parameters=parameters,
                    api_headers=self._redact_sensitive(headers),
                )
            )
        )

    def log_api_response(
        self,
        endpoint: str,
        status_code: int,
        response_body: Any,
        latency_ms: float,
    ) -> None:
        """Log API response with latency."""
        logger.info(
            json.dumps(
                self._format_log(
                    "INFO",
                    f"API response: {status_code}",
                    api_endpoint=endpoint,
                    api_status=status_code,
                    api_response=response_body,
                    latency_ms=latency_ms,
                )
            )
        )

    def log_error(
        self,
        error_message: str,
        error_type: str,
        stack_trace: str,
        context_data: dict[str, Any] | None = None,
    ) -> None:
        """Log error with full context and stack trace."""
        logger.error(
            json.dumps(
                self._format_log(
                    "ERROR",
                    error_message,
                    error_type=error_type,
                    error_stack_trace=stack_trace,
                    error_context=context_data or {},
                )
            )
        )

    def log_execution_complete(
        self,
        status: str,
        duration_ms: float,
        result: Any | None = None,
    ) -> None:
        """Log execution completion."""
        logger.info(
            json.dumps(
                self._format_log(
                    "INFO",
                    f"Execution complete: {status}",
                    execution_status=status,
                    duration_ms=duration_ms,
                    result=result,
                )
            )
        )

    @staticmethod
    def _redact_sensitive(data: dict[str, Any]) -> dict[str, Any]:
        """Remove sensitive data from logs (API keys, tokens, etc)."""
        redacted = data.copy()
        sensitive_keys = {"authorization", "api_key", "token", "password", "secret"}
        for key in sensitive_keys:
            if key in redacted:
                redacted[key] = "***REDACTED***"
        return redacted

    @contextmanager
    def log_api_execution(
        self,
        endpoint: str,
        method: str,
        parameters: dict[str, Any],
    ) -> Generator[None, None, None]:
        """Context manager for API execution with automatic timing."""
        start_time = time.time()
        self.log_api_call(endpoint, method, parameters, {})
        try:
            yield
        except Exception as e:
            self.log_error(
                f"API call failed: {str(e)}",
                type(e).__name__,
                str(e),
                {"endpoint": endpoint, "method": method},
            )
            raise
        finally:
            latency_ms = (time.time() - start_time) * 1000
            logger.debug(f"API call latency: {latency_ms:.2f}ms")
