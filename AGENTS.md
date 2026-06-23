# AgentWatch — Agent Instructions

## Repo Structure

Three independent codebases in one repo:

| Path | What | Stack |
|---|---|---|
| `agentwatch/` | Python package (`agentwatch-ai`) | FastAPI, SQLAlchemy async, Celery, Pydantic |
| `frontend/` | Dashboard UI | Next.js 14, React 18, Tailwind, Jest |
| `agentwatch-landing/` | Public landing page | Next.js 16, React 19, GSAP, Three.js |

**Critical:** `frontend/` and `agentwatch-landing/` are separate Next.js apps with different versions. Do not mix deps or share components between them.

## Python

```bash
# Install (from repo root)
pip install -e ".[dev]"

# Lint
ruff check agentwatch/
ruff format --check agentwatch/

# Tests (requires Postgres + Redis — use docker compose up -d first)
pytest tests/ -v --cov=agentwatch --cov-fail-under=70
```

- Python 3.12+. Build system: hatchling.
- `tests/conftest.py` mocks sentence-transformers — do not remove; tests will hang downloading models.
- Coverage gate: 70% minimum (enforced in CI).
- Ruff ignores `E501` (line length), `S101` (assert), `S104` (0.0.0.0 bind), `S202` (tarfile.extractall). These are intentional.
- `__init__.py` files use wildcard re-exports — ruff `F401`/`F403` are suppressed per-file.
- `asyncio_mode = "auto"` — no need for `@pytest.mark.asyncio` on async tests.

## Frontend (`frontend/`)

```bash
cd frontend
npm ci
npm run type-check   # tsc --noEmit
npm run build
npm run test         # Jest
```

- API URL defaults to `/api/v1`. Override with `NEXT_PUBLIC_API_URL`.
- WebSocket endpoint at `/ws/events`.

## Landing Page (`agentwatch-landing/`)

**Next.js 16 — this is NOT the version you trained on.** API conventions, file structure, and React patterns may differ. Read `node_modules/next/dist/docs/` before writing code. Heed deprecation notices.

```bash
cd agentwatch-landing
npm run dev
```

## CI

- **CI** (`ci.yml`): lint → tests → integration tests → frontend build → Docker build. Tests and integration tests run with Postgres+Redis service containers.
- **PR tests** (`test-on-pr.yml`): runs pytest + ruff, but only pytest is a hard gate. Lint is reported but not blocking.
- Both workflows target Python 3.12.

## Docker

```bash
docker compose up -d   # Postgres (pgvector), Redis, API, worker, frontend
```

Services: `postgres` (pgvector:pg16), `redis`, `api` (FastAPI on :8000), `worker` (Celery), `frontend` (Next.js on :3000). Optional profiles: `workers`, `tracing` (Jaeger).

## Environment

Copy `.env.example` to `.env`. Key vars:

- `DATABASE_URL` — asyncpg connection string (overrides individual `DB_*` vars)
- `REDIS_URL` / `CELERY_BROKER_URL`
- `AGENTWATCH_API_KEY` — required in production, optional in dev
- `ANTHROPIC_API_KEY` — used by Reasoning Auditor

## Installed Skills (`.agents/skills/`)

| Skill | Use Case |
|---|---|
| `docker-expert` | Optimize Dockerfiles, harden container security, design multi-stage builds, troubleshoot compose setups |
| `python-design-patterns` | Refactor God classes, pick composition vs inheritance, reduce coupling, structure new services cleanly |
| `python-observability` | Add structured logging, wire up Prometheus metrics, set up distributed tracing, debug prod issues |
| `seo-audit` | Audit meta tags, diagnose ranking drops, fix crawl/indexing errors, review Core Web Vitals |
| `wcag-audit-patterns` | Run WCAG 2.2 accessibility audits, fix violations, implement accessible components, meet ADA/508 |

## Gotchas

- `agentwatch-landing/` already has its own `AGENTS.md` (Next.js 16 rules). Do not overwrite it.
- Release: bump version in `pyproject.toml`, then `git tag vX.Y && git push origin vX.Y`. PyPI publish is automatic.
- CONTRIBUTING.md requires issue assignment before work begins. PRs on unassigned issues may be closed.
- CLI commands are routed through `agentwatch/cli/_utils` — do not shell out directly.
