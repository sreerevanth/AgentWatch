# AgentWatch v3 — Research Hypotheses, AWBench, and Roadmap

Status: AWBench v1 implemented. **Thresholds below are pre-registered targets. Measured values live only in `benchmarks/awbench/results/` (see section 6).**

---

## 1. Framing

**System Mechanistic Interpretability** is the project's research framing: explaining how behaviour arises from the interaction of components in an AI-native system (models, prompts, tools, retrieval, memory, services, humans), using runtime evidence. The phrase describes this project's orientation. It is not a claim to a new academic field.

The governing question has three parts, and each part becomes a family of hypotheses:

1. **Reconstruction.** Can observed events be assembled into a faithful computational structure? (H1–H3)
2. **Explanation.** Does that structure localize and explain behaviour and behavioural change? (H4–H8)
3. **Estimation.** Can it estimate unobserved (future or counterfactual) trajectories with calibrated uncertainty? (H9–H11)

Every hypothesis below records:

- the **claim**,
- its **operationalization** (the metric definition),
- the **baseline** it must beat,
- a **pre-registered success threshold**, which may be revised only *before* results are seen, with a changelog,
- the **falsification condition**,
- the **AWBench tasks** it depends on.

---

## 2. Hypotheses

### H1: Cross-source normalization

- **Claim:** Heterogeneous sources (OTel GenAI spans, LangChain callbacks, Claude Code transcripts, v0.2 `AgentEvent`s) can be mapped to one event algebra without losing information that later analyses need.
- **Metrics:**
  - *Kind coverage:* fraction of observations mapped to a non-`UNKNOWN` kind.
  - *Round-trip retention:* fraction of source fields either mapped or preserved in `attributes`. The target is 100% by construction, so it is a test, not a hypothesis.
  - *Cross-source equivalence:* the same reference application instrumented two ways (OTel vs LangChain callbacks) yields event multisets that match on (kind, operation, object, status) at ≥ threshold.
- **Baseline:** none. This is an engineering validation.
- **Threshold:** kind coverage ≥ 0.95 on AWBench systems; cross-source equivalence F1 ≥ 0.9.
- **Falsified if:** equivalence stays < 0.8 after normalizer iteration. That would mean the algebra needs revision.
- **Phase:** 1.

### H2: Structural recovery

- **Claim:** Declared identifiers plus content matching recover execution and information dependencies accurately. Temporal heuristics add recall at a measurable precision cost.
- **Metrics:** edge precision, recall and F1 against the AWBench ground-truth dependency graph, reported **separately per basis** (DECLARED, CONTENT_MATCH, TEMPORAL, HEURISTIC).
- **Baseline:** temporal adjacency only (what v0.2 can do).
- **Threshold:** DECLARED ∪ CONTENT_MATCH F1 ≥ 0.9 on execution edges and ≥ 0.75 on information edges for systems with full instrumentation. Report the degradation curve as instrumentation is removed.
- **Falsified if:** information-edge F1 is no better than the temporal baseline.
- **Phase:** 2.

### H3: Provenance measurability

- **Claim:** Provenance depth, evidence retention and unsupported-information ratio can be defined so that they are (a) computable from the INFORMATION view and (b) respond monotonically to controlled perturbations: more summarization hops, a corrupted retrieval, injected unsupported facts.
- **Metric definitions (draft, v0):**
  - *Provenance depth* d(a): the longest `DERIVES_FROM`/`TRANSFORMS` path from artifact a to an `EXTERNAL_INPUT` or retrieval-source artifact.
  - *Evidence retention* R(a, s): for source s in a's lineage, the fraction of s's content units retained in a. v0 uses n-gram containment; semantic variants are versioned separately.
  - *Unsupported-information ratio* U(a): the fraction of a's content units with no match (above a threshold τ) in any artifact in a's ancestor set. This generalizes v0.2's `reasoning/hallucination.py` heuristic.
- **Baseline:** random lineage; v0.2 hallucination heuristic.
- **Threshold:** Spearman ρ ≥ 0.7 between each metric and the injected perturbation magnitude, across ≥ 3 AWBench systems; U(a) AUROC ≥ 0.8 for detecting injected unsupported facts.
- **Falsified if:** metrics are non-monotonic in perturbation magnitude, or dominated by surface paraphrase effects.
- **Caveat:** these metrics measure *textual traceability*, not truth. They must never be presented as factuality scores.
- **Phase:** 2–3.

