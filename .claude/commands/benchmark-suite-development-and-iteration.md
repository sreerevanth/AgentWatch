---
name: benchmark-suite-development-and-iteration
description: Workflow command scaffold for benchmark-suite-development-and-iteration in AgentWatch.
allowed_tools: ["Bash", "Read", "Write", "Grep", "Glob"]
---

# /benchmark-suite-development-and-iteration

Use this workflow when working on **benchmark-suite-development-and-iteration** in `AgentWatch`.

## Goal

Developing and iterating on a benchmark suite for reasoning auditor, including adding scripts, test cases, and result files.

## Common Files

- `benchmarks/generate_cases.py`
- `benchmarks/run_eval.py`
- `benchmarks/test_cases.json`
- `benchmarks/results/eval_latest.json`
- `benchmarks/README.md`

## Suggested Sequence

1. Understand the current state and failure mode before editing.
2. Make the smallest coherent change that satisfies the workflow goal.
3. Run the most relevant verification for touched files.
4. Summarize what changed and what still needs review.

## Typical Commit Signals

- Edit or add Python scripts for generating or running benchmarks (generate_cases.py, run_eval.py)
- Update or create test case files (test_cases.json)
- Update benchmark results (results/eval_latest.json)
- Update documentation (benchmarks/README.md)

## Notes

- Treat this as a scaffold, not a hard-coded script.
- Update the command if the workflow evolves materially.