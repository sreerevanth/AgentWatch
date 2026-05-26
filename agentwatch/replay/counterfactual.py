"""
OBS-009 — Counterfactual Replay.

Rewind a session to any step, swap a tool's output for an alternate value,
and re-run forward through a user-supplied step function.

This is a deterministic engine, not a model rerun. It threads alternate
tool outputs through the same downstream logic the operator wires up.
"""

from __future__ import annotations

import copy
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from agentwatch.core.schema import AgentEvent, EventType, ToolResultData

logger = logging.getLogger(__name__)


@dataclass
class CounterfactualScenario:
    """A what-if scenario: at step N, replace tool result with `replacement`."""

    rewind_to_step: int
    tool_id: str | None = None
    replacement: Any = None
    notes: str = ""


@dataclass
class CounterfactualResult:
    scenario: CounterfactualScenario
    original_events: list[AgentEvent]
    alternate_events: list[AgentEvent]
    diverged_at_step: int | None
    summary: dict[str, Any] = field(default_factory=dict)

    @property
    def diverged(self) -> bool:
        return self.diverged_at_step is not None


# A user-supplied step function maps (prior_events, latest_event) → next_event_or_None
StepFn = Callable[[list[AgentEvent], AgentEvent], AgentEvent | None]


class CounterfactualEngine:
    """Replay a session forward from a chosen step under an alternate output."""

    def __init__(self, step_fn: StepFn | None = None):
        # If no step fn is given, the engine just replays the alternate
        # tool result through the original timeline (no branching).
        self.step_fn = step_fn

    def run(
        self,
        events: list[AgentEvent],
        scenario: CounterfactualScenario,
    ) -> CounterfactualResult:
        if scenario.rewind_to_step < 0 or scenario.rewind_to_step >= len(events):
            raise ValueError(
                f"rewind_to_step {scenario.rewind_to_step} out of range "
                f"[0, {len(events)})"
            )

        prefix = [copy.deepcopy(e) for e in events[: scenario.rewind_to_step + 1]]
        target = prefix[-1]

        # Apply the swap onto the targeted event
        applied = self._apply_swap(target, scenario)

        # Build the alternate timeline by either deferring to step_fn or
        # replaying the original suffix with the swap applied to the very
        # first step (then comparing event-by-event for divergence).
        alternate: list[AgentEvent] = list(prefix)
        diverged_step: int | None = None

        if self.step_fn is not None:
            while True:
                latest = alternate[-1]
                nxt = self.step_fn(alternate, latest)
                if nxt is None:
                    break
                alternate.append(nxt)
        else:
            original_suffix = events[scenario.rewind_to_step + 1 :]
            for idx, orig in enumerate(original_suffix):
                clone = copy.deepcopy(orig)
                alternate.append(clone)
                # mark divergence if applied swap chained through (we have no
                # downstream simulator, so just record the swap step)
                if diverged_step is None and applied:
                    diverged_step = scenario.rewind_to_step + idx

        summary = {
            "rewind_step": scenario.rewind_to_step,
            "swap_applied": applied,
            "original_length": len(events),
            "alternate_length": len(alternate),
        }

        return CounterfactualResult(
            scenario=scenario,
            original_events=list(events),
            alternate_events=alternate,
            diverged_at_step=diverged_step if applied else None,
            summary=summary,
        )

    def _apply_swap(
        self,
        event: AgentEvent,
        scenario: CounterfactualScenario,
    ) -> bool:
        if event.event_type not in (EventType.TOOL_RESULT, EventType.TOOL_CALL):
            return False

        if scenario.tool_id and event.tool_call:
            if event.tool_call.tool_id != scenario.tool_id:
                # Match by name as a fallback
                if event.tool_call.tool_name != scenario.tool_id:
                    return False

        if event.tool_result is None:
            event.tool_result = ToolResultData(
                tool_name=event.tool_call.tool_name if event.tool_call else "unknown",
                output=scenario.replacement,
            )
        else:
            event.tool_result.output = scenario.replacement
            event.tool_result.error = None

        event.metadata["counterfactual"] = True
        event.metadata["counterfactual_notes"] = scenario.notes
        return True


__all__ = ["CounterfactualEngine", "CounterfactualScenario", "CounterfactualResult"]