### H4: Divergence localization (COMPARE)

- **Claim:** Structural alignment of two runs localizes the first behaviourally significant divergence near the injected perturbation.
- **Metric:** rank of the true perturbation point among the reported divergence points (top-1, top-3 accuracy). Mean event distance from reported to true point.
- **Baseline:** first textual difference in an index-aligned event list (v0.2 `compare_sessions`).
- **Threshold:** top-3 ≥ 0.8 across perturbation types, and strictly better than the baseline on every perturbation type with ≥ 30 trials.
- **Phase:** 3.

### H5: Motif validity

- **Claim:** Hand-defined motifs (Retrieval Echo, Delegation Ping-Pong, Retry Storm, Context Growth Spiral, Silent Strategy Change, Resource Contention) can be detected with high precision. Their presence carries information about outcomes beyond simple baselines.
- **Metrics:**
  - per-motif precision and recall on AWBench runs with *injected* motif-inducing perturbations and labelled instances;
  - outcome association: conditional failure-rate lift with a bootstrap CI, controlled for run length.
- **Baseline:** run length, retry count and token count as predictors.
- **Threshold:** precision ≥ 0.9, recall ≥ 0.8 for rule motifs. The association claim is made only if the CI excludes zero *after* conditioning on the baselines.
- **Phase:** 4.

### H6: Behavioural genome and distance

- **Claim:** A feature vector of motif frequencies and structural statistics per SystemVersion:
  - (a) is stable across re-runs of the same configuration: within-version distance is small relative to between-version distance;
  - (b) separates known configuration changes (model swap, prompt edit, tool removal, memory strategy change).
- **Metrics:**
  - for each candidate distance (L1 over normalized features, Jensen–Shannon over motif distributions, graph-kernel distance, energy distance): ratio of between-config to within-config distance;
  - kNN classification accuracy of config identity;
  - test–retest stability.
- **Baseline:** aggregate metrics only (latency, tokens, error rate).
- **Threshold:** at least one distance achieves config-identification accuracy ≥ baseline + 0.15, with test–retest ICC ≥ 0.8. **No single "canonical" D_behaviour is declared.** Candidates are reported side by side.
- **Phase:** 4.

### H7: Drift under preserved quality

- **Claim:** Configuration changes that leave output-quality metrics and tests unchanged still produce detectable genome drift.
- **Metric:** detection power at a fixed false-positive rate (α = 0.05, Benjamini–Hochberg across features) vs number of runs per version.
- **Baseline:** drift on aggregate latency, tokens and error rate.
- **Threshold:** power ≥ 0.8 with ≤ 50 runs per version for ≥ 3 of 5 AWBench silent-change scenarios, where the baseline power is ≤ 0.5.
- **Phase:** 4.

### H8: Evidence-graded root-cause localization

- **Claim:** Ranking candidate causes within a failure's ancestor cone, ordered first by evidence class and then by effect estimate, localizes injected root causes better than recency or anomaly-score baselines. Interventional evidence (AWBench ablation or L3 replay) improves ranking further.
- **Metrics:**
  - top-k localization accuracy;
  - cone size (fraction of the run inside the cone), where smaller is better provided recall is maintained;
  - separately for OBSERVATIONAL-only vs with-INTERVENTIONAL evidence.
- **Baselines:** last error before failure; highest anomaly score; LLM-proposed root cause given the full trace (reported as a baseline, never used as ground truth).
- **Threshold:** top-3 ≥ 0.7 with observational evidence; ≥ 0.85 with interventional evidence. Mean cone size ≤ 0.3 of run.
- **Phase:** 5.

### H9: Latent state usefulness

- **Claim:** A low-dimensional latent state inferred from event sequences (HMM baseline first) predicts next-event kind and eventual outcome better than a no-state n-gram model. States are also interpretable enough to name.
- **Metrics:** held-out log-likelihood per event; outcome AUROC from state trajectory; human agreement on state naming (κ).
- **Baseline:** n-gram over event kinds; rule-based states (retrying / looping / exploring) derived from motifs.
- **Threshold:** log-likelihood improvement significant (paired bootstrap) across ≥ 3 systems. No state vocabulary is fixed before this is shown.
- **Phase:** 7.

