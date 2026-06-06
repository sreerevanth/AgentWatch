---
name: update-github-actions-workflow
description: Workflow command scaffold for update-github-actions-workflow in AgentWatch.
allowed_tools: ["Bash", "Read", "Write", "Grep", "Glob"]
---

# /update-github-actions-workflow

Use this workflow when working on **update-github-actions-workflow** in `AgentWatch`.

## Goal

Update or refactor GitHub Actions workflow files for CI, including splitting workflows, pinning action versions, or improving logic.

## Common Files

- `.github/workflows/report-on-pr.yml`
- `.github/workflows/test-on-pr.yml`

## Suggested Sequence

1. Understand the current state and failure mode before editing.
2. Make the smallest coherent change that satisfies the workflow goal.
3. Run the most relevant verification for touched files.
4. Summarize what changed and what still needs review.

## Typical Commit Signals

- Edit one or more files in .github/workflows/ (e.g., report-on-pr.yml, test-on-pr.yml)
- Commit changes with a message describing the CI improvement or fix

## Notes

- Treat this as a scaffold, not a hard-coded script.
- Update the command if the workflow evolves materially.