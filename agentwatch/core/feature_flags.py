"""Feature flags system with runtime toggle.

Provides a lightweight feature flag system that supports:
- Boolean on/off flags
- Percentage-based rollouts
- Environment-scoped flags
- Runtime toggle without restart
- Event callbacks on flag changes
"""

from __future__ import annotations

import enum
import hashlib
import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable

logger = logging.getLogger(__name__)


class FlagState(enum.Enum):
    ENABLED = "enabled"
    DISABLED = "disabled"
    CONDITIONAL = "conditional"


@dataclass
class FeatureFlag:
    name: str
    state: FlagState = FlagState.DISABLED
    description: str = ""
    rollout_percentage: float = 100.0
    allowed_environments: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    @property
    def is_on(self) -> bool:
        return self.state == FlagState.ENABLED

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "state": self.state.value,
            "description": self.description,
            "rollout_percentage": self.rollout_percentage,
            "allowed_environments": self.allowed_environments,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class FeatureFlagStore:
    """In-memory feature flag store with thread-safe access.

    Usage:
        store = FeatureFlagStore()
        store.define("new_safety_engine", enabled=True, description="v2 safety")
        store.define("beta_reasoning", enabled=False)

        if store.is_enabled("new_safety_engine"):
            use_new_engine()
    """

    def __init__(self, environment: str = "development") -> None:
        self._flags: dict[str, FeatureFlag] = {}
        self._environment = environment
        self._lock = threading.Lock()
        self._callbacks: dict[str, list[Callable[[str, bool, bool], None]]] = {}
        self._global_callbacks: list[Callable[[str, bool, bool], None]] = []

    @property
    def environment(self) -> str:
        return self._environment

    def define(
        self,
        name: str,
        enabled: bool = False,
        description: str = "",
        rollout_percentage: float | None = None,
        allowed_environments: list[str] | None = None,
        **metadata: Any,
    ) -> FeatureFlag:
        with self._lock:
            if name in self._flags:
                flag = self._flags[name]
                old_enabled = flag.is_on
                flag.state = FlagState.ENABLED if enabled else FlagState.DISABLED
                if rollout_percentage is not None:
                    flag.rollout_percentage = rollout_percentage
                    flag.state = FlagState.CONDITIONAL
                if allowed_environments is not None:
                    flag.allowed_environments = allowed_environments
                flag.updated_at = time.time()
                if metadata:
                    flag.metadata.update(metadata)
                self._notify_callbacks(name, old_enabled, flag.is_on)
                return flag

            state = FlagState.ENABLED if enabled else FlagState.DISABLED
            if rollout_percentage is not None and rollout_percentage < 100.0:
                state = FlagState.CONDITIONAL

            flag = FeatureFlag(
                name=name,
                state=state,
                description=description,
                rollout_percentage=rollout_percentage or (100.0 if enabled else 0.0),
                allowed_environments=allowed_environments or [],
                metadata=metadata,
            )
            self._flags[name] = flag
            return flag

    def is_enabled(self, name: str, user_id: str | None = None) -> bool:
        with self._lock:
            flag = self._flags.get(name)
            if flag is None:
                logger.debug("Feature flag '%s' not defined, defaulting to False", name)
                return False

            if flag.state == FlagState.DISABLED:
                return False
            if flag.state == FlagState.ENABLED:
                return self._check_environment(flag)

            if flag.state == FlagState.CONDITIONAL:
                if not self._check_environment(flag):
                    return False
                return self._check_rollout(flag, user_id)

            return False

    def _check_environment(self, flag: FeatureFlag) -> bool:
        if not flag.allowed_environments:
            return True
        return self._environment in flag.allowed_environments

    def _check_rollout(self, flag: FeatureFlag, user_id: str | None) -> bool:
        if flag.rollout_percentage >= 100.0:
            return True
        if flag.rollout_percentage <= 0.0:
            return False
        if user_id is None:
            import random
            return random.random() * 100 < flag.rollout_percentage
        hash_input = f"{flag.name}:{user_id}"
        hash_val = int(hashlib.md5(hash_input.encode()).hexdigest()[:8], 16)
        return (hash_val % 100) < flag.rollout_percentage

    def enable(self, name: str) -> bool:
        with self._lock:
            flag = self._flags.get(name)
            if flag is None:
                return False
            old = flag.is_on
            flag.state = FlagState.ENABLED
            flag.updated_at = time.time()
            self._notify_callbacks(name, old, True)
            return True

    def disable(self, name: str) -> bool:
        with self._lock:
            flag = self._flags.get(name)
            if flag is None:
                return False
            old = flag.is_on
            flag.state = FlagState.DISABLED
            flag.updated_at = time.time()
            self._notify_callbacks(name, old, False)
            return True

    def set_rollout(self, name: str, percentage: float) -> bool:
        with self._lock:
            flag = self._flags.get(name)
            if flag is None:
                return False
            old = flag.is_on
            flag.rollout_percentage = max(0.0, min(100.0, percentage))
            if flag.rollout_percentage >= 100.0:
                flag.state = FlagState.ENABLED
            elif flag.rollout_percentage <= 0.0:
                flag.state = FlagState.DISABLED
            else:
                flag.state = FlagState.CONDITIONAL
            flag.updated_at = time.time()
            self._notify_callbacks(name, old, flag.is_on)
            return True

    def remove(self, name: str) -> bool:
        with self._lock:
            if name in self._flags:
                del self._flags[name]
                return True
            return False

    def get(self, name: str) -> FeatureFlag | None:
        return self._flags.get(name)

    def list_flags(self) -> list[FeatureFlag]:
        return list(self._flags.values())

    def list_enabled(self) -> list[str]:
        return [f.name for f in self._flags.values() if f.is_on]

    def list_disabled(self) -> list[str]:
        return [f.name for f in self._flags.values() if not f.is_on]

    def on_change(self, callback: Callable[[str, bool, bool], None], flag_name: str | None = None) -> None:
        with self._lock:
            if flag_name:
                self._callbacks.setdefault(flag_name, []).append(callback)
            else:
                self._global_callbacks.append(callback)

    def _notify_callbacks(self, name: str, old_enabled: bool, new_enabled: bool) -> None:
        for cb in self._callbacks.get(name, []):
            try:
                cb(name, old_enabled, new_enabled)
            except Exception as exc:
                logger.error("Feature flag callback error for '%s': %s", name, exc)
        for cb in self._global_callbacks:
            try:
                cb(name, old_enabled, new_enabled)
            except Exception as exc:
                logger.error("Feature flag global callback error: %s", exc)

    def to_dict(self) -> dict[str, Any]:
        return {
            "environment": self._environment,
            "flags": {name: f.to_dict() for name, f in self._flags.items()},
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any], environment: str | None = None) -> FeatureFlagStore:
        store = cls(environment=environment or data.get("environment", "development"))
        for name, flag_data in data.get("flags", {}).items():
            flag = FeatureFlag(
                name=name,
                state=FlagState(flag_data["state"]),
                description=flag_data.get("description", ""),
                rollout_percentage=flag_data.get("rollout_percentage", 100.0),
                allowed_environments=flag_data.get("allowed_environments", []),
                metadata=flag_data.get("metadata", {}),
                created_at=flag_data.get("created_at", time.time()),
                updated_at=flag_data.get("updated_at", time.time()),
            )
            store._flags[name] = flag
        return store
