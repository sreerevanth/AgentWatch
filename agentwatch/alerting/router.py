"""
ELUSoC_2026 - Alerting Router.
Handles dispatching alerts to multiple destination channels based on custom routing logic.
"""

from __future__ import annotations

import logging
from typing import Any
from agentwatch.core.schema import AgentEvent

logger = logging.getLogger(__name__)


class AlertRouter:
    """Routes alerts dynamically based on event risk levels and custom parameters."""

    def __init__(self, channels: list[str] | None = None) -> None:
        self.channels = channels or ["slack", "pagerduty"]

    def determine_destinations(self, event: AgentEvent) -> list[str]:
        """Determine which channels should receive the alert based on the event payload."""
        destinations = []
        if not event.safety:
            return ["slack"]

        risk = event.safety.risk_level
        # Critical risk goes to PagerDuty and Slack
        if risk.value in ("critical", "high"):
            destinations.extend(self.channels)
        else:
            # Low/Safe risk goes to Slack only
            destinations.append("slack")
            
        return list(set(destinations))
