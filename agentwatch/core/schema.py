"""
AgentWatch Universal Event Schema
All agent events are normalized into this schema regardless of framework.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, field_validator


# ─────────────────────────────────────────────
# Enumerations
# ─────────────────────────────────────────────

class EventType(str, Enum):
    """Normalized event kinds emitted by AgentWatch adapters."""

    # Lifecycle
    SESSION_START = "session.start"
    SESSION_END = "session.end"
    AGENT_START = "agent.start"
    AGENT_END = "agent.end"
    AGENT_ERROR = "agent.error"

    # Planning
    PLANNER_INPUT = "planner.input"
    PLANNER_OUTPUT = "planner.output"
    GOAL_SET = "goal.set"
    GOAL_DRIFT = "goal.drift"

    # Tool execution
    TOOL_CALL = "tool.call"
    TOOL_RESULT = "tool.result"
    TOOL_ERROR = "tool.error"
    TOOL_RETRY = "tool.retry"

    # Memory
    MEMORY_READ = "memory.read"
    MEMORY_WRITE = "memory.write"
    MEMORY_EVICT = "memory.evict"
    MEMORY_CONTRADICTION = "memory.contradiction"

    # Safety
    SAFETY_CHECK = "safety.check"
    SAFETY_BLOCK = "safety.block"
    SAFETY_APPROVE = "safety.approve"
    SAFETY_ESCALATE = "safety.escalate"

    # Multi-agent
    AGENT_MESSAGE = "agent.message"
    TASK_DELEGATE = "task.delegate"
    TASK_COMPLETE = "task.complete"
    TASK_FAIL = "task.fail"

    # Rollback
    CHECKPOINT_CREATE = "checkpoint.create"
    ROLLBACK_TRIGGER = "rollback.trigger"
    ROLLBACK_COMPLETE = "rollback.complete"

    # Confidence
    CONFIDENCE_SCORE = "confidence.score"
    ANOMALY_DETECTED = "anomaly.detected"

    # Generic
    CUSTOM = "custom"


class RiskLevel(str, Enum):
    """Severity tier assigned by the safety engine to a tool call or action."""

    SAFE = "safe"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AgentFramework(str, Enum):
    """Source framework that produced an event or session."""

    CLAUDE_CODE = "claude_code"
    LANGCHAIN = "langchain"
    CREWAI = "crewai"
    AUTOGPT = "autogpt"
    OPENAI_AGENTS = "openai_agents"
    HERMES = "hermes"
    OPENCLAW = "openclaw"
    CUSTOM = "custom"


class ExecutionStatus(str, Enum):
    """Lifecycle state of an event, session, or task."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILURE = "failure"
    BLOCKED = "blocked"
    ROLLED_BACK = "rolled_back"
    TIMEOUT = "timeout"


# ─────────────────────────────────────────────
# Core sub-models
# ─────────────────────────────────────────────

