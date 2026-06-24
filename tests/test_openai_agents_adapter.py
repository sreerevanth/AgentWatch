from agentwatch.adapters.openai_agents import AgentWatchOpenAIAgentsAdapter
from agentwatch.core.event_bus import EventBus
from agentwatch.core.schema import EventType, ExecutionStatus


def _make_bus():
    bus = EventBus()
    captured = []
    bus.subscribe_fn(
        lambda event: captured.append(event),
        handler_id="test.capture",
    )
    return bus, captured


def test_agent_start_emits_agent_start():
    bus, captured = _make_bus()

    adapter = AgentWatchOpenAIAgentsAdapter(event_bus=bus)
    adapter.on_agent_start(role="Researcher")

    assert len(captured) == 1
    assert captured[0].event_type == EventType.AGENT_START


def test_agent_end_emits_agent_end():
    bus, captured = _make_bus()

    adapter = AgentWatchOpenAIAgentsAdapter(event_bus=bus)
    adapter.on_agent_end(result="done")

    assert len(captured) == 1
    assert captured[0].event_type == EventType.AGENT_END
    assert captured[0].status == ExecutionStatus.SUCCESS


def test_tool_call_emits_tool_call():
    bus, captured = _make_bus()

    adapter = AgentWatchOpenAIAgentsAdapter(event_bus=bus)
    adapter.on_tool_call("calculator", input="2+2")

    assert len(captured) == 1
    assert captured[0].event_type == EventType.TOOL_CALL


def test_tool_result_emits_tool_result():
    bus, captured = _make_bus()

    adapter = AgentWatchOpenAIAgentsAdapter(event_bus=bus)
    adapter.on_tool_result("calculator", result="4")

    assert len(captured) == 1
    assert captured[0].event_type == EventType.TOOL_RESULT


def test_handoff_emits_planner_output():
    bus, captured = _make_bus()

    adapter = AgentWatchOpenAIAgentsAdapter(event_bus=bus)
    adapter.on_handoff("researcher", "writer")

    assert len(captured) == 1
    assert captured[0].event_type == EventType.PLANNER_OUTPUT


def test_agent_error_emits_failure():
    bus, captured = _make_bus()

    adapter = AgentWatchOpenAIAgentsAdapter(event_bus=bus)
    adapter.on_agent_error(RuntimeError("boom"))

    assert len(captured) == 1
    assert captured[0].event_type == EventType.AGENT_ERROR
    assert captured[0].status == ExecutionStatus.FAILURE
