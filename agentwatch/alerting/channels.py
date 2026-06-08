"""Validation for Slack and PagerDuty notification channel configurations."""
from __future__ import annotations

import re
import logging

logger = logging.getLogger(__name__)

# Slack webhook URLs must match: https://hooks.slack.com/services/T.../B.../...
_SLACK_WEBHOOK_RE = re.compile(
    r"^https://hooks\.slack\.com/services/T[A-Z0-9]+/B[A-Z0-9]+/[A-Za-z0-9]+$"
)

# PagerDuty routing keys are 32-character hex strings
_PAGERDUTY_KEY_RE = re.compile(r"^[a-f0-9]{32}$")

# PagerDuty webhook URLs must start with https://events.pagerduty.com/
_PAGERDUTY_WEBHOOK_RE = re.compile(
    r"^https://events\.pagerduty\.com/.*$"
)


class ChannelConfigError(ValueError):
    """Raised when a notification channel configuration is invalid."""


def validate_slack_webhook(url: str) -> None:
    """Validate a Slack webhook URL format.

    Args:
        url: The Slack webhook URL to validate.

    Raises:
        ChannelConfigError: If the URL does not match the expected Slack format.
    """
    if not _SLACK_WEBHOOK_RE.match(url):
        raise ChannelConfigError(
            f"Invalid Slack webhook URL: {url!r}. "
            "Expected format: https://hooks.slack.com/services/TXXXXXXXX/BXXXXXXXX/XXXXXXXX"
        )
    logger.debug("Slack webhook URL validated successfully.")


def validate_pagerduty_key(key: str) -> None:
    """Validate a PagerDuty routing key format.

    Args:
        key: The PagerDuty routing key to validate.

    Raises:
        ChannelConfigError: If the key does not match the expected 32-char hex format.
    """
    if not _PAGERDUTY_KEY_RE.match(key):
        raise ChannelConfigError(
            f"Invalid PagerDuty routing key: {key!r}. "
            "Expected a 32-character hexadecimal string."
        )
    logger.debug("PagerDuty routing key validated successfully.")


def validate_pagerduty_webhook(url: str) -> None:
    """Validate a PagerDuty webhook URL format.

    Args:
        url: The PagerDuty webhook URL to validate.

    Raises:
        ChannelConfigError: If the URL does not match the expected PagerDuty format.
    """
    if not _PAGERDUTY_WEBHOOK_RE.match(url):
        raise ChannelConfigError(
            f"Invalid PagerDuty webhook URL: {url!r}. "
            "Expected format: https://events.pagerduty.com/..."
        )
    logger.debug("PagerDuty webhook URL validated successfully.")


def validate_channels(
    slack_webhook_url: str | None = None,
    pagerduty_webhook_url: str | None = None,
    pagerduty_routing_key: str | None = None,
) -> None:
    """Validate all provided notification channel configurations.

    Call this at startup to catch invalid configurations before any alerts fire.

    Args:
        slack_webhook_url: Optional Slack webhook URL.
        pagerduty_webhook_url: Optional PagerDuty webhook URL.
        pagerduty_routing_key: Optional PagerDuty routing key.

    Raises:
        ChannelConfigError: If any provided value is invalid.
    """
    if slack_webhook_url:
        validate_slack_webhook(slack_webhook_url)

    if pagerduty_webhook_url:
        validate_pagerduty_webhook(pagerduty_webhook_url)

    if pagerduty_routing_key:
        validate_pagerduty_key(pagerduty_routing_key)
