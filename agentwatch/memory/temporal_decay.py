"""
MEM-005 — Temporal Decay Curve Manager.

Wires the exponential forgetting curve (:mod:`agentwatch.memory.decay`) into the
layered :class:`~agentwatch.memory.engine.MemoryEngine`. The manager:

- computes a decayed-importance factor for each memory entry,
- deprioritizes stale episodic memories during retrieval, and
- selects decayed entries for background cleanup (by strength, not importance
  level) while keeping CRITICAL memories persistent.

It is intentionally stateless and synchronous — callers (or the engine) own the
entries and decide when to refresh factors or prune. Decay is measured from
``last_accessed`` so that retrieving a memory rehearses it and resets the curve.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime

from agentwatch.memory.decay import Importance, strength_at
from agentwatch.memory.engine import ImportanceLevel, MemoryEntry, MemoryType

# Map the engine's importance levels onto the forgetting-curve half-lives.
_IMPORTANCE_MAP: dict[ImportanceLevel, Importance] = {
    ImportanceLevel.LOW: Importance.LOW,
    ImportanceLevel.MEDIUM: Importance.NORMAL,
    ImportanceLevel.HIGH: Importance.HIGH,
    ImportanceLevel.CRITICAL: Importance.CRITICAL,
}


class TemporalDecayManager:
    """Apply an importance-weighted exponential forgetting curve to memories.

    Parameters
    ----------
    prune_threshold:
        Entries whose decayed strength falls below this value become eligible
        for cleanup. CRITICAL memories are always exempt.
    decay_episodic_only:
        When ``True`` (default) only episodic memories decay; semantic and
        procedural knowledge is treated as durable and keeps full strength.
    """

    def __init__(
        self,
        *,
        prune_threshold: float = 0.05,
        decay_episodic_only: bool = True,
    ) -> None:
        self.prune_threshold = prune_threshold
        self.decay_episodic_only = decay_episodic_only

    def _decays(self, entry: MemoryEntry) -> bool:
        """Whether the forgetting curve applies to this entry at all."""
        if entry.importance == ImportanceLevel.CRITICAL:
            return False
        if self.decay_episodic_only:
            return entry.memory_type == MemoryType.EPISODIC
        return True

    def strength(self, entry: MemoryEntry, now: datetime | None = None) -> float:
        """Current forgetting-curve strength for ``entry`` in ``[0.0, 1.0]``."""
        if not self._decays(entry):
            return 1.0
        importance = _IMPORTANCE_MAP[entry.importance]
        return strength_at(importance, entry.last_accessed, entry.access_count, now)

    def refresh(self, entry: MemoryEntry, now: datetime | None = None) -> float:
        """Recompute and store ``entry.decay_factor``; return the new value."""
        entry.decay_factor = self.strength(entry, now)
        return entry.decay_factor

    def is_prunable(self, entry: MemoryEntry, now: datetime | None = None) -> bool:
        """Whether ``entry`` has decayed below the cleanup threshold."""
        if not self._decays(entry):
            return False
        return self.strength(entry, now) < self.prune_threshold

    def select_prunable(
        self,
        entries: Iterable[MemoryEntry],
        now: datetime | None = None,
    ) -> list[MemoryEntry]:
        """Return the subset of ``entries`` eligible for cleanup."""
        return [e for e in entries if self.is_prunable(e, now)]


__all__ = ["TemporalDecayManager"]
