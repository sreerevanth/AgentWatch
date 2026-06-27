"""
CircuitBreakerRegistry
----------------------
Singleton-style registry that manages one CircuitBreaker per session.
"""

from __future__ import annotations

import threading
from typing import Dict, Optional

from .circuit_breaker import CircuitBreaker, CircuitBreakerConfig


class CircuitBreakerRegistry:
    """Thread-safe registry of CircuitBreaker instances keyed by session_id."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._breakers: Dict[str, CircuitBreaker] = {}

    def get_or_create(self, session_id: str, config: Optional[CircuitBreakerConfig] = None) -> CircuitBreaker:
        with self._lock:
            if session_id not in self._breakers:
                self._breakers[session_id] = CircuitBreaker(session_id=session_id, config=config)
            return self._breakers[session_id]

    def get(self, session_id: str) -> Optional[CircuitBreaker]:
        with self._lock:
            return self._breakers.get(session_id)

    def remove(self, session_id: str) -> None:
        with self._lock:
            self._breakers.pop(session_id, None)

    def all_sessions(self) -> Dict[str, CircuitBreaker]:
        with self._lock:
            return dict(self._breakers)


registry = CircuitBreakerRegistry()
