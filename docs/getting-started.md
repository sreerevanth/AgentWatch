# Getting Started with AgentWatch

AgentWatch gives you a fast path from "clone the repo" to "watching your first agent session in the dashboard." This guide is written for a clean machine and uses the smallest working setup that matches the code in this repository.

## Before You Start

You will need:

- Python 3.12 or newer
- Docker Desktop or Docker Engine with the Docker Compose plugin
- A terminal open at the repository root

If you are on Windows, make sure Docker Desktop is running before you start the stack.

## 1. Installation

Install the Python package first:

```bash
python -m pip install agentwatch-ai
```

Start the local stack:

```bash
docker compose up -d
```

What this starts:

| Service | Port | Purpose |
| --- | --- | --- |
| PostgreSQL | 5432 | Stores sessions, events, checkpoints, and dashboard data |
| Redis | 6379 | Used by the background worker and queue |
| API | 8000 | REST API, WebSocket stream, and alerting hooks |
| Frontend | 3000 | The dashboard UI |

Optional tracing services are available too:

```bash
docker compose --profile tracing up -d
```

That adds Jaeger on:

- 16686 for the Jaeger UI
- 4317 and 4318 for OTLP ingest

### Environment Variables

For a local Docker setup, the compose file already injects the core backend values. If you need to run the API or frontend outside Docker, use these defaults:

```bash
DATABASE_URL=postgresql+asyncpg://agentwatch:agentwatch@localhost:5432/agentwatch
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
AGENTWATCH_ENV=production
AGENTWATCH_API_URL=http://localhost:8000
NEXT_PUBLIC_API_URL=/api/v1
```

### Docker Requirements

- Docker must be able to run Linux containers
- Compose must support the `docker compose` command
- The stack expects ports 3000, 5432, 6379, and 8000 to be free

If one of those ports is already in use, stop the conflicting process before starting AgentWatch.

## 2. Run the Demo

From the repository root, run:

```bash
python demo.py
```

Then open:

- http://localhost:3000

The demo script does three things:

1. Confirms the API is reachable
2. Registers a synthetic agent session
3. Streams events into the dashboard over the WebSocket feed

### What You Should See

In the terminal, you should see output like:

- API connectivity verified
- Session registered
- Live events streaming
- A blocked dangerous command, such as `rm -rf /var/log/*`
- A final success message showing the pipeline demo completed

In the dashboard, expect to see:

- A new session in the sessions table
- Live events appearing in real time
- One or more safety blocks
- Confidence and cost metrics updating

The demo also confirms the dashboard can receive events through the WebSocket stream at `/ws/events`.

### Common Troubleshooting

- If the demo says it cannot reach `http://localhost:8000`, the API container is not ready yet. Wait a few seconds and try again.
- If the dashboard is blank, confirm `docker compose up -d` completed successfully and refresh the page.
- If port 3000, 8000, 5432, or 6379 is already in use, stop the conflicting service and restart the stack.
- If the final WebSocket confirmation line mentions the `websockets` package, you can ignore it for a basic walkthrough, or install it with `python -m pip install websockets` and rerun the demo.

## 3. Connect Your First Agent

### Claude Code

The smallest working setup is to install AgentWatch and wrap your Claude Code command with the AgentWatch CLI:

```bash
agentwatch watch "Build me a REST API"
```

If you want to pin a model or change the safety policy, add options:

```bash
agentwatch watch "Build me a REST API" --model claude-opus-4-5 --policy default
```

What happens:

- AgentWatch captures the session
- Events appear in the live feed
- The session shows up in the sessions table
- Dangerous tool calls are blocked and logged

### LangChain

If you are using LangChain, install the LangChain extra first:

```bash
python -m pip install "agentwatch-ai[langchain]"
```

Then add the callback handler to your existing agent:

```python
from agentwatch.adapters.langchain import AgentWatchCallbackHandler
from langchain.agents import AgentExecutor

handler = AgentWatchCallbackHandler(session_id="my-first-session")

agent = AgentExecutor(
    agent=...,  # your existing LangChain agent
    tools=...,  # your existing tools
    callbacks=[handler],
)
```

If you are calling a runnable or model directly, pass `callbacks=[handler]` to that call in the same way.

For the least setup possible, keep your current LangChain code and only add the callback handler.

## 4. Understanding the Dashboard

Open http://localhost:3000 after running the demo or your own agent. The main dashboard is split into four parts:

### Live Event Feed

This is the real-time stream of agent activity. It shows session starts, planner output, tool calls, tool results, and blocked actions as they happen.

### Sessions Table

This table lists recent sessions with:

- Session ID
- Framework
- Status
- Event count
- Token usage
- Estimated cost
- Start time

Click a session row to open the session detail page.

### Safety Blocks

This panel shows commands that were blocked by policy, along with the reason they were stopped. It is the fastest way to verify that AgentWatch is intercepting risky actions.

### Confidence Trends

This chart shows recent session confidence scores. Use it to spot sessions that are drifting, unstable, or likely to fail.

### Tool Traces

Tool traces live on the session detail page. Open a session from the table to see the execution trace, expand individual steps, review commands and outputs, and inspect rollback options.

### Screenshot

![AgentWatch dashboard](https://github.com/user-attachments/assets/51d4d77a-d377-4235-8f9c-193e717f9a64)

## 5. Configure Alerts

AgentWatch can send alerts to Slack and PagerDuty when risky activity is detected.

### Slack Webhook

Create a Slack incoming webhook and add it to your environment:

```bash
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/xxx/yyy/zzz
```

### Optional PagerDuty Webhook

If you also want PagerDuty notifications:

```bash
PAGERDUTY_WEBHOOK_URL=https://events.pagerduty.com/v2/enqueue
```

### Example `.env`

If you are running outside Docker Compose, create a `.env` file at the repository root:

```bash
DATABASE_URL=postgresql+asyncpg://agentwatch:agentwatch@localhost:5432/agentwatch
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
AGENTWATCH_ENV=production
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/xxx/yyy/zzz
PAGERDUTY_WEBHOOK_URL=https://events.pagerduty.com/v2/enqueue
```

### Enable Notifications

1. Add the webhook URL(s).
2. Restart the API so it picks up the new environment.
3. Trigger a blocked or high-risk action, such as the demo command that tries to delete `/var/log`.
4. Confirm the alert arrives in Slack, and PagerDuty if configured.

AgentWatch sends Slack alerts for any configured webhook and pages to PagerDuty only when the event risk meets the default high-risk threshold.

## Fast Check

When everything is working, you should be able to complete this flow in order:

1. Install `agentwatch-ai`
2. Start the stack with `docker compose up -d`
3. Run `python demo.py`
4. Open http://localhost:3000
5. See a live session, a safety block, and a confidence chart update

If you get stuck, start by checking whether the API is healthy at http://localhost:8000/health.
