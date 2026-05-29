"""Phase 7 — Cost Intelligence tests (CST-001..007)."""

from __future__ import annotations

from agentwatch.core.schema import AgentEvent, EventType, TokenUsage
from agentwatch.cost.anomaly import CostAnomalyDetector
from agentwatch.cost.comparator import estimate, estimate_for_text
from agentwatch.cost.governance import BudgetAction, BudgetGovernance
from agentwatch.cost.predictor import TaskCostPredictor
from agentwatch.cost.roi import DAMAGE_BY_SEVERITY, ROILedger
from agentwatch.cost.router import ModelRouter
from agentwatch.cost.tracker import CostTracker

# ─────────────────────────────────────────────
# CST-001 — Per-session token budget (existing tracker)
# ─────────────────────────────────────────────


def test_tracker_explicit_zero_budget():
    tracker = CostTracker(default_token_budget=1000, default_usd_budget=10.0)
    # Testing that 0 is preserved and not replaced by default
    budget = tracker.configure_session("zero-session", token_budget=0, usd_budget=0.0)
    assert budget.token_budget == 0
    assert budget.usd_budget == 0.0


def test_tracker_warns_at_80_percent():
    tracker = CostTracker(default_token_budget=1000, default_usd_budget=10.0)
    tracker.configure_session("S", token_budget=1000, usd_budget=10.0)
    ev = AgentEvent(
        session_id="S",
        agent_id="A",
        event_type=EventType.TOOL_CALL,
        token_usage=TokenUsage(prompt_tokens=400, completion_tokens=400, total_tokens=800),
    )
    budget = tracker.ingest_event(ev)
    assert "token_budget_near_limit" in budget.warnings
    assert not budget.exceeded


def test_tracker_blocks_at_100_percent():
    tracker = CostTracker(default_token_budget=1000, default_usd_budget=10.0)
    tracker.configure_session("S", token_budget=1000, usd_budget=10.0)
    ev = AgentEvent(
        session_id="S",
        agent_id="A",
        event_type=EventType.TOOL_CALL,
        token_usage=TokenUsage(total_tokens=1500),
    )
    budget = tracker.ingest_event(ev)
    assert budget.exceeded


# ─────────────────────────────────────────────
# CST-002 — Cost comparator
# ─────────────────────────────────────────────


def test_comparator_returns_cheapest_model():
    report = estimate(input_tokens=10_000, output_tokens=5_000)
    cheap = report.cheapest()
    expensive = report.most_expensive()
    assert cheap.total < expensive.total
    # gemini-1.5-flash should beat claude-opus-4-5 at these volumes
    assert cheap.model in {"gemini-1.5-flash", "gpt-4o-mini"}


def test_comparator_from_text():
    report = estimate_for_text("hello world", "summary")
    assert len(report.estimates) >= 5


# ─────────────────────────────────────────────
# CST-003 — Model router
# ─────────────────────────────────────────────


def test_router_picks_primary_when_healthy():
    r = ModelRouter(["primary", "backup1", "backup2"])
    r.observe("primary", confidence=0.9, latency_ms=500)
    decision = r.choose()
    assert decision.chosen == "primary"


def test_router_failover_on_confidence_drop():
    r = ModelRouter(["primary", "backup"])
    for _ in range(10):
        r.observe("primary", confidence=0.2)
    r.observe("backup", confidence=0.9)
    decision = r.choose()
    assert decision.chosen == "backup"
    assert "primary" in decision.bypassed


def test_router_failover_on_errors():
    r = ModelRouter(["primary", "backup"], error_ceiling=3)
    for _ in range(5):
        r.observe("primary", error=True)
    r.observe("backup", confidence=0.9)
    assert r.choose().chosen == "backup"


# ─────────────────────────────────────────────
# CST-004 — Task cost predictor
# ─────────────────────────────────────────────


def test_predictor_returns_fallback_when_empty():
    p = TaskCostPredictor()
    pred = p.predict("write a function")
    assert pred.n_neighbors == 0
    assert pred.expected_usd > 0


def test_predictor_uses_similar_history():
    p = TaskCostPredictor(k=3, fallback_usd=0.0)
    p.add("write a python function for sorting", 1000, 0.05)
    p.add("write a python function for filtering", 1100, 0.06)
    p.add("compile a kubernetes cluster manifest", 9000, 1.20)
    pred = p.predict("write a python function for parsing")
    assert pred.n_neighbors == 3
    # Should be closer to the python-function cases than the k8s one
    assert pred.expected_usd < 0.50


# ─────────────────────────────────────────────
# CST-005 — Anomaly
# ─────────────────────────────────────────────


def test_anomaly_detects_3x_spike():
    det = CostAnomalyDetector(min_samples=3)
    for _ in range(5):
        det.record("normal", 0.10)
    anomaly = det.record("spike", 0.40)
    assert anomaly is not None
    assert anomaly.severity in ("high", "critical")


def test_anomaly_quiet_below_2x():
    det = CostAnomalyDetector(min_samples=3)
    for _ in range(5):
        det.record("normal", 0.10)
    assert det.record("slight", 0.12) is None


# ─────────────────────────────────────────────
# CST-006 — ROI
# ─────────────────────────────────────────────


def test_roi_block_saves_per_severity():
    ledger = ROILedger()
    ledger.record_block("critical", "rm -rf /")
    ledger.record_block("low", "minor")
    summary = ledger.summary()
    assert summary.total_saved_usd == DAMAGE_BY_SEVERITY["critical"] + DAMAGE_BY_SEVERITY["low"]


def test_roi_net_and_ratio():
    ledger = ROILedger()
    ledger.record_failure_caught(1000, "missed bug")
    ledger.record_cost(100, "agent run")
    summary = ledger.summary()
    assert summary.net_roi_usd == 900
    assert summary.roi_ratio == 10.0
    assert summary.failures_caught == 1


# ─────────────────────────────────────────────
# CST-007 — Budget governance
# ─────────────────────────────────────────────


def test_budget_governance_auto_approve_small_action():
    g = BudgetGovernance()
    g.configure_team("team-a", monthly_cap_usd=1000.0, auto_approve_ceiling_usd=2.0)
    g.configure_agent("agent-1", "team-a", daily_cap_usd=50.0)
    dec = g.request("agent-1", action_cost_usd=1.0)
    assert dec.action == BudgetAction.APPROVE


def test_budget_governance_blocks_over_team_cap():
    g = BudgetGovernance()
    g.configure_team("team-a", monthly_cap_usd=5.0, auto_approve_ceiling_usd=100.0)
    g.configure_agent("agent-1", "team-a", daily_cap_usd=50.0)
    dec = g.request("agent-1", action_cost_usd=10.0)
    assert dec.action == BudgetAction.BLOCK
    assert "team" in dec.reason


def test_budget_governance_requires_human_above_auto_approve():
    g = BudgetGovernance()
    g.configure_team("team-a", monthly_cap_usd=1000.0, auto_approve_ceiling_usd=1.0)
    g.configure_agent("agent-1", "team-a", daily_cap_usd=50.0)
    dec = g.request("agent-1", action_cost_usd=10.0)
    assert dec.action == BudgetAction.REQUIRE_HUMAN
