# AgentWatch v3 — Implementation State

Branch: `architecture/v3` · Updated 2026-09-26

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
- **AWBench results come from stub models.** No analytic capability is VALIDATED yet. Two held-out architectures exist (RESEARCH_HYPOTHESES §6.2); both have since informed fixes. On first contact, `hybrid_rag_cache` failed information precision (0.53) and motif recall (0.55).
- **Information precision** is below 0.75 on both held-out architectures (0.47, 0.51). Identical content produced by several events stays ambiguous.
- **Content-shortcut reduction** (graph.information@5) can explain a report through an unused intermediate that reproduces the same text. This produces false M006 bottlenecks (map_reduce: 21/21 runs).
- **Processing**: new observations are processed incrementally per correlation group, which is about 11× faster than a full rebuild for one new run in a 4k-event store. LangChain observations (no run-scoped key), run-less events and unresolved links fall back to a full rebuild. Entity aggregation still reads all events.
- **Storage** is about 9.6 KB per observation, including derived rows and relations. Not optimized.
- **Privacy**: per-subject crypto-shredding exists but is opt-in (`AGENTWATCH_ENCRYPT_PAYLOADS=1`), and declared ids are not encrypted (ADR-0011, as built). Secret redaction is on by default; PII redaction is opt-in (`PayloadPolicy(redact_pii=True)`).
- **Replay** only mocks calls made through `aw.tool` / `aw.model` / `aw.retriever`. Other program logic runs live, and the reports say so.
- **Entity resolution** is exact-key only. There is no aliasing (e.g. model version aliases).
- **Legacy HIPAA redactor** (v0.2) misses US SSNs and mislabels email local parts as MRNs, as observed in the regression test. It is a v0.2 module and has not been fixed here.
- **Packaging split** (ADR-0008) is scheduled with M4; the base install still includes the server stack. Legacy quarantine is logical and enforced by a CI contract test (ADR-0016).
- Local development used Python 3.14 against a `>=3.12,<3.13` pin (`--ignore-requires-python`). CI runs 3.12.

## Next exact tasks

1. M4 (owner decision): merge to `main` together with the packaging split (ADR-0008, ADR-0016).
2. AWBench: a third held-out architecture (to test graph.information@5), and real-model runs behind an opt-in flag.
3. OTel normalizer: map `file.*` / `db.operation=insert` attributes to STATE_MUTATION, and re-measure H1.
