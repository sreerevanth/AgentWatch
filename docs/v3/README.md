# AgentWatch v3 — Architecture Documents (Phase 0)

AgentWatch v3 is an instrument that reconstructs, explains, compares, replays and (experimentally) forecasts the behaviour of AI-native software systems from passive runtime observations.

## Reading order

1. [CURRENT_ARCHITECTURE.md](CURRENT_ARCHITECTURE.md): forensic review of v0.2. What exists, and the architectural debt (D1–D14) that blocks v3.
2. [V3_ARCHITECTURE.md](V3_ARCHITECTURE.md): planes, domain model, data architecture, query engine, frontend information architecture, repository restructure.
3. [MIGRATION_MAP.md](MIGRATION_MAP.md): KEEP / ADAPT / REWRITE / DEPRECATE / REMOVE for every package; strangler migration stages M0–M5; branch procedure.
4. [RESEARCH_HYPOTHESES.md](RESEARCH_HYPOTHESES.md): hypotheses H1–H11 with pre-registered thresholds, AWBench design, research roadmap (engineering / research / experimental), threats to validity.
5. [adr/](adr/): architecture decision records 0001–0013.
6. [PHASE1_PLAN.md](PHASE1_PLAN.md): the observation-core implementation plan, with work packages, tests and exit criteria.

## ADR index

| # | Decision |
|---|---|
| [0001](adr/0001-v3-strangler-in-repo.md) | Build v3 in-repo as a strangler around a new core |
| [0002](adr/0002-passive-sidecar.md) | Passive sidecar: v3 core never controls the observed system |
| [0003](adr/0003-immutable-evidence-versioned-interpretation.md) | Immutable evidence; versioned, re-derivable interpretations |
| [0004](adr/0004-computational-event-model.md) | `ComputationalEvent` algebra; OTel as input, not model |
| [0005](adr/0005-three-views-one-relation-store.md) | Execution / information / causal views over one hyperedge store |
| [0006](adr/0006-storage-relational-first.md) | SQLite/Postgres + blobs; graph DB and columnar only on measured triggers |
| [0007](adr/0007-evidence-classes-and-uncertainty.md) | Evidence classes and uncertainty are required fields |
| [0008](adr/0008-sensor-plugins-light-sdk.md) | Plugin sensors; light base install; server behind an extra |
| [0009](adr/0009-deterministic-first-llm-bounded.md) | Deterministic first; LLMs bounded and grounded |
| [0010](adr/0010-maturity-labels.md) | EXPERIMENTAL / VALIDATED / PRODUCTION enforced in code |
| [0011](adr/0011-privacy-redaction-and-erasure.md) | Edge redaction; erasure by crypto-shredding |
| [0012](adr/0012-modular-monolith.md) | Modular monolith; no microservices |
| [0013](adr/0013-awbench-gates-claims.md) | AWBench gates every analytic claim |

## Status

All documents are **PROPOSED**. No v3 code exists yet. No benchmark results exist yet. Thresholds in RESEARCH_HYPOTHESES are pre-registered targets, not results.
