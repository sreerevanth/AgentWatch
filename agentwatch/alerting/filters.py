"""
ELUSoC_2026 - Alerting Filters.
Provides filtering capabilities to suppress repetitive or low-value alerts.
"""

from __future__ import annotations

import logging
from agentwatch.core.schema import AgentEvent

logger = logging.getLogger(__name__)


class AlertFilter:
    """Filters duplicate/spam alerts within a rolling window."""

    def __init__(self) -> None:
        self._sent_keys: set[str] = set()

    def should_suppress(self, event: AgentEvent) -> bool:
        """Return True if the event is a duplicate and should be suppressed."""
        if not event.safety:
            return False

        # Generate deduplication key based on session and blocked status
        key = f"{event.session_id}:{event.safety.blocked}"
        if key in self._sent_keys:
            logger.info("Suppressing duplicate alert for key: %s", key)
            return True

        self._sent_keys.add(key)
        return False

    def clear(self) -> None:
        self._sent_keys.clear()
