# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

The PyPI publish workflow reads the section matching the release tag from this
file and uses it as the GitHub Release body, so keep each version's notes here.

## [Unreleased]

### Added
- Scheduled red-team automation (issue #399): externalized the attack corpus to `agentwatch/security/payloads.json` (loadable via `load_corpus()`), plus a Celery task `agentwatch.tasks.run_redteam` that runs the red-team harness on a schedule and returns a JSON vulnerability report (bypassed = guardrails that failed).
- Cost-aware model router (`agentwatch.cost.complexity_router`): scores task complexity and routes to the cheapest model capable of handling it — simple subtasks to cheap models (e.g. Gemini Flash), advanced models reserved for complex work — with a budget ceiling and manual override, reusing the `DEFAULT_PRICING` table.
- Automated red-team safety harness (`agentwatch.security.redteam` + `agentwatch redteam` CLI): runs a curated corpus of simulated prompt-injection, path-traversal, credential-scan, and tool-misuse attacks through the detection layer (payloads scored, never executed) and emits a structured resilience report scoring how many attacks are defended vs. bypassed.
- CLI `--api-key` option (with `AGENTWATCH_API_KEY` env fallback) for the `status`, `sessions`, `export`, `compare`, and `session prune` commands, sending the `X-Api-Key` header to protected API endpoints, plus consistent 401 Unauthorized messaging.
- Temporal decay curve manager for episodic memory: importance-weighted exponential forgetting wired into `MemoryEngine` retrieval scoring, plus `prune_decayed()` background cleanup of stale low-importance entries (critical memories persist).
- Locust load-test suite (`tests/load/`) simulating weighted agent traffic.
- Auto-updating contributors wall (scheduled workflow + `contributors.json`).
- PyPI auto-publish workflow on `v*` tags and a PR test/coverage workflow.

## [0.2.0-preview] - 2026-05-27

### Added
- Universal `watch()` one-line agent wrapper
- LangGraph, AutoGen, and Smolagents adapters
- OpenAI Agents adapter support
- Independent reasoning auditor (12 features)
- Safety engine with OWASP Agentic Top 10 checks
- Multi-agent causal DAG for failure tracing
- Causal memory graph (cross-session reasoning trails)
- 9 new frontend dashboard pages
- 205 test cases passing

### Fixed
- CORS wildcard + credentials bypass vulnerability (CORS fix)
- Hardcoded database password fallback to prevent unauthenticated database access (DB password hardening)
- `publish_sync` logging for silent exception drops
- Duplicate module tree import failures on startup

## [0.1.0] - 2026-05-22

### Added
- Initial release of AgentWatch core features
- Core architecture components: `watch()`, `SafetyEngine`, `EventBus`, FastAPI REST server, and Next.js dashboard UI
- `SafetyEngine` equipped with 40+ destructive command/query pattern detectors
- Independent reasoning auditor to verify reasoning steps pre-execution
- Live real-time WebSocket dashboard stream
- Git-backed session checkpointing and one-click rollback
- Claude Code, LangChain, and AutoGPT adapters
- 47 test cases passing
