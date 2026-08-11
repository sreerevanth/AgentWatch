"""Tests for the Phase 5 (#665) advisory-only refactor of ``ReasoningAuditor``.

The v1 auditor emitted verdicts ``"sound" / "acceptable" / "weak"`` and lived
next to substring pattern matching. The v2 refactor promotes an explicit
advisory taxonomy (``advisory_clean`` / ``advisory_note`` / ``advisory_warn``)
and moves the legacy regex matching to the Capability Lattice.

These tests pin the new surface while preserving the v1 risk-signal names
so dashboards keep working.
"""

from __future__ import annotations

import asyncio

from agentwatch.core.schema import (
    AgentEvent,
    AgentFramework,
    EventType,
    ExecutionStatus,
    ToolCallData,
)
from agentwatch.lattice.capability import (
    CapabilitySignal,
    CapabilitySignals,
    detect_capability_signals,
)
from agentwatch.reasoning.auditor import (
    ADVISORY_CLEAN,
    ADVISORY_NOTE,
    ADVISORY_WARN,
    LEGACY_VERDICT_ACCEPTABLE,
    LEGACY_VERDICT_SOUND,
    LEGACY_VERDICT_WEAK,
    ReasoningAuditor,
    StepAudit,
)


def _tool_call(
    tool: str,
    args: dict | None = None,
    raw: str | None = None,
    *,
    status: ExecutionStatus = ExecutionStatus.RUNNING,
) -> AgentEvent:
    return AgentEvent(
        session_id="S",
        agent_id="A",
        framework=AgentFramework.CUSTOM,
        event_type=EventType.TOOL_CALL,
        status=status,
        tool_call=ToolCallData(tool_name=tool, arguments=args or {}, raw_command=raw),
    )


# ----------------------------------------------------------------- verdict taxonomy


def test_verdict_constants_distinct():
    assert {ADVISORY_CLEAN, ADVISORY_NOTE, ADVISORY_WARN} == {
        "advisory_clean",
        "advisory_note",
        "advisory_warn",
    }


def test_legacy_verdict_aliases_preserved():
    # v1 dashboards may still query the old names — they must be importable.
    assert LEGACY_VERDICT_SOUND == "sound"
    assert LEGACY_VERDICT_ACCEPTABLE == "acceptable"
    assert LEGACY_VERDICT_WEAK == "weak"


# ----------------------------------------------------------------- StepAudit advisory-only flag


def test_step_audit_is_advisory_only_default():
    audit = StepAudit(step_index=0, event_id="e", score=0.9, verdict="x", rationale="ok")
    assert audit.is_advisory_only is True


def test_step_audit_to_dict_exposes_advisory_flag():
    audit = StepAudit(step_index=0, event_id="e", score=0.9, verdict="x", rationale="ok")
    payload = audit.to_dict()
    assert payload["is_advisory_only"] is True


# ----------------------------------------------------------------- heuristic verdicts


def test_heuristic_high_score_is_advisory_clean():
    auditor = ReasoningAuditor()
    # A planner-only event with a long output gets score 0.85 (≥ 0.70 threshold).
    event = AgentEvent(
        session_id="S",
        agent_id="A",
        framework=AgentFramework.CUSTOM,
        event_type=EventType.PLANNER_OUTPUT,
        planner_output_preview="Step one then step two then step three then step four then step five then step six then step seven then step eight",
    )
    audit = asyncio.run(auditor.audit_step(0, event))
    assert audit.verdict == ADVISORY_CLEAN, audit.to_dict()


def test_heuristic_low_score_is_advisory_warn():
    auditor = ReasoningAuditor()
    # An event with no planner text, no tool args, and a tool_result error gets
    # score 0.55 - 0.25 = 0.30 (under the 0.40 warn threshold).
    from agentwatch.core.schema import ToolResultData

    event = AgentEvent(
        session_id="S",
        agent_id="A",
        framework=AgentFramework.CUSTOM,
        event_type=EventType.TOOL_CALL,
        tool_call=ToolCallData(tool_name="stub"),
        tool_result=ToolResultData(
            tool_name="stub",
            tool_id="t1",
            output="",
            error="command not found",
        ),
    )
    audit = asyncio.run(auditor.audit_step(0, event))
    assert audit.verdict == ADVISORY_WARN, audit.to_dict()


