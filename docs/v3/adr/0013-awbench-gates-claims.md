# ADR-0013: AWBench gates every analytic claim

- Status: Proposed
- Date: 2026-09-25

## Context

v0.2's only analytic benchmark shows 0% F1 for its default configuration, while features are described as capabilities. v3 claims must be empirically testable.

## Decision

- AWBench (RESEARCH_HYPOTHESES §3) is built **from Phase 1**, in parallel with the core, starting with systems S1 and S2 on deterministic stub models.
- Each hypothesis H1–H11 has a task module, pre-registered thresholds in `REGISTRY.yaml`, and machine-generated, committed results.
- Stub-model and real-model results are always reported separately.
- The AgentWatch pipeline under test runs in a separate process with no access to ground-truth files.
- README and docs capability statements must cite a registry entry and result file (ADR-0010).

## Consequences

- Phases 2–5 cannot declare their deliverables *validated* without AWBench tasks for them.
- AWBench is itself a research contribution and must be versioned like a dataset.
