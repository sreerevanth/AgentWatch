"""AWBench reference systems (deterministic, offline).

    python workbench.py --arch rag_memory --scenario corrupted_retrieval --seed 3 --gt out.json

Architectures:
    tool_loop    single model-driven tool loop
    rag_memory   retrieval → summarize → memory → write, with a second retrieval round
    multi_agent  planner delegates to researcher/analyst/critic, synthesizer joins results

Ground truth (what really happened, including the injected root cause) is written to
``--gt``. Ground truth never goes into the observation stream; the only benchmark-specific
value AgentWatch sees is an opaque ``awbench_id`` span attribute used by the evaluator to
match events to ground-truth nodes.

``--sensor otel`` records the tool_loop architecture through OpenTelemetry spans (via the
AgentWatch SpanProcessor) instead of the native SDK, for cross-source comparison.
"""

from __future__ import annotations

import argparse
import asyncio
import contextvars
import json
import random
import sys
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from agentwatch import instrument as aw

SCENARIOS = [
    "normal",
    "bad_retrieval",
    "corrupted_retrieval",
    "stale_memory",
    "duplicate_memory",
    "tool_timeout",
    "tool_error",
    "incorrect_tool_result",
    "message_duplication",
    "message_loss",
    "context_pressure",
    "model_substitution",
    "latency_injection",
    "retry_loop",
    "delegation_loop",
    "resource_contention",
]

CORPUS = {
    "D1": "Solar photovoltaic panels convert sunlight into direct current electricity using silicon cells.",
    "D2": "Inverters convert the direct current from solar panels into alternating current for the grid.",
    "D3": "Battery storage lets households use solar electricity after sunset and during outages.",
    "D4": "Panel efficiency for commercial silicon modules typically ranges from eighteen to twenty two percent.",
    "D5": "Medieval castles used thick stone walls, towers and moats to defend against sieges.",
    "D6": "Tidal energy uses the rise and fall of ocean tides to spin underwater turbines.",
}
RELEVANT = ["D1", "D2", "D3", "D4"]


class _ContextStack:
    """The ground-truth parent stack, per execution context: concurrent asyncio tasks each
    see their own stack (a plain list would interleave their parents)."""

    def __init__(self) -> None:
        self._var: contextvars.ContextVar[tuple[str, ...]] = contextvars.ContextVar(
            "gt_stack", default=()
        )

    def append(self, nid: str) -> None:
        self._var.set((*self._var.get(), nid))

    def pop(self) -> str:
        cur = self._var.get()
        self._var.set(cur[:-1])
        return cur[-1]

    def __getitem__(self, i: int) -> str:
        return self._var.get()[i]

    def __bool__(self) -> bool:
        return bool(self._var.get())


class GroundTruth:
    def __init__(self, arch: str, scenario: str, seed: int) -> None:
        self.data: dict[str, Any] = {
            "arch": arch,
            "scenario": scenario,
            "seed": seed,
            "nodes": {},
            "exec_edges": [],
            "data_edges": [],
            "root_cause": None,
            "expected_motifs": [],
            "origin_docs": [],
            "final_output": None,
            "outcome": "ok",
        }
        self.counts: dict[str, int] = {}
        self.stack = _ContextStack()

    def node(self, label: str, kind: str) -> str:
        self.counts[label] = self.counts.get(label, 0) + 1
        nid = f"{label}#{self.counts[label]}"
        self.data["nodes"][nid] = {"kind": kind, "label": label}
        if self.stack:
            self.data["exec_edges"].append([self.stack[-1], nid])
        return nid

    def flow(self, producer: str, consumer: str) -> None:
        self.data["data_edges"].append([producer, consumer])


GT: GroundTruth
RNG: random.Random
SCEN: str


@contextmanager
def op(kind: str, label: str, **kw: Any) -> Any:
    nid = GT.node(label, kind)
    with aw.span(kind, label, awbench_id=nid, **kw) as s:
        GT.stack.append(nid)
        try:
            yield s, nid
        finally:
            GT.stack.pop()


def call(kind: str, label: str, fn: Any, arg: Any, *, obj: str, actor: str) -> tuple[Any, str]:
    """An instrumented, replayable call tagged with its awbench id."""
    nid = GT.node(label, kind)
    deco = {"TOOL_INVOCATION": aw.tool, "RETRIEVAL": aw.retriever, "MODEL_INVOCATION": aw.model}[
        kind
    ]
    inner = deco(obj, actor=actor)(fn)
    GT.stack.append(nid)
    try:
        with aw.tag(awbench_id=nid):
            out = inner(arg)
    finally:
        GT.stack.pop()
    return out, nid


# ── stubs ──────────────────────────────────────────────────────────────────
# which retrieval calls a retrieval scenario perturbs (map_reduce perturbs only one worker)
PERTURB = {"retrieval": True}


