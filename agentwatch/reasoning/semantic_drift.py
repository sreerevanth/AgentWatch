"""
RSN-006 — Semantic Drift Detection (Cross-Session).

For a given user goal phrasing, embed each session's planner output and
compare against prior sessions' embeddings. Surfaces when "the same goal"
produces semantically divergent behavior over time.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from agentwatch.scoring.drift import cosine, embed


@dataclass
class SessionFingerprint:
    session_id: str
    goal: str
    timestamp: datetime
    vector: list[float] = field(default_factory=list)


@dataclass
class SemanticDriftAlert:
    goal_canonical: str
    n_sessions: int
    drift_magnitude: float  # 0..1
    diverged: bool
    examples: list[tuple[str, str]]  # (session_id, excerpt)


class CrossSessionDrift:
    """Maintain a registry of session fingerprints keyed by canonical goal."""

    def __init__(self, drift_threshold: float = 0.4):
        self.threshold = drift_threshold
        self._index: dict[str, list[SessionFingerprint]] = {}

    @staticmethod
    def canonical(goal: str) -> str:
        return " ".join(goal.lower().split())

    def register(self, session_id: str, goal: str, summary: str, when: datetime) -> None:
        key = self.canonical(goal)
        fp = SessionFingerprint(
            session_id=session_id,
            goal=goal,
            timestamp=when,
            vector=embed(summary),
        )
        self._index.setdefault(key, []).append(fp)

    def analyze(self, goal: str) -> SemanticDriftAlert | None:
        key = self.canonical(goal)
        fps = self._index.get(key, [])
        if len(fps) < 2:
            return None
        # Compare each fingerprint to the chronologically-first one
        anchor = fps[0]
        distances = [1 - cosine(fp.vector, anchor.vector) for fp in fps[1:]]
        drift_magnitude = max(distances) if distances else 0.0
        diverged = drift_magnitude >= self.threshold
        examples = [
            (fp.session_id, fp.goal[:120])
            for fp in fps
            if 1 - cosine(fp.vector, anchor.vector) >= self.threshold
        ]
        return SemanticDriftAlert(
            goal_canonical=key,
            n_sessions=len(fps),
            drift_magnitude=drift_magnitude,
            diverged=diverged,
            examples=examples,
        )


__all__ = ["CrossSessionDrift", "SessionFingerprint", "SemanticDriftAlert"]
