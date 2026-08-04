"""v2 Capability Lattice — surface structural risk signals on tool calls.

The Capability Lattice owns the legacy ``_DESTRUCTIVE_PATTERNS`` substring
checks that used to live in ``agentwatch.reasoning.auditor``. Moving them
out of the auditor makes the v2 architecture's separation of concerns
explicit: the auditor is advisory-only; the Capability Lattice surfaces
*structural* signals that the SafetyEngine (or a future v2 Safety Lattice)
can use to block actions.

This module is a pure function library — no I/O, no class state. The set
of matched patterns is returned as a structured list that downstream
consumers can render, log, or escalate.
"""

from __future__ import annotations

from dataclasses import dataclass

from agentwatch.core.schema import AgentEvent, ToolCallData

# Substrings that mark a shell/tool command as destructive. Kept intentionally
# conservative and lowercase; matched against the command + string arguments.
# Moved verbatim from ``agentwatch.reasoning.auditor._DESTRUCTIVE_PATTERNS``
# when the v1 auditor was deprecated to advisory-only.
_DESTRUCTIVE_PATTERNS: tuple[str, ...] = (
    "rm -rf",
    "rm -r ",
    "rmdir",
    "drop table",
    "drop database",
    "truncate ",
    "mkfs",
    "dd if=",
    "shutdown",
    "reboot",
    "> /dev/sd",
    ":(){:|:&};:",
)

# Mirrors the signal taxonomy that the v1 auditor emitted so downstream
# dashboards keep working without code changes.
PRIVILEGE_ESCALATION_MARKERS = ("sudo",)
EXTERNAL_FETCH_MARKERS = ("curl ", "wget ", "http://", "https://")

__all__ = [
    "CapabilitySignal",
    "CapabilitySignals",
    "detect_capability_signals",
]


@dataclass(frozen=True)
class CapabilitySignal:
    """One structural signal surfaced by the Capability Lattice.

    Attributes:
        kind: Signal name (e.g. ``"destructive_command"``). Stable across versions
            so dashboards and audit logs can match on it.
        matched: The substring that triggered the signal. Useful for log-only
            contexts where the actual pattern matched matters for forensics.
    """

    kind: str
    matched: str


@dataclass(frozen=True)
class CapabilitySignals:
    """Aggregate signal report for one tool call."""

    signals: tuple[CapabilitySignal, ...]
    has_destructive: bool
    has_privilege_escalation: bool
    has_broad_wildcard: bool
    has_external_fetch: bool

    def to_risk_signal_names(self) -> list[str]:
        """Return the v1 risk-signal names so dashboards keep working."""
        names: list[str] = []
        if self.has_destructive:
            names.append("destructive_command")
        if self.has_privilege_escalation:
            names.append("privilege_escalation")
        if self.has_broad_wildcard:
            names.append("broad_wildcard")
        if self.has_external_fetch:
            names.append("external_fetch")
        return names


def _command_text(tool_call: ToolCallData) -> str:
    """Lowercased concatenation of ``raw_command`` and string arguments."""
    command = (tool_call.raw_command or "").lower()
    arg_text = (
        " ".join(
            str(value).lower() for value in tool_call.arguments.values() if isinstance(value, str)
        )
        if tool_call.arguments
        else ""
    )
    return f"{command} {arg_text}".strip()


def detect_capability_signals(event: AgentEvent) -> CapabilitySignals:
    """Surface structural risk signals on a tool call.

    Returns an empty :class:`CapabilitySignals` when the event has no
    ``tool_call`` payload, or when no patterns matched.
    """
    tool_call = event.tool_call
    if tool_call is None:
        return CapabilitySignals((), False, False, False, False)

    haystack = _command_text(tool_call)
    signals: list[CapabilitySignal] = []

    for pattern in _DESTRUCTIVE_PATTERNS:
        if pattern in haystack:
            signals.append(CapabilitySignal("destructive_command", pattern))
            break

    for marker in PRIVILEGE_ESCALATION_MARKERS:
        if haystack.startswith(marker) or f"{marker} " in haystack:
            signals.append(CapabilitySignal("privilege_escalation", marker))
            break

    if "*" in haystack:
        signals.append(CapabilitySignal("broad_wildcard", "*"))

    for marker in EXTERNAL_FETCH_MARKERS:
        if marker in haystack:
            signals.append(CapabilitySignal("external_fetch", marker))
            break

    return CapabilitySignals(
        signals=tuple(signals),
        has_destructive=any(s.kind == "destructive_command" for s in signals),
        has_privilege_escalation=any(s.kind == "privilege_escalation" for s in signals),
        has_broad_wildcard=any(s.kind == "broad_wildcard" for s in signals),
        has_external_fetch=any(s.kind == "external_fetch" for s in signals),
    )