class TokenUsage(BaseModel):
    """LLM token counts and optional cost estimate for a single step."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: Optional[float] = None


class ToolCallData(BaseModel):
    """Payload for a tool invocation before execution."""

    tool_name: str
    tool_id: Optional[str] = None
    arguments: Dict[str, Any] = Field(default_factory=dict)
    raw_command: Optional[str] = None
    affected_resources: List[str] = Field(default_factory=list)


class ToolResultData(BaseModel):
    """Payload for a completed or failed tool execution."""

    tool_name: str
    tool_id: Optional[str] = None
    output: Any = None
    error: Optional[str] = None
    exit_code: Optional[int] = None
    execution_time_ms: Optional[float] = None


class SafetyCheckData(BaseModel):
    """Outcome of a safety policy evaluation on a tool call."""

    risk_level: RiskLevel
    risk_score: float = Field(ge=0.0, le=1.0)
    blocked: bool = False
    reasons: List[str] = Field(default_factory=list)
    matched_policies: List[str] = Field(default_factory=list)
    requires_approval: bool = False
    approval_timeout_seconds: int = 60


class MemoryData(BaseModel):
    """Memory read/write metadata (episodic, semantic, or procedural)."""

    memory_type: str  # episodic | semantic | procedural
    key: Optional[str] = None
    content: Optional[str] = None
    embedding_model: Optional[str] = None
    similarity_score: Optional[float] = None
    retrieved_count: int = 0


class ConfidenceData(BaseModel):
    """Confidence and anomaly signals attached to an agent step."""

    overall_score: float = Field(ge=0.0, le=1.0)
    goal_alignment: float = Field(ge=0.0, le=1.0, default=1.0)
    consistency_score: float = Field(ge=0.0, le=1.0, default=1.0)
    anomaly_flags: List[str] = Field(default_factory=list)
    explanation: Optional[str] = None


class AgentMessageData(BaseModel):
    """Inter-agent message in a multi-agent workflow."""

    sender_agent_id: str
    receiver_agent_id: str
    message_type: str  # task | result | query | broadcast
    content: Dict[str, Any] = Field(default_factory=dict)
    correlation_id: Optional[str] = None


class CheckpointData(BaseModel):
    """Rollback checkpoint reference (filesystem, git, memory, or container)."""

    checkpoint_id: str
    snapshot_type: str  # filesystem | memory | git | container
    snapshot_path: Optional[str] = None
    git_ref: Optional[str] = None
    size_bytes: Optional[int] = None


# ─────────────────────────────────────────────
# Universal Event
# ─────────────────────────────────────────────

class AgentEvent(BaseModel):
    """
    Universal event emitted by any AgentWatch adapter.
    All framework-specific events are normalized to this schema.
    """

    # Identity
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    agent_id: str
    agent_name: Optional[str] = None
    framework: AgentFramework = AgentFramework.CUSTOM
    parent_event_id: Optional[str] = None
    trace_id: Optional[str] = None  # OpenTelemetry trace ID

    # Classification
    event_type: EventType
    status: ExecutionStatus = ExecutionStatus.RUNNING

    # Timing
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    duration_ms: Optional[float] = None

    # Context
    step_number: int = 0
    iteration: int = 0
    goal: Optional[str] = None
    task_id: Optional[str] = None
    parent_task_id: Optional[str] = None

    # Payload — one of these is populated per event type
    tool_call: Optional[ToolCallData] = None
    tool_result: Optional[ToolResultData] = None
    safety: Optional[SafetyCheckData] = None
    memory: Optional[MemoryData] = None
    confidence: Optional[ConfidenceData] = None
    agent_message: Optional[AgentMessageData] = None
    checkpoint: Optional[CheckpointData] = None

    # Prompt/planner data (non-hidden, observable artifacts only)
    prompt_preview: Optional[str] = None       # first 500 chars of prompt
    planner_output_preview: Optional[str] = None  # observable planner text

    # Token / cost
    token_usage: Optional[TokenUsage] = None

    # Extensible metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)

    # Environment snapshot
    working_directory: Optional[str] = None
    environment_vars_redacted: List[str] = Field(default_factory=list)

    @field_validator("timestamp", mode="before")
    @classmethod
    def ensure_utc(cls, v: Any) -> datetime:
        """Parse ISO strings and normalize timestamps to UTC-aware datetimes.

        Args:
            v: Raw timestamp value from JSON or Python.

        Returns:
            A timezone-aware datetime in UTC.
        """
        if isinstance(v, str):
            parsed = datetime.fromisoformat(v)
        elif isinstance(v, datetime):
            parsed = v
        else:
            return v

        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

    def model_dump_for_storage(self) -> Dict[str, Any]:
        """Serialize the event for persistence with ISO-8601 timestamps.

        Returns:
            JSON-compatible dict with ``timestamp`` as an ISO string.
        """
        data = self.model_dump(exclude_none=True)
        data["timestamp"] = self.timestamp.isoformat()
        return data

    @property
    def is_dangerous(self) -> bool:
        """Return True if safety metadata indicates HIGH or CRITICAL risk."""
        return bool(
            self.safety
            and self.safety.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL)
        )

    @property
    def is_blocked(self) -> bool:
        """Return True if the event was blocked by the safety engine."""
        return self.status == ExecutionStatus.BLOCKED


# ─────────────────────────────────────────────
# Session model
# ─────────────────────────────────────────────

class AgentSession(BaseModel):
    """Top-level session grouping events from one agent run."""

    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str
    agent_name: Optional[str] = None
    framework: AgentFramework = AgentFramework.CUSTOM
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    ended_at: Optional[datetime] = None
    status: ExecutionStatus = ExecutionStatus.RUNNING
    goal: Optional[str] = None
    total_events: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    final_confidence: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ─────────────────────────────────────────────
# Task graph node
# ─────────────────────────────────────────────

class TaskNode(BaseModel):
    """Node in a delegated task graph within a session."""

    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    parent_task_id: Optional[str] = None
    assigned_agent_id: Optional[str] = None
    title: str
    description: Optional[str] = None
    status: ExecutionStatus = ExecutionStatus.PENDING
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    dependencies: List[str] = Field(default_factory=list)
    outputs: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ─────────────────────────────────────────────
# Plugin manifest
# ─────────────────────────────────────────────

class PluginPermissions(BaseModel):
    """Capability flags requested by a sandboxed plugin."""

    filesystem_read: bool = False
    filesystem_write: bool = False
    network_outbound: bool = False
    network_inbound: bool = False
    subprocess_exec: bool = False
    credential_access: bool = False
    memory_read: bool = True
    memory_write: bool = False


class PluginManifest(BaseModel):
    """Signed manifest describing a plugin and its permissions."""

    plugin_id: str
    name: str
    version: str
    author: str
    description: str
    homepage: Optional[str] = None
    license: str = "MIT"
    permissions: PluginPermissions = Field(default_factory=PluginPermissions)
    trust_level: int = Field(ge=0, le=5, default=0)  # 0=untrusted, 5=core
    signature: Optional[str] = None  # Ed25519 signature
    checksum_sha256: Optional[str] = None
    min_agentwatch_version: str = "0.1.0"
    tags: List[str] = Field(default_factory=list)
