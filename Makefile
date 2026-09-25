# AgentWatch — monorepo convenience targets.
# The Python package, the dashboard UI, and the landing page each have their
# own formatter (Ruff / Prettier). This Makefile ties them together so a
# contributor can run `make format` from the repo root and have every
# sub-package format itself in one shot.

.PHONY: format format-check format-py format-js format-landing format-frontend help

help:
	@echo "Available targets:"
	@echo "  make format       - Format Python, dashboard UI, and landing page"
	@echo "  make format-check - Verify formatting without modifying files"
	@echo "  make format-py    - ruff format (Python)"
	@echo "  make format-frontend - Prettier (frontend/)"
	@echo "  make format-landing  - Prettier (agentwatch-landing/)"

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