### H10: Counterfactual estimation

- **Claim:** For interventions of type "replace artifact X", the outcome of the modified run can be estimated with calibrated uncertainty. Two routes: (a) L2/L3 re-execution when available; (b) outcome models over structurally similar historical runs otherwise.
- **Metric:** agreement between estimates and *actually executed* interventions on AWBench (Brier score, ECE, accuracy of predicted divergence point).
- **Baseline:** base-rate outcome; nearest-neighbour outcome without structure.
- **Threshold:** ECE ≤ 0.1 and Brier better than the base rate. Estimates from route (b) are always labelled `MODEL_ESTIMATED`.
- **Phase:** 8.

### H11: Failure forecasting

- **Claim:** Given a partial trajectory (a prefix of k% of events), the distribution of eventual outcomes can be forecast with calibrated probabilities that beat the system's base rate.
- **Metrics:** Brier, ECE and AUROC as functions of prefix fraction; lead time (events before failure at which AUROC ≥ 0.75).
- **Baselines:** base rate; logistic regression on counts (tokens, retries, errors so far).
- **Threshold:** calibrated (ECE ≤ 0.1) and AUROC better than the counts baseline at 50% prefix on ≥ 3 systems.
- **Phase:** 9.

### Emergence observatory (exploratory, no hypothesis yet)

Coordination entropy, delegation entropy, influence concentration, memory amplification and role migration are **candidate descriptive statistics**. Each needs:

- a definition document,
- a demonstration that it responds to a controlled manipulation,
- a demonstration that it adds information beyond existing genome features.

Only then does it become a hypothesis. Until that point these statistics are not exposed in the UI.

---

## 3. AWBench: design

AWBench is **mandatory infrastructure**, not a marketing artefact. v3 claims are checked against it.

### 3.1 Components

```text
benchmarks/awbench/
  systems/            reference AI-native systems (each runnable offline with a deterministic stub model AND with real models)
  stubs/              deterministic model/tool/retriever stubs with seeded stochasticity
  perturbations/      declarative perturbation specs + injectors (sensor-independent; injected in the SYSTEM, not in the evidence)
  ground_truth/       emitted by instrumented harness: true dependency graph, true root cause, true motif instances, labels
  tasks/              one module per evaluation task (H1…H11), consuming AgentWatch outputs + ground truth
  runner.py           orchestrates: system × config × perturbation × seed × instrumentation-level
  reports/            versioned JSON results + generated markdown; never hand-edited
  REGISTRY.yaml       every benchmark definition, versioned; results reference the registry hash
```

### 3.2 Reference systems (initial set, spanning architectures)

| ID | Architecture | Framework / instrumentation | Why |
|---|---|---|---|
| S1 | Single-model tool loop (ReAct style) | Raw SDK + OTel GenAI | Minimal system, no framework |
| S2 | RAG pipeline with memory write-back | LangGraph + callbacks | Retrieval, memory, information flow |
| S3 | Planner / executor / critic multi-agent | Plain-python + OTel **and** AutoGen (same logic, two frameworks) | Delegation; cross-framework transfer |
| S4 | Service-oriented: API → queue → worker → vector DB → LLM | FastAPI + Redis + pgvector, OTel only | Non-agent system, distributed, concurrency |
| S5 | Coding agent transcripts | Claude Code stream-json (recorded, replayed as files) | Real-world, non-synthetic traces |

Every system can run with a **deterministic stub model**, so that ground truth is exact and CI can run AWBench offline. It can also run with **real models**, so that results reflect real nondeterminism. Stub results and real-model results are reported separately and never averaged together.

### 3.3 Perturbation catalogue (v0)

