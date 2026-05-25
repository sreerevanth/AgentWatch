"""Per-session token and cost budget tracking."""

from __future__ import annotations

from dataclasses import dataclass, field

from agentwatch.core.schema import AgentEvent


@dataclass
class SessionBudget:
    session_id: str
    token_budget: int
    usd_budget: float
    tokens_used: int = 0
    usd_used: float = 0.0
    exceeded: bool = False
    warnings: list[str] = field(default_factory=list)

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
            token_budget=token_budget or self._default_token_budget,
            usd_budget=usd_budget or self._default_usd_budget,
        )
        self._budgets[session_id] = budget
        return budget

    def ingest_event(self, event: AgentEvent) -> SessionBudget:
        budget = self._budgets.get(event.session_id) or self.configure_session(event.session_id)
        if event.token_usage:
            budget.tokens_used += event.token_usage.total_tokens
            budget.usd_used += float(event.token_usage.estimated_cost_usd or 0.0)
        self._evaluate(budget)
        return budget

    def get_session(self, session_id: str) -> SessionBudget | None:
        return self._budgets.get(session_id)

    def stats(self) -> dict[str, object]:
        return {
            "tracked_sessions": len(self._budgets),
            "sessions_over_budget": sum(1 for budget in self._budgets.values() if budget.exceeded),
        }

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
