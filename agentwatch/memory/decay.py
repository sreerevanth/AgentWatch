"""
MEM-005 — Forgetting Curve Engine.

Importance-weighted decay. Critical memories never decay. Routine memories
fade following an Ebbinghaus-style exponential.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum


class Importance(str, Enum):
    CRITICAL = "critical"  # never decays
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


_IMPORTANCE_HALFLIFE_DAYS = {
    Importance.CRITICAL: float("inf"),
    Importance.HIGH: 365.0,
    Importance.NORMAL: 30.0,
    Importance.LOW: 7.0,
}


@dataclass
class DecayingMemory:
    key: str
    value: object
    importance: Importance = Importance.NORMAL
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    last_accessed: datetime = field(default_factory=lambda: datetime.now(UTC))
    access_count: int = 0

    def strength(self, now: datetime | None = None) -> float:
        now = now or datetime.now(UTC)
        halflife = _IMPORTANCE_HALFLIFE_DAYS[self.importance]
        if halflife == float("inf"):
            return 1.0
        age_days = (now - self.last_accessed).total_seconds() / 86400
        base = math.exp(-math.log(2) * age_days / halflife)
        # Each access slightly boosts strength (rehearsal effect)
        boost = min(0.5, 0.05 * self.access_count)
        return min(1.0, base + boost)


class ForgettingEngine:
    """Sliding-window importance-weighted memory store."""

    def __init__(self, prune_threshold: float = 0.05):
        self.prune_threshold = prune_threshold
        self._store: dict[str, DecayingMemory] = {}

    def put(
        self,
        key: str,
        value: object,
        importance: Importance = Importance.NORMAL,
    ) -> DecayingMemory:
        mem = DecayingMemory(key=key, value=value, importance=importance)
        self._store[key] = mem
        return mem

    def access(self, key: str) -> DecayingMemory | None:
        mem = self._store.get(key)
        if mem is None:
            return None
        mem.last_accessed = datetime.now(UTC)
        mem.access_count += 1
        return mem

    def prune(self, *, now: datetime | None = None) -> list[str]:
        """Remove memories below the strength threshold. Returns removed keys."""
        removed: list[str] = []
        for k, m in list(self._store.items()):
            if m.strength(now) < self.prune_threshold and m.importance != Importance.CRITICAL:
                removed.append(k)
                del self._store[k]
        return removed

    def snapshot(self, *, now: datetime | None = None) -> list[tuple[str, float, Importance]]:
        return [(k, m.strength(now), m.importance) for k, m in self._store.items()]

    def __len__(self) -> int:
        return len(self._store)


__all__ = ["DecayingMemory", "Importance", "ForgettingEngine"]