| Perturbation | Injection point | Primary tasks |
|---|---|---|
| stale memory, duplicate memory | memory store | H3, H5 (retrieval echo), H8 |
| corrupted retrieval, wrong retrieval | retriever | H3, H4, H8 |
| tool timeout, tool corruption, API failure | tool stub | H4, H5 (retry storm), H8, H11 |
| model replacement | model router in system | H6, H7 |
| prompt edit (quality-preserving) | config | H7 |
| message duplication / loss | inter-component channel | H2, H5 (ping-pong), H8 |
| context pressure | prompt assembly | H5 (context spiral), H9, H11 |
| latency injection, queue delay | transport | H4, H8 |
| concurrency race, resource starvation | S4 worker pool | H5 (contention), H8 |
| invalid external data | tool / webhook input | H3, H8 |

Every perturbation spec records its parameters, magnitude and seed. The harness emits a ground-truth record: `root_cause_node`, `affected_nodes`, `expected_motifs`.

### 3.4 Instrumentation levels

Each system is run at three instrumentation levels:

- **L-full:** all sensors, all declared ids.
- **L-partial:** framework callbacks without inner tool spans.
- **L-min:** LLM API calls only.

This measures how AgentWatch degrades as observability degrades. Degradation curves are reported alongside the headline numbers.

### 3.5 Integrity rules

- Result files are machine-generated, include the git SHA, registry hash, seeds and environment, and are committed. **No hand-written results.**
- Thresholds live in `REGISTRY.yaml`. Changing one requires a changelog entry *dated before* the result it applies to.
- Negative results are published in the same place as positive ones.
- The LLM-based baselines state the model id, prompt hash and temperature.

---

## 4. Research roadmap

Work is split into three tracks. An item moves from Experimental to Research when it has a hypothesis and a benchmark task, and from Research to Engineering when it reaches VALIDATED.

### 4.1 Engineering track (buildable now; correctness is testable by unit and property tests)

| Phase | Item |
|---|---|
| 1 | Observation envelope, append-only store, segment sealing and verification, blob store |
| 1 | Sensors: otel (OTLP receiver + GenAI mapping), legacy translator, langchain/langgraph, claude_code |
| 1 | Normalizers (pairing, kind mapping, effects), deterministic entity and artifact resolution, run segmentation |
| 1 | `/v3` ingest and read API, CLI, TIMELINE-lite |
| 1 | AWBench harness skeleton, S1 + S2 with stub models, overhead benchmark |
| 2 | Relation store, EXECUTION and INFORMATION builders (declared + content-match), temporal index, cones (reachability), lineage queries, MAP (run) |
| 3 | Run alignment, structural diff, behaviour statistics, version comparison, COMPARE view, structured query API |
| 4 | Motif registry and rule/graph-query detectors, genome feature extraction with bootstrap CIs, drift tests with FDR control, GENOME view |
| 5 | Causal hypothesis store, evidence-class machinery, root-cause ranking skeleton |
| 6 | Timelines, branches, L0/L1/L2 replay, reproducibility report, LAB view |

### 4.2 Research track (hypothesis-driven; success is measured on AWBench)

| Hypothesis | Research question | Earliest phase |
|---|---|---|
| H2 | How much do content-matching and heuristic edges add over declared edges? | 2 |
| H3 | Which lineage metrics are monotone in perturbation magnitude? | 2–3 |
| H4 | Which alignment method best localizes divergence? | 3 |
| H5, H6, H7 | Are motifs, genomes and drift tests valid, stable and useful? | 4 |
| H8 | Does evidence-graded ranking beat baselines, and by how much do interventions help? | 5 |
| — | Causal discovery methods (Granger-style over event-kind series, PC / FCI with temporal tiers, NOTEARS variants) as **hypothesis generators**; evaluated on graph recovery against AWBench ground truth | 5 |
| H9 | Latent state models: HMM → state-space → temporal graph models | 7 |

### 4.3 Experimental track (speculative; no user-facing exposure without a hypothesis)

- Unsupervised motif discovery (frequent temporal subgraph mining, graph-kernel clustering).
- Neural CDEs and temporal transformers for state estimation.
- L3 partial re-execution and L4 environment reconstruction.
- Counterfactual outcome models (H10), forecasting (H11).
- Emergence metrics.
- LLM-assisted hypothesis proposal, where every proposal enters as `CausalHypothesis(status=PROPOSED, evidence_class=None)` and must be tested.
- Semantic (embedding-based) information-distortion metrics.

---

## 5. Threats to validity (tracked from day one)

