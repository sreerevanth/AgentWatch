"""
AgentWatch Universal watch() — FOUND-001

One-line agent instrumentation:

    from agentwatch import watch
    agent = watch(agent)

Auto-detects the agent's framework, attaches the right adapter,
and returns the agent unchanged. Never blocks or crashes the host agent.

Supported frameworks (detected by class lineage, module name, or duck typing):
  - LangChain         (AgentExecutor, Runnable)
  - LangGraph         (CompiledGraph)
  - CrewAI            (Crew, Agent)
  - AutoGPT           (Agent)
  - AutoGen           (ConversableAgent, GroupChat)
  - Claude Code       (subprocess wrapper, SDK client)
  - OpenAI Agents SDK (Agent, Runner)
  - Smolagents        (CodeAgent, ToolCallingAgent)
  - OpenClaw          (ClawAgent)

Unknown frameworks fall back to GenericAdapter (best-effort wrapping
of any object with `.run`, `.invoke`, `.__call__`, or `astream`).
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from agentwatch.core.event_bus import EventBus, get_event_bus
from agentwatch.core.schema import (
    AgentEvent,
    AgentFramework,
    EventType,
    ExecutionStatus,
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# Framework detection
# ─────────────────────────────────────────────


def detect_framework(agent: Any) -> AgentFramework:
    """
    Identify the framework backing `agent` without importing any framework.
    Returns AgentFramework.CUSTOM if unknown.
    """
    if agent is None:
        return AgentFramework.CUSTOM

    cls = type(agent)
    mro_names = [f"{c.__module__}.{c.__name__}" for c in cls.__mro__]
    blob = " ".join(mro_names).lower()
    cls_name = cls.__name__.lower()

    # LangGraph before LangChain — LangGraph uses langchain_core internally
    if "langgraph" in blob or "compiledgraph" in cls_name or "stategraph" in cls_name:
        return AgentFramework.CUSTOM  # mapped to custom; specific adapter handles it
    if "langchain" in blob or "agentexecutor" in cls_name or "runnable" in cls_name:
        return AgentFramework.LANGCHAIN
    if "crewai" in blob or cls_name in {"crew", "agent"} and "crewai" in blob:
        return AgentFramework.CREWAI
    if "autogen" in blob or "conversableagent" in cls_name or "groupchat" in cls_name:
        return AgentFramework.CUSTOM
    if "autogpt" in blob:
        return AgentFramework.AUTOGPT
    if "smolagents" in blob or "codeagent" in cls_name or "toolcallingagent" in cls_name:
        return AgentFramework.CUSTOM
    if "openai" in blob and ("agent" in cls_name or "runner" in cls_name):
        return AgentFramework.OPENAI_AGENTS
    if "claude" in blob and "code" in blob:
        return AgentFramework.CLAUDE_CODE
    if "openclaw" in blob or "clawagent" in cls_name:
        return AgentFramework.OPENCLAW

    return AgentFramework.CUSTOM


def detect_framework_label(agent: Any) -> str:
    """Return a human-readable framework label, even for CUSTOM detections."""
    cls = type(agent)
    blob = " ".join(f"{c.__module__}.{c.__name__}" for c in cls.__mro__).lower()
    cls_name = cls.__name__.lower()

    if "langgraph" in blob or "compiledgraph" in cls_name:
        return "langgraph"
    if "autogen" in blob or "conversableagent" in cls_name:
        return "autogen"
    if "smolagents" in blob or cls_name in {"codeagent", "toolcallingagent"}:
        return "smolagents"
    fw = detect_framework(agent)
    return fw.value


# ─────────────────────────────────────────────
# GenericAdapter — fallback wrapper
# ─────────────────────────────────────────────


class GenericAdapter:
    """
    Best-effort wrapper that intercepts the agent's primary entry points
    (`__call__`, `invoke`, `run`, `astream`, `ainvoke`) and emits events.

    Never raises into the host agent — failures are swallowed and logged.
    """

    INTERCEPT_METHODS = (
        "__call__",
        "invoke",
        "ainvoke",
        "run",
        "arun",
        "stream",
        "astream",
        "execute",
        "kickoff",  # CrewAI
        "step",     # AutoGPT-like
    )

    def __init__(
        self,
        agent: Any,
        framework: AgentFramework = AgentFramework.CUSTOM,
        framework_label: str = "custom",
        event_bus: EventBus | None = None,
        session_id: str | None = None,
        agent_id: str | None = None,
    ):
        self.agent = agent
        self.framework = framework
        self.framework_label = framework_label
        self.bus = event_bus or get_event_bus()
        self.session_id = session_id or str(uuid.uuid4())
        self.agent_id = agent_id or f"{framework_label}-{uuid.uuid4().hex[:8]}"
        self._step = 0
        self._wrapped_methods: dict[str, Any] = {}

    def attach(self) -> Any:
        """
        Monkey-patch the agent's methods so each call emits AgentEvents.
        Returns the (same) agent object — never a proxy, so identity is preserved.
        """
        emitted_session_start = False

        for name in self.INTERCEPT_METHODS:
            if not hasattr(self.agent, name):
                continue
            original = getattr(self.agent, name)
            if not callable(original):
                continue
            # Skip already-wrapped methods (idempotent)
            if getattr(original, "_agentwatch_wrapped", False):
                continue

            wrapped = self._wrap(name, original)
            wrapped._agentwatch_wrapped = True  # type: ignore[attr-defined]
            try:
                setattr(self.agent, name, wrapped)
                self._wrapped_methods[name] = original
            except (AttributeError, TypeError):
                # Some agents have read-only attrs (e.g. slotted classes) — skip
                logger.debug("Could not wrap %s on %s", name, type(self.agent).__name__)
                continue

            if not emitted_session_start:
                self._emit_safely(
                    EventType.SESSION_START,
                    metadata={"framework": self.framework_label},
                )
                emitted_session_start = True

        # Stash the adapter on the agent for later retrieval/diagnostics
        try:
            self.agent._agentwatch_adapter = self
        except (AttributeError, TypeError):
            pass

        return self.agent

    def _wrap(self, method_name: str, original: Any) -> Any:
        import asyncio
        import functools

        if asyncio.iscoroutinefunction(original):

            @functools.wraps(original)
            async def async_wrapped(*args: Any, **kwargs: Any) -> Any:
                self._step += 1
                self._emit_safely(
                    EventType.AGENT_START,
                    metadata={"method": method_name, "step": self._step},
                )
                try:
                    result = await original(*args, **kwargs)
                    self._emit_safely(
                        EventType.AGENT_END,
                        status=ExecutionStatus.SUCCESS,
                        metadata={"method": method_name},
                    )
                    return result
                except Exception as exc:
                    self._emit_safely(
                        EventType.AGENT_ERROR,
                        status=ExecutionStatus.FAILURE,
                        metadata={"method": method_name, "error": str(exc)},
                    )
                    raise

            return async_wrapped

        @functools.wraps(original)
        def sync_wrapped(*args: Any, **kwargs: Any) -> Any:
            self._step += 1
            self._emit_safely(
                EventType.AGENT_START,
                metadata={"method": method_name, "step": self._step},
            )
            try:
                result = original(*args, **kwargs)
                self._emit_safely(
                    EventType.AGENT_END,
                    status=ExecutionStatus.SUCCESS,
                    metadata={"method": method_name},
                )
                return result
            except Exception as exc:
                self._emit_safely(
                    EventType.AGENT_ERROR,
                    status=ExecutionStatus.FAILURE,
                    metadata={"method": method_name, "error": str(exc)},
                )
                raise

        return sync_wrapped

    def _emit_safely(
        self,
        event_type: EventType,
        *,
        status: ExecutionStatus = ExecutionStatus.RUNNING,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Emit an event without ever raising into the host agent."""
        try:
            event = AgentEvent(
                session_id=self.session_id,
                agent_id=self.agent_id,
                agent_name=self.framework_label,
                framework=self.framework,
                event_type=event_type,
                status=status,
                step_number=self._step,
                metadata=metadata or {},
            )
            self.bus.publish_sync(event)
        except Exception as exc:  # noqa: BLE001 — invisible-when-healthy contract
            logger.debug("AgentWatch emit failed (suppressed): %s", exc)


