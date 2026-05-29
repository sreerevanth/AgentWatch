import pytest
from unittest.mock import MagicMock

from agentwatch.adapters.openai_agents import AgentWatchOpenAIAgentsAdapter
from agentwatch.core.schema import EventType, ExecutionStatus

@pytest.fixture
def mock_bus():
    return MagicMock()

@pytest.fixture
def adapter(mock_bus):
    return AgentWatchOpenAIAgentsAdapter(session_id="test-session", event_bus=mock_bus)

class MockAgent:
    def __init__(self, name="test_agent"):
        self.name = name

class MockToolCall:
    def __init__(self, name="test_tool", arguments=None):
        self.name = name
        self.arguments = arguments or {"arg1": "val1"}

@pytest.mark.asyncio
async def test_session_lifecycle(adapter, mock_bus):
    agent = MockAgent()
    
    await adapter.on_agent_start(context=None, agent=agent)
    assert mock_bus.publish_sync.call_count == 1
    event = mock_bus.publish_sync.call_args[0][0]
    assert event.event_type == EventType.SESSION_START
    assert event.metadata["agent_name"] == "test_agent"
    
    mock_bus.reset_mock()
    
    await adapter.on_agent_end(context=None, agent=agent)
    assert mock_bus.publish_sync.call_count == 1
    event = mock_bus.publish_sync.call_args[0][0]
    assert event.event_type == EventType.SESSION_END
    assert event.status == ExecutionStatus.SUCCESS
    assert event.metadata["agent_name"] == "test_agent"

@pytest.mark.asyncio
async def test_tool_execution(adapter, mock_bus):
    agent = MockAgent()
    tool_call = MockToolCall()
    
    await adapter.on_tool_call(context=None, agent=agent, tool_call=tool_call)
    assert mock_bus.publish_sync.call_count == 1
    event = mock_bus.publish_sync.call_args[0][0]
    assert event.event_type == EventType.TOOL_CALL
    assert event.tool_call.tool_name == "test_tool"
    assert event.tool_call.arguments == {"arg1": "val1"}
    
    mock_bus.reset_mock()
    
    await adapter.on_tool_result(context=None, agent=agent, tool_call=tool_call, result="success_result")
    assert mock_bus.publish_sync.call_count == 1
    event = mock_bus.publish_sync.call_args[0][0]
    assert event.event_type == EventType.TOOL_RESULT
    assert event.status == ExecutionStatus.SUCCESS
    assert event.tool_result.tool_name == "test_tool"
    assert event.tool_result.output == "success_result"

@pytest.mark.asyncio
async def test_handoff(adapter, mock_bus):
    source = MockAgent("source_agent")
    target = MockAgent("target_agent")
        
    await adapter.on_handoff(context=None, agent=source, target=target)
    assert mock_bus.publish_sync.call_count == 1
    event = mock_bus.publish_sync.call_args[0][0]
    assert event.event_type == EventType.PLANNER_OUTPUT
    assert event.metadata["handoff_source"] == "source_agent"
    assert event.metadata["handoff_target"] == "target_agent"

@pytest.mark.asyncio
async def test_error_handling_string_arguments(adapter, mock_bus):
    agent = MockAgent()
    tool_call = MockToolCall(arguments='{"arg1": "val1"}')
    
    await adapter.on_tool_call(context=None, agent=agent, tool_call=tool_call)
    assert mock_bus.publish_sync.call_count == 1
    event = mock_bus.publish_sync.call_args[0][0]
    assert event.event_type == EventType.TOOL_CALL
    assert event.tool_call.arguments == {"arg1": "val1"}

@pytest.mark.asyncio
async def test_error_handling_bad_json_arguments(adapter, mock_bus):
    agent = MockAgent()
    tool_call = MockToolCall(arguments='invalid json')
    
    await adapter.on_tool_call(context=None, agent=agent, tool_call=tool_call)
    assert mock_bus.publish_sync.call_count == 1
    event = mock_bus.publish_sync.call_args[0][0]
    assert event.event_type == EventType.TOOL_CALL
    assert event.tool_call.arguments == {"raw": "invalid json"}
