# ADR-0010: Maturity labels (EXPERIMENTAL / VALIDATED / PRODUCTION) enforced in code

- Status: Proposed
- Date: 2026-09-25

## Context

The brief requires speculative features never to be presented as proven. In v0.2, every feature ships with the same apparent authority.

## Decision

- Every analyzer, metric and derived-record producer registers through an `@analyzer(name, version, maturity=…)` decorator. Metrics also reference a definition document in `docs/v3/metrics/`. Registration fails without that document.
- `EXPERIMENTAL` is the default.
- Promotion to `VALIDATED` requires a committed AWBench result file meeting the pre-registered thresholds in `benchmarks/awbench/REGISTRY.yaml`. CI verifies that the referenced result exists and that it passes.
- Promotion to `PRODUCTION` additionally requires documented performance and robustness budgets, measured on the reference server spec.
- Every API response containing derived data includes `maturity` and `derived_by`. The frontend shows a badge. `EXPERIMENTAL` outputs are hidden behind an explicit toggle in LIVE and MAP.
- Demotion is automatic when a newer benchmark run falls below thresholds.

## Consequences

- Marketing and README claims can be generated from the registry instead of written by hand.
- Adding a feature costs slightly more, by design.