# ─────────────────────────────────────────────
# Framework-specific adapter wiring
# ─────────────────────────────────────────────


def _attach_langchain(agent: Any, session_id: str | None, bus: EventBus) -> Any:
    """Attach an AgentWatchCallbackHandler if the agent supports callbacks."""
    try:
        from agentwatch.adapters.langchain import AgentWatchCallbackHandler

        handler = AgentWatchCallbackHandler(
            session_id=session_id, event_bus=bus
        )
        # Newer LangChain: set on `.callbacks`
        if hasattr(agent, "callbacks"):
            existing = getattr(agent, "callbacks", None) or []
            if isinstance(existing, list):
                if not any(isinstance(h, AgentWatchCallbackHandler) for h in existing):
                    existing.append(handler)
                    agent.callbacks = existing
            else:
                # CallbackManager instance — try add_handler
                if hasattr(existing, "add_handler"):
                    try:
                        existing.add_handler(handler)
                    except Exception:  # noqa: BLE001
                        pass
        # Stash for diagnostics
        try:
            agent._agentwatch_handler = handler
        except (AttributeError, TypeError):
            pass
        return agent
    except Exception as exc:  # noqa: BLE001
        logger.debug("LangChain attach failed, falling back to generic: %s", exc)
        return None


def _attach_langgraph(agent: Any, session_id: str | None, bus: EventBus) -> Any:
    """LangGraph CompiledGraph exposes `invoke`/`astream` — wrap them generically.
    Also try to install a LangChain callback handler since LangGraph reuses it.
    """
    try:
        from agentwatch.adapters.langgraph import LangGraphAdapter

        return LangGraphAdapter(
            agent, event_bus=bus, session_id=session_id
        ).attach()
    except Exception as exc:  # noqa: BLE001
        logger.debug("LangGraph attach failed: %s", exc)
        return None


