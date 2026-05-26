<div align="center">

<img src="https://img.shields.io/badge/AgentWatch-v0.1.0-black?style=for-the-badge" />

# AgentWatch

### Your AI agent is lying to you.
### AgentWatch catches it — before it deletes your database.

<br/>

[![Tests](https://img.shields.io/badge/tests-47_passing-brightgreen?style=flat-square)](https://github.com/sreerevanth/AgentWatch)
[![License](https://img.shields.io/badge/license-Apache_2.0-blue?style=flat-square)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-blue?style=flat-square&logo=python)](https://python.org)
[![Discord](https://img.shields.io/badge/Discord-Join_Community-5865F2?style=flat-square&logo=discord)](https://discord.gg/n2RzUmZ4)
[![Stars](https://img.shields.io/github/stars/sreerevanth/AgentWatch?style=flat-square&color=gold)](https://github.com/sreerevanth/AgentWatch/stargazers)
[![Forks](https://img.shields.io/github/forks/sreerevanth/AgentWatch?style=flat-square&color=orange)](https://github.com/sreerevanth/AgentWatch/network)
[![NSoC](https://img.shields.io/badge/NSoC_26'-participating-purple?style=flat-square)](https://github.com/sreerevanth/AgentWatch/issues)

<br/>

```
pip install agentwatch
agentwatch watch "your agent command"
```

*One command. Every failure caught. Before it runs.*

<br/>

[**Quick Start**](#quick-start) · [**How It Works**](#how-it-works) · [**Supported Frameworks**](#supported-frameworks) · [**Discord**](https://discord.gg/n2RzUmZ4) · [**Contribute**](#contributing)

</div>

---

## The Problem Nobody Is Solving

```
Agent runs.
Output looks correct.
Database is corrupted.
You find out 3 hours later when a customer complains.
```

**1 in 20 AI agent requests fail silently in production.**

Current observability tools — Langfuse, Phoenix, Datadog — tell you what happened *after* it happened. By then the damage is done.

The real problem: **an agent that confidently fails is indistinguishable from an agent that correctly succeeds.** 

Unless you have a layer watching the *reasoning*, not just the output.

That layer didn't exist.

**Until now.**

---

## How It Works

AgentWatch sits between your agent and the world.

```
Your Agent
    │
    ▼
┌─────────────────────────────────────┐
│           AgentWatch                │
│                                     │
│  1. Captures every reasoning step   │
│  2. Independent model scores it     │
│  3. Blocks dangerous actions        │
│  4. Fires alert if confidence drops │
│  5. Checkpoints for rollback        │
└─────────────────────────────────────┘
    │
    ▼
 The World (tools, APIs, databases)
```

The key insight: **an agent scoring its own reasoning is structurally biased toward overconfidence.** It almost always thinks it did well — even when it didn't.

AgentWatch deploys a second model, architecturally separate, with no access to the agent's own reasoning trace. Its only job: find failure before the next action fires.

---

## Quick Start

```bash
# Install
pip install agentwatch

# Start the dashboard
docker compose up -d

# Wrap your agent
agentwatch watch "Build me a REST API"
```

**Dashboard** → http://localhost:3000  
**API Docs** → http://localhost:8000/docs

That's it. Zero config. Real data immediately.

---

## Supported Frameworks

AgentWatch wraps your existing agent. **You change nothing.**

<details>
<summary><b>Claude Code</b></summary>

```bash
agentwatch watch "Build me a REST API"
```
</details>

<details>
<summary><b>LangChain</b></summary>

```python
from agentwatch.adapters.langchain import AgentWatchCallbackHandler

handler = AgentWatchCallbackHandler()
agent = AgentExecutor(agent=..., callbacks=[handler])
```
</details>

<details>
<summary><b>CrewAI</b></summary>

```python
from agentwatch.adapters.crewai import AgentWatchCrewAdapter

adapter = AgentWatchCrewAdapter(crew=my_crew)
await adapter.run()
```
</details>

<details>
<summary><b>AutoGPT</b></summary>

```python
from agentwatch.adapters.autogpt import AutoGPTAdapter

adapter = AutoGPTAdapter(session_id="session-1")
await adapter.on_action(action)
```
</details>

<details>
<summary><b>LangGraph</b></summary>

```python
from agentwatch.adapters.langgraph import AgentWatchLangGraphAdapter

adapter = AgentWatchLangGraphAdapter(graph=my_graph)
result = await adapter.run(input)
```
</details>

<details>
<summary><b>AutoGen</b></summary>

```python
from agentwatch.adapters.autogen import AgentWatchAutoGenAdapter

adapter = AgentWatchAutoGenAdapter(agents=agent_list)
await adapter.run(task)
```
</details>

<details>
<summary><b>Universal one-liner (any framework)</b></summary>

```python
from agentwatch import watch

agent = watch(your_agent)  # auto-detects framework
```
</details>

---

## Core Features

### 🧠 Reasoning Auditor
The feature nobody else has built.

```python
from agentwatch.reasoning.auditor import ReasoningAuditor

auditor = ReasoningAuditor()
result = await auditor.score_step(step)

print(result.confidence)          # 0.0 – 1.0
print(result.hallucination_risk)  # low / medium / high  
print(result.goal_drift)          # True if agent is off-task
```

When confidence drops below your threshold, the next action is **held** — not logged after the fact. An alert fires. You decide what happens next.

---

### 🛡️ Safety Engine

```python
from agentwatch.core.safety import SafetyEngine

engine = SafetyEngine()
result = await engine.check_event(event)

if result.is_blocked:
    print(f"Blocked: {result.safety.reasons}")
    print(f"Risk level: {result.safety.risk_level.value}")
```

**Blocked by default:**
- `rm -rf /` · `curl | bash` · disk formatting
- Credential exfiltration · `DROP TABLE`
- Mass deletion · privilege escalation
- 40+ additional critical patterns

**Pre-execution. Not post-hoc logging.**

---

### ⏪ One-Click Rollback

```bash
agentwatch rollback <session-id> --to-step 12
```

Every step is a git-backed filesystem snapshot. Irreversible actions become reversible. Click rollback in the dashboard or use the CLI.

---

### 📊 Live Dashboard

Real-time WebSocket stream of every action your agent takes. Confidence meter updating per step. Colour-coded by span type. No polling. No refresh.

---

### 💾 Persistent Memory

Cross-session episodic, semantic, and procedural memory. Your agent remembers what it decided and why — across restarts, across sessions.

---

### 💰 Cost Intelligence

Per-session token budget with hard stop. Real-time spend tracking. Alerts at 80%. Blocks at 100%. Prevents runaway agents from bankrupting you overnight.

---

### 🔔 Alerting

Slack + PagerDuty when confidence drops or actions are blocked. Every alert contains full context — not just "something failed."

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

Full Swagger docs at `localhost:8000/docs`

---

## What Nobody Else Has Built

| Feature | AgentWatch | Langfuse | Phoenix | Datadog |
|---------|:----------:|:--------:|:-------:|:-------:|
| Pre-execution blocking | ✅ | ❌ | ❌ | ❌ |
| Independent reasoning auditor | ✅ | ❌ | ❌ | ❌ |
| Git-backed rollback | ✅ | ❌ | ❌ | ❌ |
| Session replay | ✅ | ❌ | ✅ | ⚠️ |
| Cross-session memory | ✅ | ❌ | ❌ | ❌ |
| Goal drift detection | ✅ | ❌ | ❌ | ❌ |
| Hallucination risk per step | ✅ | ❌ | ❌ | ❌ |

---

## Stack

| Layer | Tech |
|-------|------|
| Backend | FastAPI · PostgreSQL · Redis · Celery |
| Frontend | Next.js · Tailwind · Recharts · WebSockets |
| Infra | Docker Compose · GitHub Actions CI |
| Telemetry | OpenTelemetry compatible |

---

## Verified

```
✅ 47/47 tests passing
✅ docker compose up — zero errors  
✅ API live at localhost:8000
✅ Dashboard live at localhost:3000
✅ Claude Code, LangChain, CrewAI, AutoGPT adapters working
```

---

## Contributing

AgentWatch is built in the open. Contributors get their name on the landing page after their first merged PR.

**Before you start → join the Discord:** https://discord.gg/n2RzUmZ4

Get help picking the right issue, discuss your approach, and ship faster.

```bash
git clone https://github.com/sreerevanth/AgentWatch
cd AgentWatch
docker compose up -d
pip install -e ".[dev]"
pytest tests/
```

Browse [open issues](https://github.com/sreerevanth/AgentWatch/issues) — tagged by difficulty: `good first issue` · `intermediate` · `advanced`

---

## Roadmap

AgentWatch v0.2.0 is being built now — 90 features across 10 phases including:

- Causal memory graph (cross-session reasoning trails)
- Inter-agent causal DAG (multi-agent failure tracing)  
- OWASP Agentic Top 10 scanner
- EU AI Act Article 15 compliance package
- Counterfactual replay ("what if step 3 was different")
- Open reasoning trace schema (the OTEL play)

Every open issue on the roadmap is available to contributors. [Browse them here.](https://github.com/sreerevanth/AgentWatch/issues)

---

## Community

💬 **Discord** — discord.gg/n2RzUmZ4  
Contributors discuss issues, get unblocked, and ship together.  
Your name on the landing page after your first PR merges.

---

## License

Apache 2.0 — use it, fork it, build on it.

---

<div align="center">

Built by [sreerevanth](https://github.com/sreerevanth)

**[⭐ Star it](https://github.com/sreerevanth/AgentWatch) · [🐛 Open an issue](https://github.com/sreerevanth/AgentWatch/issues) · [💬 Join Discord](https://discord.gg/n2RzUmZ4)**

</div>
