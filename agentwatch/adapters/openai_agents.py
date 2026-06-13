"""
AgentWatch OpenAI Agents SDK Adapter
"""

from __future__ import annotations

import uuid

from agentwatch.core.event_bus import EventBus, get_event_bus
from agentwatch.core.schema import (
    AgentEvent,
    AgentFramework,
    EventType,
    ExecutionStatus,
)


class AgentWatchOpenAIAgentsAdapter:
    def __init__(
        self,
        session_id: str | None = None,
        agent_id: str | None = None,
        event_bus: EventBus | None = None,
    ):
        self.session_id = session_id or str(uuid.uuid4())
        self.agent_id = agent_id or f"openai-agents-{uuid.uuid4().hex[:8]}"
        self._bus = event_bus or get_event_bus()
        self._step = 0

    def _step_up(self) -> int:
        self._step += 1
        return self._step

    def _base(self, event_type: EventType) -> AgentEvent:
        return AgentEvent(
            session_id=self.session_id,
            agent_id=self.agent_id,
            agent_name="openai_agents",
            framework=AgentFramework.OPENAI_AGENTS,
            event_type=event_type,
            step_number=self._step_up(),
        )

    def _emit(self, event: AgentEvent) -> None:
        self._bus.publish_sync(event)

    def on_agent_start(self, **kwargs):
        event = self._base(EventType.AGENT_START)
        event.metadata["kwargs"] = kwargs
        self._emit(event)

    def on_agent_end(self, result=None):
        event = self._base(EventType.AGENT_END)
        event.status = ExecutionStatus.SUCCESS
        event.metadata["result"] = result
        self._emit(event)

    def on_tool_call(self, tool_name, input=None):
        event = self._base(EventType.TOOL_CALL)
        event.metadata["tool_name"] = tool_name
        event.metadata["input"] = input
        self._emit(event)

    def on_tool_result(self, tool_name, result=None):
        event = self._base(EventType.TOOL_RESULT)
        event.status = ExecutionStatus.SUCCESS
        event.metadata["tool_name"] = tool_name
        event.metadata["result"] = result
        self._emit(event)

    def on_handoff(self, from_agent, to_agent):
        event = self._base(EventType.PLANNER_OUTPUT)
        event.metadata["from_agent"] = from_agent
        event.metadata["to_agent"] = to_agent
        self._emit(event)

    def on_agent_error(self, error):
        event = self._base(EventType.AGENT_ERROR)
        event.status = ExecutionStatus.FAILURE
        event.metadata["error"] = str(error)
        self._emit(event)

    def on_agent_finish(self, result=None):
        self.on_agent_end(result=result)
