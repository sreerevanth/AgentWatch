"""System Health Monitoring & Metrics"""
from prometheus_client import Counter, Gauge, Histogram

# Metrics
agent_failures = Counter('agent_failures_total', 'Total agent failures')
api_latency = Histogram('api_latency_seconds', 'API latency')
system_health = Gauge('system_health', 'System health score 0-100')

def record_failure(agent_id: str):
    """Record agent failure."""
    agent_failures.labels(agent_id=agent_id).inc()

def record_api_latency(endpoint: str, latency_sec: float):
    """Record API latency."""
    api_latency.labels(endpoint=endpoint).observe(latency_sec)