def retrieve_docs(query: str) -> list[dict[str, str]]:
    if SCEN == "bad_retrieval" and PERTURB["retrieval"]:
        ids = ["D5", "D6"]
    else:
        ids = sorted(RNG.sample(RELEVANT, 3))  # seed-dependent choice of relevant documents
    docs = [{"id": i, "text": CORPUS[i]} for i in ids]
    if SCEN == "corrupted_retrieval" and PERTURB["retrieval"]:
        docs[0] = {"id": docs[0]["id"], "text": "#### corrupted #### " + docs[0]["text"][::-1]}
    if SCEN == "latency_injection":
        time.sleep(0.05)
    return docs


def summarize_v1(prompt: str) -> str:
    lines = [ln.lstrip("- ") for ln in prompt.splitlines() if ln.startswith("- ")]
    return "Summary: " + " ".join(lines[:3])


def summarize_v2(prompt: str) -> str:
    lines = [ln.lstrip("- ") for ln in prompt.splitlines() if ln.startswith("- ")]
    return "Detailed summary. " + " ".join(lines) + " End of summary."


_calc_state = {"fail": 0}


def calculator(expr: str) -> float:
    time.sleep(RNG.uniform(0, 0.003))  # seeded latency jitter
    if _calc_state["fail"] > 0:
        _calc_state["fail"] -= 1
        raise TimeoutError("calculator timed out")
    if SCEN == "tool_error":
        raise ValueError("calculator: malformed expression")
    a, o, b = expr.split()
    val = {"*": float(a) * float(b), "+": float(a) + float(b)}[o]
    if SCEN == "incorrect_tool_result":
        val = val * 10
    return val


# ── architectures ──────────────────────────────────────────────────────────
def arch_tool_loop() -> None:
    model = summarize_v2 if SCEN == "model_substitution" else summarize_v1
    model_name = "stub/summarizer-v2" if SCEN == "model_substitution" else "stub/summarizer-v1"
    with op("OPERATION", "agent_loop", actor="agent:solo"):
        docs, r = call(
            "RETRIEVAL",
            "retrieve",
            retrieve_docs,
            "solar electricity",
            obj="corpus",
            actor="agent:solo",
        )
        GT.data["origin_docs"] = [d["id"] for d in docs]
        if SCEN in ("bad_retrieval", "corrupted_retrieval"):
            GT.data["root_cause"] = r
        prompt = "Context:\n" + "\n".join(f"- {d['text']}" for d in docs)
        if SCEN == "context_pressure":
            for i in range(3):
                prompt = prompt + "\n" + prompt  # context grows each turn
                _, m = call(
                    "MODEL_INVOCATION", "think", model, prompt, obj=model_name, actor="agent:solo"
                )
                GT.flow(r, m)
            GT.data["expected_motifs"].append("M005")
            GT.data["root_cause"] = GT.data["root_cause"] or "think#1"
        summary, m = call(
            "MODEL_INVOCATION", "summarize", model, prompt, obj=model_name, actor="agent:solo"
        )
        GT.flow(r, m)
        if SCEN == "model_substitution":
            GT.data["root_cause"] = m
        value, t = _calc_with_retries()
        with op(
            "STATE_MUTATION", "write_report", actor="agent:solo", facets=["artifact_creation"]
        ) as (s, w):
            s.output(f"{summary}\nEstimate: {value}", role="artifact", label="report.md")
            GT.flow(m, w)
            if t:
                GT.flow(t, w)
            GT.data["final_output"] = w


def _calc_with_retries() -> tuple[Any, str | None]:
    if SCEN in ("tool_timeout", "retry_loop"):
        # seed-dependent number of failures before success
        fails = RNG.randint(1, 3) if SCEN == "tool_timeout" else RNG.randint(3, 4)
        _calc_state["fail"] = fails
        GT.data["expected_motifs"].append("M001")  # >=2 attempts form a retry chain
        if fails + 1 >= 3:
            GT.data["expected_motifs"].append("M002")  # >=3 identical calls
    last = None
    first = None
    for _ in range(5):
        try:
            v, last = call(
                "TOOL_INVOCATION",
                "calculate",
                calculator,
                "5 * 365",
                obj="calculator",
                actor="agent:analyst",
            )
            first = first or last
            if SCEN in ("tool_timeout", "retry_loop", "tool_error", "incorrect_tool_result"):
                GT.data["root_cause"] = GT.data["root_cause"] or "calculate#1"
            return v, last
        except TimeoutError:
            first = first or f"calculate#{GT.counts.get('calculate', 1)}"
            continue
        except ValueError:
            GT.data["root_cause"] = GT.data["root_cause"] or "calculate#1"
            GT.data["outcome"] = "degraded"
            return None, f"calculate#{GT.counts.get('calculate', 1)}"
    return None, last


