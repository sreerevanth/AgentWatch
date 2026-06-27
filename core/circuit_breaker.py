"""
Active Circuit Breaker with Safe Pause & Resume
Issue #483 — AgentWatch

State machine: CLOSED → OPEN → PAUSED → HALF_OPEN → CLOSED
"""

from __future__ import annotations

import json
import time
import uuid
import logging
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    PAUSED = "PAUSED"
    HALF_OPEN = "HALF_OPEN"
    RESOLVED = "RESOLVED"


@dataclass
class CircuitBreakerConfig:
    error_threshold: int = 5
    error_window_seconds: float = 60
    max_tokens_per_session: int = 50_000
    hallucination_threshold: float = 0.7
    hallucination_consecutive: int = 3
    half_open_max_calls: int = 1
    recovery_timeout_seconds: float = 300
    pause_requires_manual_resume: bool = True
    auto_resume_timeout_seconds: float = 600


@dataclass
class SessionCheckpoint:
    checkpoint_id: str
    session_id: str
    timestamp: float
    state_snapshot: Dict[str, Any]
    circuit_state: CircuitState
    error_count: int
    token_count: int
    hallucination_consecutive: int
    trigger_reason: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["circuit_state"] = self.circuit_state.value
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "SessionCheckpoint":
        d = dict(d)
        d["circuit_state"] = CircuitState(d["circuit_state"])
        return cls(**d)


@dataclass
class ComplianceEvent:
    event_id: str
    session_id: str
    timestamp: float
    event_type: str
    previous_state: CircuitState
    new_state: CircuitState
    trigger_reason: str
    operator_id: Optional[str]
    checkpoint_id: Optional[str]
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["previous_state"] = self.previous_state.value
        d["new_state"] = self.new_state.value
        return d


@dataclass
class CircuitBreakerResult:
    allowed: bool
    state: CircuitState
    reason: str = ""
    checkpoint_id: Optional[str] = None


