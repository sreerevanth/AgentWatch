"""
AgentWatch CrewAI Adapter
Converts CrewAI lifecycle callbacks into AgentWatch events.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Optional

from agentwatch.core.event_bus import EventBus, get_event_bus
from agentwatch.core.schema import (
    AgentEvent,
    AgentFramework,
    EventType,
    ExecutionStatus,
)

logger = logging.getLogger(__name__)


class AgentWatchCrewAIAdapter:
    """
    Minimal CrewAI adapter following LangChain adapter pattern.
    """

    def __init__(
        self,
        session_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        event_bus: Optional[EventBus] = None,
    ):
        self.session_id = session_id or str(uuid.uuid4())
        self.agent_id = agent_id or f"crewai-{uuid.uuid4().hex[:8]}"
        self._bus = event_bus or get_event_bus()
        self._step = 0

    # ── helpers ───────────────────────────────

    def _next_step(self) -> int:
        self._step += 1
        return self._step

    def _emit(self, event: AgentEvent) -> None:
        self._bus.publish_sync(event)

    def _base(self, event_type: EventType) -> AgentEvent:
        return AgentEvent(
            session_id=self.session_id,
            agent_id=self.agent_id,
            agent_name="crewai",
            framework=AgentFramework.CREWAI,
            event_type=event_type,
            step_number=self._next_step(),
        )

    # ── CrewAI callbacks ──────────────────────

    # on_agent_start → SESSION_START
    def on_agent_start(self, *args, **kwargs):
        event = self._base(EventType.SESSION_START)
        event.status = ExecutionStatus.SUCCESS
        event.metadata = {
            "args": str(args),
            "kwargs": str(kwargs),
        }
        self._emit(event)

    # on_agent_finish → SESSION_END
    def on_agent_finish(self, *args, **kwargs):
        event = self._base(EventType.SESSION_END)
        event.status = ExecutionStatus.SUCCESS
        event.metadata = {
            "result": str(kwargs.get("result")),
        }
        self._emit(event)

    # on_tool_start → TOOL_CALL
    def on_tool_start(self, tool_name, *args, **kwargs):
        event = self._base(EventType.TOOL_CALL)
        event.metadata = {
            "tool_name": tool_name,
            "args": str(args),
            "kwargs": str(kwargs),
        }
        self._emit(event)

    # on_tool_end → TOOL_RESULT
    def on_tool_end(self, tool_name, result=None, *args, **kwargs):
        event = self._base(EventType.TOOL_RESULT)
        event.status = ExecutionStatus.SUCCESS
        event.metadata = {
            "tool_name": tool_name,
            "result": str(result),
        }
        self._emit(event)

    # on_chain_error → ERROR
    def on_chain_error(self, error, *args, **kwargs):
        event = self._base(EventType.ERROR)
        event.status = ExecutionStatus.FAILURE
        event.metadata = {
            "error": str(error),
        }
        self._emit(event)