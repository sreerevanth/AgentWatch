
import pytest
import asyncio
from agentwatch.core.schema import AgentEvent, EventType, ToolCallData, AgentFramework
from agentwatch.core.safety import SafetyEngine, RiskLevel, SafetyPolicy
from agentwatch.core.policy_dsl import PolicyEngine

def test_sync_vs_async_parity():
    """
    Demonstrates the bypass by showing a DSL rule that blocks in async but is ignored in sync.
    """
    dsl = """
    rules:
      - if: command contains "secret"
        then: block
    """
    policy_engine = PolicyEngine.from_yaml(dsl)
    engine = SafetyEngine(policy_engine=policy_engine)
    
    # A command that matches the DSL rule but NOT the builtin patterns
    tool_call = ToolCallData(
        tool_name="bash",
        raw_command="cat secret.txt"
    )
    
    event = AgentEvent(
        session_id="test-session",
        agent_id="test-agent",
        framework=AgentFramework.CLAUDE_CODE,
        event_type=EventType.TOOL_CALL,
        tool_call=tool_call
    )
    
    # 1. Test Sync
    blocked_sync, reasons_sync = engine.check_tool_call_sync(tool_call)
    
    # 2. Test Async
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        checked_event = loop.run_until_complete(engine.check_event(event))
        blocked_async = checked_event.safety.blocked
        reasons_async = checked_event.safety.reasons
    finally:
        loop.close()
    
    print(f"\n[PARITY CHECK - DSL BYPASS]")
    print(f"Command: {tool_call.raw_command}")
    print(f"Sync:  blocked={blocked_sync}, reasons={reasons_sync}")
    print(f"Async: blocked={blocked_async}, reasons={reasons_async}")
    
    if blocked_sync != blocked_async:
        print("\n[REPRO] DISCREPANCY DETECTED: Sync safety bypassed DSL rule.")

if __name__ == "__main__":
    test_sync_vs_async_parity()
