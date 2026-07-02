"""
MAG-010 — Confidence Discount Propagation Across Multi-Agent DAGs.

When an upstream agent produces output with low confidence or high
hallucination risk, a discount factor is computed per DAG edge and
propagated downstream via topological traversal. The cumulative
discount is applied to downstream confidence scores so that
untrusted inputs are reflected in every dependent agent's evaluation.
"""

from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass, field

from agentwatch.orchestration.dag import InterAgentDAG
from agentwatch.orchestration.trust import InterAgentTrust
from agentwatch.reasoning.hallucination import HallucinationClassifier, HallucinationRisk
from agentwatch.scoring.confidence import ConfidenceScorer, ScoringResult

logger = logging.getLogger(__name__)

DISCOUNT_HIGH_RISK = 0.40
DISCOUNT_MEDIUM_RISK = 0.20
DISCOUNT_LOW_RISK = 0.0
DISCOUNT_MIN_TRUST = 0.30
DISCOUNT_WEIGHT_TRUST = 0.5
DISCOUNT_WEIGHT_HALLUCINATION = 0.5


@dataclass
class DiscountEdge:
    src: str
    dst: str
    discount: float = 0.0
    reasons: list[str] = field(default_factory=list)


@dataclass
class DiscountReport:
    origin_node: str
    origin_agent: str
    origin_confidence: float
    discounts: list[DiscountEdge] = field(default_factory=list)
    depth: int = 0

    @property
    def max_downstream_discount(self) -> float:
        if not self.discounts:
            return 0.0
        return max(e.discount for e in self.discounts)


