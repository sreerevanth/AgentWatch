<div align="center">

  <h1>AgentWatch</h1>

  <p><strong>Your AI agent is lying to you.<br/>AgentWatch catches it — before it deletes your database.</strong></p>

  <p>
    <img src="https://img.shields.io/badge/built_with-Python-blue?style=flat-square&logo=python" />
    <img src="https://img.shields.io/badge/status-live-brightgreen?style=flat-square" />
    <img src="https://img.shields.io/badge/license-Apache_2.0-blue?style=flat-square" />
    <img src="https://img.shields.io/badge/tests-47_passing-brightgreen?style=flat-square" />
    <img src="https://img.shields.io/github/stars/sreerevanth/AgentWatch?style=flat-square&color=gold" />
  </p>

</div>
---
CONTRIBUTORS AND SUPPORTORS PLEASE JOIN THE DISCORD 
-- https://discord.gg/n2RzUmZ4
---
<img width="1598" height="730" alt="image" src="https://github.com/user-attachments/assets/51d4d77a-d377-4235-8f9c-193e717f9a64" />

---

## The Crisis Nobody Is Talking About

1 in 20 AI agent requests fail in production right now — silently.

The system keeps running. The output looks correct. Nobody notices until
a customer complains, a database is corrupted, or an audit finds something
three weeks later.

76% of AI agent deployments fail within 90 days. Not because the models
are bad. Because nobody can see what the agent is doing while it's doing it.

Gartner says 40% of enterprise apps will have AI agents by end of 2026.
The same Gartner research says 40% of those projects will be cancelled by
2027 — specifically because of monitoring gaps.

The problem is not the model. The problem is that **an agent that
confidently fails is indistinguishable from an agent that correctly
succeeds** — unless you have a layer watching the reasoning, not just
the output.

That layer didn't exist.

**Until now.**

---

## What is AgentWatch?

AgentWatch is the first production observability layer built specifically
for AI agent reasoning — not just outputs.

It sits between your agent and the world. It watches every action, scores
every reasoning step with an independent model, blocks dangerous commands
before they run, and gives you a full replay of exactly what happened
and why.

57% of organizations run AI agents in production. Observability is the
lowest-rated part of their stack. Current tools were built for single
LLM calls — not multi-step agents that fail across 14 distinct failure
modes.

AgentWatch was built for the agent era.

---

## What It Does

| | |
|---|---|
| 🧠 **Reasoning Auditor** | Independent LLM scores every reasoning step — not just the output |
| 🛡️ **Safety Engine** | Blocks dangerous commands before they execute |
| 📊 **Live Dashboard** | Real-time trace of every action your agent takes |
| ⏪ **One-Click Rollback** | Git-backed checkpoints at every step |
| 💾 **Persistent Memory** | Cross-session episodic, semantic, and procedural memory |
| 💰 **Cost Tracker** | Per-session token budget with live spend alerts |
| 🔔 **Alerting** | Slack + PagerDuty when confidence drops or actions are blocked |
| 📋 **Compliance** | GDPR/HIPAA audit exports, RBAC governance |
| 🔌 **Universal** | Claude Code, LangChain, AutoGPT, OpenClaw — no rewrites |

---

## Quick Start

```bash
pip install agentwatch
docker compose up -d
```

Dashboard → http://localhost:3000
API → http://localhost:8000/docs

---

## Supported Agents

AgentWatch wraps your existing agent. You change nothing.

### Claude Code
```bash
agentwatch watch "Build me a REST API"
```

### LangChain
```python
from agentwatch.adapters.langchain import AgentWatchCallbackHandler

handler = AgentWatchCallbackHandler()
agent = AgentExecutor(agent=..., callbacks=[handler])
```

### AutoGPT
```python
from agentwatch.adapters.autogpt import AutoGPTAdapter

adapter = AutoGPTAdapter(session_id="session-1")
await adapter.on_action(action)
```

### OpenClaw
```python
from agentwatch.adapters.openclaw import OpenClawAdapter

adapter = OpenClawAdapter(session_id="session-1")
await adapter.on_skill_execution(skill_name, payload)
```

---

## The Reasoning Auditor

This is what nobody else has built.

Every agent scores its own work. And it almost always thinks it did
well — even when it didn't. The confidence is the problem, not the
failure.

AgentWatch deploys an independent model — architecturally separate,
no access to the agent's reasoning trace — whose only job is to find
failure before the next action fires.

```python
from agentwatch.reasoning.auditor import ReasoningAuditor

auditor = ReasoningAuditor()
result = await auditor.score_step(step)

print(result.confidence)          # 0.0 – 1.0
print(result.hallucination_risk)  # low / medium / high
print(result.goal_drift)          # True if agent is off-task
```

When confidence drops below your threshold, AgentWatch holds the next
action and fires an alert. Not after the damage. Before it.

---

## Safety Engine

```python
from agentwatch.core.safety import SafetyEngine

engine = SafetyEngine()
result = await engine.check_event(event)

if result.is_blocked:
    print(f"Blocked: {result.safety.reasons}")
    print(f"Risk level: {result.safety.risk_level.value}")
```

Blocked by default: `rm -rf /`, `curl | bash`, disk formatting,
credential exfiltration, and 40+ other critical patterns.

---

## Rollback

```bash
agentwatch rollback <session-id> --to-step 12
```

Or click rollback in the dashboard. Every checkpoint is a full
filesystem snapshot backed by git. Irreversible actions become
reversible.

---

## REST API

```
GET  /api/v1/sessions
GET  /api/v1/sessions/{id}/replay
GET  /api/v1/sessions/{id}/confidence
GET  /api/v1/sessions/{id}/checkpoints
POST /api/v1/sessions/{id}/rollback
GET  /api/v1/safety/blocked
GET  /api/v1/dashboard/summary
WS   /ws/events
```

---

## Stack

- **Backend** — FastAPI, PostgreSQL, Redis, Celery
- **Frontend** — Next.js, Tailwind, Recharts, WebSockets
- **Infra** — Docker Compose, GitHub Actions CI
- **Telemetry** — OpenTelemetry compatible

---

## Verified

```
✅ 47/47 tests passing
✅ docker compose up — zero errors
✅ API live at localhost:8000
✅ Dashboard live at localhost:3000
✅ Claude Code, LangChain, AutoGPT, OpenClaw adapters working
```

---

## License

Apache 2.0

---

<div align="center">
  <sub>Built by <a href="https://github.com/sreerevanth">sreerevanth</a> · Issues → open one</sub>
</div>
```

