<div align="center">

<img src="https://img.shields.io/badge/AgentWatch-v0.2.0-black?style=for-the-badge" alt="AgentWatch v0.2.0" />

# AgentWatch

<img width="130" height="130" alt="AgentWatch logo" src="https://github.com/user-attachments/assets/4e6fd818-2458-4ac2-bb9c-25542622dd00" />

**Your AI agent is lying to you.**
**AgentWatch catches it — before it deletes your database.**

<br/>

[![Tests](https://img.shields.io/badge/tests-205_passing-brightgreen?style=flat-square)](https://github.com/sreerevanth/AgentWatch)
[![Coverage](https://img.shields.io/codecov/c/github/sreerevanth/AgentWatch?style=flat-square)](https://codecov.io/gh/sreerevanth/AgentWatch)
[![License](https://img.shields.io/badge/license-Apache_2.0-blue?style=flat-square)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-blue?style=flat-square&logo=python)](https://python.org)
[![Discord](https://img.shields.io/badge/Discord-Join_Community-5865F2?style=flat-square&logo=discord)](https://discord.gg/n2RzUmZ4)
[![Stars](https://img.shields.io/github/stars/sreerevanth/AgentWatch?style=flat-square&color=gold)](https://github.com/sreerevanth/AgentWatch/stargazers)
[![Forks](https://img.shields.io/github/forks/sreerevanth/AgentWatch?style=flat-square&color=orange)](https://github.com/sreerevanth/AgentWatch/network)
[![NSoC](https://img.shields.io/badge/NSoC_26'-participating-purple?style=flat-square)](https://github.com/sreerevanth/AgentWatch/issues)

<br/>

```
pip install agentwatch-ai
agentwatch watch "your agent command"
```

*One command. Every failure caught. Before it runs.*

<br/>

[**Quick Start**](#-quick-start) · [**How It Works**](#-how-it-works) · [**Architecture**](#-architecture) · [**Frameworks**](#-supported-frameworks) · [**Discord**](https://discord.gg/n2RzUmZ4) · [**Contribute**](#-contributing)

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

Current observability tools — Langfuse, Phoenix, Datadog — tell you *what happened* **after** it happened. By then the damage is done.

The real problem: **an agent that confidently fails is indistinguishable from an agent that correctly succeeds** — unless you have a layer watching the *reasoning*, not just the output.

That layer didn't exist. **Until now.**

| The cost of silent failure | |
|---|---|
| **1 in 20** | agent requests fail silently |
| **40%** | of enterprise AI projects cancelled by 2027 *(Gartner)* |
| **76%** | of agent deployments fail within 90 days |

---

## 💡 How It Works

AgentWatch sits **between your agent and the world**, intercepting every action *before* it executes.

```mermaid
flowchart LR
    A["🤖 Your Agent"] --> AW

    subgraph AW["🛡️ AgentWatch"]
        direction TB
        S1["1 . Capture<br/>every reasoning step"]
        S2["2 . Score<br/>independent model audit"]
        S3["3 . Block<br/>dangerous actions pre-execution"]
        S1 --> S2 --> S3
    end

    AW -->|"✅ allowed"| W["🌍 The World<br/>tools · APIs · databases"]
    AW -.->|"⛔ blocked"| X["🚫 Action vetoed<br/>+ alert fired"]

    style A fill:#1e293b,stroke:#3ecf8e,color:#fff
    style AW fill:#0f172a,stroke:#3ecf8e,color:#fff
    style W fill:#1e293b,stroke:#3ecf8e,color:#fff
    style X fill:#3b1212,stroke:#ef4444,color:#fff
```

**The key insight:** an agent scoring its own reasoning is structurally biased toward overconfidence. It almost always thinks it did well — even when it didn't.

AgentWatch deploys a **second model**, architecturally separate, with no access to the agent's own reasoning trace. Its only job: **find failure before the next action fires.**

---

## 📸 Screenshots

<div align="center">

<table>
  <tr>
    <td width="50%" align="center" valign="top">
      <img src="docs/screenshots/01-hero.png" alt="AgentWatch landing page — your AI agent is lying to you, AgentWatch catches it" /><br/>
      <sub><b>Pre-execution blocking, not post-hoc logging.</b><br/>A blocked <code>rm -rf /tmp/*</code> with live confidence (0.18) and blast-radius (HIGH) read out before it ever runs.</sub>
    </td>
    <td width="50%" align="center" valign="top">
      <img src="docs/screenshots/02-how-it-works.png" alt="Pre-execution blocking flow: Your Agent to AgentWatch to The World" /><br/>
      <sub><b>Your Agent → AgentWatch → The World.</b><br/>Capture every reasoning step, score it with an independent model, block dangerous actions before they run.</sub>
    </td>
  </tr>
  <tr>
    <td width="50%" align="center" valign="top">
      <img src="docs/screenshots/03-features.png" alt="Six production-grade modules" /><br/>
      <sub><b>Six production-grade modules.</b><br/>Reasoning Auditor · Safety Engine · One-Click Rollback · Multi-Agent DAG · Causal Memory · Compliance Ready.</sub>
    </td>
    <td width="50%" align="center" valign="top">
      <img src="docs/screenshots/04-comparison.png" alt="AgentWatch vs Langfuse, Phoenix, Datadog — and the 60-second quickstart" /><br/>
      <sub><b>What nobody else ships.</b><br/>Pre-execution blocking, independent audit, git-backed rollback — and it wraps any agent framework in 60 seconds.</sub>
    </td>
  </tr>
</table>

</div>

---

## 🏗️ Architecture

AgentWatch is built as a layered system — adapters feed a normalized event stream into the core engine, which fans out to safety, reasoning, rollback, and observability subsystems.

```mermaid
flowchart TB
    subgraph ADAPTERS["🔌 Framework Adapters"]
        direction LR
        LC["LangChain"]
        CR["CrewAI"]
        AG["AutoGPT"]
        CC["Claude Code"]
        LG["LangGraph"]
        AU["AutoGen"]
    end

    ADAPTERS --> BUS["📡 Event Bus<br/>normalized AgentEvent stream"]

    BUS --> CORE

    subgraph CORE["⚙️ Core Engine"]
        direction TB
        SAFE["🛡️ Safety Engine<br/>40+ patterns · blast radius"]
        REASON["🧠 Reasoning Auditor<br/>independent scoring"]
        SAFE --- REASON
    end

    CORE --> ROLL["⏪ Rollback<br/>git-backed checkpoints"]
    CORE --> MEM["💾 Causal Memory<br/>cross-session trails"]
    CORE --> COST["💰 Cost Governance<br/>per-session budgets"]
    CORE --> GOV["📋 Compliance<br/>GDPR · HIPAA · EU AI Act"]

    CORE --> TEL["🔭 Telemetry<br/>OpenTelemetry spans"]
    TEL --> API["🌐 REST + WebSocket API"]
    API --> DASH["📊 Live Dashboard<br/>Next.js"]

    style ADAPTERS fill:#0f172a,stroke:#64748b,color:#fff
    style CORE fill:#0f172a,stroke:#3ecf8e,color:#fff
    style BUS fill:#1e293b,stroke:#3ecf8e,color:#fff
    style API fill:#1e293b,stroke:#3ecf8e,color:#fff
    style DASH fill:#1e293b,stroke:#3ecf8e,color:#fff
```

---

## 🔐 Security Pipeline

Every `TOOL_CALL` event runs the full gauntlet before it is ever allowed to touch the outside world. Blocking happens **pre-execution** — not as a post-hoc log entry.

```mermaid
flowchart TD
    EV["📥 TOOL_CALL event"] --> CHK{"event is<br/>a tool call?"}
    CHK -->|no| PASS["↩️ pass through unchanged"]
    CHK -->|yes| AUDIT["🧠 Reasoning audit<br/>confidence score 0.0 – 1.0"]

    AUDIT --> MATCH["🔍 Pattern match<br/>40+ risk patterns"]
    MATCH --> NORM["🧹 Intent normalizers<br/>rm · disk · perms · RCE pipe"]
    NORM --> BLAST["💥 Blast-radius estimate"]

    BLAST --> DECIDE{"policy<br/>decision"}
    DECIDE -->|block| BLOCK["⛔ BLOCKED<br/>status set · alert fired"]
    DECIDE -->|approval| HITL{"human<br/>approves?"}
    DECIDE -->|allow| ALLOW["✅ ALLOWED<br/>action proceeds"]

    HITL -->|yes| ALLOW
    HITL -->|no / no callback| BLOCK

    style EV fill:#1e293b,stroke:#3ecf8e,color:#fff
    style BLOCK fill:#3b1212,stroke:#ef4444,color:#fff
    style ALLOW fill:#0f2a18,stroke:#3ecf8e,color:#fff
    style HITL fill:#2a230f,stroke:#eab308,color:#fff
```

**Blocked by default:** `rm -rf /` · `curl | bash` · disk formatting · credential exfiltration · `DROP TABLE` · mass deletion · privilege escalation · **40+ additional critical patterns.**

The intent normalizers are what make this robust — they catch bypass attempts the naive regex misses: split flags (`rm -r -f /`), long-form flags (`rm --recursive --force /`), and reordered fetch-then-interpret RCE chains.

---

## 🔄 Reasoning Audit Sequence

The independent auditor scores each step *before* the action runs. A drop below threshold holds the next action and fires an alert — it is never logged after the fact.

```mermaid
sequenceDiagram
    participant Agent
    participant AgentWatch
    participant Auditor as Independent Auditor
    participant World as Tools / APIs / DB

    Agent->>AgentWatch: emit reasoning step + tool call
    AgentWatch->>Auditor: score_step(step)
    Auditor-->>AgentWatch: confidence · hallucination risk · goal drift

    alt confidence below threshold
        AgentWatch--xAgent: HOLD action + fire alert
        Note over AgentWatch: human decides next move
    else confidence ok
        AgentWatch->>World: action proceeds
        World-->>Agent: result
        AgentWatch->>AgentWatch: checkpoint for rollback
    end
```

---

## 🚀 Quick Start

```bash
# Install
pip install agentwatch-ai

# Configure environment variables (optional)
# Copy the template and edit it to set custom DB passwords, API keys, etc.
cp .env.example .env

# Start the dashboard
docker compose up -d

# Wrap your agent
agentwatch watch "Build me a REST API"
```

**Dashboard** → http://localhost:3000
**API Docs** → http://localhost:8000/docs

That's it. Zero config for default settings, or customize via the [.env.example](.env.example) file. Real data immediately.

---

## 🔌 Supported Frameworks

AgentWatch wraps your existing agent. **You change nothing.** Detailed guides for each framework live in the [`docs/adapters/`](docs/adapters/) directory.

| Framework | Adapter | Framework | Adapter |
|---|---|---|---|
| 🦜 **LangChain** | ✅ | 🔗 **LangGraph** | ✅ |
| 👥 **CrewAI** | ✅ | 🤖 **AutoGen** | ✅ |
| ⚡ **AutoGPT** | ✅ | 🧩 **smolagents** | ✅ |
| 🖥️ **Claude Code** | ✅ | 🌐 **Universal one-liner** | ✅ |

---

## ✨ Core Features

### 🧠 Reasoning Auditor
*The feature nobody else has built.*

```python
from agentwatch.reasoning.auditor import ReasoningAuditor

auditor = ReasoningAuditor()
audit = await auditor.audit_step(step.step_number, step)

print(audit.score)        # 0.0 – 1.0 confidence in the step
print(audit.rationale)    # why the auditor scored it this way
```

When the score drops below your threshold, the next action is **held — not logged after the fact.** An alert fires. You decide what happens next.

### 🛡️ Safety Engine

```python
from agentwatch.core.safety import SafetyEngine
from agentwatch.core.schema import ExecutionStatus

engine = SafetyEngine()
checked = await engine.check_event(event)

if checked.status == ExecutionStatus.BLOCKED:
    print(f"Blocked: {checked.safety.reasons}")
    print(f"Risk level: {checked.safety.risk_level.value}")
```

Blocks **40+ dangerous patterns pre-execution**, not post-hoc logging.

### ⏪ One-Click Rollback

```bash
agentwatch rollback <session-id> --to-step 12
```

Every step is a **git-backed filesystem snapshot.** Irreversible actions become reversible. Click rollback in the dashboard or use the CLI.

### 📊 Live Dashboard
Real-time WebSocket stream of every action your agent takes. Confidence meter updating per step. Colour-coded by span type. No polling. No refresh.

### 💾 Persistent Memory
Cross-session episodic, semantic, and procedural memory backed by a causal graph. Your agent remembers what it decided and *why* — across restarts, across sessions.

### 💰 Cost Intelligence
Per-session token budget with hard stop. Real-time spend tracking. Alerts at 80%. Blocks at 100%. Prevents runaway agents from bankrupting you overnight.

### 🔔 Alerting
Slack + PagerDuty when confidence drops or actions are blocked. Every alert contains full context — not just "something failed."

---

## 🌐 REST API

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

Full Swagger docs at `localhost:8000/docs`.

---

## 🏆 What Nobody Else Has Built

| Feature | AgentWatch | Langfuse | Phoenix | Datadog |
|---|:---:|:---:|:---:|:---:|
| Pre-execution blocking | ✅ | ❌ | ❌ | ❌ |
| Independent reasoning auditor | ✅ | ❌ | ❌ | ❌ |
| Git-backed rollback | ✅ | ❌ | ❌ | ❌ |
| Inter-agent causal DAG | ✅ | ❌ | ❌ | ❌ |
| Cross-session memory | ✅ | ❌ | ❌ | ❌ |
| Session replay | ✅ | ❌ | ✅ | ⚠️ |
| Goal drift detection | ✅ | ❌ | ❌ | ❌ |
| Hallucination risk per step | ✅ | ❌ | ❌ | ❌ |

---

## 🧱 Stack

| Layer | Tech |
|---|---|
| **Backend** | FastAPI · PostgreSQL · Redis · Celery |
| **Frontend** | Next.js · Tailwind · Recharts · WebSockets |
| **Infra** | Docker Compose · GitHub Actions CI |
| **Telemetry** | OpenTelemetry compatible |

---

## ✅ Verified

- **205/205 tests passing**
- `docker compose up` — zero errors
- API live at `localhost:8000`
- Dashboard live at `localhost:3000`
- Claude Code, LangChain, CrewAI, AutoGPT adapters working

---

## 🤝 Contributing

AgentWatch is built in the open. **Contributors get their name on the landing page after their first merged PR.**

```mermaid
flowchart LR
    A["💬 Join Discord<br/>discuss your approach"] --> B["🔍 Pick an issue<br/>good first · intermediate · advanced"]
    B --> C["🔨 Build<br/>fork · branch · code"]
    C --> D["✅ Open PR<br/>auto-tested by CI"]
    D --> E["🎉 Merge<br/>your name on the landing page"]

    style A fill:#0f172a,stroke:#5865F2,color:#fff
    style B fill:#0f172a,stroke:#3ecf8e,color:#fff
    style C fill:#0f172a,stroke:#3ecf8e,color:#fff
    style D fill:#0f172a,stroke:#3ecf8e,color:#fff
    style E fill:#0f2a18,stroke:#3ecf8e,color:#fff
```

**Before you start** → join the [Discord](https://discord.gg/n2RzUmZ4). Get help picking the right issue, discuss your approach, and ship faster.

### Local Backend Setup

```bash
git clone https://github.com/sreerevanth/AgentWatch
cd AgentWatch
docker compose up -d
pip install -e ".[dev]"
pytest tests/
```

### Local Frontend Dashboard Setup

```bash
cd frontend
npm install
npm run dev
```

The dashboard will be live at `http://localhost:3000`.

Every PR to `main` is automatically tested by the **test-on-pr** workflow, which runs the suite with coverage and posts the results as a PR comment.

---

## 📦 Release Process

Releases publish to PyPI automatically via the **publish-pypi** workflow whenever a version tag is pushed:

```bash
# Bump [project].version in pyproject.toml to match the tag first, then:
git tag v0.X.Y
git push origin v0.X.Y
# PyPI publishes automatically.
```

On a `v*` tag the workflow verifies the tag matches `pyproject.toml` (failing fast on a mismatch), builds the wheel + sdist, runs `twine check`, uploads with `twine`, and creates a GitHub Release titled **AgentWatch v0.X.Y** — notes pulled from `CHANGELOG.md`, with the `.whl` and `.tar.gz` attached.

### One-time setup — add the PyPI token

The upload step authenticates with a PyPI API token stored as a GitHub secret named `PYPI_TOKEN`:

1. Create a token at pypi.org → Account settings → API tokens (scope it to this project).
2. In the repo: Settings → Secrets and variables → Actions → New repository secret.
3. Name it `PYPI_TOKEN` and paste your `pypi-...` token as the value.

---

## 🗺️ Roadmap

AgentWatch **v0.2.0** is being built now — 90 features across 10 phases including:

- Causal memory graph (cross-session reasoning trails)
- Inter-agent causal DAG (multi-agent failure tracing)
- OWASP Agentic Top 10 scanner
- EU AI Act Article 15 compliance package
- Counterfactual replay ("what if step 3 was different")
- Open reasoning trace schema (the OTEL play)

Every open issue on the roadmap is available to contributors. [Browse them here.](https://github.com/sreerevanth/AgentWatch/issues)

---

## 💬 Community

**Discord** — [discord.gg/n2RzUmZ4](https://discord.gg/n2RzUmZ4)

Contributors discuss issues, get unblocked, and ship together. Your name on the landing page after your first PR merges.

---

## 📄 License

**Apache 2.0** — use it, fork it, build on it.

<div align="center">

Built by [sreerevanth](https://github.com/sreerevanth)

⭐ **Star it** · 🐛 [**Open an issue**](https://github.com/sreerevanth/AgentWatch/issues) · 💬 [**Join Discord**](https://discord.gg/n2RzUmZ4)

</div>
