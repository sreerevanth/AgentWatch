# ADR-0004: A canonical ComputationalEvent model; OpenTelemetry is an input, not the model

- Status: Proposed
- Date: 2026-09-25

## Context

We need one representation for heterogeneous sources. The candidates were:

- (a) keep `AgentEvent`,
- (b) adopt OTel spans as the internal model,
- (c) define a richer event algebra.

`AgentEvent` is agent-centric, uses closed enums, and has no inputs, outputs or effects (D4). OTel spans are excellent for execution nesting. They have no first-class notion of the artifacts read and written, which information-flow and provenance analysis require. Semantic conventions also differ across sources.

## Decision

- Adopt `ComputationalEvent` (V3_ARCHITECTURE §2.2): actor, operation and object; content-addressed inputs and outputs; typed `effects`; interval time with uncertainty; declared parent links; status; resources; separate observation and attribution confidence; and a namespaced `attributes` remainder that never drops source data.
- The `EventKind` core vocabulary is small (15 kinds) and closed. Extension is through namespaced kinds (`x.<vendor>.<kind>`) and multi-label `facets`.
- OTel (including the GenAI semantic conventions) is the **preferred wire input**. The OTLP receiver maps spans and span events onto `ComputationalEvent`. The mapping is versioned in a normalizer.
- `AgentEvent` survives only as a legacy wire format, handled by the `legacy` sensor and normalizer.

## Consequences

- AgentWatch can ingest the whole OTel ecosystem without forcing its own SDK on users.
- Normalizers carry real logic (pairing, effect extraction), and that logic needs golden tests per source.
- Observed systems do not need "agents" or "sessions". A run is derived from declared roots or segmentation.
