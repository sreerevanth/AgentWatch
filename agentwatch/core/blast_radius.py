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
    affected_row_count: int | None = None
    affected_file_count: int | None = None
    is_critical_resource: bool = False
    explanation: str = ""

    def to_dict(self) -> dict:
        return {
            "affected_resources": self.affected_resources,
            "downstream_services": self.downstream_services,
            "cost_estimate_usd": self.cost_estimate_usd,
            "reversibility": self.reversibility.value,
            "score": self.score,
            "affected_row_count": self.affected_row_count,
            "affected_file_count": self.affected_file_count,
            "is_critical_resource": self.is_critical_resource,
            "explanation": self.explanation,
        }


# Pattern → (service, reversibility, score)
_BLAST_PATTERNS: list[tuple[re.Pattern, str, Reversibility, int]] = [
    (re.compile(r"\brm\s+-rf?\s+/"), "filesystem", Reversibility.IRREVERSIBLE, 95),
    (re.compile(r"\bDROP\s+TABLE\b", re.I), "database", Reversibility.IRREVERSIBLE, 85),
    (re.compile(r"\bDROP\s+DATABASE\b", re.I), "database", Reversibility.IRREVERSIBLE, 95),
    (re.compile(r"\bDELETE\s+FROM\b", re.I), "database", Reversibility.PARTIALLY_REVERSIBLE, 50),
    (re.compile(r"\bUPDATE\b.*\bSET\b", re.I), "database", Reversibility.PARTIALLY_REVERSIBLE, 50),
    (re.compile(r"\bgit\s+push\s+(--force|-f)\b"), "git", Reversibility.IRREVERSIBLE, 70),
    (re.compile(r"\bkubectl\s+delete\b"), "k8s", Reversibility.PARTIALLY_REVERSIBLE, 70),
    (re.compile(r"\baws\s+s3\s+rb\b"), "s3", Reversibility.IRREVERSIBLE, 80),
    (re.compile(r"\bterraform\s+destroy\b"), "infra", Reversibility.IRREVERSIBLE, 95),
    (re.compile(r"\brm\b"), "filesystem", Reversibility.PARTIALLY_REVERSIBLE, 25),
]