- **Synthetic-to-real gap.** Stub-model systems have unrealistically clean structure. Mitigation: S5 real transcripts, real-model runs, and reporting stub and real results separately.
- **Benchmark overfitting.** Detectors are tuned on the systems they are evaluated on. Mitigation: hold out one system and one perturbation family per evaluation; report leave-one-system-out results.
- **Observer effect.** Sensors perturb latency and memory. Mitigation: the overhead benchmark gates each sensor release; runs record the sensor configuration.
- **Sampling bias.** Tail sampling over-represents failures. Mitigation: sampling decisions are recorded as evidence and statistics are reweighted.
- **Ground-truth leakage.** The harness knows the injection point. The AgentWatch pipeline must not read ground-truth files. This is enforced by process isolation in the runner.
- **Construct validity of "behaviour".** Genome features are chosen by us. Mitigation: report feature-ablation results and never interpret a genome as more than "repeatable measured structure".


---

## 6. First AWBench results (2026-09-25)

These are machine-generated values from `benchmarks/awbench/results/latest.json` (deterministic stub systems, 3 architectures x 16 scenarios, seed 0, drift n = 10 per side). Summary:

- **Met:**
  - H2 execution F1 1.0 (temporal baseline 0.26)
  - H2 information recall 0.79 / precision 0.84
  - H3 lineage F1 0.86
  - H4 top-1 localization 0.97 (index-aligned baseline 0.93)
  - H5 motif precision/recall 0.94/0.94
  - H7 drift detected (control: 0 features flagged)
  - replay L1/L2 fidelity 1.0
  - counterfactual accuracy 1.0
  - causal hypotheses 1.0/1.0
  - explanation faithfulness 1.0
- **Not met:** H1 cross-source kind F1 **0.80 < 0.90**. OpenTelemetry has no convention for "artifact write", so the OTel-instrumented system's write span normalizes to OPERATION.

**Validity caveats — read before citing any number:**

1. **In-sample.** Several components were corrected after earlier AWBench runs exposed defects:
   - memory TRANSFERS on stale reads
   - traversal through shared artifacts ignoring time
   - explanation rounding
   - drift power
   - profile features

   These results therefore do not count as held-out validation. No analytic capability is promoted beyond EXPERIMENTAL on their basis.
2. **Stub systems.** Deterministic stub models make ground truth exact but unrealistically clean (section 5, synthetic-to-real gap). There are no results with real models yet.
3. **One seed.** Variance across seeds is not yet reported.
4. **Evaluator definitions** are in `benchmarks/awbench/tasks.py`. Their docstrings and notes state what each metric does and does not measure.

Before any VALIDATED claim, the next steps are held-out architectures, real-model runs, and multiple seeds.


### 6.1 Three-seed run (2026-09-26)

With seeded variability (seeds now change the retrieved documents, tool-failure counts and latency jitter), 3 seeds × 3 architectures × 16 scenarios, plus drift sets (108 runs, clean tree `a3fa5c1`):

- **Not met:**
  - **H1 cross-source kind F1 0.80** (unchanged cause: no OTel convention for artifact writes).
  - **H2 information precision 0.747** pooled; 0.69–0.77 per seed; threshold 0.75. With varied documents, identical content produced by several events makes content-addressed flow ambiguous more often (ADR-0015). The evaluator counts every such ambiguous pair as a false positive.
- **Met:**
  - H2 execution F1 1.0
  - information recall 0.85 (0.90 per seed)
  - H3 lineage F1 0.88 (0.90–0.91)
  - H4 top-1 0.96 (baseline 0.91)
  - H5 precision/recall 0.94/0.94
  - H7 drift detected with a clean control
  - replay, counterfactual, hypotheses and faithfulness all at 1.0

"Pooled" values also include the extra drift-set runs. The per-seed ranges use only each seed's matrix runs. Variance across seeds is small because the systems are stubs; it is not an estimate of real-world variance.

### 6.2 Held-out architectures (2026-09-26)

Held-out architectures are added after AgentWatch development, committed before their first run, and scored separately (per architecture) with the same thresholds. Once an architecture's results have led to a change in AgentWatch, it stops being held-out evidence for the affected metrics. The registry changelog records each such step.

