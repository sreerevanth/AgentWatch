"""
MAG-007 — Consensus Failure Detector.

When agents disagree on approach, surface conflict to the human.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from agentwatch.scoring.drift import cosine, embed


@dataclass
class AgentVote:
    agent_id: str
    proposal: str


@dataclass
class ConsensusReport:
    agreed: bool
    majority_proposal: str | None
    minority_proposals: list[str]
    agreement_ratio: float
    semantic_clusters: list[list[str]]  # list of clusters by agent_id


def detect_consensus(
    votes: list[AgentVote],
    *,
    similarity_threshold: float = 0.65,
    majority_ratio: float = 0.6,
) -> ConsensusReport:
    if not votes:
        return ConsensusReport(True, None, [], 1.0, [])

    # Greedy cluster proposals by semantic similarity
    clusters: list[tuple[list[float], list[AgentVote]]] = []
    for v in votes:
        vec = embed(v.proposal)
        placed = False
        for c_vec, c_votes in clusters:
            if cosine(vec, c_vec) >= similarity_threshold:
                c_votes.append(v)
                placed = True
                break
        if not placed:
            clusters.append((vec, [v]))

    cluster_sizes = [len(c) for _, c in clusters]
    total = sum(cluster_sizes)
    biggest_idx = cluster_sizes.index(max(cluster_sizes))
    biggest = clusters[biggest_idx][1]
    agreement_ratio = len(biggest) / total
    agreed = agreement_ratio >= majority_ratio

    return ConsensusReport(
        agreed=agreed,
        majority_proposal=biggest[0].proposal if agreed else None,
        minority_proposals=[
            v.proposal for i, (_, c) in enumerate(clusters) if i != biggest_idx for v in c
        ],
        agreement_ratio=agreement_ratio,
        semantic_clusters=[[v.agent_id for v in c] for _, c in clusters],
    )


__all__ = ["AgentVote", "ConsensusReport", "detect_consensus"]
