"""Verifies that DSL rules are enforced the same in sync and async contexts."""

import asyncio

from agentwatch.core.policy_dsl import PolicyEngine
from agentwatch.core.safety import SafetyEngine
from agentwatch.core.schema import AgentEvent, AgentFramework, EventType, ToolCallData


def test_sync_vs_async_parity():
    """
    Verifies parity between synchronous and asynchronous execution.
    """
    dsl = """
    rules:
      - if: command contains "secret"
        then: block
    """
    policy_engine = PolicyEngine.from_yaml(dsl)
    engine = SafetyEngine(policy_engine=policy_engine)

    # A command that matches the DSL rule but NOT the builtin patterns
    tool_call = ToolCallData(tool_name="bash", raw_command="cat secret.txt")

    event = AgentEvent(
        session_id="test-session",
        agent_id="test-agent",
        framework=AgentFramework.CLAUDE_CODE,
        event_type=EventType.TOOL_CALL,
        tool_call=tool_call,
    )

    # 1. Test Sync
    blocked_sync, reasons_sync = engine.check_tool_call_sync(tool_call)

    # 2. Test Async
    try:
        old_loop = asyncio.get_event_loop_policy().get_event_loop()
    except (RuntimeError, AssertionError):
        old_loop = None

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        checked_event = loop.run_until_complete(engine.check_event(event))
        blocked_async = checked_event.safety.blocked
        reasons_async = checked_event.safety.reasons
    finally:
        loop.close()
        if old_loop:
            asyncio.set_event_loop(old_loop)
        else:
            asyncio.set_event_loop(None)

    print("\n[PARITY CHECK - DSL BYPASS]")
    print(f"Command: {tool_call.raw_command}")
    print(f"Sync:  blocked={blocked_sync}, reasons={reasons_sync}")
    print(f"Async: blocked={blocked_async}, reasons={reasons_async}")

    # Assertion parity of block state and reasons
    assert blocked_sync == blocked_async, (
        f"Sync/async block discrepancy: {blocked_sync} != {blocked_async}"
    )
    assert reasons_sync == reasons_async, (
        f"Sync/async reasons discrepancy: {reasons_sync} != {reasons_async}"
    )
    assert (len(reasons_sync) > 0) == blocked_sync, (
        "Metadata discrepancy: blocked is True but no reasons provided"
    )


if __name__ == "__main__":
    test_sync_vs_async_parity()