**map_reduce** (planner → 3 workers → reducer join, critic model):

| step | information precision | motif precision | note |
|---|---|---|---|
| first run | 0.37 | 0.28 | held-out evidence; also exposed ground-truth bugs, fixed and logged |
| after M005 v2 + most-recent-producer traversal + MATCHES_CONTENT | 0.40–0.43 | 1.0 | development evidence |
| after content-shortcut reduction (graph.information@5) | 0.47 | 0.19 | development evidence; M006 false positive in every run (below) |

**hybrid_rag_cache** (vector + keyword retrieval, dedupe tool, answerer over a growing multi-turn history, cache write and read-back). It was committed at `1cf3886`, before its first run.

- **First run: held-out evidence for the fixes above.** Results file `results/awbench-20260926T104846Z.json`, commit `1cf3886`.
  - Met: execution F1 1.0, information recall 0.92, lineage F1 0.96, H4 top-1 1.0, motif precision 1.0 (M005 v2 correct in 21/21 runs), replay, counterfactual and faithfulness.
  - **Not met: information precision 0.53** (threshold 0.75). **Not met: motif recall 0.55**, because M006 was detected in 0/21 runs.
  - So most-recent-producer traversal and MATCHES_CONTENT did **not** generalize enough to bring information precision to threshold on a new architecture. M005 v2 did generalize.
- **Diagnosis of M006 and the change made.** The answerer quotes retrieved text, so the report contained that text, and every retrieved item got a direct DERIVES_FROM edge to the report, bypassing the answer. The builder now drops a direct content edge y→x when an in-system intermediate m carries *all* the text x shares with y, and y demonstrably reaches m before x exists. "Demonstrably" means either a content edge y→m, or m being produced by an event that consumed y. This is a transitive reduction, so reachability is preserved.
- **After the change: development evidence only.** Motif precision/recall 1.0 / 0.96, information precision 0.51.
- **A benchmark ground-truth correction was made at the same time.** M006 is structural, so its expectation is now derived from the true data flow for every run rather than declared per scenario.

**What the change costs.** In map_reduce, a critic model reproduces all three worker summaries in a draft that is then discarded, and the report is assembled from the worker messages. Content cannot distinguish that unused draft from a real intermediate. The reduction therefore explains the report through the draft and reports a false bottleneck, which gives 21 M006 false positives. This is a form of the known common-source limitation (no "explaining away"): when an unused artifact reproduces the same text, content matching picks the wrong explanation. Only declared inputs on the report-writing operation could settle it, and neither stub system declares them.

**Open:**
- Information precision on both labelled architectures (0.47, 0.51). The main cause is identical content produced by several events (ADR-0015), which remains ambiguous.
- The M006 false positive described above.
- A third held-out architecture is needed to test the reduction.


### 6.3 Information instances and the third held-out architecture (2026-09-26)

Both earlier held-out architectures had shown the same failure: identical or overlapping content was treated as information flow. The information model was rebuilt around information instances, an evidence hierarchy and preserved ambiguity (ADR-0017), rather than patched per architecture.

**Pre-registration.** `async_event_pipeline` was designed and committed before those changes were tested (architecture `88f46a9`, pre-registration `bfc68cb`). It features asyncio workers completing out of order, an at-least-once queue, a discarded draft identical to the published result, shared evidence overlapping a worker's own retrieval, retries, a glossary cache hit and a database read-back.

**First scored run.** Clean tree, 3 seeds, commit `9f7e97c`, results `awbench-20260926T145401Z.json`, recorded unchanged in `a00dac2`.

| task | metric | held-out result | threshold |
|---|---|---|---|
| H2 | execution F1 | 1.0 | 0.9 ✓ |
| H2 | information precision | **0.95** | 0.75 ✓ |
| H2 | information recall | 0.51 | 0.75 ✗ |
| H3 | lineage F1 | 0.33 (precision 1.0, recall 0.20) | 0.8 ✗ |
| H4 | top-1 / root at or upstream | 0.89 / 0.89 | 0.7 ✓ / 0.9 ✗ |
| H5 | motif precision / recall | 1.0 / 0.64 | 0.9 ✓ / 0.8 ✗ |
| lab, faithfulness | replay, counterfactual, faithfulness | 1.0 | ✓ |

