"""AutoGPT adapter."""

from __future__ import annotations

import uuid
from typing import Any, Dict, Optional

from agentwatch.core.event_bus import EventBus, get_event_bus
from agentwatch.core.schema import AgentEvent, AgentFramework, EventType, ExecutionStatus, ToolCallData, ToolResultData


class AutoGPTAdapter:
    def __init__(self, session_id: Optional[str] = None, agent_id: Optional[str] = None, event_bus: Optional[EventBus] = None):
        self.session_id = session_id or str(uuid.uuid4())
        self.agent_id = agent_id or f"autogpt-{uuid.uuid4().hex[:8]}"
        self._bus = event_bus or get_event_bus()

    async def emit_action(self, command: str, arguments: Optional[Dict[str, Any]] = None) -> AgentEvent:
        event = AgentEvent(
            session_id=self.session_id,
            agent_id=self.agent_id,
            framework=AgentFramework.AUTOGPT,
            event_type=EventType.TOOL_CALL,
            tool_call=ToolCallData(tool_name="autogpt_action", raw_command=command, arguments=arguments or {}),
        )
        await self._bus.publish(event)
        return event

    async def emit_result(self, output: Any, error: Optional[str] = None) -> AgentEvent:
        event = AgentEvent(
            session_id=self.session_id,
            agent_id=self.agent_id,
            framework=AgentFramework.AUTOGPT,
            event_type=EventType.TOOL_RESULT if error is None else EventType.TOOL_ERROR,
            status=ExecutionStatus.SUCCESS if error is None else ExecutionStatus.FAILURE,
            tool_result=ToolResultData(tool_name="autogpt_action", output=output, error=error),
        )
        await self._bus.publish(event)
        return event
