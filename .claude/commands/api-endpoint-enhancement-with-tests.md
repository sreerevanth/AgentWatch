---
name: api-endpoint-enhancement-with-tests
description: Workflow command scaffold for api-endpoint-enhancement-with-tests in AgentWatch.
allowed_tools: ["Bash", "Read", "Write", "Grep", "Glob"]
---

# /api-endpoint-enhancement-with-tests

Use this workflow when working on **api-endpoint-enhancement-with-tests** in `AgentWatch`.

## Goal

Implements or updates API endpoint logic and ensures correctness with corresponding tests.

## Common Files

- `agentwatch/api/server.py`
- `tests/test_rate_limiting.py`

## Suggested Sequence

1. Understand the current state and failure mode before editing.
2. Make the smallest coherent change that satisfies the workflow goal.
3. Run the most relevant verification for touched files.
4. Summarize what changed and what still needs review.

## Typical Commit Signals

- Edit or enhance the API endpoint implementation in agentwatch/api/server.py
- Update or add corresponding tests in tests/test_rate_limiting.py

## Notes

- Treat this as a scaffold, not a hard-coded script.
- Update the command if the workflow evolves materially.