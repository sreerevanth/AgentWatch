# Optimized Alert Routing & Suppression (ELUSoC_2026)

## Background
In large-scale agentic deployments, alert fatigue quickly becomes a major bottleneck if every warning routes to high-urgency channels (like PagerDuty), or if repeated/looping agent events flood system admins with duplicate alerts.

## Solution
AgentWatch incorporates an **Alerting Router** and **Alerting Filter** directly inside the alerting loop:
1. **Dynamic Routing**: Divides event processing between channels (e.g. low-risk to Slack, critical/blocked actions to PagerDuty + Slack).
2. **Alert Suppression**: Detects repeating identical alerts in the same agent execution sequence and deduplicates them using rolling window keys.

## Components
- **`agentwatch/alerting/router.py`**: Declares `AlertRouter` destination calculations.
- **`agentwatch/alerting/filters.py`**: Declares rolling duplicate filters.
