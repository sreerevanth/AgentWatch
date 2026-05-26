"""OpenClaw adapter."""

from __future__ import annotations

import uuid
from typing import Any, Dict, Optional

from agentwatch.core.event_bus import EventBus, get_event_bus
from agentwatch.core.schema import AgentEvent, AgentFramework, EventType


class OpenClawAdapter:
    def __init__(self, session_id: Optional[str] = None, agent_id: Optional[str] = None, event_bus: Optional[EventBus] = None):
        self.session_id = session_id or str(uuid.uuid4())
        self.agent_id = agent_id or f"openclaw-{uuid.uuid4().hex[:8]}"
        self._bus = event_bus or get_event_bus()

    async def emit_observation(self, payload: Dict[str, Any]) -> AgentEvent:
        event = AgentEvent(
            session_id=self.session_id,
            agent_id=self.agent_id,
            framework=AgentFramework.OPENCLAW,
            event_type=EventType.CUSTOM,
            metadata=payload,
        )
        await self._bus.publish(event)
        return event