def arch_rag_memory() -> None:
    model = summarize_v2 if SCEN == "model_substitution" else summarize_v1
    model_name = "stub/summarizer-v2" if SCEN == "model_substitution" else "stub/summarizer-v1"
    memory: dict[str, str] = {
        "notes": "Old note: solar is only for satellites and space probes in orbit."
    }
    with op("OPERATION", "rag_pipeline", actor="agent:rag"):
        docs, r = call(
            "RETRIEVAL",
            "retrieve",
            retrieve_docs,
            "solar electricity",
            obj="corpus",
            actor="agent:rag",
        )
        GT.data["origin_docs"] = [d["id"] for d in docs]
        if SCEN in ("bad_retrieval", "corrupted_retrieval"):
            GT.data["root_cause"] = r
        prompt = "Context:\n" + "\n".join(f"- {d['text']}" for d in docs)
        summary, m = call(
            "MODEL_INVOCATION", "summarize", model, prompt, obj=model_name, actor="agent:rag"
        )
        GT.flow(r, m)
        if SCEN == "model_substitution":
            GT.data["root_cause"] = m
        with op(
            "MEMORY_ACCESS",
            "write:notes",
            object="memory:notes",
            actor="agent:rag",
            facets=["write"],
        ) as (s, w):
            s.input(summary, role="value", label="notes").set(key="notes", access="write")
            GT.flow(m, w)
        memory["notes"] = summary
        if SCEN == "duplicate_memory":
            with op(
                "MEMORY_ACCESS",
                "write:notes",
                object="memory:notes",
                actor="agent:rag",
                facets=["write"],
            ) as (s, w2):
                s.input(summary, role="value", label="notes").set(key="notes", access="write")
        read_value = (
            memory["notes"]
            if SCEN != "stale_memory"
            else "Old note: solar is only for satellites and space probes in orbit."
        )
        with op(
            "MEMORY_ACCESS",
            "read:notes",
            object="memory:notes",
            actor="agent:writer",
            facets=["read"],
        ) as (s, rd):
            s.set(key="notes", access="read").output(read_value, role="value", label="notes")
            if SCEN != "stale_memory":
                GT.flow(w, rd)
            else:
                GT.data["root_cause"] = rd

        # second round: retrieve again using the note (retrieval echo when the note is indexed)
        def retrieve_again(q: str) -> list[dict[str, str]]:
            return [{"id": "NOTE", "text": read_value}, {"id": "D4", "text": CORPUS["D4"]}]

        docs2, r2 = call(
            "RETRIEVAL",
            "retrieve",
            retrieve_again,
            read_value[:40],
            obj="corpus",
            actor="agent:writer",
        )
        GT.flow(rd, r2)
        GT.data["expected_motifs"].append(
            "M004"
        )  # the note (model output) comes back through retrieval
        with op(
            "STATE_MUTATION", "write_report", actor="agent:writer", facets=["artifact_creation"]
        ) as (s, fw):
            s.output(
                "# Report\n" + " ".join(d["text"] for d in docs2),
                role="artifact",
                label="report.md",
            )
            GT.flow(r2, fw)
            GT.data["final_output"] = fw


