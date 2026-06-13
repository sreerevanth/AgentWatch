"""System Health Monitoring & Metrics

Prometheus-based metrics collection for comprehensive system health monitoring
and alerting on agent failures, API latency, and system health.
"""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

# Prometheus metrics
agent_failures = Counter(
    "agent_failures_total",
    "Total agent failures",
    labelnames=["agent_id"],
)
api_latency = Histogram(
    "api_latency_seconds",
    "API request latency in seconds",
    labelnames=["endpoint"],
)
system_health = Gauge(
    "system_health",
    "System health score 0-100",
)


def record_failure(agent_id: str) -> None:
    """Record agent failure metric.

    Args:
        agent_id: The agent identifier
    """
    agent_failures.labels(agent_id=agent_id).inc()


def record_api_latency(endpoint: str, latency_sec: float) -> None:
    """Record API request latency metric.

    Args:
        endpoint: The API endpoint path
        latency_sec: Request latency in seconds
    """
    api_latency.labels(endpoint=endpoint).observe(latency_sec)
