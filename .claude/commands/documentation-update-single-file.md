---
name: documentation-update-single-file
description: Workflow command scaffold for documentation-update-single-file in AgentWatch.
allowed_tools: ["Bash", "Read", "Write", "Grep", "Glob"]
---

# /documentation-update-single-file

Use this workflow when working on **documentation-update-single-file** in `AgentWatch`.

## Goal

Update or add documentation in a single markdown file, often to address reviews or clarify migration/feature details.

## Common Files

- `frontend/NEXT_15_MIGRATION.md`

## Suggested Sequence

1. Understand the current state and failure mode before editing.
2. Make the smallest coherent change that satisfies the workflow goal.
3. Run the most relevant verification for touched files.
4. Summarize what changed and what still needs review.

## Typical Commit Signals

- Edit a specific markdown file in the documentation directory (e.g., NEXT_15_MIGRATION.md).
- Commit the change with a 'docs:' prefix and a brief description.

## Notes

- Treat this as a scaffold, not a hard-coded script.
- Update the command if the workflow evolves materially.