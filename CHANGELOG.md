# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

The PyPI publish workflow reads the section matching the release tag from this
file and uses it as the GitHub Release body, so keep each version's notes here.

## [Unreleased]

### Added
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