def test_heuristic_rationale_mentions_advisory_only():
    auditor = ReasoningAuditor()
    event = _tool_call("shell", {"command": "ls"}, raw="ls")
    audit = asyncio.run(auditor.audit_step(0, event))
    assert "advisory-only" in audit.rationale
    assert "lattices" in audit.rationale


# ----------------------------------------------------------------- Capability Lattice


def test_detect_capability_signals_empty_event():
    event = AgentEvent(
        session_id="S",
        agent_id="A",
        framework=AgentFramework.CUSTOM,
        event_type=EventType.SESSION_START,
    )
    result = detect_capability_signals(event)
    assert result.signals == ()
    assert result.has_destructive is False
    assert result.has_privilege_escalation is False
    assert result.has_broad_wildcard is False
    assert result.has_external_fetch is False


def test_detect_capability_signals_destructive():
    event = _tool_call("shell", {"command": "rm -rf /"}, raw="rm -rf /")
    result = detect_capability_signals(event)
    assert result.has_destructive is True
    kinds = {s.kind for s in result.signals}
    assert "destructive_command" in kinds


def test_detect_capability_signals_privilege_escalation():
    event = _tool_call("shell", {"command": "sudo apt-get update"}, raw="sudo apt-get update")
    result = detect_capability_signals(event)
    assert result.has_privilege_escalation is True


def test_detect_capability_signals_broad_wildcard():
    event = _tool_call("shell", {"command": "ls *"}, raw="ls *")
    result = detect_capability_signals(event)
    assert result.has_broad_wildcard is True


def test_detect_capability_signals_external_fetch():
    event = _tool_call(
        "curl", {"command": "curl https://example.com"}, raw="curl https://example.com"
    )
    result = detect_capability_signals(event)
    assert result.has_external_fetch is True


def test_detect_capability_signals_to_risk_signal_names_round_trip():
    event = _tool_call(
        "shell",
        {"command": "sudo rm -rf /tmp/* && curl https://x"},
        raw="sudo rm -rf /tmp/* && curl https://x",
    )
    result = detect_capability_signals(event)
    names = result.to_risk_signal_names()
    assert "destructive_command" in names
    assert "privilege_escalation" in names
    assert "broad_wildcard" in names
    assert "external_fetch" in names


# ----------------------------------------------------------------- CapabilitySignals dataclass


def test_capability_signals_is_frozen():
    signals = CapabilitySignals((), False, False, False, False)
    try:
        signals.has_destructive = True  # type: ignore[misc]
        raise AssertionError("expected frozen dataclass to raise")
    except AttributeError:
        pass


def test_capability_signal_is_frozen():
    sig = CapabilitySignal("destructive_command", "rm -rf")
    try:
        sig.kind = "x"  # type: ignore[misc]
        raise AssertionError("expected frozen dataclass to raise")
    except AttributeError:
        pass


# ----------------------------------------------------------------- auditor delegates to lattice


def test_auditor_risk_signals_match_capability_lattice_names():
    auditor = ReasoningAuditor()
    event = _tool_call(
        "shell",
        {"command": "sudo rm -rf /var/*"},
        raw="sudo rm -rf /var/*",
    )
    audit = asyncio.run(auditor.audit_step(0, event))
    # The auditor's v1-style ``risk_signals`` list must match what the lattice would say.
    expected = detect_capability_signals(event).to_risk_signal_names()
    for name in expected:
        assert name in audit.risk_signals, f"{name!r} missing from auditor's risk_signals"


def test_auditor_does_not_modify_event_status():
    """The auditor must never flip an event's status to BLOCKED."""
    auditor = ReasoningAuditor()
    event = _tool_call(
        "shell",
        {"command": "rm -rf /"},
        raw="rm -rf /",
    )
    asyncio.run(auditor.audit_step(0, event))
    assert event.status != ExecutionStatus.BLOCKED, (
        "Phase 5 (#665): auditor is advisory-only and must not set BLOCKED status"
    )


# ----------------------------------------------------------------- regression — existing risk_signals surface


def test_blocked_action_signal_emitted_when_event_is_blocked():
    """Legacy risk-signal surface must still flag pre-blocked events."""
    auditor = ReasoningAuditor()
    event = _tool_call(
        "shell",
        {"command": "echo hi"},
        raw="echo hi",
        status=ExecutionStatus.BLOCKED,
    )
    audit = asyncio.run(auditor.audit_step(0, event))
    assert "blocked_action" in audit.risk_signals
