# AgentWatch — monorepo convenience targets.
# The Python package, the dashboard UI, and the landing page each have their
# own formatter (Ruff / Prettier). This Makefile ties them together so a
# contributor can run `make format` from the repo root and have every
# sub-package format itself in one shot.

.PHONY: format format-check format-py format-js format-landing format-frontend typecheck help

help:
	@echo "Available targets:"
	@echo "  make format       - Format Python, dashboard UI, and landing page"
	@echo "  make format-check - Verify formatting without modifying files"
	@echo "  make format-py    - ruff format (Python)"
	@echo "  make format-frontend - Prettier (frontend/)"
	@echo "  make format-landing  - Prettier (agentwatch-landing/)"
	@echo "  make typecheck    - mypy over the v3 modules"

format-py:
	ruff format agentwatch/

format-frontend:
	cd frontend && npm run format

format-landing:
	cd agentwatch-landing && npm run format

format: format-py format-frontend format-landing

format-check: format-check-py format-check-frontend format-check-landing

format-check-py:
	ruff format --check agentwatch/

format-check-frontend:
	cd frontend && npm run format:check

format-check-landing:
	cd agentwatch-landing && npm run format:check

# v3 modules are type-checked in CI; the v0.2 packages are not (yet).
V3_MODULES = agentwatch/evidence agentwatch/storage agentwatch/sensors agentwatch/events 	agentwatch/runtime agentwatch/graph agentwatch/provenance agentwatch/compare 	agentwatch/behaviour agentwatch/causality agentwatch/lab agentwatch/state 	agentwatch/forecasting agentwatch/analysis agentwatch/query agentwatch/runs 	agentwatch/entities agentwatch/api/v3.py agentwatch/cli/v3.py agentwatch/instrument.py

typecheck:
	mypy $(V3_MODULES)
