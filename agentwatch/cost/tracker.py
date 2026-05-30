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

        Scans for entries whose last_active timestamp is older than
        _SESSION_TTL_SECONDS. Eviction only runs when the dict is at or
        above _MAX_BUDGET_ENTRIES so the cost is paid only when necessary.
        """
        if len(self._budgets) < _MAX_BUDGET_ENTRIES:
            return
        cutoff = time.monotonic() - _SESSION_TTL_SECONDS
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
