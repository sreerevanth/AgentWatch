"""
SAF-004 — Blast Radius Estimator.

Before executing an action, estimate worst-case impact:
    data affected, downstream services, cost exposure, reversibility.
Above-threshold blast radius requires approval.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum

from agentwatch.core.schema import AgentEvent


class Reversibility(str, Enum):
    REVERSIBLE = "reversible"
    PARTIALLY_REVERSIBLE = "partially_reversible"
    IRREVERSIBLE = "irreversible"


@dataclass
class BlastRadius:
    affected_resources: list[str] = field(default_factory=list)
    downstream_services: list[str] = field(default_factory=list)
    cost_estimate_usd: float = 0.0
    reversibility: Reversibility = Reversibility.REVERSIBLE
    score: int = 0  # 0..100

    def to_dict(self) -> dict:
        return {
            "affected_resources": self.affected_resources,
            "downstream_services": self.downstream_services,
            "cost_estimate_usd": self.cost_estimate_usd,
            "reversibility": self.reversibility.value,
            "score": self.score,
        }


# Pattern → (service, reversibility, score)
_BLAST_PATTERNS: list[tuple[re.Pattern, str, Reversibility, int]] = [
    (re.compile(r"\brm\s+-rf?\s+/"), "filesystem", Reversibility.IRREVERSIBLE, 95),
    (re.compile(r"\bDROP\s+TABLE\b", re.I), "database", Reversibility.IRREVERSIBLE, 85),
    (re.compile(r"\bDROP\s+DATABASE\b", re.I), "database", Reversibility.IRREVERSIBLE, 95),
    (re.compile(r"\bDELETE\s+FROM\b", re.I), "database", Reversibility.PARTIALLY_REVERSIBLE, 60),
    (re.compile(r"\bgit\s+push\s+(--force|-f)\b"), "git", Reversibility.IRREVERSIBLE, 70),
    (re.compile(r"\bkubectl\s+delete\b"), "k8s", Reversibility.PARTIALLY_REVERSIBLE, 70),
    (re.compile(r"\baws\s+s3\s+rb\b"), "s3", Reversibility.IRREVERSIBLE, 80),
    (re.compile(r"\bterraform\s+destroy\b"), "infra", Reversibility.IRREVERSIBLE, 95),
    (re.compile(r"\brm\b"), "filesystem", Reversibility.PARTIALLY_REVERSIBLE, 25),
]


@dataclass
class BlastRadiusEstimator:
    approval_threshold: int = 60

    def estimate(self, event: AgentEvent) -> BlastRadius:
        radius = BlastRadius()
        raw = ""
        if event.tool_call:
            raw = event.tool_call.raw_command or repr(event.tool_call.arguments)
            radius.affected_resources = list(event.tool_call.affected_resources)

        for pat, service, reversibility, score in _BLAST_PATTERNS:
            if pat.search(raw):
                radius.downstream_services.append(service)
                radius.score = max(radius.score, score)
                # Worst case wins
                if reversibility == Reversibility.IRREVERSIBLE:
                    radius.reversibility = Reversibility.IRREVERSIBLE
                elif (
                    reversibility == Reversibility.PARTIALLY_REVERSIBLE
                    and radius.reversibility != Reversibility.IRREVERSIBLE
                ):
                    radius.reversibility = Reversibility.PARTIALLY_REVERSIBLE

        # Cost heuristic — heavy db ops cost more
        if "database" in radius.downstream_services:
            radius.cost_estimate_usd = 10.0
        if "infra" in radius.downstream_services:
            radius.cost_estimate_usd = 100.0

        return radius

    def requires_approval(self, radius: BlastRadius) -> bool:
        return radius.score >= self.approval_threshold


__all__ = ["BlastRadius", "BlastRadiusEstimator", "Reversibility"]