class ConfidenceDiscountPropagator:
    def __init__(
        self,
        trust: InterAgentTrust | None = None,
        hallucination_classifier: HallucinationClassifier | None = None,
        confidence_scorer: ConfidenceScorer | None = None,
    ):
        self._trust = trust or InterAgentTrust()
        self._hallucination_classifier = hallucination_classifier or HallucinationClassifier()
        self._confidence_scorer = confidence_scorer or ConfidenceScorer()

    def _trust_discount(self, src: str, dst: str) -> tuple[float, str]:
        """Compute discount from trust score — low trust → high discount."""
        score = self._trust.score(src)
        edges = self._trust.edges()
        pair_edges = [e for e in edges if e.src == src and e.dst == dst]
        pair_score = pair_edges[0].score if pair_edges else score

        if pair_score <= 0.3:
            return DISCOUNT_MIN_TRUST, f"trust_score_{pair_score:.2f}"
        if pair_score <= 0.5:
            return 0.15, f"trust_score_{pair_score:.2f}"
        return 0.0, ""

    def _hallucination_discount(self, agent_id: str) -> tuple[float, str]:
        """
        Estimate hallucination risk at the agent level.
        Uses the classifier's per-step risk; if no sessions exist,
        returns low risk.
        """
        if not self._hallucination_classifier.session_flags:
            return 0.0, "no_hallucination_data"
        flags = self._hallucination_classifier.session_flags.get(agent_id, [])
        if not flags:
            return 0.0, "no_hallucination_flags"
        max_risk = max(f.risk for f in flags)
        mapping = {
            HallucinationRisk.HIGH: DISCOUNT_HIGH_RISK,
            HallucinationRisk.MEDIUM: DISCOUNT_MEDIUM_RISK,
            HallucinationRisk.LOW: DISCOUNT_LOW_RISK,
        }
        discount = mapping.get(max_risk, 0.0)
        return discount, f"hallucination_{max_risk.value}"

    def _agent_confidence_discount(self, confidence: ScoringResult | None) -> tuple[float, str]:
        """Low confidence scores translate to higher discount."""
        if confidence is None:
            return 0.0, "no_confidence_data"
        score = confidence.overall_score
        if score < 0.3:
            return DISCOUNT_MIN_TRUST, f"confidence_{score:.2f}"
        if score < 0.6:
            return 0.15, f"confidence_{score:.2f}"
        return 0.0, ""

    def compute_edge_discount(
        self,
        src_agent: str,
        dst_agent: str,
        src_confidence: ScoringResult | None = None,
    ) -> tuple[float, list[str]]:
        """Compute blended discount for a single DAG edge."""
        reasons: list[str] = []

        trust_discount, trust_reason = self._trust_discount(src_agent, dst_agent)
        if trust_discount > 0:
            reasons.append(trust_reason)

        hallucination_discount, hallu_reason = self._hallucination_discount(src_agent)
        if hallucination_discount > 0:
            reasons.append(hallu_reason)

        confidence_discount, conf_reason = self._agent_confidence_discount(src_confidence)
        if confidence_discount > 0:
            reasons.append(conf_reason)

        blended = (
            trust_discount * DISCOUNT_WEIGHT_TRUST
            + max(hallucination_discount, confidence_discount) * DISCOUNT_WEIGHT_HALLUCINATION
        )
        blended = min(blended, 0.95)
        return blended, reasons

    def propagate(
        self,
        dag: InterAgentDAG,
        origin_node: str,
        origin_agent: str,
        origin_confidence: float,
        agent_confidence_map: dict[str, ScoringResult] | None = None,
    ) -> DiscountReport:
        """
        BFS traversal from the origin node through the DAG, computing
        cumulative discount at each downstream node.

        The cumulative discount at node N is:
            discount(N) = 1 - prod(1 - discount(edge)) for all edges on path

        Args:
            dag: The inter-agent causal DAG.
            origin_node: The node where the low-confidence output originated.
            origin_agent: The agent that produced the low-confidence output.
            origin_confidence: The confidence score of the origin (0-1).
            agent_confidence_map: Optional map of agent_id -> ScoringResult
                for richer discount computation.

        Returns:
            A DiscountReport with per-edge discounts.
        """
        if origin_node not in dag.nodes:
            return DiscountReport(
                origin_node=origin_node,
                origin_agent=origin_agent,
                origin_confidence=origin_confidence,
            )

        out_index: dict[str, list[str]] = {}
        edge_kind: dict[tuple[str, str], str] = {}
        for e in dag.edges:
            out_index.setdefault(e.src, []).append(e.dst)
            edge_kind[(e.src, e.dst)] = e.kind

        discounts: list[DiscountEdge] = []
        depth = 0
        seen = {origin_node}
        frontier: deque[tuple[str, int, float]] = deque([(origin_node, 0, 1.0)])

        while frontier:
            node_id, d, cumulative_discount = frontier.popleft()
            depth = max(depth, d)

            for nxt in out_index.get(node_id, []):
                src_agent = dag.nodes[node_id].agent_id
                dst_agent = dag.nodes[nxt].agent_id
                src_confidence = (agent_confidence_map or {}).get(src_agent)

                edge_discount, reasons = self.compute_edge_discount(
                    src_agent, dst_agent, src_confidence
                )

                new_cumulative = 1.0 - (1.0 - cumulative_discount) * (1.0 - edge_discount)

                discounts.append(DiscountEdge(
                    src=node_id,
                    dst=nxt,
                    discount=round(new_cumulative, 4),
                    reasons=reasons,
                ))

                if nxt not in seen:
                    seen.add(nxt)
                    frontier.append((nxt, d + 1, new_cumulative))

        return DiscountReport(
            origin_node=origin_node,
            origin_agent=origin_agent,
            origin_confidence=origin_confidence,
            discounts=discounts,
            depth=depth,
        )

    def apply_discount(self, score: float, discount: float) -> float:
        """Apply a cumulative discount to a confidence score."""
        return max(0.0, round(score * (1.0 - discount), 4))


__all__ = [
    "ConfidenceDiscountPropagator",
    "DiscountReport",
    "DiscountEdge",
]
