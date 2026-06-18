"""Reasoning step auditor with optional LLM-judge callback."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from statistics import mean
from typing import Any, cast

from agentwatch.core.schema import AgentEvent, EventType

JudgeCallback = Callable[[str, AgentEvent], Awaitable[dict[str, Any]]]


@dataclass
class StepAudit:
    step_index: int
    event_id: str
    score: float
    verdict: str
    rationale: str
    evidence: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "step_index": self.step_index,
            "event_id": self.event_id,
            "score": round(self.score, 3),
            "verdict": self.verdict,
            "rationale": self.rationale,
            "evidence": self.evidence,
        }


@dataclass
class AuditSummary:
    session_id: str
    average_score: float
    weakest_step: int | None
    strongest_step: int | None
    audits: list[StepAudit]

    def to_dict(self) -> dict[str, object]:
        return {
            "session_id": self.session_id,
            "average_score": round(self.average_score, 3),
            "weakest_step": self.weakest_step,
            "strongest_step": self.strongest_step,
            "audits": [audit.to_dict() for audit in self.audits],
        }


class ReasoningAuditor:
    """
    Audits observable reasoning artifacts.

    If a judge callback is provided, it is treated as the LLM-as-judge layer.
    Without one, the auditor falls back to a deterministic heuristic so the
    system remains usable in offline and test environments.
    """

    def __init__(self, judge: JudgeCallback | None = None):
        self._judge = judge

    async def audit_session(self, events: list[AgentEvent]) -> AuditSummary:
        audits: list[StepAudit] = []
        observable = [
            event
            for event in events
            if event.event_type
            in (EventType.PLANNER_OUTPUT, EventType.TOOL_CALL, EventType.TOOL_RESULT)
        ]

        for index, event in enumerate(observable):
            audits.append(await self.audit_step(index, event))

        scores = [audit.score for audit in audits] or [1.0]
        weakest = min(audits, key=lambda item: item.score).step_index if audits else None
        strongest = max(audits, key=lambda item: item.score).step_index if audits else None
        session_id = events[0].session_id if events else ""
        return AuditSummary(
            session_id=session_id,
            average_score=mean(scores),
            weakest_step=weakest,
            strongest_step=strongest,
            audits=audits,
        )

    async def audit_step(self, step_index: int, event: AgentEvent) -> StepAudit:
        prompt = self._build_prompt(event)
        if self._judge:
            judged = await self._judge(prompt, event)
            return StepAudit(
                step_index=step_index,
                event_id=event.event_id,
                score=float(cast(float, judged.get("score", 0.5))),
                verdict=str(judged.get("verdict", "uncertain")),
                rationale=str(judged.get("rationale", "No rationale returned.")),
                evidence=[str(item) for item in cast(list[Any], judged.get("evidence", []))],
            )
        return self._heuristic_audit(step_index, event)

    def _build_prompt(self, event: AgentEvent) -> str:
        return (
            "Judge the quality of this agent reasoning artifact on a 0-1 scale.\n"
            f"Event type: {event.event_type.value}\n"
            f"Planner output: {event.planner_output_preview or ''}\n"
            f"Tool call: {event.tool_call.model_dump() if event.tool_call else ''}\n"
            f"Tool result: {event.tool_result.model_dump() if event.tool_result else ''}\n"
            "Return JSON with score, verdict, rationale, and evidence."
        )

    def _heuristic_audit(self, step_index: int, event: AgentEvent) -> StepAudit:
        score = 0.55
        evidence: list[str] = []

        if event.planner_output_preview:
            score += 0.2
            evidence.append("planner_output_present")
            if len(event.planner_output_preview.split()) >= 8:
                score += 0.1
                evidence.append("planner_output_specific")

        if event.tool_call:
            evidence.append(f"tool:{event.tool_call.tool_name}")
            if event.tool_call.raw_command or event.tool_call.arguments:
                score += 0.1
                evidence.append("tool_arguments_present")

        if event.tool_result:
            evidence.append("tool_result_present")
            if event.tool_result.error:
                score -= 0.25
                evidence.append("tool_result_error")
            else:
                score += 0.05

        if event.is_blocked:
            score -= 0.2
            evidence.append("blocked_action")

        score = max(0.0, min(score, 1.0))
        verdict = "sound" if score >= 0.75 else "acceptable" if score >= 0.5 else "weak"
        rationale = (
            "Heuristic audit based on observability artifacts because no external judge "
            "callback is configured."
        )
        return StepAudit(
            step_index=step_index,
            event_id=event.event_id,
            score=score,
            verdict=verdict,
            rationale=rationale,
            evidence=evidence,
        )
