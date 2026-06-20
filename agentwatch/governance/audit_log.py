"""
CMP-005 — Tamper-evident audit log for RBAC and policy changes (issue #395).

Every administrative change (role assignment, user add, team-policy update) is
appended as a record in a hash chain: each record's ``record_hash`` is computed
over its own fields *and* the previous record's hash. Altering any past record
breaks every hash after it, so :meth:`AuditLog.verify` detects tampering even
though the log is held in memory.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

# Hash that seeds the chain — the "previous hash" of the first record.
GENESIS_HASH = "0" * 64


def _digest(
    seq: int,
    timestamp: str,
    actor: str | None,
    action: str,
    target: str,
    details: dict[str, Any],
    prev_hash: str,
) -> str:
    """Return the SHA-256 chain hash for a record's fields."""
    canonical = json.dumps(
        {
            "seq": seq,
            "timestamp": timestamp,
            "actor": actor,
            "action": action,
            "target": target,
            "details": details,
            "prev_hash": prev_hash,
        },
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass
class AuditRecord:
    """A single tamper-evident entry in the audit chain."""

    seq: int
    timestamp: str
    actor: str | None
    action: str
    target: str
    details: dict[str, Any]
    prev_hash: str
    record_hash: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "seq": self.seq,
            "timestamp": self.timestamp,
            "actor": self.actor,
            "action": self.action,
            "target": self.target,
            "details": self.details,
            "prev_hash": self.prev_hash,
            "record_hash": self.record_hash,
        }


class AuditLog:
    """An append-only, hash-chained audit log."""

    def __init__(self) -> None:
        self._records: list[AuditRecord] = []

    @property
    def head_hash(self) -> str:
        """Hash of the most recent record (or the genesis hash when empty)."""
        return self._records[-1].record_hash if self._records else GENESIS_HASH

    def append(
        self,
        action: str,
        target: str,
        *,
        actor: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> AuditRecord:
        """Append a new record to the chain and return it."""
        seq = len(self._records)
        timestamp = datetime.now(UTC).isoformat()
        prev_hash = self.head_hash
        details = dict(details or {})
        record = AuditRecord(
            seq=seq,
            timestamp=timestamp,
            actor=actor,
            action=action,
            target=target,
            details=details,
            prev_hash=prev_hash,
            record_hash=_digest(seq, timestamp, actor, action, target, details, prev_hash),
        )
        self._records.append(record)
        return record

    def records(self) -> list[AuditRecord]:
        """Return the records in chronological order."""
        return list(self._records)

    def verify(self) -> bool:
        """Return whether the chain is intact (no record altered or reordered)."""
        prev_hash = GENESIS_HASH
        for record in self._records:
            if record.prev_hash != prev_hash:
                return False
            expected = _digest(
                record.seq,
                record.timestamp,
                record.actor,
                record.action,
                record.target,
                record.details,
                record.prev_hash,
            )
            if expected != record.record_hash:
                return False
            prev_hash = record.record_hash
        return True

    def __len__(self) -> int:
        return len(self._records)


__all__ = ["GENESIS_HASH", "AuditRecord", "AuditLog"]