def arch_multi_agent() -> None:
    lock = threading.Lock()
    with op("OPERATION", "plan", actor="agent:planner") as (_, p):
        for target in ("agent:researcher", "agent:analyst"):
            with op("DELEGATION", f"delegate:{target}", actor="agent:planner", object=target) as (
                s,
                _d,
            ):
                s.input({"task": target}, role="task").output({"task": target}, role="task")
        if SCEN == "delegation_loop":
            for _ in range(2):
                for a, b in (("agent:planner", "agent:critic"), ("agent:critic", "agent:planner")):
                    with op("DELEGATION", f"delegate:{b}", actor=a, object=b) as (s, _d):
                        s.input({"task": "revise"}, role="task").output(
                            {"task": "revise"}, role="task"
                        )
            GT.data["expected_motifs"].append("M003")
            GT.data["root_cause"] = "delegate:agent:critic#1"
        with op("OPERATION", "research", actor="agent:researcher") as (rs, rnode):
            docs, r = call(
                "RETRIEVAL",
                "retrieve",
                retrieve_docs,
                "solar",
                obj="corpus",
                actor="agent:researcher",
            )
            GT.data["origin_docs"] = [d["id"] for d in docs]
            if SCEN in ("bad_retrieval", "corrupted_retrieval"):
                GT.data["root_cause"] = r
            model = summarize_v2 if SCEN == "model_substitution" else summarize_v1
            model_name = (
                "stub/summarizer-v2" if SCEN == "model_substitution" else "stub/summarizer-v1"
            )
            findings, m = call(
                "MODEL_INVOCATION",
                "summarize",
                model,
                "Context:\n" + "\n".join(f"- {d['text']}" for d in docs),
                obj=model_name,
                actor="agent:researcher",
            )
            GT.flow(r, m)
            if SCEN == "model_substitution":
                GT.data["root_cause"] = m
        with op("OPERATION", "analysis", actor="agent:analyst") as (asp, anode):
            if SCEN == "resource_contention":
                results = []

                def worker(i: int) -> None:
                    with lock:
                        time.sleep(0.01)
                    results.append(i)

                ts = [threading.Thread(target=worker, args=(i,)) for i in range(4)]
                for t in ts:
                    t.start()
                for t in ts:
                    t.join()
                GT.data["root_cause"] = "calculate#1"
            value, t = _calc_with_retries()
        msgs = [findings]
        if SCEN == "message_duplication":
            msgs = [findings, findings]
        if SCEN == "message_loss":
            msgs = []
            GT.data["root_cause"] = "send:agent:synthesizer#1"
            GT.data["outcome"] = "degraded"
        first_msg = None
        for msg in msgs:
            with op(
                "MESSAGE",
                "send:agent:synthesizer",
                actor="agent:researcher",
                object="agent:synthesizer",
            ) as (s, mid):
                s.input(msg, role="message").output(msg, role="message")
                GT.flow(m, mid)
                first_msg = first_msg or mid
        if SCEN == "message_duplication":
            GT.data["root_cause"] = "send:agent:synthesizer#2"
        with op("OPERATION", "synthesize", actor="agent:synthesizer", links=[rs, asp]) as (s, syn):
            GT.data["exec_edges"] += [[rnode, syn], [anode, syn]]
            text = (msgs[0] if msgs else "No findings received.") + f" Estimate: {value}"
            with op(
                "STATE_MUTATION",
                "write_report",
                actor="agent:synthesizer",
                facets=["artifact_creation"],
            ) as (ws, fw):
                ws.output(text, role="artifact", label="report.md")
                if msgs:
                    GT.flow(m, fw)
                    GT.flow(
                        first_msg, fw
                    )  # the report text is built from the first received message
                GT.data["final_output"] = fw


def arch_map_reduce() -> None:
    """HELD-OUT architecture (added after AgentWatch development; never used to tune it).

    planner fans a question out to three workers; each retrieves and summarizes one facet;
    the reducer joins the worker results (multi-parent), a critic model reviews the merged
    draft and may call a checker tool, and the final report is written.
    """
    model = summarize_v2 if SCEN == "model_substitution" else summarize_v1
    model_name = "stub/summarizer-v2" if SCEN == "model_substitution" else "stub/summarizer-v1"
    facets = ["cost", "efficiency", "storage"]
    with op("OPERATION", "plan", actor="agent:planner"):
        worker_spans = []
        worker_nodes = []
        results: list[tuple[str, str]] = []
        for i, facet in enumerate(facets):
            with op("OPERATION", f"worker:{facet}", actor=f"agent:worker{i}") as (ws, wnode):
                PERTURB["retrieval"] = i == 1  # retrieval scenarios hit worker 1 only
                worker_spans.append(ws)
                worker_nodes.append(wnode)
                docs, r = call(
                    "RETRIEVAL",
                    "retrieve",
                    retrieve_docs,
                    f"solar {facet}",
                    obj="corpus",
                    actor=f"agent:worker{i}",
                )
                if SCEN in ("bad_retrieval", "corrupted_retrieval") and i == 1:
                    GT.data["root_cause"] = GT.data["root_cause"] or r
                prompt = f"Facet {facet}:\n" + "\n".join(f"- {d['text']}" for d in docs)
                summary, m = call(
                    "MODEL_INVOCATION",
                    "summarize",
                    model,
                    prompt,
                    obj=model_name,
                    actor=f"agent:worker{i}",
                )
                GT.flow(r, m)
                if SCEN == "model_substitution" and i == 0:
                    GT.data["root_cause"] = m
                if SCEN == "message_loss" and i == 2:
                    # root cause: worker 2's message to the reducer, which the baseline sends
                    GT.data["root_cause"] = GT.data["root_cause"] or "send:agent:reducer#3"
                    GT.data["outcome"] = "degraded"
                    continue  # the worker's result never reaches the reducer
                with op(
                    "MESSAGE",
                    "send:agent:reducer",
                    actor=f"agent:worker{i}",
                    object="agent:reducer",
                ) as (ms, mid):
                    ms.input(summary, role="message").output(summary, role="message")
                    GT.flow(m, mid)
                results.append((summary, mid))
        PERTURB["retrieval"] = True
        with op("OPERATION", "reduce", actor="agent:reducer", links=worker_spans) as (_, red):
            GT.data["exec_edges"] += [[w, red] for w in worker_nodes]
            merged = " ".join(text for text, _ in results)
            draft, critic = call(
                "MODEL_INVOCATION",
                "critique",
                model,
                "Review:\n" + "\n".join(f"- {t}" for t, _ in results),
                obj=model_name,
                actor="agent:critic",
            )
            for _, mid in results:
                GT.flow(mid, critic)
            value, t = _calc_with_retries()
            with op(
                "STATE_MUTATION",
                "write_report",
                actor="agent:reducer",
                facets=["artifact_creation"],
            ) as (fs, fw):
                fs.output(merged + f" Estimate: {value}", role="artifact", label="report.md")
                for _, mid in results:
                    GT.flow(mid, fw)
                if t:
                    GT.flow(t, fw)
                GT.data["final_output"] = fw


