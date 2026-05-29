"""Compliance reporting over governance and session data."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from agentwatch.governance.engine import AuditEventType, GovernanceEngine
from agentwatch.tracing.collector import TraceCollector


@dataclass
class ComplianceReport:
    generated_at: str
    summary: Dict[str, Any]
    findings: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "summary": self.summary,
            "findings": self.findings,
        }


class ComplianceReporter:
    def __init__(self, governance: GovernanceEngine, collector: Optional[TraceCollector] = None):
        self._governance = governance
        self._collector = collector

    def generate(self) -> ComplianceReport:
        audit_log = self._governance.get_audit_log(limit=10_000)
        denied = [entry for entry in audit_log if not entry.allowed]
        overrides = [entry for entry in audit_log if entry.event_type == AuditEventType.SAFETY_OVERRIDE]
        sessions = self._collector.list_sessions(limit=10_000) if self._collector else []
        findings = {
            "permission_denials": len(denied),
            "safety_overrides": len(overrides),
            "active_sessions": sum(1 for session in sessions if session.status.value == "running"),
            "sample_denials": [entry.to_dict() for entry in denied[:20]],
        }
        summary = {
            "total_audit_entries": len(audit_log),
            "total_sessions": len(sessions),
        }
        return ComplianceReport(
            generated_at=datetime.now(timezone.utc).isoformat(),
            summary=summary,
            findings=findings,
        )
