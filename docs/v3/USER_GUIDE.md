# AgentWatch v3 — User Guide

AgentWatch v3 passively records what an AI-native system does. It reconstructs each run as an execution graph and an information graph, and lets you inspect, compare, replay and question that reconstruction. Every answer points back to immutable raw evidence.

Everything below describes features that exist on the `architecture/v3` branch. Maturity labels, as shown by `agentwatch status`, tell you what has been validated. Most analysis features are still **EXPERIMENTAL**.

## 1. Install

```bash
pip install -e ".[dev]"            # from a checkout (Python 3.12)
pip install "agentwatch-ai[otel]"  # optional: OTLP protobuf decoding and the OTel SDK processor
```

By default the store is `~/.agentwatch/agentwatch.db` (SQLite). You can point it elsewhere with `--store` or `AGENTWATCH_STORE`:

```bash
export AGENTWATCH_STORE=sqlite:///./aw.db
export AGENTWATCH_STORE=postgresql+psycopg://user:pass@host:5432/agentwatch   # server mode
```

## 2. Record a program

### Native SDK

```python
from agentwatch import instrument as aw

@aw.retriever("kb")
def search(q): ...

@aw.model("anthropic/claude-sonnet-5")
def llm(prompt): ...

@aw.tool("calculator")
def calc(expr): ...

with aw.run("research"):
    with aw.span("OPERATION", "plan", actor="agent:planner") as plan:
        docs = search("solar")
        answer = llm(prompt_from(docs))
        aw.memory_write("notes", "k", answer)
    with aw.span("OPERATION", "write", actor="agent:writer", links=[plan]):  # multi-parent
        aw.artifact("report.md", answer)
```

The SDK provides:

- `aw.message`
- `aw.delegate`
- `aw.memory_read`
- `aw.external_input`
- `aw.event` (point events)
- `aw.tag(**attrs)`

### Run it under observation

```bash
agentwatch observe python examples/research_system.py
agentwatch observe python examples/research_system.py --variant flaky_tool
```

`observe` runs the program in its own process. It records its command so the run can be replayed later, ingests what it recorded, and prints the run id.

### Other sources

| Source | How |
|---|---|
| OpenTelemetry (incl. GenAI conventions) | Send OTLP/HTTP to `POST /v1/traces`, add `AgentWatchSpanProcessor(sink)` to your SDK, or run `agentwatch ingest spans.json` |
| LangChain / LangGraph | `callbacks=[AgentWatchLangChainSensor(sink)]` (keeps `run_id` / `parent_run_id`) |
| Claude Code | `agentwatch ingest transcript.jsonl` (stream-json or transcript files) |
| OpenAI / Anthropic SDK | `instrument_openai(client, sink)`, `instrument_anthropic(client, sink)` |
| MCP | `MCPTap(sink, server="github").record(direction, message)` |
| v0.2 `AgentEvent` | `POST /api/v1/events` (automatically teed into v3) or `agentwatch ingest events.jsonl` |

Each legacy event goes through `LegacyTranslator`, which reports ACCEPTED, ACCEPTED_WITH_LOSS or REJECTED, together with the fields that were lost.

## 3. Investigate

```bash
agentwatch runs                                # reconstructed runs
agentwatch inspect latest                      # execution tree, failures, motifs, missing facts
agentwatch events latest --kind TOOL_INVOCATION
agentwatch show <event>                        # normalized event + raw evidence + relations
agentwatch graph latest --view information --format dot | dot -Tsvg > g.svg
agentwatch provenance report.md --run latest   # where did this come from?
agentwatch dependents report.md                # what depends on it?
agentwatch compare latest~1 latest             # earliest divergence, structure, resources
agentwatch motifs latest                       # behavioural motifs (EXPERIMENTAL)
agentwatch causes <event>                      # dependency / correlation / hypotheses / interventions
agentwatch effects <event>
agentwatch query "why did latest take longer than latest~1?"
```

Run references can be full ids, prefixes, run names, `latest` or `latest~N`.

**What the outputs mean**

- **Missing facts stay missing.** If the source didn't declare an actor, parent, run or timestamp, the event lists it under `missing`. AgentWatch never invents these.
- **Relation basis.**
  - `DECLARED`: the source said so.
  - `CONTENT_MATCH`: identical content, or text containment (with a confidence).
  - `KEY_MATCH`: same memory key, content unverified.
  - `HEURISTIC`: for example retries; labelled as such.
- **Dependency is not causation.** `compare` reports a *dependency cone*. `causes` keeps four sections separate:
  - dependency (OBSERVATIONAL);
  - cross-run correlation (CORRELATIONAL);
  - hypotheses, whose evidence class is computed from recorded evidence;
  - interventions (INTERVENTIONAL / VERIFIED).

## 4. Replay, branch, counterfactual (LAB)

```bash
agentwatch replay latest --level L0   # timeline reconstruction, nothing executed
agentwatch replay latest --level L1   # re-derive structure from raw evidence and check consistency
agentwatch replay latest --level L2   # re-execute; every instrumented call served from captures
agentwatch replay latest --level L3 --live calculator  # selected calls run live
agentwatch branch latest --at <retrieval-event> --substitute '[{"id":"X","text":"..."}]'
agentwatch counterfactual latest --at <event> --alternative '<json>'
agentwatch branches latest
```

Replay is never claimed to be deterministic. Each replay reports:

- `reproduction_confidence` (uncalibrated),
- the components that were mocked or run live,
- missing dependencies,
- *stale captures*: a recorded result whose input no longer matches is never served.

Counterfactual results are labelled with one of:

| Label | Meaning |
|---|---|
| OBSERVED | recorded in the source run |
| SIMULATED | produced by an actual branch run |
| MODEL_ESTIMATED | from ≥3 historical runs where the alternative happened |
| UNKNOWN | neither of the above is available |

## 5. Behaviour over many runs (EXPERIMENTAL)

```bash
agentwatch genome name:research_system
agentwatch drift variant:normal variant:model_v2
agentwatch states
agentwatch forecast latest
agentwatch forecast --evaluate
```

- **Drift** runs permutation tests with FDR control. It reports `insufficient_data` or `underpowered` rather than "no drift" when the sample cannot support a conclusion.
- **States and forecasts** are baselines. They return `insufficient_data` until enough runs exist.

## 6. Evidence integrity

```bash
agentwatch evidence verify                                   # seal pending observations, verify the Merkle chain
agentwatch evidence show <obs_id>                            # raw observation + inclusion proof
agentwatch evidence purge --older-than-days 90 --reason "retention" --yes
agentwatch reprocess                                         # rebuild the interpretation from evidence
```

Raw observations cannot be updated or deleted. Database triggers reject both. Retention removes whole sealed segments, and the purge authorization is recorded. Secrets are redacted before storage, and a redaction manifest is kept.

## 7. Server and UI

```bash
AGENTWATCH_STORE=postgresql+psycopg://... uvicorn agentwatch.api.server:app   # /api/v3 + /v1/traces
cd frontend && AGENTWATCH_API_URL=http://localhost:8000 npm run dev            # http://localhost:3000
```

The UI has seven views, all reading the same `/api/v3` model: **LIVE, MAP, TIMELINE, LAB, GENOME, COMPARE, QUERY**. Re-execution from the API (L2/L3, branches) is disabled unless the server sets `AGENTWATCH_ALLOW_REEXECUTION=1`.

## 8. Benchmarks

```bash
python -m benchmarks.awbench.runner      # AWBench; writes benchmarks/awbench/results/
python -m benchmarks.perf.v3_perf        # throughput and latency measurements
```
