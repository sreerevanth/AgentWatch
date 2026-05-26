"""Phase 6 — Multi-Agent tests (MAG-001..008)."""

from __future__ import annotations

import pytest

from agentwatch.core.event_bus import EventBus
from agentwatch.orchestration.consensus import AgentVote, detect_consensus
from agentwatch.orchestration.crew_context import CrewContext
from agentwatch.orchestration.dag import InterAgentDAG
from agentwatch.orchestration.deadlock import DeadlockDetector
from agentwatch.orchestration.propagation import trace_propagation
from agentwatch.orchestration.shapley import shapley_attribution
from agentwatch.orchestration.spawning import SpawnLimitExceeded, SpawningTracker
from agentwatch.orchestration.trust import InterAgentTrust


# ─────────────────────────────────────────────
# MAG-001 — Inter-Agent DAG
# ─────────────────────────────────────────────


def test_dag_traces_failure_back_to_root_cause():
    dag = InterAgentDAG()
    dag.add_node("n1", "agent-2", "hallucinate_path")
    dag.add_node("n2", "agent-3", "call_tool")
    dag.add_node("n5", "agent-5", "final_fail")
    dag.add_edge("n1", "n2")
    dag.add_edge("n2", "n5")
    chain = dag.trace_failure("n5")
    ids = {n.node_id for n in chain}
    assert {"n5", "n2", "n1"} <= ids


def test_dag_refuses_cycle():
    dag = InterAgentDAG()
    dag.add_node("a", "x", "")
    dag.add_node("b", "y", "")
    dag.add_edge("a", "b")
    with pytest.raises(ValueError):
        dag.add_edge("b", "a")


# ─────────────────────────────────────────────
# MAG-002 — Deadlock
# ─────────────────────────────────────────────


def test_deadlock_cycle_detected():
    det = DeadlockDetector()
    det.set_wait("A", "B")
    det.set_wait("B", "C")
    det.set_wait("C", "A")
    rep = det.scan()
    assert rep.deadlocked
    assert set(rep.cycle) >= {"A", "B", "C"}


def test_deadlock_no_cycle():
    det = DeadlockDetector()
    det.set_wait("A", "B")
    assert det.scan().deadlocked is False


# ─────────────────────────────────────────────
# MAG-003 — Trust
# ─────────────────────────────────────────────


def test_trust_score_updates_with_outcomes():
    t = InterAgentTrust()
    for _ in range(8):
        t.record("agent-a", "agent-b", success=True)
    t.record("agent-a", "agent-b", success=False)
    assert t.score("agent-a") > 0.7


def test_low_trust_influences_high_trust():
    t = InterAgentTrust()
    for _ in range(5):
        t.record("low", "high", success=False)
    for _ in range(10):
        t.record("high", "x", success=True)
    flagged = t.low_trust_influencing_high_trust()
    assert any(e.src == "low" for e in flagged)


# ─────────────────────────────────────────────
# MAG-004 — Propagation
# ─────────────────────────────────────────────


def test_propagation_reaches_downstream():
    dag = InterAgentDAG()
    for n in ("a", "b", "c"):
        dag.add_node(n, n, "")
    dag.add_edge("a", "b")
    dag.add_edge("b", "c")
    rep = trace_propagation(dag, "a")
    assert "b" in rep.impacted_nodes
    assert "c" in rep.impacted_nodes
    assert rep.depth == 2


# ─────────────────────────────────────────────
# MAG-005 — Crew context
# ─────────────────────────────────────────────


def test_crew_context_shared_session():
    crew = CrewContext(event_bus=EventBus())
    crew.register("agent-a", "researcher")
    crew.register("agent-b", "writer")
    node = crew.record_call("agent-a", "agent-b", "summarize", {"text": "..."})
    assert node in crew.dag.nodes


# ─────────────────────────────────────────────
# MAG-006 — Shapley
# ─────────────────────────────────────────────


def test_shapley_blame_attribution_sums_to_total():
    # Failing function returns 1 when 'bad' agent is in the coalition.
    def vfn(coalition: list[str]) -> float:
        return 1.0 if "bad" in coalition else 0.0

    result = shapley_attribution(["good", "bad", "ok"], vfn)
    total_pct = sum(result.percentages.values())
    assert abs(total_pct - 100.0) < 0.01
    # 'bad' should have all the contribution
    assert max(result.contributions, key=result.contributions.get) == "bad"


# ─────────────────────────────────────────────
# MAG-007 — Consensus
# ─────────────────────────────────────────────


def test_consensus_majority():
    votes = [
        AgentVote("a", "use cache layer for speed"),
        AgentVote("b", "add a cache to boost performance"),
        AgentVote("c", "implement caching for faster results"),
        AgentVote("d", "rewrite the whole module from scratch"),
    ]
    rep = detect_consensus(votes, similarity_threshold=0.4, majority_ratio=0.5)
    assert rep.agreement_ratio >= 0.5


def test_consensus_no_agreement():
    votes = [
        AgentVote("a", "use sqlite locally"),
        AgentVote("b", "deploy a kubernetes cluster"),
        AgentVote("c", "rewrite the api in rust"),
    ]
    rep = detect_consensus(votes, majority_ratio=0.7)
    assert rep.agreed is False


# ─────────────────────────────────────────────
# MAG-008 — Spawning
# ─────────────────────────────────────────────


def test_spawning_enforces_depth():
    tr = SpawningTracker(max_depth=2)
    tr.register("a")
    tr.register("b", parent_id="a")
    tr.register("c", parent_id="b")
    with pytest.raises(SpawnLimitExceeded):
        tr.register("d", parent_id="c")


def test_spawning_enforces_total():
    tr = SpawningTracker(max_total=3)
    tr.register("a")
    tr.register("b")
    tr.register("c")
    with pytest.raises(SpawnLimitExceeded):
        tr.register("d")


def test_spawning_descendants():
    tr = SpawningTracker()
    tr.register("root")
    tr.register("child1", parent_id="root")
    tr.register("child2", parent_id="root")
    tr.register("grand", parent_id="child1")
    desc = tr.descendants("root")
    assert {n.agent_id for n in desc} == {"child1", "child2", "grand"}
