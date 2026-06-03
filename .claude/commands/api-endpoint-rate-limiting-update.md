---
name: api-endpoint-rate-limiting-update
description: Workflow command scaffold for api-endpoint-rate-limiting-update in AgentWatch.
allowed_tools: ["Bash", "Read", "Write", "Grep", "Glob"]
---

# /api-endpoint-rate-limiting-update

Use this workflow when working on **api-endpoint-rate-limiting-update** in `AgentWatch`.

## Goal

Implements or fixes rate limiting logic for an API endpoint, including updating server logic and corresponding tests.

## Common Files

- `agentwatch/api/server.py`
- `tests/test_rate_limiting.py`

## Suggested Sequence

1. Understand the current state and failure mode before editing.
2. Make the smallest coherent change that satisfies the workflow goal.
3. Run the most relevant verification for touched files.
4. Summarize what changed and what still needs review.

## Typical Commit Signals

- Modify or extend rate limiting logic in agentwatch/api/server.py
- Update or add tests in tests/test_rate_limiting.py
- Ensure correct error contracts and headers are handled

## Notes

- Treat this as a scaffold, not a hard-coded script.
- Update the command if the workflow evolves materially.