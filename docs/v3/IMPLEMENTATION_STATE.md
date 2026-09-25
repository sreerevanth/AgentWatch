# AgentWatch v3 — Implementation State

Branch: `architecture/v3` · Updated 2026-09-25

## Completed

| Area | Where | Status |
|---|---|---|
| Immutable evidence: frozen observations, DB-enforced immutability, idempotent append, edge redaction + manifests, blobs, Merkle segments, verify, inclusion proofs, authorized purge | `agentwatch/evidence`, `agentwatch/storage` | tested on SQLite and PostgreSQL (CI) |
| Sensors: native SDK, OTel (OTLP JSON/protobuf, SpanProcessor), LangChain (keeps parent_run_id), Claude Code, OpenAI/Anthropic wrappers, MCP tap, LegacyTranslator | `agentwatch/sensors`, `agentwatch/instrument.py` | tested |
| Normalizers + canonical event algebra with explicit missing facts | `agentwatch/events` | tested (golden-style assertions per source) |
| Engine: versioned, deterministic, atomic rebuild; every observation → event or diagnostic | `agentwatch/runtime` | tested, incl. concurrent engines on PG |
| Runs from declared ids only; exact-key entities | `agentwatch/runs`, `agentwatch/entities` | tested |
| Execution + information graphs (hyperedges, per-run content relations, time-respecting traversal) | `agentwatch/graph` | tested + AWBench H2 |
| Provenance, dependents | `agentwatch/provenance` | tested + AWBench H3 |
| Run inspection and comparison | `agentwatch/compare` | tested + AWBench H4 |
| Motifs (7), profiles v2, genome, distances, drift with power check | `agentwatch/behaviour` | tested + AWBench H5/H7 |
| Causality: hypotheses with computed evidence class; causes/effects | `agentwatch/causality` | tested + AWBench |
| Lab: observe, replay L0–L3 (stale captures never served), branches, counterfactuals | `agentwatch/lab` | end-to-end tests + AWBench |
| Latent states, forecasting frameworks | `agentwatch/state`, `agentwatch/forecasting` | tested (EXPERIMENTAL, insufficient-data paths) |
| Query engine (structured + deterministic NL routing) | `agentwatch/query/engine.py` | tested + AWBench faithfulness |
| API `/api/v3` + `/v1/traces` + legacy tee | `agentwatch/api/v3.py` | tested |
| CLI (24 commands + `evidence` group) | `agentwatch/cli/v3.py` | end-to-end tests |
| Frontend: LIVE, MAP, TIMELINE, LAB, GENOME, COMPARE, QUERY | `frontend/` | Jest, type-check, lint, build; verified in a browser against live data |
| AWBench (3 architectures × 16 scenarios, 10 tasks, pre-registered thresholds) | `benchmarks/awbench` | results committed |
| Performance benchmark | `benchmarks/perf` | results committed |
| Misleading v0.2 outputs relabelled | `api/server.py`, `replay/counterfactual.py`, `governance/causal.py` | tested |

## Known limitations (honest list)

- **H1 cross-source equivalence** is below its threshold (0.80 < 0.90). OTel lacks a convention for artifact writes.
- **AWBench results are in-sample** and come from stub models. No analytic capability is VALIDATED yet; see RESEARCH_HYPOTHESES §6.
- **Full rebuild per interpretation**: 5.2 s for 4k events on a laptop. Fine for development-scale stores; large deployments need incremental processing.
- **Storage** is about 9.6 KB per observation, including derived rows and relations. Not optimized.
- **Privacy**: there is no per-subject encryption or crypto-shredding yet (ADR-0011). Erasure is available only as authorized purge of whole sealed segments. Secret redaction is on by default; PII redaction is opt-in (`PayloadPolicy(redact_pii=True)`).
- **Replay** only mocks calls made through `aw.tool` / `aw.model` / `aw.retriever`. Other program logic runs live, and the reports say so.
- **Entity resolution** is exact-key only. There is no aliasing (e.g. model version aliases).
- **Legacy HIPAA redactor** (v0.2) misses US SSNs and mislabels email local parts as MRNs, as observed in the regression test. It is a v0.2 module and has not been fixed here.
- **Packaging split** (ADR-0008) and legacy quarantine (M2) are not done. The base install still includes the server stack.
- Local development used Python 3.14 against a `>=3.12,<3.13` pin (`--ignore-requires-python`). CI runs 3.12.

## Next exact tasks

1. M2: move DEPRECATE modules to `agentwatch/legacy/` with import shims, and add an import-linter contract to CI.
2. AWBench: held-out architecture(s), real-model runs behind an opt-in flag, multiple seeds with CIs.
3. OTel normalizer: map `file.*` / `db.operation=insert` attributes to STATE_MUTATION, and re-measure H1.
4. Incremental normalization keyed by run, once a workload needs it.
5. Crypto-shredding for per-subject erasure.