class CircuitBreaker:
    def __init__(
        self,
        session_id: str,
        config: Optional[CircuitBreakerConfig] = None,
        on_state_change: Optional[Callable[["CircuitBreaker", CircuitState, CircuitState], None]] = None,
        on_compliance_event: Optional[Callable[[ComplianceEvent], None]] = None,
    ) -> None:
        self.session_id = session_id
        self.config = config or CircuitBreakerConfig()
        self._on_state_change = on_state_change
        self._on_compliance_event = on_compliance_event
        self._state: CircuitState = CircuitState.CLOSED
        self._error_count: int = 0
        self._error_timestamps: List[float] = []
        self._token_count: int = 0
        self._hallucination_consecutive: int = 0
        self._half_open_calls: int = 0
        self._last_open_time: Optional[float] = None
        self._last_pause_time: Optional[float] = None
        self._checkpoints: Dict[str, SessionCheckpoint] = {}
        self._latest_checkpoint_id: Optional[str] = None
        self._compliance_log: List[ComplianceEvent] = []

    @property
    def state(self) -> CircuitState:
        self._maybe_auto_transition()
        return self._state

    def call(self, agent_state: Dict[str, Any], metrics: Optional[Dict[str, Any]] = None) -> CircuitBreakerResult:
        self._maybe_auto_transition()
        metrics = metrics or {}
        self._update_counters(metrics)
        state = self._state

        if state == CircuitState.CLOSED:
            reason = self._check_thresholds()
            if reason:
                self._trip(agent_state, reason)
                return CircuitBreakerResult(allowed=False, state=self._state, reason=reason, checkpoint_id=self._latest_checkpoint_id)
            return CircuitBreakerResult(allowed=True, state=state)

        if state == CircuitState.OPEN:
            return CircuitBreakerResult(allowed=False, state=state, reason="Circuit is OPEN; requests blocked.", checkpoint_id=self._latest_checkpoint_id)

        if state == CircuitState.PAUSED:
            return CircuitBreakerResult(allowed=False, state=state, reason="Agent is PAUSED awaiting operator review.", checkpoint_id=self._latest_checkpoint_id)

        if state == CircuitState.HALF_OPEN:
            if self._half_open_calls >= self.config.half_open_max_calls:
                return CircuitBreakerResult(allowed=False, state=state, reason="HALF_OPEN probe quota exhausted.")
            self._half_open_calls += 1
            return CircuitBreakerResult(allowed=True, state=state)

        return CircuitBreakerResult(allowed=True, state=state)

    def record_success(self) -> None:
        if self._state == CircuitState.HALF_OPEN:
            self._transition(CircuitState.CLOSED, "Probe action succeeded; circuit recovered.")
            self._reset_counters()

    def record_failure(self, agent_state: Dict[str, Any], reason: str = "probe failed") -> None:
        if self._state == CircuitState.HALF_OPEN:
            self._trip(agent_state, reason)

    def pause(self, agent_state: Dict[str, Any], reason: str = "manual pause") -> SessionCheckpoint:
        checkpoint = self._checkpoint(agent_state, reason)
        if self._state not in (CircuitState.PAUSED, CircuitState.RESOLVED):
            self._transition(CircuitState.PAUSED, reason)
        self._last_pause_time = time.time()
        return checkpoint

    def resume(self, operator_id: str, agent_state: Optional[Dict[str, Any]] = None, checkpoint_id: Optional[str] = None) -> SessionCheckpoint:
        if self._state != CircuitState.PAUSED:
            raise RuntimeError(f"Cannot resume — circuit is in state {self._state.value}, not PAUSED.")
        cp_id = checkpoint_id or self._latest_checkpoint_id
        if cp_id is None or cp_id not in self._checkpoints:
            raise RuntimeError("No valid checkpoint found to resume from.")
        checkpoint = self._checkpoints[cp_id]
        if agent_state is not None:
            checkpoint = self._checkpoint(agent_state, f"resume by {operator_id}")
        self._reset_counters()
        self._transition(CircuitState.HALF_OPEN, f"Resumed by operator {operator_id} from checkpoint {cp_id}", operator_id=operator_id, checkpoint_id=cp_id)
        self._half_open_calls = 0
        return checkpoint

    def resolve(self, operator_id: str, notes: str = "") -> None:
        self._transition(CircuitState.RESOLVED, f"Resolved by {operator_id}. Notes: {notes}", operator_id=operator_id)

    def get_checkpoint(self, checkpoint_id: str) -> Optional[SessionCheckpoint]:
        return self._checkpoints.get(checkpoint_id)

    def get_latest_checkpoint(self) -> Optional[SessionCheckpoint]:
        if self._latest_checkpoint_id:
            return self._checkpoints.get(self._latest_checkpoint_id)
        return None

    def list_checkpoints(self) -> List[SessionCheckpoint]:
        return sorted(self._checkpoints.values(), key=lambda c: c.timestamp)

    def compliance_report(self) -> Dict[str, Any]:
        return {
            "report_type": "EU_AI_ACT_ARTICLE_12",
            "session_id": self.session_id,
            "generated_at": time.time(),
            "current_state": self._state.value,
            "total_events": len(self._compliance_log),
            "checkpoints": [c.to_dict() for c in self.list_checkpoints()],
            "event_log": [e.to_dict() for e in self._compliance_log],
            "thresholds": asdict(self.config),
            "summary": {
                "total_errors": self._error_count,
                "total_tokens": self._token_count,
                "consecutive_hallucinations": self._hallucination_consecutive,
                "times_tripped": sum(1 for e in self._compliance_log if e.event_type == "CIRCUIT_TRIPPED"),
                "times_paused": sum(1 for e in self._compliance_log if e.event_type == "AGENT_PAUSED"),
                "times_resumed": sum(1 for e in self._compliance_log if e.event_type == "AGENT_RESUMED"),
            },
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "state": self._state.value,
            "error_count": self._error_count,
            "error_timestamps": self._error_timestamps,
            "token_count": self._token_count,
            "hallucination_consecutive": self._hallucination_consecutive,
            "half_open_calls": self._half_open_calls,
            "last_open_time": self._last_open_time,
            "last_pause_time": self._last_pause_time,
            "latest_checkpoint_id": self._latest_checkpoint_id,
            "checkpoints": {k: v.to_dict() for k, v in self._checkpoints.items()},
            "compliance_log": [e.to_dict() for e in self._compliance_log],
            "config": asdict(self.config),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "CircuitBreaker":
        config = CircuitBreakerConfig(**d["config"])
        cb = cls(session_id=d["session_id"], config=config)
        cb._state = CircuitState(d["state"])
        cb._error_count = d["error_count"]
        cb._error_timestamps = d["error_timestamps"]
        cb._token_count = d["token_count"]
        cb._hallucination_consecutive = d["hallucination_consecutive"]
        cb._half_open_calls = d["half_open_calls"]
        cb._last_open_time = d["last_open_time"]
        cb._last_pause_time = d["last_pause_time"]
        cb._latest_checkpoint_id = d["latest_checkpoint_id"]
        cb._checkpoints = {k: SessionCheckpoint.from_dict(v) for k, v in d["checkpoints"].items()}
        for raw in d["compliance_log"]:
            raw = dict(raw)
            raw["previous_state"] = CircuitState(raw["previous_state"])
            raw["new_state"] = CircuitState(raw["new_state"])
            cb._compliance_log.append(ComplianceEvent(**raw))
        return cb

    def _update_counters(self, metrics: Dict[str, Any]) -> None:
        now = time.time()
        if metrics.get("tokens_used"):
            self._token_count += int(metrics["tokens_used"])
        if metrics.get("error"):
            self._error_timestamps.append(now)
            cutoff = now - self.config.error_window_seconds
            self._error_timestamps = [t for t in self._error_timestamps if t >= cutoff]
            self._error_count = len(self._error_timestamps)
        hallucination_risk = metrics.get("hallucination_risk", 0.0)
        if hallucination_risk >= self.config.hallucination_threshold:
            self._hallucination_consecutive += 1
        else:
            self._hallucination_consecutive = 0

    def _check_thresholds(self) -> Optional[str]:
        if self._error_count >= self.config.error_threshold:
            return f"Error threshold breached: {self._error_count} errors in last {self.config.error_window_seconds}s (limit: {self.config.error_threshold})"
        if self._token_count >= self.config.max_tokens_per_session:
            return f"Token budget exceeded: {self._token_count} tokens used (limit: {self.config.max_tokens_per_session})"
        if self._hallucination_consecutive >= self.config.hallucination_consecutive:
            return f"Consecutive hallucination risk threshold breached: {self._hallucination_consecutive} steps (limit: {self.config.hallucination_consecutive})"
        return None

    def _trip(self, agent_state: Dict[str, Any], reason: str) -> None:
        checkpoint = self._checkpoint(agent_state, reason)
        self._transition(CircuitState.OPEN, reason, checkpoint_id=checkpoint.checkpoint_id)
        self._last_open_time = time.time()
        self._transition(CircuitState.PAUSED, f"Auto-paused after trip: {reason}", checkpoint_id=checkpoint.checkpoint_id)
        self._last_pause_time = time.time()

    def _transition(self, new_state: CircuitState, reason: str, operator_id: Optional[str] = None, checkpoint_id: Optional[str] = None) -> None:
        previous = self._state
        self._state = new_state
        event_type_map = {
            CircuitState.OPEN: "CIRCUIT_TRIPPED",
            CircuitState.PAUSED: "AGENT_PAUSED",
            CircuitState.HALF_OPEN: "AGENT_RESUMED",
            CircuitState.CLOSED: "CIRCUIT_CLOSED",
            CircuitState.RESOLVED: "CIRCUIT_RESOLVED",
        }
        event = ComplianceEvent(
            event_id=str(uuid.uuid4()),
            session_id=self.session_id,
            timestamp=time.time(),
            event_type=event_type_map.get(new_state, "STATE_CHANGE"),
            previous_state=previous,
            new_state=new_state,
            trigger_reason=reason,
            operator_id=operator_id,
            checkpoint_id=checkpoint_id,
        )
        self._compliance_log.append(event)
        if self._on_compliance_event:
            try:
                self._on_compliance_event(event)
            except Exception:
                logger.exception("[CB] Compliance event callback raised")
        if self._on_state_change:
            try:
                self._on_state_change(self, previous, new_state)
            except Exception:
                logger.exception("[CB] State-change callback raised")

    def _checkpoint(self, agent_state: Dict[str, Any], reason: str) -> SessionCheckpoint:
        cp = SessionCheckpoint(
            checkpoint_id=str(uuid.uuid4()),
            session_id=self.session_id,
            timestamp=time.time(),
            state_snapshot=agent_state,
            circuit_state=self._state,
            error_count=self._error_count,
            token_count=self._token_count,
            hallucination_consecutive=self._hallucination_consecutive,
            trigger_reason=reason,
        )
        self._checkpoints[cp.checkpoint_id] = cp
        self._latest_checkpoint_id = cp.checkpoint_id
        return cp

    def _reset_counters(self) -> None:
        self._error_count = 0
        self._error_timestamps = []
        self._hallucination_consecutive = 0
        self._half_open_calls = 0

    def _maybe_auto_transition(self) -> None:
        now = time.time()
        if self._state == CircuitState.OPEN and self._last_open_time is not None and (now - self._last_open_time) >= self.config.recovery_timeout_seconds:
            self._transition(CircuitState.HALF_OPEN, "Auto-recovery timeout elapsed.")
            self._half_open_calls = 0
        if self._state == CircuitState.PAUSED and not self.config.pause_requires_manual_resume and self._last_pause_time is not None and (now - self._last_pause_time) >= self.config.auto_resume_timeout_seconds:
            self._transition(CircuitState.HALF_OPEN, "Auto-resume timeout elapsed.")
            self._half_open_calls = 0
