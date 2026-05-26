"""Phase 4 — Persistent Memory tests (MEM-001..009)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from agentwatch.memory.causal_graph import (
    CausalEdge,
    CausalGraph,
    CausalNode,
    EdgeKind,
)
from agentwatch.memory.decay import ForgettingEngine, Importance
from agentwatch.memory.governance import (
    ErasureRequest,
    MemoryGovernance,
    RetentionPolicy,
)
from agentwatch.memory.health import MemoryHealthMonitor
from agentwatch.memory.identity import IdentityStore
from agentwatch.memory.nlquery import parse, query
from agentwatch.memory.resolver import (
    MemoryConflictResolver,
    MemoryEntry,
    resolve,
)
from agentwatch.memory.visualization import build_payload


# ─────────────────────────────────────────────
# MEM-002 — Causal graph
# ─────────────────────────────────────────────


def test_causal_graph_explain_chain():
    g = CausalGraph()
    ctx = CausalNode(node_id="c1", kind="context", text="user wants speed")
    constraint = CausalNode(node_id="x1", kind="constraint", text="no breaking changes")
    decision = CausalNode(node_id="d1", kind="decision", text="add cache layer")
    outcome = CausalNode(node_id="o1", kind="outcome", text="3x speedup")
    for n in (ctx, constraint, decision, outcome):
        g.add_node(n)
    g.add_edge("c1", "d1", EdgeKind.CAUSED_BY)
    g.add_edge("x1", "d1", EdgeKind.CONSTRAINED_BY)
    g.add_edge("d1", "o1", EdgeKind.PRODUCED)

    chain = g.explain("d1")
    chain_ids = {n.node_id for n in chain}
    assert {"d1", "c1", "x1"} <= chain_ids


def test_causal_graph_downstream():
    g = CausalGraph()
    g.add_node(CausalNode(node_id="d1", kind="decision", text="x"))
    g.add_node(CausalNode(node_id="o1", kind="outcome", text="y"))
    g.add_edge("d1", "o1", EdgeKind.PRODUCED)
    out = g.downstream("d1")
    assert any(n.node_id == "o1" for n in out)


# ─────────────────────────────────────────────
# MEM-003 — Identity
# ─────────────────────────────────────────────


def test_identity_store_isolates_users():
    s = IdentityStore()
    s.set_preference("alice", "p1", "theme", "dark")
    s.set_preference("bob", "p1", "theme", "light")
    a = s.get_or_create("alice", "p1")
    b = s.get_or_create("bob", "p1")
    assert a.preferences["theme"] == "dark"
    assert b.preferences["theme"] == "light"
    assert a.identity_key != b.identity_key


def test_identity_constraints_and_decisions():
    s = IdentityStore()
    s.add_constraint("u", "p", "no PII in logs")
    s.add_decision("u", "p", "db", "postgres", "team preference")
    rec = s.get_or_create("u", "p")
    assert "no PII in logs" in rec.constraints
    assert rec.decisions and rec.decisions[0]["decided"] == "postgres"


# ─────────────────────────────────────────────
# MEM-004 — Resolver
# ─────────────────────────────────────────────


def test_resolver_picks_recent_higher_trust():
    now = datetime.now(UTC)
    older = MemoryEntry(key="db", value="mysql", trust=0.5, timestamp=now - timedelta(days=30))
    newer = MemoryEntry(key="db", value="postgres", trust=0.9, timestamp=now)
    res = resolve([older, newer])
    assert res.winner.value == "postgres"


def test_resolver_in_store():
    r = MemoryConflictResolver()
    r.add(MemoryEntry(key="k", value="v1", trust=0.5))
    r.add(MemoryEntry(key="k", value="v2", trust=0.9))
    out = r.get("k")
    assert out is not None
    assert out.winner.value in ("v1", "v2")


# ─────────────────────────────────────────────
# MEM-005 — Forgetting curve
# ─────────────────────────────────────────────


def test_critical_memories_never_decay():
    e = ForgettingEngine()
    e.put("k", "v", importance=Importance.CRITICAL)
    e.put("temp", "x", importance=Importance.LOW)
    pruned = e.prune()
    assert "k" not in pruned


def test_low_importance_prune_after_long_idle():
    e = ForgettingEngine(prune_threshold=0.99)  # very aggressive
    e.put("k", "v", importance=Importance.LOW)
    pruned = e.prune(now=datetime.now(UTC) + timedelta(days=100))
    assert "k" in pruned


# ─────────────────────────────────────────────
# MEM-006 — Health monitor
# ─────────────────────────────────────────────


def test_health_monitor_flags_stale_and_conflict():
    monitor = MemoryHealthMonitor(stale_after=timedelta(days=10))
    now = datetime.now(UTC)
    memories = [
        {"key": "a", "value": 1, "timestamp": (now - timedelta(days=30)).isoformat()},
        {"key": "b", "value": 2, "timestamp": now.isoformat()},
        {"key": "b", "value": 3, "timestamp": now.isoformat()},  # conflict
        {"missing_key": True, "value": None},  # corrupt
    ]
    rep = monitor.inspect(memories, now=now)
    kinds = {i.kind for i in rep.issues}
    assert "stale" in kinds
    assert "conflict" in kinds
    assert "corrupt" in kinds
    assert 0 <= rep.score <= 1


# ─────────────────────────────────────────────
# MEM-007 — NL query
# ─────────────────────────────────────────────


def test_parse_extracts_time_and_topic():
    f = parse("What did we decide about the database last week?")
    assert f.since is not None
    assert f.topic and "database" in f.topic.lower()


def test_query_returns_relevant_first():
    memories = [
        {"key": "a", "value": "we chose postgres", "timestamp": datetime.now(UTC).isoformat()},
        {"key": "b", "value": "lunch plans", "timestamp": datetime.now(UTC).isoformat()},
    ]
    results = query("what about the database?", memories)
    assert results
    assert results[0].key == "a"


# ─────────────────────────────────────────────
# MEM-008 — Governance
# ─────────────────────────────────────────────


def test_retention_drops_old_when_policy_applies():
    g = MemoryGovernance()
    g.add_policy(RetentionPolicy(name="default", applies_to="all", retain_for=timedelta(days=10)))
    now = datetime.now(UTC)
    memories = [
        {"key": "old", "value": 1, "timestamp": (now - timedelta(days=30)).isoformat()},
        {"key": "new", "value": 2, "timestamp": now.isoformat()},
    ]
    kept = g.apply_retention(memories, now=now)
    keys = {m["key"] for m in kept}
    assert "new" in keys
    assert "old" not in keys


def test_erasure_removes_user_data_and_returns_receipt():
    g = MemoryGovernance()
    memories = [
        {"key": "a", "value": 1, "user_id": "alice"},
        {"key": "b", "value": 2, "user_id": "bob"},
    ]
    kept, receipt = g.erase(ErasureRequest(user_id="alice"), memories)
    assert len(kept) == 1
    assert kept[0]["user_id"] == "bob"
    assert receipt.items_deleted == 1


# ─────────────────────────────────────────────
# MEM-009 — Visualization
# ─────────────────────────────────────────────


def test_visualization_payload_marks_corrupted():
    from agentwatch.memory.health import HealthIssue, HealthReport

    memories = [
        {"key": "a", "type": "episodic", "value": "x"},
        {"key": "b", "type": "semantic", "value": "y"},
    ]
    health = HealthReport(total_memories=2, issues=[HealthIssue(key="b", kind="corrupt", detail="x")])
    payload = build_payload(memories, retrievals=[("a", "b")], health=health)
    by_id = {n.id: n for n in payload.nodes}
    assert by_id["b"].kind == "corrupted"
    assert len(payload.edges) == 1
