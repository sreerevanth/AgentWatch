"""Regression tests for bugs found during the v3 work."""

from __future__ import annotations

import asyncio

from agentwatch.core.event_bus import EventBus
from agentwatch.core.schema import AgentEvent, EventType
from agentwatch.tracing.collector import TraceCollector


def test_hipaa_redaction_does_not_leak_into_other_handlers():
    """v0.2 bug: the collector redacted the shared event in place, so whether another handler
    (the Postgres writer) saw raw or redacted PHI depended on dispatch order."""
    for _ in range(5):  # dispatch order comes from a set; repeat to cover orderings
        bus = EventBus()
        collector = TraceCollector(hipaa_compliance_mode=True)
        seen: list[str] = []

        async def persist(ev: AgentEvent) -> None:
            seen.append(ev.goal or "")

        bus.subscribe_fn(collector.ingest, handler_id="collector")
        bus.subscribe_fn(persist, handler_id="persist")
        original = "MRN: 1234567 diagnosed with diabetes"
        event = AgentEvent(session_id="s", agent_id="a", event_type=EventType.SESSION_START, goal=original)
        asyncio.run(bus.publish(event))
        assert event.goal == original, "publisher's object must not be mutated"
        assert seen == [original], "other handlers see the event as published"
        trace = collector.get_trace("s")
        assert trace is not None
        assert "1234567" not in (trace.session.goal or ""), "collector keeps only its redacted copy"
