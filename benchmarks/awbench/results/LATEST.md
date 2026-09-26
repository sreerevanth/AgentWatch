# AWBench results (machine-generated — do not edit)

- generated: 2026-09-26T11:04:47.685289+00:00
- git: `7500e229febe61ede7d64703349c28d8aa42df74` · registry sha256 `c488cad8bc68`
- runs: 108 · seeds: 3 · models: deterministic stubs (no real LLMs)
- python 3.14.2 on Windows-11-10.0.26200-SP0

| task | metric | measured (pooled) | across seeds (min–max) | threshold | met |
|---|---|---|---|---|---|
| h1_normalization | kind_coverage | 1.0 | 1.0–1.0 (n=3) | 0.95 | yes |
| h1_normalization | cross_source_kind_f1 | 0.8 | 0.8–0.8 (n=3) | 0.9 | **no** |
| h2_structure | execution_precision | 1.0 | 1.0–1.0 (n=3) |  |  |
| h2_structure | execution_recall | 1.0 | 1.0–1.0 (n=3) |  |  |
| h2_structure | execution_f1 | 1.0 | 1.0–1.0 (n=3) | 0.9 | yes |
| h2_structure | baseline_temporal_f1 | 0.2664 | 0.2689–0.2689 (n=3) |  |  |
| h2_structure | information_recall | 0.7907 | 0.819–0.819 (n=3) | 0.75 | yes |
| h2_structure | information_precision | 0.7846 | 0.7288–0.8113 (n=3) | 0.75 | yes |
| h3_lineage | lineage_membership_precision | 0.9431 | 0.9286–0.9398 (n=3) |  |  |
| h3_lineage | lineage_membership_recall | 0.8319 | 0.8764–0.8764 (n=3) |  |  |
| h3_lineage | lineage_membership_f1 | 0.884 | 0.9017–0.907 (n=3) | 0.8 | yes |
| h4_divergence | top1_localization | 0.9571 | 0.9524–0.9524 (n=3) | 0.7 | yes |
| h4_divergence | root_at_or_upstream | 0.9571 | 0.9524–0.9524 (n=3) | 0.9 | yes |
| h4_divergence | baseline_index_aligned_top1 | 0.9143 | 0.9048–0.9048 (n=3) |  |  |
| h5_motifs | micro_precision | 0.9773 | 0.9722–0.9722 (n=3) | 0.9 | yes |
| h5_motifs | micro_recall | 0.9773 | 0.9722–0.9722 (n=3) | 0.8 | yes |
| h7_drift | detects_model_substitution | True |  | True | yes |
| h7_drift | control_flagged_features_max | 0 |  | 0 | yes |
| h7_drift | candidate_flagged_features | 1 |  |  |  |
| replay_fidelity | l1_consistency | 1.0 | 1.0–1.0 (n=3) | 1.0 | yes |
| replay_fidelity | l2_mean_reproduction | 1.0 | 1.0–1.0 (n=3) | 0.99 | yes |
| counterfactual_quality | simulated_outcome_accuracy | 1.0 | 1.0–1.0 (n=3) | 0.8 | yes |
| causal_hypotheses | true_hypothesis_supported | 1.0 | 1.0–1.0 (n=3) | 0.8 | yes |
| causal_hypotheses | control_not_supported | 1.0 | 1.0–1.0 (n=3) | 0.8 | yes |
| explanation_faithfulness | evidence_resolves | 1.0 | 1.0–1.0 (n=3) | 1.0 | yes |
| explanation_faithfulness | numbers_grounded | 1.0 | 1.0–1.0 (n=3) | 0.95 | yes |

## Held-out architecture: map_reduce

Informed fixes after its first runs (ground-truth corrections; M005 v2; most-recent-producer traversal; MATCHES_CONTENT). Its information-precision and motif-precision numbers are development evidence, not held-out evidence.


