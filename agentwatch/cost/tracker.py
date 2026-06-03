"""Per-session token and cost budget tracking."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from agentwatch.core.schema import AgentEvent

# Maximum number of sessions held in memory at once.
# Keeps heap usage bounded on long-running deployments that process
# thousands of unique sessions per day.
_MAX_BUDGET_ENTRIES: int = 50_000

# Sessions with no activity for this many seconds are eligible for eviction.
_SESSION_TTL_SECONDS: float = 7_200  # 2 hours

# Minimum interval between full eviction scans (seconds).
# Prevents _maybe_evict() from performing an O(n) scan on every ingest
# when _budgets is at capacity and all sessions are still active.
_EVICTION_INTERVAL_SECONDS: float = 60.0


@dataclass
class SessionBudget:
    session_id: str
    token_budget: int
    usd_budget: float
    tokens_used: int = 0
    usd_used: float = 0.0
    exceeded: bool = False
    warnings: list[str] = field(default_factory=list)
    last_active: float = field(default_factory=time.monotonic)

    def to_dict(self) -> dict[str, object]:
        return {
            "session_id": self.session_id,
            "token_budget": self.token_budget,
            "usd_budget": self.usd_budget,
            "tokens_used": self.tokens_used,
            "usd_used": round(self.usd_used, 6),
            "exceeded": self.exceeded,
            "warnings": self.warnings,
        }


class CostTracker:
    def __init__(self, default_token_budget: int = 100_000, default_usd_budget: float = 25.0):
        self._default_token_budget = default_token_budget
        self._default_usd_budget = default_usd_budget
        self._budgets: dict[str, SessionBudget] = {}
        # Timestamp of the last full eviction scan. Initialised to 0 so the
        # first call to _maybe_evict() always runs a scan if warranted.
        self._last_eviction: float = 0.0

    def configure_session(
        self,
        session_id: str,
        token_budget: int | None = None,
        usd_budget: float | None = None,
    ) -> SessionBudget:
        budget = SessionBudget(
            session_id=session_id,
            token_budget=token_budget if token_budget is not None else self._default_token_budget,
            usd_budget=usd_budget if usd_budget is not None else self._default_usd_budget,
        )
        self._budgets[session_id] = budget
        return budget

    def ingest_event(self, event: AgentEvent) -> SessionBudget:
        budget = self._budgets.get(event.session_id) or self.configure_session(event.session_id)
        if event.token_usage:
            budget.tokens_used += event.token_usage.total_tokens
            budget.usd_used += float(event.token_usage.estimated_cost_usd or 0.0)
        budget.last_active = time.monotonic()
        self._evaluate(budget)
        self._maybe_evict()
        return budget

    def get_session(self, session_id: str) -> SessionBudget | None:
        return self._budgets.get(session_id)

    def stats(self) -> dict[str, object]:
        return {
            "tracked_sessions": len(self._budgets),
            "sessions_over_budget": sum(1 for budget in self._budgets.values() if budget.exceeded),
        }

    def _maybe_evict(self) -> None:
        """Remove stale sessions when the store grows beyond its cap.

        Eviction runs only when two conditions are both true:
        1. The number of tracked sessions is at or above _MAX_BUDGET_ENTRIES.
        2. At least _EVICTION_INTERVAL_SECONDS have elapsed since the last scan.

        The interval guard prevents repeated O(n) scans on every ingest_event
        call when the store is at capacity but all sessions are still active
        (the scenario the maintainer identified as a hot-path risk). In the
        worst case, one scan runs per interval window regardless of throughput.
        """
        if len(self._budgets) < _MAX_BUDGET_ENTRIES:
            return
        now = time.monotonic()
        if now - self._last_eviction < _EVICTION_INTERVAL_SECONDS:
            return
        self._last_eviction = now
        cutoff = now - _SESSION_TTL_SECONDS
        stale = [sid for sid, b in self._budgets.items() if b.last_active < cutoff]
        for sid in stale:
            del self._budgets[sid]

    def _evaluate(self, budget: SessionBudget) -> None:
        budget.warnings = []
        budget.exceeded = False
        if budget.tokens_used >= budget.token_budget * 0.8:
            budget.warnings.append("token_budget_near_limit")
        if budget.usd_used >= budget.usd_budget * 0.8:
            budget.warnings.append("usd_budget_near_limit")
        if budget.tokens_used > budget.token_budget or budget.usd_used > budget.usd_budget:
            budget.exceeded = True
            budget.warnings.append("budget_exceeded")