def arch_hybrid_rag_cache() -> None:
    """SECOND HELD-OUT architecture (added after the most-recent-producer / MATCHES_CONTENT /
    M005 v2 changes; never used to design them).

    Three conversation turns. Each turn: vector retrieval (+ keyword retrieval in turn 1) ->
    dedupe tool -> answer model over an accumulated history that carries earlier turns forward
    (same actor) -> cache write. From turn 2 the cached previous answer is read back into the
    history. A final report is written from the last answer.
    """
    model = summarize_v2 if SCEN == "model_substitution" else summarize_v1
    model_name = "stub/summarizer-v2" if SCEN == "model_substitution" else "stub/summarizer-v1"

    def dedupe(docs: list[dict[str, str]]) -> list[dict[str, str]]:
        seen: dict[str, dict[str, str]] = {}
        for d in docs:
            seen.setdefault(d["id"], d)
        return [seen[k] for k in sorted(seen)]

    cache: dict[str, str] = {}
    history = "Conversation history:"
    dedupe_nodes: list[str] = []
    last_answer = ""
    last_answer_node = None
    cache_write_node = ""
    with op("OPERATION", "session", actor="agent:router"):
        for turn in range(3):
            with op("OPERATION", f"turn{turn}", actor="agent:router"):
                PERTURB["retrieval"] = False
                vec, rv = call(
                    "RETRIEVAL",
                    "vector_search",
                    retrieve_docs,
                    f"solar turn {turn}",
                    obj="vector_index",
                    actor="agent:router",
                )
                sources = [rv]
                docs = list(vec)
                if turn == 0:
                    PERTURB["retrieval"] = (
                        True  # retrieval scenarios hit the keyword retriever only
                    )
                    kw, rk = call(
                        "RETRIEVAL",
                        "keyword_search",
                        retrieve_docs,
                        "solar keywords",
                        obj="keyword_index",
                        actor="agent:router",
                    )
                    PERTURB["retrieval"] = False
                    docs += kw
                    sources.append(rk)
                    if SCEN in ("bad_retrieval", "corrupted_retrieval"):
                        GT.data["root_cause"] = rk
                merged, dd = call(
                    "TOOL_INVOCATION", "dedupe", dedupe, docs, obj="dedupe", actor="agent:router"
                )
                for src in sources:
                    GT.flow(src, dd)
                cached = None
                rd = None
                if turn > 0:
                    stale = SCEN == "stale_memory" and turn == 1
                    value = (
                        "Stale cached answer from an older session about wind turbines and tidal energy."
                        if stale
                        else cache.get("last")
                    )
                    with op(
                        "MEMORY_ACCESS",
                        "read:cache",
                        object="memory:cache",
                        actor="agent:answerer",
                        facets=["read"],
                    ) as (ms, rd):
                        ms.set(key="last", access="read").output(value, role="value", label="last")
                    cached = value
                    if stale:
                        GT.data["root_cause"] = rd
                    elif last_answer_node:
                        # the cache returned what the previous turn wrote
                        GT.flow(cache_write_node, rd)
                history = (
                    history
                    + f"\nTurn {turn} context:\n"
                    + "\n".join(f"- {d['text']}" for d in merged)
                )
                if cached:
                    history = history + f"\n- previous answer: {cached}"
                answer, am = call(
                    "MODEL_INVOCATION",
                    "answer",
                    model,
                    history,
                    obj=model_name,
                    actor="agent:answerer",
                )
                GT.flow(dd, am)
                for prev in dedupe_nodes:
                    GT.flow(prev, am)  # earlier turns' documents are carried in the history
                if rd is not None:
                    GT.flow(rd, am)
                if SCEN == "model_substitution" and turn == 0:
                    GT.data["root_cause"] = am
                dedupe_nodes.append(dd)
                with op(
                    "MEMORY_ACCESS",
                    "write:cache",
                    object="memory:cache",
                    actor="agent:answerer",
                    facets=["write"],
                ) as (ws, cw):
                    ws.input(answer, role="value", label="last").set(key="last", access="write")
                    GT.flow(am, cw)
                cache["last"] = answer
                if SCEN == "duplicate_memory":
                    with op(
                        "MEMORY_ACCESS",
                        "write:cache",
                        object="memory:cache",
                        actor="agent:answerer",
                        facets=["write"],
                    ) as (ws2, cw2):
                        ws2.input(answer, role="value", label="last").set(
                            key="last", access="write"
                        )
                        GT.flow(am, cw2)
                    cw = cw2
                cache_write_node = cw
                last_answer, last_answer_node = answer, am
        GT.data["expected_motifs"].append("M005")  # the answerer's history grows turn over turn
        # every retrieved document reaches the report only through the last answer (M006 by definition)
        GT.data["expected_motifs"].append("M006")
        value, t = _calc_with_retries()
        with op(
            "STATE_MUTATION", "write_report", actor="agent:router", facets=["artifact_creation"]
        ) as (fs, fw):
            fs.output(last_answer + f" Estimate: {value}", role="artifact", label="report.md")
            GT.flow(last_answer_node, fw)
            if t:
                GT.flow(t, fw)
            GT.data["final_output"] = fw
        PERTURB["retrieval"] = True