class BlastRadiusEstimator:
    def __init__(self, approval_threshold: int = 60):
        self.approval_threshold = approval_threshold

    def estimate(self, event: AgentEvent) -> BlastRadius:
        """Estimate the blast radius of a tool call event.

        Performs both pattern-based and causal-heuristic analysis.
        """
        radius = BlastRadius()
        if not event.tool_call:
            return radius

        raw = event.tool_call.raw_command or ""
        radius.affected_resources = list(event.tool_call.affected_resources)

        # 1. Pattern matching (base score)
        for pat, service, reversibility, score in _BLAST_PATTERNS:
            if pat.search(raw):
                if service not in radius.downstream_services:
                    radius.downstream_services.append(service)
                radius.score = max(radius.score, score)
                if reversibility == Reversibility.IRREVERSIBLE:
                    radius.reversibility = Reversibility.IRREVERSIBLE
                elif (
                    reversibility == Reversibility.PARTIALLY_REVERSIBLE
                    and radius.reversibility != Reversibility.IRREVERSIBLE
                ):
                    radius.reversibility = Reversibility.PARTIALLY_REVERSIBLE

        # 2. Causal Heuristics
        # Database Causal Analysis
        if "database" in radius.downstream_services:
            self._analyze_database_impact(raw, radius)

        # Filesystem Causal Analysis
        if "filesystem" in radius.downstream_services:
            self._analyze_filesystem_impact(raw, radius)

        # Resource Criticality Analysis
        self._analyze_resource_criticality(radius)

        # 3. Final Score Normalization
        if radius.is_critical_resource:
            radius.score = max(radius.score, 80)
        if radius.reversibility == Reversibility.IRREVERSIBLE:
            radius.score = max(radius.score, 70)

        # Summary explanation
        radius.explanation = self._generate_explanation(radius)

        return radius

    def _analyze_database_impact(self, raw: str, radius: BlastRadius) -> None:
        """Heuristically estimate SQL impact."""
        # Check for missing WHERE clause in destructive ops
        if re.search(r"\b(DELETE|UPDATE)\b", raw, re.I) and not re.search(r"\bWHERE\b", raw, re.I):
            radius.score = max(radius.score, 90)
            radius.affected_row_count = 1000000  # Assume entire table
            radius.is_critical_resource = True

        # Check for critical table names
        critical_tables = {"users", "billing", "orders", "credentials", "audit_log", "config"}
        for table in critical_tables:
            if re.search(rf"\b{table}\b", raw, re.I):
                radius.is_critical_resource = True
                radius.score = max(radius.score, 75)

    def _analyze_filesystem_impact(self, raw: str, radius: BlastRadius) -> None:
        """Heuristically estimate FS impact."""
        import shlex
        import os

        def parse_and_scan(text: str) -> list[tuple[set[str], list[str]]]:
            try:
                tokens = shlex.split(text)
            except Exception:
                tokens = text.split()

            invocations = []
            i = 0
            while i < len(tokens):
                token = tokens[i]
                if any(sub in token for sub in ("rm ", "rm\t")):
                    invocations.extend(parse_and_scan(token))
                elif token == "rm":
                    flags = set()
                    paths = []
                    j = i + 1
                    while j < len(tokens):
                        arg = tokens[j]
                        if arg.startswith("-") and len(arg) > 1:
                            if arg.startswith("--"):
                                flags.add(arg)
                            else:
                                for char in arg[1:]:
                                    flags.add(f"-{char}")
                        else:
                            paths.append(arg)
                        j += 1
                    invocations.append((flags, paths))
                i += 1
            return invocations

        def is_sub_or_equal(target: str, critical: str) -> bool:
            # Normalize target path to handle relative components and cross-platform slashes
            normalized = os.path.normpath(target).replace("\\", "/")
            if not normalized.startswith("/") and target.startswith("/"):
                normalized = "/" + normalized
            
            target_parts = [p for p in normalized.split("/") if p]
            critical_parts = [p for p in critical.split("/") if p]
            
            if len(target_parts) >= len(critical_parts):
                return target_parts[:len(critical_parts)] == critical_parts
            return False

        critical_paths = {"/etc", "/var", "/boot", "/root", "/home", "/usr", "/bin", "/sbin", "/"}
        invocations = parse_and_scan(raw)

        for flags, paths in invocations:
            is_recursive = any(f in flags for f in ("-r", "-R", "--recursive"))
            for path in paths:
                # Check for critical path deletions (recursive or not, but usually recursive is critical)
                if any(is_sub_or_equal(path, cp) for cp in critical_paths):
                    if is_recursive or path in ("/", "/*"):
                        radius.is_critical_resource = True
                        radius.score = max(radius.score, 100)
                        radius.affected_file_count = 50000
                
                # Check for wildcard deletions
                if is_recursive and any(char in path for char in "*?"):
                    radius.score = max(radius.score, 65)
                    if radius.affected_file_count is None:
                        radius.affected_file_count = 100

    def _analyze_resource_criticality(self, radius: BlastRadius) -> None:
        """Check if any explicitly affected resources are tagged or named as critical."""
        critical_indicators = {"#prod", "#production", "#critical", "#p0", ".prod.", ".production"}
        for res in radius.affected_resources:
            res_lower = res.lower()
            if any(ind in res_lower for ind in critical_indicators):
                radius.is_critical_resource = True
                radius.score = max(radius.score, 90)

    def _generate_explanation(self, radius: BlastRadius) -> str:
        if radius.score >= 90:
            return "Extreme blast radius: potentially irreversible system-wide impact."
        if radius.score >= 70:
            return f"Significant blast radius: touches critical {', '.join(radius.downstream_services)} resources."
        if radius.score >= 40:
            return f"Moderate blast radius: multi-{', '.join(radius.downstream_services)} impact detected."
        return "Low blast radius: localized impact."

    def requires_approval(self, radius: BlastRadius) -> bool:
        return radius.score >= self.approval_threshold


__all__ = ["BlastRadius", "BlastRadiusEstimator", "Reversibility"]
