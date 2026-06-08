"""Tests for Slack and PagerDuty channel configuration validation."""
from __future__ import annotations

import pytest

from agentwatch.alerting.channels import (
    ChannelConfigError,
    validate_slack_webhook,
    validate_pagerduty_key,
    validate_pagerduty_webhook,
    validate_channels,
)


# ---------------------------------------------------------------------------
# Slack webhook tests
# ---------------------------------------------------------------------------

def test_valid_slack_webhook():
    validate_slack_webhook("https://hooks.slack.com/services/TABC12345/BABC12345/abcdefghijklmnop")


def test_invalid_slack_webhook_wrong_domain():
    with pytest.raises(ChannelConfigError, match="Invalid Slack webhook URL"):
        validate_slack_webhook("https://evil.com/services/TABC/BABC/xyz")


def test_invalid_slack_webhook_missing_parts():
    with pytest.raises(ChannelConfigError, match="Invalid Slack webhook URL"):
        validate_slack_webhook("https://hooks.slack.com/services/TABC")


def test_invalid_slack_webhook_empty():
    with pytest.raises(ChannelConfigError, match="Invalid Slack webhook URL"):
        validate_slack_webhook("")


# ---------------------------------------------------------------------------
# PagerDuty routing key tests
# ---------------------------------------------------------------------------

def test_valid_pagerduty_key():
    validate_pagerduty_key("a" * 32)


def test_invalid_pagerduty_key_too_short():
    with pytest.raises(ChannelConfigError, match="Invalid PagerDuty routing key"):
        validate_pagerduty_key("abc123")


def test_invalid_pagerduty_key_non_hex():
    with pytest.raises(ChannelConfigError, match="Invalid PagerDuty routing key"):
        validate_pagerduty_key("z" * 32)


def test_invalid_pagerduty_key_empty():
    with pytest.raises(ChannelConfigError, match="Invalid PagerDuty routing key"):
        validate_pagerduty_key("")


# ---------------------------------------------------------------------------
# PagerDuty webhook tests
# ---------------------------------------------------------------------------

def test_valid_pagerduty_webhook():
    validate_pagerduty_webhook("https://events.pagerduty.com/v2/enqueue")


def test_invalid_pagerduty_webhook_wrong_domain():
    with pytest.raises(ChannelConfigError, match="Invalid PagerDuty webhook URL"):
        validate_pagerduty_webhook("https://evil.com/v2/enqueue")


def test_invalid_pagerduty_webhook_http():
    with pytest.raises(ChannelConfigError, match="Invalid PagerDuty webhook URL"):
        validate_pagerduty_webhook("http://events.pagerduty.com/v2/enqueue")


# ---------------------------------------------------------------------------
# validate_channels (combined) tests
# ---------------------------------------------------------------------------

def test_validate_channels_all_none():
    # Should not raise when nothing is configured
    validate_channels()


def test_validate_channels_valid_slack_only():
    validate_channels(
        slack_webhook_url="https://hooks.slack.com/services/TABC12345/BABC12345/abcdefghijklmnop"
    )


def test_validate_channels_invalid_slack_raises():
    with pytest.raises(ChannelConfigError):
        validate_channels(slack_webhook_url="not-a-valid-url")


def test_validate_channels_valid_pagerduty():
    validate_channels(
        pagerduty_webhook_url="https://events.pagerduty.com/v2/enqueue",
        pagerduty_routing_key="a" * 32,
    )


def test_validate_channels_invalid_pagerduty_key_raises():
    with pytest.raises(ChannelConfigError):
        validate_channels(
            pagerduty_webhook_url="https://events.pagerduty.com/v2/enqueue",
            pagerduty_routing_key="invalid-key",
        )
