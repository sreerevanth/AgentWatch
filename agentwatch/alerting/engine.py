"""Alert routing for Slack and PagerDuty webhooks."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import httpx

from agentwatch.core.schema import AgentEvent, RiskLevel

logger = logging.getLogger(__name__)


@dataclass
class AlertingConfig:
    slack_webhook_url: str | None = None
    pagerduty_webhook_url: str | None = None
    pagerduty_routing_key: str | None = None
    min_risk_for_pagerduty: RiskLevel = RiskLevel.HIGH


class AlertingEngine:
    def __init__(self, config: AlertingConfig | None = None):
        self._config = config or AlertingConfig()

    async def alert_event(self, event: AgentEvent) -> dict[str, bool]:
        payload = self._build_payload(event)
        sent = {"slack": False, "pagerduty": False}

        if self._config.slack_webhook_url:
            sent["slack"] = await self._post(self._config.slack_webhook_url, payload["slack"])

        risk_level = event.safety.risk_level if event.safety else RiskLevel.SAFE
        if self._config.pagerduty_webhook_url and self._should_page(risk_level):
            sent["pagerduty"] = await self._post(
                self._config.pagerduty_webhook_url,
                payload["pagerduty"],
            )
        return sent

    def _should_page(self, risk_level: RiskLevel) -> bool:
        order = [
            RiskLevel.SAFE,
            RiskLevel.LOW,
            RiskLevel.MEDIUM,
            RiskLevel.HIGH,
            RiskLevel.CRITICAL,
        ]
        return order.index(risk_level) >= order.index(self._config.min_risk_for_pagerduty)

    def _build_payload(self, event: AgentEvent) -> dict[str, dict[str, Any]]:
        tool = event.tool_call.tool_name if event.tool_call else event.event_type.value
        risk = event.safety.risk_level.value if event.safety else "safe"
        reasons = event.safety.reasons if event.safety else []
        summary = f"AgentWatch {event.status.value}: {tool} ({risk})"
        return {
            "slack": {
                "text": summary,
                "blocks": [
                    {"type": "section", "text": {"type": "mrkdwn", "text": f"*{summary}*"}},
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "\n".join(
                                [
                                    f"*Session:* `{event.session_id}`",
                                    f"*Agent:* `{event.agent_id}`",
                                    f"*Event:* `{event.event_type.value}`",
                                    f"*Reasons:* {', '.join(reasons) or 'n/a'}",
                                ]
                            ),
                        },
                    },
                ],
            },
            "pagerduty": {
                "routing_key": self._config.pagerduty_routing_key or "",
                "event_action": "trigger",
                "payload": {
                    "summary": summary,
                    "source": "agentwatch",
                    "severity": "critical" if risk == "critical" else "error",
                    "custom_details": {
                        "session_id": event.session_id,
                        "agent_id": event.agent_id,
                        "event_type": event.event_type.value,
                        "reasons": reasons,
                    },
                },
            },
        }

    async def _post(self, url: str, payload: dict[str, Any], max_retries: int = 3) -> bool:
        import asyncio

        delay = 0.5
        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    response = await client.post(url, json=payload)
                    response.raise_for_status()
                    return True
            except Exception as exc:
                logger.warning(
                    "Alert delivery failed for %s (attempt %d/%d): %s",
                    url,
                    attempt + 1,
                    max_retries,
                    exc,
                )
                if attempt < max_retries - 1:
                    await asyncio.sleep(delay)
                    delay *= 2
        return False
