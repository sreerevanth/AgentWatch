# AWBench results (machine-generated — do not edit)

- generated: 2026-09-26T07:37:15.021767+00:00
- git: `a3fa5c1fbd0a7627c5eacf95265a18e71d72b2be` · registry sha256 `5231dd928fd7`
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
| h2_structure | information_recall | 0.8527 | 0.8952–0.8952 (n=3) | 0.75 | yes |
| h2_structure | information_precision | 0.7466 | 0.6912–0.7705 (n=3) | 0.75 | **no** |
| h3_lineage | lineage_membership_precision | 0.9431 | 0.9286–0.9398 (n=3) |  |  |
| h3_lineage | lineage_membership_recall | 0.8319 | 0.8764–0.8764 (n=3) |  |  |
| h3_lineage | lineage_membership_f1 | 0.884 | 0.9017–0.907 (n=3) | 0.8 | yes |
| h4_divergence | top1_localization | 0.9571 | 0.9524–0.9524 (n=3) | 0.7 | yes |
| h4_divergence | root_at_or_upstream | 0.9571 | 0.9524–0.9524 (n=3) | 0.9 | yes |
| h4_divergence | baseline_index_aligned_top1 | 0.9143 | 0.9048–0.9048 (n=3) |  |  |
| h5_motifs | micro_precision | 0.9412 | 0.9412–0.9412 (n=3) | 0.9 | yes |
| h5_motifs | micro_recall | 0.9412 | 0.9412–0.9412 (n=3) | 0.8 | yes |
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

Results come from stub systems (seeded document choice, failure counts and latency jitter); they do not measure behaviour with real models. Lab and faithfulness tasks use the lowest seed of each set.

- **h1_normalization**: cross-source compares the same program instrumented natively vs via OpenTelemetry GenAI spans
- **h2_structure**: execution edges from DECLARED relations only; information precision counts reachable pairs not in the transitive closure of true data flow
- **h3_lineage**: does lineage(final output) contain exactly the operations whose data truly flowed into it
- **h5_motifs**: expected motifs come from the injected scenario; motifs not injected but detected count as false positives
- **h7_drift**: tool_loop normal vs model_substitution; control = normal vs normal (different seeds)
- **counterfactual_quality**: substitute the clean retrieval result into a corrupted run; the simulated final report must equal the actually observed clean report
- **causal_hypotheses**: hypotheses become SUPPORTED only through recorded interventions
- **explanation_faithfulness**: every cited id must resolve; every number in the answer must appear in (or be a percentage of) the structured result
