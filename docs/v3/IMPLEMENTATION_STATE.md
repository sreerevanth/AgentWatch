# AgentWatch v3 — Implementation State

Branch: `main` (v3 merged 2026-09-27, `17d667d`) · Updated 2026-09-27 · Release readiness: [RELEASE_READINESS.md](RELEASE_READINESS.md)

## Completed

| Area | Where | Status |
|---|---|---|
| Immutable evidence: frozen observations, DB-enforced immutability, idempotent append, edge redaction + manifests, blobs, Merkle segments, verify, inclusion proofs, authorized purge | `agentwatch/evidence`, `agentwatch/storage` | tested on SQLite and PostgreSQL (CI) |
| Crypto-shredding: per-subject keys, erasure destroys the key and purges derived copies | `agentwatch/evidence/crypto.py`, `storage` | tested; graph invariant: erased data is not reconstructable |
| Sensors: native SDK (incl. runtime object identity and explicit `source=`), OTel (OTLP JSON/protobuf, SpanProcessor, `agentwatch.*` extension attributes), LangChain, Claude Code, OpenAI/Anthropic wrappers, MCP tap, LegacyTranslator | `agentwatch/sensors`, `agentwatch/instrument.py` | tested |
| Normalizers + canonical event algebra with explicit missing facts | `agentwatch/events` | tested |
| Engine: versioned, deterministic rebuild; incremental per correlation group (with cross-run memory context); every observation → event or diagnostic | `agentwatch/runtime` | tested; incremental == full over random programs |
| Runs from declared ids only; exact-key entities | `agentwatch/runs`, `agentwatch/entities` | tested |
| Execution graph | `agentwatch/graph/build.py` | **VALIDATED**: AWBench H2 F1 1.0 on development and on the first run of all three held-out architectures |
| Information graph over information instances, with an evidence hierarchy and preserved ambiguity (ADR-0017) | `agentwatch/graph/information.py` | high-fidelity mode **VALIDATED** (held-out code_review_pipeline: information P/R 1.0/0.92, lineage F1 0.91); best-effort mode EXPERIMENTAL |
| Provenance with ambiguity records and per-run evidence summaries | `agentwatch/provenance` | tested; API/CLI parity |
| Run comparison (retry-aware earliest divergence) | `agentwatch/compare` | tested + AWBench H4 |
| Motifs (7), profiles, genome, drift with power check | `agentwatch/behaviour` | tested + AWBench H5/H7 |
| Causality: hypotheses with computed evidence class; causes/effects | `agentwatch/causality` | tested + AWBench |
| Lab: observe, replay L0–L3, branches, counterfactuals, experiments API | `agentwatch/lab` | end-to-end tests + AWBench |
| Latent states, forecasting | `agentwatch/state`, `agentwatch/forecasting` | EXPERIMENTAL, insufficient-data paths tested |
| Query engine | `agentwatch/query/engine.py` | tested + AWBench faithfulness |
| API `/api/v3` + `/v1/traces` + legacy tee | `agentwatch/api/v3.py` | tested; parity with read model and CLI |
| CLI (v3 commands + `evidence` group; `doctor` checks the v3 store) | `agentwatch/cli/v3.py` | full-surface test on a store written by `observe` |
| Frontend: LIVE, MAP, TIMELINE, LAB, GENOME, COMPARE, QUERY (values, evidence strength, ambiguity, erased state) | `frontend/` | Jest, type-check, build; production build verified against live data |
| AWBench: 3 development + 4 held-out architectures, computed evidence status, pre-registration, opt-in real-model mode | `benchmarks/awbench` | results committed |
| Performance benchmark (with comparison to the previous run) | `benchmarks/perf` | results committed |
| Docker images (API, frontend) | `Dockerfile.api`, `frontend/Dockerfile` | built in CI on every push |

## Known limitations

- **Best-effort information lineage is conservative, and its recall is low.**
  - With value-level telemetry, an intermediate that only copies text can't be proven to have been used rather than its sources. It is kept as an ambiguous candidate. AWBench's stub models are extractive, so this shows up everywhere there.
  - Held-out `async_event_pipeline`, first run: information precision 0.95, recall of certain links 0.51; lineage precision 1.0, recall 0.20.
  - With candidates, recall rises to 0.58–0.95 at lower precision.
  - Declared inputs (`source=`, passing the produced object, OTel `agentwatch.information.source`) make lineage exact.
- **H1 cross-source equivalence (OTel only) is 0.80 < 0.90.**
  - OpenTelemetry has no artifact-write convention.
  - With the AgentWatch extension it is 1.0. That figure is unthresholded: the extension is AgentWatch's own mapping.
- **M006 (information bottleneck)** fires only when a bottleneck is certain, so recall is low with extractive intermediates.
- **Content matching has a resolution limit.** Candidates that differ by fewer shingles than one concatenation seam (4) cannot be separated.
- **AWBench uses stub models.** Real-model runs are implemented (`--real-model`) but have not been run: no usable credential was available. The OpenAI key in this environment is rejected by the provider (401, `account_deactivated`).
- **Held-out status.** Three held-out architectures have informed fixes and are FORMER_HELD_OUT. The fourth (`code_review_pipeline`, high-fidelity) met every threshold on its first run. It becomes FORMER_HELD_OUT on the next AgentWatch code change, so a fifth is needed for any later change.
- **Privacy.**
  - Crypto-shredding is opt-in (`AGENTWATCH_ENCRYPT_PAYLOADS=1`), and declared ids are not encrypted (ADR-0011).
  - PII redaction is opt-in.
- **Replay** mocks only instrumented calls. Other program logic runs live, as the reports say.
- **Entity resolution** is exact-key only.
- **Packaging split (ADR-0008)** is not done; the base install still includes the server stack.
- **Python versions.** Local development used Python 3.14 against a `>=3.12,<3.13` pin; CI runs 3.12.

## Next exact tasks

1. Owner decision: the packaging split (ADR-0008) and a release tag. v3 is merged into `main`.
2. Run AWBench `--real-model` with a working credential, and the `external` test marker.
3. A fifth held-out architecture before claiming anything about later changes; a real-model held-out run would test best-effort lineage on abstractive outputs.