| task | metric | measured | threshold | met |
|---|---|---|---|---|
| h2_structure | execution_precision | 1.0 |  |  |
| h2_structure | execution_recall | 1.0 |  |  |
| h2_structure | execution_f1 | 1.0 | 0.9 | yes |
| h2_structure | baseline_temporal_f1 | 0.2834 |  |  |
| h2_structure | information_recall | 0.9205 | 0.75 | yes |
| h2_structure | information_precision | 0.4682 | 0.75 | **no** |
| h3_lineage | lineage_membership_precision | 0.8713 |  |  |
| h3_lineage | lineage_membership_recall | 0.8756 |  |  |
| h3_lineage | lineage_membership_f1 | 0.8734 | 0.8 | yes |
| h4_divergence | top1_localization | 1.0 | 0.7 | yes |
| h4_divergence | root_at_or_upstream | 1.0 | 0.9 | yes |
| h4_divergence | baseline_index_aligned_top1 | 1.0 |  |  |
| h5_motifs | micro_precision | 0.1923 | 0.9 | **no** |
| h5_motifs | micro_recall | 1.0 | 0.8 | yes |
| replay_fidelity | l1_consistency | 1.0 | 1.0 | yes |
| replay_fidelity | l2_mean_reproduction | 1.0 | 0.99 | yes |
| counterfactual_quality | simulated_outcome_accuracy | 1.0 | 0.8 | yes |
| explanation_faithfulness | evidence_resolves | 1.0 | 1.0 | yes |
| explanation_faithfulness | numbers_grounded | 1.0 | 0.95 | yes |

## Held-out architecture: hybrid_rag_cache

Its first run (results/awbench-20260926T104846Z.json, commit 1cf3886) is the held-out evidence: information precision 0.53 and motif recall 0.55 failed. It then informed the content-shortcut reduction (graph.information@5); later numbers are development evidence.


| task | metric | measured | threshold | met |
|---|---|---|---|---|
| h2_structure | execution_precision | 1.0 |  |  |
| h2_structure | execution_recall | 1.0 |  |  |
| h2_structure | execution_f1 | 1.0 | 0.9 | yes |
| h2_structure | baseline_temporal_f1 | 0.1931 |  |  |
| h2_structure | information_recall | 0.9235 | 0.75 | yes |
| h2_structure | information_precision | 0.5102 | 0.75 | **no** |
| h3_lineage | lineage_membership_precision | 0.9897 |  |  |
| h3_lineage | lineage_membership_recall | 0.9288 |  |  |
| h3_lineage | lineage_membership_f1 | 0.9583 | 0.8 | yes |
| h4_divergence | top1_localization | 1.0 | 0.7 | yes |
| h4_divergence | root_at_or_upstream | 1.0 | 0.9 | yes |
| h4_divergence | baseline_index_aligned_top1 | 1.0 |  |  |
| h5_motifs | micro_precision | 1.0 | 0.9 | yes |
| h5_motifs | micro_recall | 0.9574 | 0.8 | yes |
| replay_fidelity | l1_consistency | 1.0 | 1.0 | yes |
| replay_fidelity | l2_mean_reproduction | 1.0 | 0.99 | yes |
| counterfactual_quality | simulated_outcome_accuracy | 1.0 | 0.8 | yes |
| explanation_faithfulness | evidence_resolves | 1.0 | 1.0 | yes |
| explanation_faithfulness | numbers_grounded | 1.0 | 0.95 | yes |

Results come from stub systems (seeded document choice, failure counts and latency jitter); they do not measure behaviour with real models. Lab and faithfulness tasks use the lowest seed of each set.

- **h1_normalization**: cross-source compares the same program instrumented natively vs via OpenTelemetry GenAI spans
- **h2_structure**: execution edges from DECLARED relations only; information precision counts reachable pairs not in the transitive closure of true data flow
- **h3_lineage**: does lineage(final output) contain exactly the operations whose data truly flowed into it
- **h5_motifs**: expected motifs come from the injected scenario (M006: derived from ground-truth data flow); motifs not expected but detected count as false positives
- **h7_drift**: tool_loop normal vs model_substitution; control = normal vs normal (different seeds)
- **counterfactual_quality**: substitute the clean retrieval result into a corrupted run; the simulated final report must equal the actually observed clean report
- **causal_hypotheses**: hypotheses become SUPPORTED only through recorded interventions
- **explanation_faithfulness**: every cited id must resolve; every number in the answer must appear in (or be a percentage of) the structured result
