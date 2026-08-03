# AgentWatch Architecture

## Overview

AgentWatch is the reliability, safety, and observability layer for AI agents. It sits between your agent and the world — intercepting agent decisions, evaluating them against safety policies, and recording everything to an immutable audit trail.

## High-level Data Flow

```
┌─────────────┐     watch()     ┌────────────┐     commit decision    ┌──────────────┐
│  Your Agent │ ──────────────► │ AgentWatch │ ────────────────────► │ Decision Log  │
│  (LLM/host) │ ◄────────────── │  API / SDK │ ◄──────────────────── │ (PostgreSQL)  │
└─────────────┘   safety score  └────────────┘   audit trail          └──────────────┘
                                        │
                        ┌───────────────┼───────────────┐
                        ▼               ▼               ▼
                  ┌──────────┐  ┌────────────┐  ┌───────────┐
                  │ Redis    │  │ Celery     │  │ Prometheus│
                  │ (cache / │  │ (async     │  │ (metrics) │
                  │  pubsub) │  │  alerts)   │  │           │
                  └──────────┘  └────────────┘  └───────────┘
```

1. Your agent calls `agentwatch.watch()` before taking an action.
2. AgentWatch evaluates the request through **three safety lattices** (see below).
3. The result — pass/block/advisory — is returned to your agent.
4. Every decision, session, and event is written to PostgreSQL and emitted via Redis pubsub.
5. Background Celery workers handle alerts, cost tracking, and long-running analyses.

## The Three Safety Lattices (v2)

AgentWatch v2 introduces a layered safety architecture where each lattice operates at a different level of abstraction:

| Lattice | What it checks | Example |
|---|---|---|
| **Capability Lattice** | What the agent is allowed to _do_ | "Can it read this file? Can it call this API?" |
| **State Lattice** | What state the agent is _in_ right now | "Is the agent confused? Is it stuck in a loop?" |
| **Cognitive Lattice** | How the agent is *thinking* | "Is attention scattering? Is reasoning degrading?" |

The **Capability Lattice** blocks structurally invalid actions. The **State Lattice** detects anomalies like recursion, excessive memory growth, or silent failures. The **Cognitive Lattice** (Phase 4) will detect attention scatter and reasoning degradation.

## Monorepo Structure

```
agentwatch/                # Python package (the product)
├── agentwatch/
│   ├── api/               # FastAPI REST server (single-file: server.py)
│   ├── adapters/           # LangChain, AutoGPT, OpenClaw wrappers
│   ├── alerting/           # Alert dispatch, channels (email, Slack, webhook)
│   ├── circuit_breaker/    # Rate-based circuit breaking for model routing
│   ├── cli/                # Typer CLI (`agentwatch audit`, `agentwatch compliance`)
│   ├── core/               # Domain model — AgentSession, AgentEvent, TokenUsage
│   ├── cost/               # CostTracker — token budgets, session TTL
│   ├── eval/               # Eval runner — offline batch evaluation against policies
│   ├── governance/         # GDPR erasure, compliance audit log
│   ├── hitl/               # Human-in-the-loop — approval queues
│   ├── infrastructure/     # DB connection pool, migrations, Redis client
│   ├── lattice/            # v2 lattice framework (ShadowFilesystem, policy engine)
│   ├── memory/             # ForgettingEngine, TemporalDecayManager
│   ├── monitoring/         # SilenceBaseline, SilentFailureDetector
│   ├── orchestration/      # Workflow scheduler, DAG execution
│   ├── reasoning/          # ReasoningAuditor (v1 advisory → v2 deprecation)
│   ├── rollback/           # Snapshots and restore
│   ├── scoring/            # Policy scoring engine
│   ├── security/           # Input sanitisation, output validation
│   ├── telemetry/          # OpenTelemetry traces + spans
│   └── validation/         # Event schema validation
├── tests/                  # pytest suite (70% coverage gate)
├── frontend/               # Dashboard UI (Next.js 14, React 18, Tailwind 3)
├── agentwatch-landing/     # Public landing page (Next.js 16, React 19, GSAP, Three.js)
├── benchmarks/             # Benchmark runner + reference artefacts
├── Dockerfile.api           # Python API + Celery worker base image
├── docker-compose.yml       # pgvector, Redis, API, worker, frontend, optional Jaeger
└── pyproject.toml           # hatchling build, ruff, mypy, pytest config
```

## Key API Endpoints

