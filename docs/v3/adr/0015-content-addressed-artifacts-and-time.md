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