def _attach_autogen(agent: Any, session_id: str | None, bus: EventBus) -> Any:
    try:
        from agentwatch.adapters.autogen import AutoGenAdapter

        return AutoGenAdapter(
            agent, event_bus=bus, session_id=session_id
        ).attach()
    except Exception as exc:  # noqa: BLE001
        logger.debug("AutoGen attach failed: %s", exc)
        return None


def _attach_smolagents(agent: Any, session_id: str | None, bus: EventBus) -> Any:
    try:
        from agentwatch.adapters.smolagents import SmolagentsAdapter

        return SmolagentsAdapter(
            agent, event_bus=bus, session_id=session_id
        ).attach()
    except Exception as exc:  # noqa: BLE001
        logger.debug("Smolagents attach failed: %s", exc)
        return None


# ─────────────────────────────────────────────
# Public watch() API
# ─────────────────────────────────────────────


def watch(
    agent: Any,
    *,
    session_id: str | None = None,
    agent_id: str | None = None,
    event_bus: EventBus | None = None,
) -> Any:
    """
    Instrument an agent for AgentWatch observability.

    Returns the same agent object (or, for some frameworks, a wrapped object
    that quacks identically). Never crashes the host — if instrumentation
    fails, the original agent is returned unchanged.

    Args:
        agent:       any supported agent or generic callable
        session_id:  optional explicit session ID (auto-generated otherwise)
        agent_id:    optional explicit agent ID
        event_bus:   override the default EventBus (mostly for testing)
    """
    if agent is None:
        logger.warning("watch() called with None — returning None")
        return agent

    bus = event_bus or get_event_bus()
    label = detect_framework_label(agent)

    try:
        if label == "langchain":
            attached = _attach_langchain(agent, session_id, bus)
            if attached is not None:
                return attached
        elif label == "langgraph":
            attached = _attach_langgraph(agent, session_id, bus)
            if attached is not None:
                return attached
        elif label == "autogen":
            attached = _attach_autogen(agent, session_id, bus)
            if attached is not None:
                return attached
        elif label == "smolagents":
            attached = _attach_smolagents(agent, session_id, bus)
            if attached is not None:
                return attached

        # Fallback: generic wrapping
        framework = detect_framework(agent)
        adapter = GenericAdapter(
            agent,
            framework=framework,
            framework_label=label,
            event_bus=bus,
            session_id=session_id,
            agent_id=agent_id,
        )
        return adapter.attach()

    except Exception as exc:  # noqa: BLE001 — invisible-when-healthy contract
        logger.warning(
            "watch() instrumentation failed for %s: %s — returning agent unmodified",
            type(agent).__name__,
            exc,
        )
        return agent


__all__ = ["watch", "detect_framework", "detect_framework_label", "GenericAdapter"]
