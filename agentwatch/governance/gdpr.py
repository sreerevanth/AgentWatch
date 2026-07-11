"""
CMP-001 — GDPR Data Handling.

- PII detection across all traces
- Auto-redaction option
- Right-to-erasure endpoint (in-memory + persisted, HMAC-SHA256 receipts)
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol, runtime_checkable

SIGNING_KEY_ENV = "AGENTWATCH_GDPR_SIGNING_KEY"
SIGNATURE_PREFIX = "hmac-sha256:"

# Pattern → label
_PII_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b[\w._%+-]+@[\w.-]+\.[A-Za-z]{2,}\b"), "email"),
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "ssn"),
    (re.compile(r"\b(?:\d[ -]*?){13,16}\b"), "credit_card"),
    (
        re.compile(r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
        "phone",
    ),
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


@runtime_checkable
class ErasureStore(Protocol):
    """Persistence-layer contract for GDPR Article 17 erasure."""

    async def erase_user_data(self, user_id: str, *, scope: str = "all") -> int: ...


def resolve_signing_key(explicit: str | bytes | None = None) -> bytes:
    """Return the HMAC key from an explicit value or SIGNING_KEY_ENV, else raise."""
    if explicit is not None:
        key = explicit.encode("utf-8") if isinstance(explicit, str) else explicit
        if key.strip():
            return key
    else:
        from_env = os.getenv(SIGNING_KEY_ENV)
        if from_env:
            key = from_env.encode("utf-8")
            if key.strip():
                return key

    raise RuntimeError(
        f"No GDPR receipt signing key configured. Set {SIGNING_KEY_ENV} "
        "or pass signing_key=... to GDPREngine."
    )


def _receipt_payload(receipt: ErasureReceipt) -> bytes:
    # Deterministic across processes; excludes the signature itself.
    return json.dumps(
        {
            "user_id": receipt.user_id,
            "submitted_at": receipt.submitted_at.isoformat(),
            "completed_at": receipt.completed_at.isoformat(),
            "items_erased": receipt.items_erased,
            "scope": receipt.scope,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def sign_receipt(receipt: ErasureReceipt, *, key: str | bytes) -> str:
    """Return the hmac-sha256:<hex> signature for a receipt."""
    resolved = key.encode("utf-8") if isinstance(key, str) else key
    digest = hmac.new(resolved, _receipt_payload(receipt), hashlib.sha256).hexdigest()
    return f"{SIGNATURE_PREFIX}{digest}"


def verify_receipt(receipt: ErasureReceipt, *, key: str | bytes) -> bool:
    """Return whether receipt.audit_signature matches a fresh HMAC (constant-time)."""
    return hmac.compare_digest(sign_receipt(receipt, key=key), receipt.audit_signature)


class GDPREngine:
    """GDPR handler over an in-memory list or a persistent store."""

    def __init__(self, *, signing_key: str | bytes | None = None) -> None:
        # Resolve eagerly so misconfiguration fails at startup, not at erase time.
        self._signing_key = resolve_signing_key(signing_key)

    def scan_records(self, records: list[dict[str, Any]]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for r in records:
            blob = " ".join(str(v) for v in r.values() if isinstance(v, (str, int, float)))
            for f in detect_pii(blob):
                counts[f.label] = counts.get(f.label, 0) + 1
        return counts

    def _build_receipt(
        self, user_id: str, submitted: datetime, erased: int, scope: str
    ) -> ErasureReceipt:
        receipt = ErasureReceipt(
            user_id=user_id,
            submitted_at=submitted,
            completed_at=datetime.now(UTC),
            items_erased=erased,
            scope=scope,
        )
        receipt.audit_signature = sign_receipt(receipt, key=self._signing_key)
        return receipt

    def erase(
        self, user_id: str, records: list[dict[str, Any]], *, scope: str = "all"
    ) -> tuple[list[dict[str, Any]], ErasureReceipt]:
        """Erase a subject's rows from an in-memory record list."""
        submitted = datetime.now(UTC)
        kept = [r for r in records if r.get("user_id") != user_id]
        erased = len(records) - len(kept)
        return kept, self._build_receipt(user_id, submitted, erased, scope)

    async def erase_persisted(
        self, store: ErasureStore, user_id: str, *, scope: str = "all"
    ) -> ErasureReceipt:
        """Erase a subject's data through the persistence layer and sign a receipt."""
        submitted = datetime.now(UTC)
        erased = await store.erase_user_data(user_id, scope=scope)
        return self._build_receipt(user_id, submitted, erased, scope)


__all__ = [
    "SIGNING_KEY_ENV",
    "SIGNATURE_PREFIX",
    "PIIFinding",
    "RedactionResult",
    "ErasureReceipt",
    "ErasureStore",
    "GDPREngine",
    "detect_pii",
    "pii_patterns",
    "redact",
    "resolve_signing_key",
    "sign_receipt",
    "verify_receipt",
]
