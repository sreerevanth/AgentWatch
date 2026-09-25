# AgentWatch v3 — Implementation State

Branch: `architecture/v3` · Living document, updated at each milestone.

## Completed

| Area | Package | Notes |
|---|---|---|
| Evidence plane | `agentwatch/evidence`, `agentwatch/storage` | `RawObservation` (frozen; copy-on-read payload), edge redaction with manifest, SQLite/Postgres store (SQLAlchemy Core), DB triggers reject UPDATE/DELETE, idempotent append, blobs, Merkle segments, verify, inclusion proofs, authorized purge |
| Sensors | `agentwatch/sensors`, `agentwatch/instrument.py` | native SDK (`aw.run/span/tool/model/retriever/memory_*/message/delegate/artifact`), OTel (OTLP JSON/protobuf, SpanProcessor), LangChain (keeps run_id/parent_run_id), Claude Code, OpenAI/Anthropic client wrappers, MCP tap, `LegacyTranslator` (ACCEPTED / ACCEPTED_WITH_LOSS / REJECTED) |
| Events | `agentwatch/events` | `ComputationalEvent` with explicit `missing`, declared links, normalizers for every sensor, registry + entry points |
| Engine | `agentwatch/runtime/engine.py` | versioned interpretation id = hash of component versions; deterministic full rebuild; invariant: every observation → event or diagnostic |
| Runs / entities | `agentwatch/runs`, `agentwatch/entities` | runs only from declared ids (+ parent-chain inheritance, recorded); exact-key entities |
| Graph | `agentwatch/graph` | EXECUTION + INFORMATION builders (declared, content-match, key-match, retry heuristic), hyperedge relations, traversal |
| Read model | `agentwatch/query/workspace.py` | single read model for CLI/API/frontend |
| Provenance | `agentwatch/provenance` | lineage trees with execution context, dependents, EXPERIMENTAL metrics |
| Compare | `agentwatch/compare` | signature alignment, earliest divergence, structural/resource/information/motif diffs, dependency-cone share |
| Behaviour | `agentwatch/behaviour` | 7 motifs, profiles, genome with bootstrap CIs, 4 candidate distances, permutation drift + BH |
| Causality | `agentwatch/causality` | hypotheses with computed evidence class; causes/effects with separate dependency/correlation/hypothesis/intervention sections |
| Lab | `agentwatch/lab` | observe, replay L0–L3 (stale captures never served), branches, counterfactuals (SIMULATED/MODEL_ESTIMATED/UNKNOWN) |
| State / forecasting | `agentwatch/state`, `agentwatch/forecasting` | EXPERIMENTAL baselines with insufficient-data handling |
| Query | `agentwatch/query/engine.py` | structured grammar + deterministic NL patterns; evidence ids on every answer |
| CLI | `agentwatch/cli/v3.py` | all v3 commands; legacy `compare` → `agentwatch legacy compare` |
| Example | `examples/research_system.py` | deterministic multi-agent pipeline with variants |

## Currently implementing
- `/api/v3` router + OTLP `/v1/traces` + legacy tee; fix of the v0.2 shared-event redaction race

## Remaining (in order)
1. API v3 + tests (API, CLI, graph, provenance, compare, motifs, causality, lab, query)
2. Postgres store test in CI (service container exists)
3. AWBench (systems, perturbations, ground truth, tasks, runner, results; thresholds separate)
4. Performance benchmarks (ingest, normalize, graph build, traversal, query, storage)
5. Frontend rebuild: LIVE, MAP, TIMELINE, LAB, GENOME, COMPARE, QUERY on `/api/v3`
6. Relabel misleading v0.2 features (`/simulate`, `hallucination_risk`, `governance/causal.py`)
7. Docs: user guide, API reference, metric definitions, updates to V3_ARCHITECTURE/MIGRATION_MAP
8. Final quality gate

## Decisions made during implementation
- Packages sit at top level of `agentwatch/` (`evidence`, `events`, …). `lab/` holds replay/branch/counterfactual because `agentwatch/replay` is the v0.2 module.
- Evidence and derived data share one SQL store. Derived rows are keyed by `interp_id`, and rebuilds replace them atomically. Postgres rebuilds take an advisory lock.
- Replay keys instrumented calls by `kind|operation|ordinal`. A capture is served only when the call's input hash matches the recorded input.
- Content-match relations are per run, because artifacts are content-addressed and shared across runs.
- Git Credential Manager hangs in this environment. Pushes use `gh auth git-credential` (see scratch `push.sh`).
- The local Python is 3.14 while `pyproject` pins `<3.13`. The dev install uses `pip install -e . --no-deps --ignore-requires-python`.

## Known failures / limitations
- Pre-existing: none remaining. The CLI surface golden is now normalized across click versions.
- Full rebuild on every new observation batch: fine at example scale. It will be measured in the perf benchmark before any incremental design.
