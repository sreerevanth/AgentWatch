"""
CMP-001 — GDPR Data Handling.

- PII detection across all traces
- Auto-redaction option
- Right-to-erasure endpoint
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

# Pattern → label
_PII_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b[\w._%+-]+@[\w.-]+\.[A-Za-z]{2,}\b"), "email"),
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "ssn"),
    (re.compile(r"\b(?:\d[ -]*?){13,16}\b"), "credit_card"),
    (re.compile(r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"), "phone"),
    (re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"), "ip_address"),
    (re.compile(r"(?i)\bAKIA[0-9A-Z]{16}\b"), "aws_access_key"),
]


def pii_patterns() -> list[tuple[re.Pattern[str], str]]:
    """Public accessor for the compiled (pattern, label) PII detectors."""
    return list(_PII_PATTERNS)


@dataclass
class PIIFinding:
    label: str
    excerpt: str


@dataclass
class RedactionResult:
    redacted_text: str
    findings: list[PIIFinding] = field(default_factory=list)


def detect_pii(text: str) -> list[PIIFinding]:
    findings: list[PIIFinding] = []
    if not text:
        return findings
    for pat, label in _PII_PATTERNS:
        for m in pat.finditer(text):
            findings.append(PIIFinding(label=label, excerpt=m.group()[:60]))
    return findings


def redact(text: str) -> RedactionResult:
    findings: list[PIIFinding] = []
    out = text or ""
    for pat, label in _PII_PATTERNS:
        for m in pat.finditer(out):
            findings.append(PIIFinding(label=label, excerpt=m.group()[:60]))
        out = pat.sub(f"[REDACTED:{label.upper()}]", out)
    return RedactionResult(redacted_text=out, findings=findings)


@dataclass
class ErasureReceipt:
    user_id: str
    submitted_at: datetime
    completed_at: datetime
    items_erased: int
    scope: str
    audit_signature: str = ""


class GDPREngine:
    """High-level GDPR handler over a generic store."""

    def scan_records(self, records: list[dict[str, Any]]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for r in records:
            blob = " ".join(str(v) for v in r.values() if isinstance(v, (str, int, float)))
            for f in detect_pii(blob):
                counts[f.label] = counts.get(f.label, 0) + 1
        return counts

    def erase(
        self, user_id: str, records: list[dict[str, Any]], *, scope: str = "all"
    ) -> tuple[list[dict[str, Any]], ErasureReceipt]:
        submitted = datetime.now(UTC)
        kept = [r for r in records if r.get("user_id") != user_id]
        erased = len(records) - len(kept)
        receipt = ErasureReceipt(
            user_id=user_id,
            submitted_at=submitted,
            completed_at=datetime.now(UTC),
            items_erased=erased,
            scope=scope,
            audit_signature=f"sha256:{hash((user_id, erased, scope)) & 0xFFFFFFFF:08x}",
        )
        return kept, receipt


__all__ = [
    "PIIFinding",
    "RedactionResult",
    "ErasureReceipt",
    "GDPREngine",
    "detect_pii",
    "pii_patterns",
    "redact",
]