**Reading of the held-out result.**
- **Precision generalized.** Precision is 0.95 on the unseen architecture, against 0.53 and 0.47 on first contact with the previous two held-out architectures.
- **The cost is recall.** When content fits several producers, AgentWatch now lists candidates instead of choosing one, as ADR-0017 intends.
  - The stub models are extractive, so every intermediate (analysis, merge, enrich, db record) is explainable from its sources. The certain lineage of the report therefore reaches the retrieved evidence and glossary definitions, not the operations in between.
  - Following candidates too gives recall 0.58 at precision 0.36.

**Diagnosis and fixes after recording (`b2af8bb`; the architecture is FORMER_HELD_OUT since).**
1. **H4 `tool_timeout` localized in 1 of 3 seeds.** The comparator aligned steps by signature only. Extra retries were "inserted" before the first attempt, so it blamed an attempt that failed identically in both runs. The fix aligns on (signature, status) with gaps right-normalized past identical steps. After the fix, H4 is 1.0/1.0.
2. **A hierarchy violation.** A memory read's value got content-inferred parents although the transfer from its write explains it. Declared structure now outranks content for outputs too.

**Development set, after the changes** (`awbench-20260926T172315Z.json`; development evidence only):
- information precision 0.94, recall of certain links 0.49 (0.80 with candidates);
- lineage F1 0.42 (precision 1.0);
- motif precision 0.94, recall 0.36 (M006: 0/81 — bottlenecks through extractive intermediates are not certain);
- H4 0.96;
- H1 OTel-only 0.80; with the AgentWatch extension 1.0 (unthresholded, AgentWatch's own mapping, ADR-0018).

**Not yet tested.** The ambiguity is a property of value-level telemetry combined with extractive models.
- Real models are abstractive, and declared inputs remove the ambiguity.
- Neither case has been measured by a held-out run yet: real-model runs need a working credential, and a declared-instrumentation held-out architecture is the next benchmark to build.

### 6.4 Fourth held-out architecture: high-fidelity instrumentation (2026-09-27)

`code_review_pipeline` was designed after the `async_event_pipeline` fixes and committed before its only scored run (architecture `250edad`, pre-registration `e802336`). Its instrumentation passes produced values on as the objects the producing calls returned, so the SDK declares their sources. Per-file patches taken out of the diff list still reach consumers by content only, and the retrieved guidelines overlap the patches' text.

**First scored run** (clean tree, 3 seeds, `awbench-20260926T184322Z.json`, recorded unchanged in `703aab0`): every pre-registered threshold was met.

| task | metric | result | threshold |
|---|---|---|---|
| H2 | execution F1 | 1.0 | 0.9 |
| H2 | information precision / recall | **1.0 / 0.92** | 0.75 / 0.75 |
| H3 | lineage F1 | **0.91** (precision 1.0, recall 0.84) | 0.8 |
| H4 | top-1 / root at or upstream | 1.0 / 1.0 (`tool_timeout` 3/3) | 0.7 / 0.9 |
| H5 | motif precision / recall | 1.0 / 0.89 | 0.9 / 0.8 |
| lab, faithfulness | replay, counterfactual, faithfulness | 1.0 | met |

**What it shows.**
- **Declared sources fix recall.** The information model is precise in both modes. Its best-effort recall is limited by what content can prove (§6.3); with declared sources, recall and lineage reach their thresholds on an unseen system.
- **The retry fix generalized.** The retry-aware divergence fix (`b2af8bb`) located the root cause in all 3 `tool_timeout` runs of an architecture it was not designed on.

**Ground-truth correction** (benchmark only, logged in REGISTRY):
- All three M006 misses were `stale_memory` runs. There the report's only origin is the single diff value, and M006 requires ≥2 origin values, so AgentWatch was right not to fire.
- The benchmark's derivation had counted every external input as two values; it now counts one.
- With the correction, this run's motif recall is 24/24. The recorded file is kept as generated.

**Status.** The architecture is now scored, so it becomes FORMER_HELD_OUT as soon as AgentWatch code changes. Capability `graph.information.high_fidelity` is VALIDATED on this evidence. It covers stub systems only, and best-effort lineage stays EXPERIMENTAL.