def arch_async_event_pipeline() -> None:
    """THIRD HELD-OUT architecture (designed and committed before the information-instance /
    provenance-hierarchy changes; never used to design them).

    Event-driven asynchronous workflow, instrumented with value-level spans only (best-effort
    telemetry: no explicit instance references):

        request -> router (shared evidence retrieval) -> task queue
        workers A, B, C run concurrently (asyncio) and complete out of order:
          A: own retrieval (overlaps the shared evidence) + analysis
          B: a speculative draft that is DISCARDED, then the real analysis (same prompt, so the
             draft's text is identical to the published result)
          C: lookup tool with retries, then analysis
        the results queue delivers at least once (A's result is delivered twice)
        aggregator (multi-parent) dedupes deliveries and merges in task order
        enrichment: glossary cache per section (miss -> define tool -> cache write; the third
          section's term is a cache HIT returning the first definition), then an enrich model
        database write of the enriched record; final composer reads it back, writes the report

    It stresses same content vs same information instance: identical documents from two
    retrievals, identical draft/result texts from two model calls, identical duplicate
    deliveries, a cache hit identical to a tool output.
    """
    model = summarize_v2 if SCEN == "model_substitution" else summarize_v1
    model_name = "stub/summarizer-v2" if SCEN == "model_substitution" else "stub/summarizer-v1"
    first_model = {"done": False}

    def model_call(label: str, prompt: str, actor: str) -> tuple[str, str]:
        out, nid = call("MODEL_INVOCATION", label, model, prompt, obj=model_name, actor=actor)
        if SCEN == "model_substitution" and not first_model["done"]:
            GT.data["root_cause"] = nid  # the first model call to execute diverges first
        first_model["done"] = True
        return out, nid

    request = "How practical is residential solar power with battery storage?"
    with op("OPERATION", "handle_request", actor="agent:router"):
        with op("EXTERNAL_INPUT", "receive_request", actor="agent:router") as (rs, req):
            rs.output(request, role="request")
        PERTURB["retrieval"] = SCEN == "bad_retrieval"  # bad_retrieval: the shared evidence
        evidence, ev = call(
            "RETRIEVAL",
            "fetch_evidence",
            retrieve_docs,
            request,
            obj="evidence_index",
            actor="agent:router",
        )
        GT.flow(req, ev)
        if SCEN == "bad_retrieval":
            GT.data["root_cause"] = ev
        workers = ["A", "B", "C"]
        terms = {"A": "solar", "B": "storage", "C": "solar"}
        enq: dict[str, str] = {}
        for w in workers:
            msg = {"task": w, "term": terms[w], "request": request}
            with op("MESSAGE", f"enqueue:{w}", actor="agent:router", object="queue:tasks") as (
                ms,
                mid,
            ):
                ms.input(msg, role="message").output(msg, role="message")
                GT.flow(req, mid)
            enq[w] = mid
        # seed-dependent completion order: distinct delays, 40 ms apart
        order = RNG.sample(workers, 3)
        delay = {w: 0.04 * (1 + order.index(w)) for w in workers}
        # drawn in every scenario so the random stream (and worker A's documents) stays aligned
        timeout_fails = RNG.randint(3, 4)
        lookup_fails = timeout_fails if SCEN == "tool_timeout" else 1
        a_retrieval_seed = RNG.random()
        results: dict[str, tuple[str, str, Any]] = {}  # worker -> (text, publish node, span)

        async def worker(w: str) -> None:
            with op("OPERATION", f"worker:{w}", actor=f"agent:worker{w}") as (wspan, _wn):
                with op(
                    "MESSAGE", f"dequeue:{w}", actor=f"agent:worker{w}", object="queue:tasks"
                ) as (ms, dq):
                    task = {"task": w, "term": terms[w], "request": request}
                    ms.input(task, role="message").output(task, role="message")
                    GT.flow(enq[w], dq)
                await asyncio.sleep(delay[w])
                inputs = [ev]
                docs = list(evidence)
                if w == "A":
                    PERTURB["retrieval"] = SCEN == "corrupted_retrieval"
                    saved = RNG.getstate()
                    RNG.seed(a_retrieval_seed)
                    own, ra = call(
                        "RETRIEVAL",
                        "retrieve:A",
                        retrieve_docs,
                        f"{task['term']} battery storage",  # query uses the dequeued task
                        obj="doc_index",
                        actor="agent:workerA",
                    )
                    RNG.setstate(saved)
                    PERTURB["retrieval"] = False
                    GT.flow(dq, ra)
                    if SCEN == "corrupted_retrieval":
                        GT.data["root_cause"] = ra
                    seen = {d["id"] for d in docs}
                    docs += [d for d in own if d["id"] not in seen]
                    inputs.append(ra)
                if w == "C":
                    _calc_state["fail"] = lookup_fails
                    for _ in range(lookup_fails + 1):
                        try:
                            v, lk = call(
                                "TOOL_INVOCATION",
                                "lookup:C",
                                calculator,
                                "5 * 365",
                                obj="lookup_service",
                                actor="agent:workerC",
                            )
                            inputs.append(lk)  # constant expression: no flow from the task
                            docs.append({"id": "L", "text": f"Lookup: {v} sunny hours per year."})
                            break
                        except TimeoutError:
                            await asyncio.sleep(0.005)
                    if SCEN == "tool_timeout":
                        # lookup:C#1 fails in the baseline too; #2 succeeds there, fails here
                        GT.data["root_cause"] = "lookup:C#2"
                prompt = f"Task {task['task']}: {task['term']}\n" + "\n".join(
                    f"- {d['text']}" for d in docs
                )
                if w == "B":
                    # speculative draft, discarded: its text equals the real result's text
                    _draft, dr = model_call("draft:B", prompt, "agent:workerB")
                    GT.flow(dq, dr)
                    GT.flow(ev, dr)
                    await asyncio.sleep(0.01)
                text, an = model_call(f"analyze:{w}", prompt, f"agent:worker{w}")
                GT.flow(dq, an)
                for i in inputs:
                    GT.flow(i, an)
                result = {"task": w, "result": text}
                with op(
                    "MESSAGE", f"publish:{w}", actor=f"agent:worker{w}", object="queue:results"
                ) as (ms, pb):
                    ms.input(result, role="message").output(result, role="message")
                    GT.flow(an, pb)
                results[w] = (text, pb, wspan)

        async def run_workers() -> None:
            await asyncio.gather(*(worker(w) for w in workers))

        asyncio.run(run_workers())
        PERTURB["retrieval"] = True
        # at-least-once delivery in completion order; A is delivered twice
        completion = sorted(workers, key=lambda w: delay[w])
        deliveries: list[str] = []
        for w in completion:
            deliveries.append(w)
            if w == "A":
                deliveries.append(w)
        with op(
            "OPERATION",
            "aggregate",
            actor="agent:aggregator",
            links=[results[w][2] for w in workers],
        ) as (_, agg):
            GT.data["exec_edges"] += [
                [n, agg] for n, v in GT.data["nodes"].items() if v["label"].startswith("worker:")
            ]
            used: dict[str, str] = {}
            for w in deliveries:
                if SCEN == "message_loss" and w == "C":
                    GT.data["root_cause"] = "deliver:C#1"
                    GT.data["outcome"] = "degraded"
                    continue
                text, pb, _ = results[w]
                with op(
                    "MESSAGE", f"deliver:{w}", actor="agent:aggregator", object="queue:results"
                ) as (ms, dl):
                    msg = {"task": w, "result": text}
                    ms.input(msg, role="message").output(msg, role="message")
                    GT.flow(pb, dl)
                used.setdefault(w, dl)  # duplicate deliveries are dropped by the dedupe
            sections = [results[w][0] for w in workers if w in used]

            def merge(parts: list[str]) -> str:
                return "\n\n".join(parts)

            merged, mg = call(
                "TOOL_INVOCATION", "merge", merge, sections, obj="merger", actor="agent:aggregator"
            )
            for w in workers:
                if w in used:
                    GT.flow(used[w], mg)
        with op("OPERATION", "enrichment", actor="agent:enricher"):
            cache: dict[str, str] = {}
            cache_writes: dict[str, str] = {}
            definition_nodes: list[str] = []
            definitions: list[str] = []

            def define(term: str) -> str:
                return f"Glossary: {term} refers to the {term} component of a home energy system."

            for w in workers:
                if w not in used:
                    continue
                term = terms[w]
                hit = cache.get(term)
                with op(
                    "MEMORY_ACCESS",
                    "read:glossary",
                    object="memory:glossary",
                    actor="agent:enricher",
                    facets=["read"],
                ) as (rs2, rd):
                    rs2.set(key=term, access="read")
                    if hit is not None:
                        rs2.output(hit, role="value", label=term)
                        GT.flow(cache_writes[term], rd)
                if hit is not None:
                    definitions.append(hit)
                    definition_nodes.append(rd)
                    continue
                value, df = call(
                    "TOOL_INVOCATION",
                    "define",
                    define,
                    term,
                    obj="glossary_service",
                    actor="agent:enricher",
                )
                with op(
                    "MEMORY_ACCESS",
                    "write:glossary",
                    object="memory:glossary",
                    actor="agent:enricher",
                    facets=["write"],
                ) as (ws2, wr):
                    ws2.input(value, role="value", label=term).set(key=term, access="write")
                    GT.flow(df, wr)
                cache[term] = value
                cache_writes[term] = wr
                definitions.append(value)
                definition_nodes.append(df)
            enriched, en = model_call(
                "enrich",
                "Enrich:\n" + "\n".join(f"- {t}" for t in [merged, *definitions]),
                "agent:enricher",
            )
            GT.flow(mg, en)
            for n in definition_nodes:
                GT.flow(n, en)
        with op("OPERATION", "persist", actor="agent:store"):
            with op(
                "MEMORY_ACCESS",
                "write:db",
                object="db:records",
                actor="agent:store",
                facets=["write"],
            ) as (ws3, dbw):
                ws3.input(enriched, role="value", label="record").set(key="record", access="write")
                GT.flow(en, dbw)
        with op("OPERATION", "compose", actor="agent:composer"):
            stale = SCEN == "stale_memory"
            record = (
                "Archived record: wind turbines were evaluated for a coastal site last year."
                if stale
                else enriched
            )
            with op(
                "MEMORY_ACCESS",
                "read:db",
                object="db:records",
                actor="agent:composer",
                facets=["read"],
            ) as (rs3, dbr):
                rs3.set(key="record", access="read").output(record, role="value", label="record")
                if stale:
                    GT.data["root_cause"] = dbr
                else:
                    GT.flow(dbw, dbr)
            with op(
                "STATE_MUTATION",
                "write_report",
                actor="agent:composer",
                facets=["artifact_creation"],
            ) as (fs, fw):
                fs.output(f"# Report\n\n{record}\n", role="artifact", label="report.md")
                GT.flow(dbr, fw)
                GT.data["final_output"] = fw
        GT.data["expected_motifs"].append("M001")  # lookup:C always retries at least once
        if lookup_fails + 1 >= 3:
            GT.data["expected_motifs"].append("M002")  # >=3 identical lookup calls