The FastAPI server in `agentwatch/api/server.py` serves the REST API at `/api/v1/`. Core endpoints:

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/v1/system/status` | Cluster health — DB, Redis, active sessions |
| `GET` | `/health` | Minimal liveness probe |
| `POST` | `/api/v1/sessions/watch` | Start watching an agent session |
| `POST` | `/api/v1/sessions/close` | Close a session, emit final budget |
| `GET` | `/api/v1/sessions/{id}` | Get session + all events |
| `GET` | `/api/v1/sessions` | List sessions (dashboard summary) |
| `GET` | `/api/v1/compliance/audit` | Compliance audit log (CSV export) |
| `DELETE` | `/api/v1/gdpr/erase` | Right-to-be-forgotten (tenant-bound) |

### WebSocket

Clients connect to `/ws/events` for real-time event streaming. The server fans out every `AgentEvent` the moment it's recorded — used by the dashboard's live feed and external monitoring tools.

## Database Schema

PostgreSQL (pgvector enabled). Core tables:

- `agent_sessions` — session ID, agent model, metadata, user_id, tenant_id, batch_id, timestamps.
- `agent_events` — event type (decision / tool_use / error), JSON payload, session_id FK, token usage, latency.
- `cost_budgets` — budget caps per agent/session (token limit, time limit).
- `audit_records` — compliance audit log (action, old value, new value, admin user).
- `tenant_erasure_keys` — per-tenant crypto keys for GDPR right-to-forget.
- `shadow_filesystem_state` — v2 state lattice simulator for the Cognitive Lattice.

SQLAlchemy (async). `agentwatch/infrastructure/persistence.py` is the entry point. All writes go through `_pg_write_session()` / `_pg_write_event()` which batch insertions inside async sessions.

## Event-Driven Architecture

1. An agent calls `agentwatch.watch()`.
2. The SDK serialises the payload to an `AgentEvent` Pydantic model and POSTs it to `/api/v1/sessions/session_id/events`.
3. The API handler writes the event to PostgreSQL.
4. **Post-write hook** (`_after_publish`): pushes the event to Redis pubsub channel `agentwatch:events` and dispatches a Celery task for any alert condition.
5. Celery workers pick up the task and evaluate alert rules (budget exhaustion, silence detector threshold breach, etc.).
6. The WebSocket subscriber (`/ws/events`) listens to the same Redis channel and pushes to connected dashboard clients in real time.

## State Persistence

- **PostgreSQL** — primary store for sessions, events, audit logs, security keys. Connection pool via `asyncpg` (non-blocking).
- **Redis** — in-memory pubsub + cache layer. TTL-based cache for session metadata, rate-limiting counters (sliding window), Celery broker.
- **pgvector** — used by the RAG-powered reasoning evaluator (Needle program choice, vector similarity on embeddings), not by default — optional dependency through `[embeddings]` extra.

## Frontend (`frontend/`)

Next.js 14 App Router dashboard. Core pages:

- `/dashboard` — cluster overview, active sessions, model utilisation, total cost
- `/sessions/[id]` — per-session detail: all events, reasoning traces, timeline
- `/compliance` — audit log, GDPR tools
- `components/events/*` — real-time event feed via the WebSocket client that connects to `/ws/events`

State management: React Query + Axios. No Redux — query cache ensures the dashboard doesn't refetch the entire session tree on every poll.

## Service Registry

| Service | Technology | Port | Purpose |
|---|---|---|---|
| `api` | Python 3.12 / FastAPI | 8000 | REST + WebSocket |
| `frontend` | Next.js 14 | 3000 | Dashboard UI |
| `landing` | Next.js 16 | 3001 | Public landing page |
| `postgres` | pgvector:pg16 | 5432 | Sessions + events + embeddings |
| `redis` | Redis 7 | 6379 | Pubsub, cache, rate-limit counters |
| `worker` | Celery | — | Alert dispatch, budget expiry, cleanup |
| `jaeger` | All-in-one | 16686 | Distributed tracing (optional profile) |

## Deployment Profiles

| Profile | Compose command | What it adds |
|---|---|---|
| `default` | `docker compose up -d` | postgres + redis + api + frontend |
| `workers` | `--profile workers` | worker (Celery background jobs) |
| `tracing` | `--profile tracing` | Jaeger tracing UI |

## Development Flow

1. `docker compose up -d` — start all dependent services.
2. `pip install -e ".[dev]"` — install the Python package in editable mode.
3. `ruform check agentwatch/` — lint.
4. `pytest tests/ -v --cov=agentwatch --cov-fail-under=70` — run postgres tests (requires docker compose running).
5. Frontend: `cd frontend && npm run dev`.
6. Landing: `cd agentwatch-landing && npm run dev`.
7. `make format` — auto-format every sub-package.

## CLI Entrypoint

The `agentwatch` Typer CLI serves two personas:

- **Operator** (`agentwatch compliance`, `agentwatch status`): Runs production audit and cluster health checks.
- **Developer** (`agentwatch test-owasp`, `agentwatch benchmark`): Development-time tooling for policy evaluation and diagnostics.

All CLI commands use async handlers and the same `infrastructure` layer as the API — a CLI command hitting the database tests the same async pool as a production request.