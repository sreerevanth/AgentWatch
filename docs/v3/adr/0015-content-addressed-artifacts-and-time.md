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

## Amendment (2026-09-26): most-recent-producer semantics

The held-out AWBench architecture (map_reduce) showed that time-respecting traversal is not enough in fan-out systems. When several workers independently retrieve the same document, the content-identical item node linked every worker's retrieval to every later consumer; information precision was 0.37.

Traversal now follows **most-recent-producer** semantics, the equivalent of reaching definitions in dataflow analysis:

- **Forward:** a value carried from a producer *expires* once another event produces the same content. Consumers after that point are not reached from the earlier producer.
- **Backward:** from a consumer, only the latest production before the consumption is accepted.
- **Lists:** an item's producers include the producers of the lists that contain it.

**Caveat:** this rule was designed after seeing held-out results, so its effect on that architecture is **not** held-out evidence. A second held-out architecture is needed to validate it.

## Amendment (2026-09-26): content shortcuts through an intermediate are reduced

On its first run, the second held-out architecture (hybrid_rag_cache) got information precision 0.53 and detected M006 in 0 of 21 runs. The cause: a report built from a model answer that quotes retrieved text also contains that text. Every item then got a direct DERIVES_FROM edge to the report, and the answer never appeared as the bottleneck.

**Rule.** A direct content edge y→x is dropped when an in-system intermediate m meets two conditions:

- m carries **all** of the text that x shares with y. If m carries only part of it, the remainder may have come directly from y (for example, a carried-forward history), so the edge stays.
- y demonstrably reaches m before x exists, either through a content edge y→m or because m was produced by an event that consumed y.

Content edges form a time-ordered DAG, so dropping such shortcuts preserves reachability.

**Trade-off.** An *unused* intermediate that reproduces the same text is indistinguishable from a used one. Example: map_reduce's critic draft, which is discarded. The reduction then explains the output through the unused intermediate and reports a false bottleneck. Only declared inputs on the consuming operation can resolve this.

**Caveat.** This rule was designed after seeing hybrid_rag_cache's results, so it is not held-out evidence for that architecture. `graph.information@5`.
