"""Human-in-the-loop ambient integration for AgentWatch.

Adds an escalation layer on top of the existing alerting engine: agent actions
are triaged by risk level into one of three interaction patterns — NOTIFY
(fire-and-forget, actionable events only), QUESTION (agent asks a human for
clarification), or REVIEW (human must approve / reject / edit before the action
proceeds). Every human decision is recorded in an audit trail, and a bounded
feedback loop adjusts the per-risk escalation thresholds based on observed
approval patterns.
"""

from agentwatch.hitl.decisions import (
    DecisionOutcome,
    HumanDecision,
    InteractionPattern,
    RequestState,
)
from agentwatch.hitl.feedback import FeedbackLearner
from agentwatch.hitl.orchestrator import HITLOrchestrator, HITLRequest
from agentwatch.hitl.thresholds import HITLThresholds

__all__ = [
    "DecisionOutcome",
    "HumanDecision",
    "InteractionPattern",
    "RequestState",
    "FeedbackLearner",
    "HITLOrchestrator",
    "HITLRequest",
    "HITLThresholds",
]
