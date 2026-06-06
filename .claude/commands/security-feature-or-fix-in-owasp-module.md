---
name: security-feature-or-fix-in-owasp-module
description: Workflow command scaffold for security-feature-or-fix-in-owasp-module in AgentWatch.
allowed_tools: ["Bash", "Read", "Write", "Grep", "Glob"]
---

# /security-feature-or-fix-in-owasp-module

Use this workflow when working on **security-feature-or-fix-in-owasp-module** in `AgentWatch`.

## Goal

Implement or fix security features in the OWASP security scanning module, sometimes with corresponding tests.

## Common Files

- `agentwatch/security/owasp.py`
- `tests/test_owasp_security.py`

## Suggested Sequence

1. Understand the current state and failure mode before editing.
2. Make the smallest coherent change that satisfies the workflow goal.
3. Run the most relevant verification for touched files.
4. Summarize what changed and what still needs review.

## Typical Commit Signals

- Edit agentwatch/security/owasp.py to add or fix security logic
- Optionally update or add tests in tests/test_owasp_security.py
- Commit with a message describing the security change

## Notes

- Treat this as a scaffold, not a hard-coded script.
- Update the command if the workflow evolves materially.