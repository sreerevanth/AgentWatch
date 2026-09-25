# ADR-0015: Content-addressed artifacts need time-respecting, per-run semantics

- Status: Accepted
- Date: 2026-09-25 (found by AWBench, H2)

## Context

Artifacts are identified by HMAC(tenant key, canonical content), so identical values share one node. That is correct for provenance ("this is the same text"), but it has side effects:

- The same content appears in several runs.
- Within one run, the same value can be consumed by an early event and produced again by a later one.

Early AWBench runs showed information "flowing" backwards in time through such shared nodes. Item decomposition and content matches were also attributed only to the first run in which the content appeared.

## Decision

- **Per-run relations.** Relations derived from content (CONTAINS_ITEM, DERIVES_FROM) are computed per run. The relation id includes the run id.
- **Time-respecting traversal.** Graph traversal refuses to step to an event on the wrong side of time: an ancestor must not start after its descendant, and a descendant must not start before its ancestor.
- **Memory transfers need matching values.** TRANSFERS (memory write → read) is emitted only when the read returns the written value (CONTENT_MATCH), or with confidence 0.5 (KEY_MATCH) when the read value was not recorded. A read of the same key that returns different content is not information flow.

## Consequences

- Identical content produced by several events stays genuinely ambiguous. AWBench H2 precision reports it rather than hiding it.
- Traversal marks nodes as seen on first visit, so a node first reached by a path at the wrong time is not revisited by a later valid path. This is a documented approximation.
