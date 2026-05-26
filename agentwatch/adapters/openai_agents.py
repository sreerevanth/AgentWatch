"""
AgentWatch OpenAI Agents SDK Adapter
Hooks into OpenAI Agents SDK to emit normalized AgentWatch events.
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
    ToolCallData,
    ToolResultData,
)

logger = logging.getLogger(__name__)

class AgentWatchOpenAIAgentsAdapter:
    """
    OpenAI Agents SDK callback handler that emits AgentWatch events.

    Usage:
        from agentwatch.adapters.openai_agents import AgentWatchOpenAIAgentsAdapter
        from agents import Runner, Agent

        adapter = AgentWatchOpenAIAgentsAdapter(session_id="my-session")
        # You can pass this adapter directly to the Agent or Runner as hooks
        # depending on whether it inherits from the respective base class in the SDK.
    """

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
        self._run_map: dict[str, str] = {}

    def _step_up(self) -> int:
        self._step += 1
        return self._step

    def _base(self, event_type: EventType, run_id: str | None = None) -> AgentEvent:
        event = AgentEvent(
            session_id=self.session_id,
            agent_id=self.agent_id,
            agent_name="openai_agents",
            framework=AgentFramework.OPENAI_AGENTS,
            event_type=event_type,
            step_number=self._step_up(),
        )
        if run_id:
            self._run_map[str(run_id)] = event.event_id
        return event

    def _emit_sync(self, event: AgentEvent) -> None:
        self._bus.publish_sync(event)

    async def on_agent_start(self, context: Any, agent: Any, **kwargs: Any) -> None:
        event = self._base(EventType.SESSION_START)
        event.metadata["agent_name"] = getattr(agent, "name", "unknown")
        self._emit_sync(event)

    async def on_agent_end(self, context: Any, agent: Any, **kwargs: Any) -> None:
        event = self._base(EventType.SESSION_END)
        event.status = ExecutionStatus.SUCCESS
        event.metadata["agent_name"] = getattr(agent, "name", "unknown")
        self._emit_sync(event)

    async def on_tool_call(self, context: Any, agent: Any, tool_call: Any, **kwargs: Any) -> None:
        event = self._base(EventType.TOOL_CALL)
        tool_name = getattr(tool_call, "name", getattr(tool_call, "function", {}).get("name", "unknown"))
        args = getattr(tool_call, "arguments", getattr(tool_call, "function", {}).get("arguments", {}))
        
        if isinstance(args, str):
            import json
            try:
                args = json.loads(args)
            except Exception:
                args = {"raw": args}
                
        event.tool_call = ToolCallData(
            tool_name=tool_name,
            arguments=args if isinstance(args, dict) else {"raw": args},
        )
        self._emit_sync(event)

    async def on_tool_result(self, context: Any, agent: Any, tool_call: Any, result: Any, **kwargs: Any) -> None:
        event = self._base(EventType.TOOL_RESULT)
        event.status = ExecutionStatus.SUCCESS
        tool_name = getattr(tool_call, "name", getattr(tool_call, "function", {}).get("name", "unknown"))
        
        event.tool_result = ToolResultData(
            tool_name=tool_name,
            output=str(result)[:2000] if result is not None else None,
        )
        self._emit_sync(event)

    async def on_handoff(self, context: Any, agent: Any, target: Any, **kwargs: Any) -> None:
        event = self._base(EventType.PLANNER_OUTPUT)
        event.status = ExecutionStatus.SUCCESS
        event.metadata["handoff_source"] = getattr(agent, "name", "unknown")
        event.metadata["handoff_target"] = getattr(target, "name", "unknown") if hasattr(target, "name") else str(target)
        self._emit_sync(event)
