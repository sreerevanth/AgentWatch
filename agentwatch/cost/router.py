"""
CST-003 — Model Degradation Auto-Router.

When the primary model's observed confidence or latency degrades, route
traffic to backup models without context loss. Configurable priority order.
"""

from __future__ import annotations

import logging
import math
import statistics
from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ModelHealth:
    model: str
    samples: deque[float] = field(default_factory=lambda: deque(maxlen=50))
    latencies_ms: deque[float] = field(default_factory=lambda: deque(maxlen=50))
    error_count: int = 0
    last_seen: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def mean_confidence(self) -> float:
        return statistics.mean(self.samples) if self.samples else 1.0

    @property
    def mean_latency_ms(self) -> float:
        return statistics.mean(self.latencies_ms) if self.latencies_ms else 0.0


@dataclass
class RouteDecision:
    chosen: str
    reason: str
    bypassed: list[str] = field(default_factory=list)


class ModelRouter:
    """
    Track per-model health (confidence + latency + error rate).
    Pick the highest-priority model whose health is above threshold.
    """

    def __init__(
        self,
        priority: list[str],
        *,
        confidence_floor: float = 0.55,
        latency_ceiling_ms: float = 6000.0,
        error_ceiling: int = 5,
        route_timeouts: dict[str, float] | None = None,
    ):
        if not priority:
            raise ValueError("priority list must be non-empty")
        self.priority = priority
        self.confidence_floor = confidence_floor
        self.latency_ceiling_ms = latency_ceiling_ms
        self.error_ceiling = error_ceiling
        route_timeouts = dict(route_timeouts or {})
        unknown = set(route_timeouts) - set(priority)
        if unknown:
            raise ValueError(f"route_timeouts contains unknown models: {sorted(unknown)}")
        for model, timeout in route_timeouts.items():
            t = float(timeout)
            if not math.isfinite(t) or t <= 0:
                raise ValueError(f"route_timeouts[{model!r}] must be a finite positive number")
            route_timeouts[model] = t
        self.route_timeouts = route_timeouts
        self._health: dict[str, ModelHealth] = {m: ModelHealth(model=m) for m in priority}

    def observe(
        self,
        model: str,
        *,
        confidence: float | None = None,
        latency_ms: float | None = None,
        error: bool = False,
    ) -> None:
        h = self._health.setdefault(model, ModelHealth(model=model))
        h.last_seen = datetime.now(UTC)
        if confidence is not None:
            h.samples.append(float(confidence))
        if latency_ms is not None:
            h.latencies_ms.append(float(latency_ms))
        if error:
            h.error_count += 1

    def reset_errors(self, model: str) -> None:
        h = self._health.get(model)
        if h:
            h.error_count = 0

    def is_healthy(self, model: str) -> bool:
        h = self._health.get(model)
        if h is None:
            return False
        if h.error_count >= self.error_ceiling:
            return False
        if h.samples and h.mean_confidence < self.confidence_floor:
            return False
        latency_ceiling = self.route_timeouts.get(model, self.latency_ceiling_ms)
        if h.latencies_ms and h.mean_latency_ms > latency_ceiling:
            return False
        return True

    def choose(self, exclude: list[str] | None = None) -> RouteDecision:
        exclude = exclude or []
        bypassed: list[str] = []
        for model in self.priority:
            if model in exclude:
                bypassed.append(model)
                continue
            if self.is_healthy(model):
                reason = (
                    f"primary={model}"
                    if not bypassed
                    else f"failover_to={model} after {len(bypassed)} skipped"
                )
                return RouteDecision(chosen=model, reason=reason, bypassed=bypassed)
            bypassed.append(model)

        # All available models unhealthy — fall back to the highest priority model not excluded
        for model in self.priority:
            if model not in exclude:
                return RouteDecision(
                    chosen=model,
                    reason="all_models_unhealthy_falling_back_to_primary",
                    bypassed=bypassed,
                )

        raise RuntimeError(f"All priority models excluded. Excluded: {exclude}")

    def health_snapshot(self) -> dict[str, dict[str, float]]:
        return {
            m: {
                "mean_confidence": h.mean_confidence,
                "mean_latency_ms": h.mean_latency_ms,
                "error_count": h.error_count,
                "healthy": float(self.is_healthy(m)),
                "latency_ceiling_ms": self.route_timeouts.get(m, self.latency_ceiling_ms),
            }
            for m, h in self._health.items()
        }

    async def execute_with_fallback(self, func) -> Any:
        """
        Execute an async function that takes a model name as argument.
        If it raises an Exception (like 5xx, timeout), mark the model as error
        and failover to the next healthy model.
        """
        attempted: list[str] = []
        while True:
            if len(attempted) >= len(self.priority):
                raise RuntimeError(f"All models failed. Attempted: {attempted}")

            decision = self.choose(exclude=attempted)
            model = decision.chosen

            attempted.append(model)
            try:
                # Assuming the function accepts the chosen model name
                return await func(model)
            except Exception as exc:
                logger.warning("Model %s failed: %s. Failing over...", model, exc)
                self.observe(model, error=True)


__all__ = ["ModelRouter", "ModelHealth", "RouteDecision"]
