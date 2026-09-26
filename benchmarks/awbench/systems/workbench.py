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
        self.stack: list[str] = []

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


def main() -> None:
    global GT, RNG, SCEN
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--arch",
        choices=["tool_loop", "rag_memory", "multi_agent", "map_reduce"],
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
            }[args.arch]()
    Path(args.gt).write_text(json.dumps(GT.data, indent=1), encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
