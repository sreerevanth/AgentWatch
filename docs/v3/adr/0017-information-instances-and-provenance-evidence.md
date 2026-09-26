# ADR-0017: Information instances and a provenance evidence hierarchy

- Status: Accepted
- Date: 2026-09-26
- Supersedes: the most-recent-producer traversal and the content-shortcut reduction (ADR-0015 amendments)

## Context

Up to `graph.information@5`, INFORMATION nodes were content-addressed artifacts: equal bytes meant one node. On two held-out AWBench architectures, information precision was 0.53 and 0.47, and M006 detected false bottlenecks. The cause was the same each time: identical or overlapping content was treated as information flow.

- **Identical values collapsed into one node.** Two workers retrieving the same document produced one node, so every consumer of either copy looked like a consumer of both.
- **Heuristics treated symptoms.** Most-recent-producer traversal and shortcut reduction worked around the collapse, but kept "same content ⇒ same information" at their core.
- **Overlap looked like dependency.** A discarded critic draft that repeated the workers' summaries became the report's "source", because its text overlapped.

## Decision

### 1. Content identity is not information identity

The content id (HMAC of the canonical value) still deduplicates storage, but it is only an attribute. Graph nodes are **information instances**:

| node | meaning |
|---|---|
| `inst:<event>/o<k>` | the k-th value an event produced |
| `inst:<event>/o<k>/i<j>` | the j-th item of a produced list (e.g. one retrieved document) |
| `inst:<event>/in<k>` | a value an event consumed that no observed event produced as such (built by uninstrumented code, or of unknown origin) |

### 2. Resolution hierarchy for consumed values

The first level that yields evidence decides. Weaker levels are not consulted.

| level | evidence type | strength |
|---|---|---|
| 1 | `DECLARED_REFERENCE`: explicit `source=` or a sensor-declared instance id. Also runtime object identity: the native SDK sees the very object an earlier span produced being passed on. | STRONG |
| 2 | `CORRELATION_LINEAGE`: the consumer's declared parent or linked span consumed or produced this identical value | MEDIUM |
| 3 | `MESSAGE_REFERENCE` / `ARTIFACT_REFERENCE`: the identical value was produced on the same channel or object | MEDIUM |
| — | `MEMORY_REFERENCE`: a memory read is linked to the write whose value it returned. Across runs too, when a store outlives a run. | MEDIUM |
| 4 | `TEMPORAL_CONTENT_MATCH`: the identical, non-trivial value was produced earlier in the run | WEAK |
| 5 | `CONTENT_CONTAINMENT`: a constructed value contains text of earlier instances | WEAK |
| 6 | `UNRESOLVED`: no evidence; the value is an origin of unknown provenance | — |
| — | `CONTENT_MATCH_ONLY`: similarity into a value that entered from outside (`MATCHES_CONTENT`) | NONE, never a flow |

Every INFORMATION relation carries these attributes:

- `evidence_type` and `strength`;
- `mode`: `HIGH_FIDELITY` when the evidence was declared (STRONG), otherwise `BEST_EFFORT`;
- `source_event`, `target_event`, and the supporting observation ids.

The strength levels are deterministic categories, not probabilities.

### 3. Ambiguity is preserved, never resolved arbitrarily

For content-based levels (4 and 5), all candidates are collected and then:

1. **Existing ancestors.** Candidates that are already ancestors of the target are dropped.
2. **Parallel replicas.** The same operation (kind, operation, object) running in sibling declared scopes is a replica.
   - Among identical copies from replicas, only the copy produced in the scope closest to the target is kept (`scope_locality`).
   - An identical input constructed by a parallel replica is independent construction, not a source.
3. **Shortcuts.** A candidate whose shared text is fully carried by a later candidate it flowed into is a shortcut. It is dropped; reachability is kept through the later candidate.
4. **Competing explanations.** A remaining candidate *m* is **resolved** only if no other explanation fits the content as well. Two alternatives are considered:
   - a copy that carries all of *m*'s shared text;
   - *m*'s most upstream candidates covering it. The target could have been built without *m*, which is exactly what a discarded intermediate looks like.

   If an alternative fits, *m* is kept as a `CANDIDATE_SOURCE` (resolution AMBIGUOUS). This is not an information flow.
5. **Certainty under ambiguity.** For an ambiguous *m*, a candidate becomes a flow edge only if both hold:
   - it is an ancestor under *m* and under every alternative;
   - the target cannot be explained without it: removing it and its descendants leaves more unexplained text than one concatenation seam produces (shingle size − 1 shingles).

"Explains" is judged with word 5-gram shingles. An assembly of *k* parts may leave uncovered only the shingles that span its *k*+1 seams. No other tolerance is used.

### 4. Generators explain their own outputs

Model, tool and retrieval outputs are produced by their event. Similar earlier text is not evidence that they copied it. Content inference into outputs applies only to **carriers** (state writes, messages, delegation, memory access, operations, transformations) that did not declare where their data came from.

### 5. Traversal

`Graph.ancestors` and `Graph.descendants` skip AMBIGUOUS and strength-NONE relations unless `include_ambiguous=True`. A traversal can also require `min_strength` (for example `"STRONG"` for high-fidelity lineage only). Lineage lists candidates explicitly, with `ambiguous: true` and their alternatives, and does not expand them.

## Consequences

- **Precision over recall.** With value-level telemetry, an intermediate that only copies text (an extractive summary, a cache that returns the value unchanged) cannot be proven to have been used rather than its sources. The sources are certain; the intermediate is a candidate. Lineage and M006 then treat the sources as feeding the output directly. That understates the structure, but it does not invent it.
- **Instrumentation raises precision.** Explicit `source=`, declared instance ids, or passing the produced object itself make lineage exact (HIGH_FIDELITY). The OTel extension attributes (ADR-0018) carry the same information.
- **Parallel replicas are a structural rule.** It is documented here, and relations it decided carry `scope_locality: true`.
- **Short or templated texts reach a resolution limit.** When candidates differ by fewer shingles than one seam produces, content cannot separate them.
- **Incremental processing** receives other runs' memory writes as context. A late write whose key other runs read afterwards forces a full rebuild.
- **Rebuild required.** `graph.information@6`, native normalizer 2 and motifs analyzer 3 change the interpretation id, so stored interpretations are rebuilt.
