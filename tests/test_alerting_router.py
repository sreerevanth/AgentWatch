"""Unit tests for the Alerting Router and Filters."""

from __future__ import annotations

import pytest
from agentwatch.alerting.router import AlertRouter
from agentwatch.alerting.filters import AlertFilter
from agentwatch.core.schema import AgentEvent, RiskLevel, SafetyCheckData, EventType


def test_alert_router_destinations():
    router = AlertRouter()

    # Safe events go to Slack
    safe_event = AgentEvent(
        session_id="s1",
        agent_id="a1",
        step_number=1,
        event_type=EventType.TOOL_CALL,
        safety=SafetyCheckData(
            risk_level=RiskLevel.SAFE,
            risk_score=0.0,
            blocked=False,
            reasons=[],
        ),
    )
    dest1 = router.determine_destinations(safe_event)
    assert "slack" in dest1
    assert "pagerduty" not in dest1

    # Critical risk goes to both Slack and PagerDuty
    critical_event = AgentEvent(
        session_id="s2",
        agent_id="a2",
        step_number=1,
        event_type=EventType.TOOL_CALL,
        safety=SafetyCheckData(
            risk_level=RiskLevel.CRITICAL,
            risk_score=1.0,
            blocked=True,
            reasons=["Destructive command check failed"],
        ),
    )
    dest2 = router.determine_destinations(critical_event)
    assert "slack" in dest2
    assert "pagerduty" in dest2


def test_alert_filter_suppression():
    filt = AlertFilter()
    event = AgentEvent(
        session_id="s3",
        agent_id="a3",
        step_number=1,
        event_type=EventType.TOOL_CALL,
        safety=SafetyCheckData(
            risk_level=RiskLevel.HIGH,
            risk_score=0.9,
            blocked=True,
            reasons=["test"],
        ),
    )

    # First event: allowed
    assert filt.should_suppress(event) is False

    # Second event of same type/session: suppressed
    assert filt.should_suppress(event) is True
