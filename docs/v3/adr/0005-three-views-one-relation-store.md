# ADR-0005: Three graph views (execution, information, causal) over one hyperedge relation store

- Status: Proposed
- Date: 2026-09-25

## Context

v0.2 has four incompatible graph notions (D6). One of them labels asserted edges as causes.

"A called B", "B's output contains D's content" and "D influenced B's decision" are different claims with different evidentiary standards. Many effects have multiple joint causes, so binary edges under-represent them.

## Decision

- One `Relation` record type. It has `tail[]` and `head[]` member lists (a hyperedge when either has more than one member), a `view ∈ {EXECUTION, INFORMATION, CAUSAL}`, a `type`, a `basis`, a `confidence`, and evidence references. `evidence_class` is required for CAUSAL relations. `valid_from`/`valid_until` can be set.
- Physical storage uses `relations`, `relation_members` and `relation_evidence` tables in the relational store (see ADR-0006).
- A relation belongs to exactly one view. Views may reference the same nodes.
- A CAUSAL relation can cite EXECUTION and INFORMATION relations as OBSERVATIONAL evidence. It is never created implicitly from them.
- `TEMPORALLY_PRECEDES` is computed on demand from the temporal index. It is not materialized, which avoids O(n²) edge growth.
- Graphs over time use **time-indexed nodes** (events), so cycles over entities (A→B→A) are representable. There is no DAG constraint on entity-level projections.

## Consequences

- Query APIs take a `views` parameter and a minimum evidence class. The UI colour-codes by view and evidence class.
- Hyperedges complicate traversal. Cones treat a hyperedge as reachable when any tail member is reachable (for ancestor cones), and record which members were involved.
- Keeping one store avoids three sets of storage and API code.