def main() -> None:
    global GT, RNG, SCEN
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--arch",
        choices=[
            "tool_loop",
            "rag_memory",
            "multi_agent",
            "map_reduce",
            "hybrid_rag_cache",
            "async_event_pipeline",
        ],
        default="tool_loop",
    )
    ap.add_argument("--scenario", choices=SCENARIOS, default="normal")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--gt", required=True)
    ap.add_argument("--sensor", choices=["native", "otel"], default="native")
    args = ap.parse_args()
    GT = GroundTruth(args.arch, args.scenario, args.seed)
    RNG = random.Random(args.seed)  # noqa: S311 - benchmark seed, not security
    SCEN = args.scenario
    if args.sensor == "otel":
        from otel_variant import run_otel_tool_loop  # noqa: PLC0415

        run_otel_tool_loop(GT, SCEN, retrieve_docs, summarize_v1, calculator)
    else:
        with aw.run(f"awbench:{args.arch}", scenario=args.scenario, seed=args.seed, arch=args.arch):
            {
                "tool_loop": arch_tool_loop,
                "rag_memory": arch_rag_memory,
                "multi_agent": arch_multi_agent,
                "map_reduce": arch_map_reduce,
                "hybrid_rag_cache": arch_hybrid_rag_cache,
                "async_event_pipeline": arch_async_event_pipeline,
            }[args.arch]()
    Path(args.gt).write_text(json.dumps(GT.data, indent=1), encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
