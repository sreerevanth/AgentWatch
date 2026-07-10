"""Active circuit breaker for AgentWatch.

Provides a CLOSED -> OPEN -> PAUSED -> HALF_OPEN -> CLOSED state machine that
watches agent execution for threshold breaches (tokens, errors, hallucinations),
can safely pause and resume an agent by checkpointing its state through the
existing rollback engine, and records every transition for EU AI Act Article 12
record-keeping through the existing governance package.
"""

from agentwatch.circuit_breaker.breaker import (
    CircuitBreaker,
    CircuitState,
    TransitionRecord,
    TripReason,
)
from agentwatch.circuit_breaker.thresholds import CircuitThresholds

__all__ = [
    "CircuitBreaker",
    "CircuitState",
    "TripReason",
    "TransitionRecord",
    "CircuitThresholds",
]
