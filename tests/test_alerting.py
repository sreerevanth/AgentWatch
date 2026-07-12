"""Unit tests for the AlertingEngine webhook delivery retry mechanism."""

from __future__ import annotations

import asyncio

import httpx

from agentwatch.alerting.engine import AlertingConfig, AlertingEngine
from agentwatch.core.schema import AgentEvent, AgentFramework, EventType


def test_alerting_engine_retries_and_succeeds(monkeypatch):
    calls = 0

    class MockResponse:
        def raise_for_status(self):
            pass

    async def mock_post(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls < 3:
            raise httpx.ConnectError("Transient connection failure")
        return MockResponse()

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

    # Shorten delay for fast tests
    engine = AlertingEngine(
        AlertingConfig(
            slack_webhook_url="https://hooks.slack.com/services/TTEST1234/BTEST1234/abcdefghijklmn"
        )
    )

    event = AgentEvent(
        session_id="S",
        agent_id="A",
        framework=AgentFramework.CUSTOM,
        event_type=EventType.SAFETY_BLOCK,
    )

    sent = asyncio.run(engine.alert_event(event))
    assert sent["slack"] is True
    assert calls == 3


def test_alerting_engine_fails_after_max_retries(monkeypatch):
    calls = 0

    async def mock_post(*args, **kwargs):
        nonlocal calls
        calls += 1
        raise httpx.ConnectError("Permanent connection failure")

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

    engine = AlertingEngine(
        AlertingConfig(
            slack_webhook_url="https://hooks.slack.com/services/TTEST1234/BTEST1234/abcdefghijklmn"
        )
    )

    event = AgentEvent(
        session_id="S",
        agent_id="A",
        framework=AgentFramework.CUSTOM,
        event_type=EventType.SAFETY_BLOCK,
    )

    sent = asyncio.run(engine.alert_event(event))
    assert sent["slack"] is False
    assert calls == 3


def test_alert_custom_slack_and_pagerduty(monkeypatch):
    slack_payloads = []
    pd_payloads = []

    class MockResponse:
        def raise_for_status(self):
            pass

    async def mock_post(client, url, content, headers):
        import json
        data = json.loads(content.decode("utf-8"))
        if "slack.com" in url:
            slack_payloads.append(data)
        elif "pagerduty.com" in url:
            pd_payloads.append(data)
        return MockResponse()

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

    engine = AlertingEngine(
        AlertingConfig(
            slack_webhook_url="https://hooks.slack.com/services/TTEST1234/BTEST1234/abcdefghijklmn",
            pagerduty_webhook_url="https://events.pagerduty.com/v2/enqueue",
            pagerduty_routing_key="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        )
    )

    sent = asyncio.run(
        engine.alert_custom(
            title="Custom Title",
            text="Custom Text Detail",
            link="https://dashboard.example.com",
        )
    )

    assert sent["slack"] is True
    assert sent["pagerduty"] is True

    assert len(slack_payloads) == 1
    assert slack_payloads[0]["text"] == "Custom Title"
    assert slack_payloads[0]["blocks"][1]["text"]["text"] == "Custom Text Detail"

    assert len(pd_payloads) == 1
    assert pd_payloads[0]["payload"]["summary"] == "Custom Title: Custom Text Detail"
    assert pd_payloads[0]["routing_key"] == "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"


def test_alert_custom_no_webhooks_configured():
    engine = AlertingEngine(AlertingConfig())
    sent = asyncio.run(
        engine.alert_custom(
            title="Custom Title",
            text="Custom Text Detail",
        )
    )
    assert sent["slack"] is False
    assert sent["pagerduty"] is False


def test_alert_smart_alert_delivery(monkeypatch):
    slack_payloads = []

    class MockResponse:
        def raise_for_status(self):
            pass

    async def mock_post(client, url, content, headers):
        import json
        data = json.loads(content.decode("utf-8"))
        slack_payloads.append(data)
        return MockResponse()

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

    engine = AlertingEngine(
        AlertingConfig(
            slack_webhook_url="https://hooks.slack.com/services/TTEST1234/BTEST1234/abcdefghijklmn",
        )
    )

    sent = asyncio.run(
        engine.alert_smart_alert(
            alert_text="Smart alert detail",
            dashboard_link="https://dashboard.example.com/smart",
        )
    )

    assert sent["slack"] is True
    assert len(slack_payloads) == 1
    assert slack_payloads[0]["text"] == "Smart Alert: Intervention Required"
    assert slack_payloads[0]["blocks"][1]["text"]["text"] == "Smart alert detail"
    assert "https://dashboard.example.com/smart" in slack_payloads[0]["blocks"][2]["text"]["text"]

