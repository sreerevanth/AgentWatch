"""Graph, provenance, comparison, motifs, profiles/drift, causality, states, forecasting, query."""

from __future__ import annotations

import pytest

from agentwatch import instrument as aw
from agentwatch.behaviour.drift import benjamini_hochberg, drift
from agentwatch.behaviour.motifs import REGISTRY
from agentwatch.causality.cones import causes, effects
from agentwatch.causality.hypotheses import EvidenceKind, add_evidence, get, propose
from agentwatch.compare.runs import compare
from agentwatch.forecasting.trajectory import forecast
from agentwatch.graph.model import Basis, EvidenceClass, RelType, View, make_relation
from agentwatch.graph.traverse import Graph
from agentwatch.provenance.lineage import dependents, lineage, render
from agentwatch.query.engine import ask, compile_question, execute
from agentwatch.query.workspace import Workspace
from agentwatch.state.latent import infer_states

DOCS = [
    {
        "id": "D1",
        "text": "Solar panels convert sunlight into electricity using photovoltaic cells made of silicon.",
    },
    {
        "id": "D2",
        "text": "Grid scale batteries store surplus solar electricity so it can be used after sunset.",
    },
]


def research_run(variant: str = "normal", *, fail_tool: int = 0) -> None:
    fails = {"n": fail_tool}

    @aw.retriever("kb", actor="agent:researcher")
    def retrieve(q: str) -> list[dict[str, str]]:
        return (
            DOCS
            if variant != "bad"
            else [
                {
                    "id": "X",
                    "text": "Medieval castles had thick stone walls and deep moats around them.",
                }
            ]
        )

    @aw.model("stub/summarizer", actor="agent:researcher")
    def summarize(prompt: str) -> str:
        return "Summary: " + " ".join(
            line.lstrip("- ") for line in prompt.splitlines() if line.startswith("-")
        )

    @aw.tool("calc", actor="agent:analyst")
    def calc(expr: str) -> int:
        if fails["n"]:
            fails["n"] -= 1
            raise TimeoutError("calc timed out")
        return 42

    with aw.run("research", variant=variant):
        with aw.span("OPERATION", "plan", actor="agent:planner"):
            docs = retrieve("solar")
            summary = summarize("Context:\n" + "\n".join(f"- {d['text']}" for d in docs))
            aw.memory_write("notes", "k1", summary, actor="agent:researcher")
            for _ in range(4):
                try:
                    calc("6*7")
                    break
                except TimeoutError:
                    continue
            note = aw.memory_read("notes", "k1", summary, actor="agent:writer")
            aw.artifact("report.md", f"# Report\n{note}\n", actor="agent:writer")


@pytest.fixture
def ws(engine, sink):
    research_run()
    research_run(fail_tool=2)
    research_run("bad")
    engine.ingest(sink.drafts)
    return Workspace(engine)


def run_by(ws: Workspace, i: int) -> str:
    return sorted(ws.runs(), key=lambda r: r["started_at"])[i]["run_id"]


def test_provenance_reaches_retrieved_documents_through_memory(ws):
    rid = run_by(ws, 0)
    res = lineage(ws, "report.md", run_id=rid)
    text = "\n".join(render(res))
    assert "RETRIEVAL kb" in text, text
    assert "via memory from MEMORY_ACCESS write:notes" in text
    assert "MODEL_INVOCATION stub/summarizer" in text
    assert res["metrics"]["provenance_depth"] >= 4
    # every non-declared step reports its basis and confidence
    assert "content_match" in text


def test_dependents_of_retrieval_include_report(ws):
    rid = run_by(ws, 0)
    retrieval = ws.events(rid, kind="RETRIEVAL")[0]
    res = dependents(ws, f"event:{retrieval['event_id']}", run_id=rid)
    labels = {d["description"]["label"] for d in res["dependents"]}
    assert any("summarizer" in str(x) for x in labels)
    assert res["affected_outputs"]


def test_compare_localizes_tool_failure_and_bad_retrieval(ws):
    a, b, c = run_by(ws, 0), run_by(ws, 1), run_by(ws, 2)
    r = compare(ws, a, b)
    d = r["earliest_divergence"]
    assert d["b_event"]["label"] == "TOOL_INVOCATION calc" and "status OK → ERROR" in d["reasons"]
    assert r["resources"]["retries"]["delta"] == 2
    assert r["motifs"]["M001"] == {"a": 0, "b": 1}
    r2 = compare(ws, a, c)
    assert r2["earliest_divergence"]["b_event"]["label"] == "RETRIEVAL kb"
    assert "dependency, not causation" in r2["earliest_divergence"]["cone"]["interpretation"]


def test_compare_identical_runs_have_no_divergence(engine, sink):
    research_run()
    research_run()
    engine.ingest(sink.drafts)
    ws = Workspace(engine)
    r = compare(ws, run_by(ws, 0), run_by(ws, 1))
    assert r["earliest_divergence"] is None and r["identical_structure"]


def test_execution_graph_structure(ws):
    rid = run_by(ws, 0)
    g = ws.graph(rid)
    stats = g.stats({f"event:{e['event_id']}" for e in ws.events(rid)})
    assert stats["roots"] == 1 and stats["unreached_events"] == 0
    plan = next(e for e in ws.events(rid) if e["operation"] == "plan")
    kids = g.children(f"event:{plan['event_id']}")
    assert len(kids) >= 5
    anc = g.ancestors(kids[0], views=["EXECUTION"], types=["CONTAINS"])
    assert [ws.describe_node(s.node)["label"] for s in anc][0] == "OPERATION plan"


def test_hyperedge_traversal_and_causal_view_rules():
    rel = make_relation(
        View.INFORMATION,
        RelType.DERIVES_FROM,
        ["artifact:a", "artifact:b"],
        ["artifact:c"],
        basis=Basis.CONTENT_MATCH,
        confidence=0.8,
        run_id=None,
        derived_by="t",
    )
    g = Graph([rel])
    assert {s.node for s in g.ancestors("artifact:c")} == {"artifact:a", "artifact:b"}
    assert g.ancestors("artifact:c", min_confidence=0.9) == []
    with pytest.raises(ValueError):
        make_relation(
            View.CAUSAL,
            RelType.CAUSES,
            ["a"],
            ["b"],
            basis=Basis.HYPOTHESIS,
            run_id=None,
            derived_by="t",
        )
    with pytest.raises(ValueError):
        make_relation(
            View.EXECUTION,
            RelType.CAUSES,
            ["a"],
            ["b"],
            basis=Basis.DECLARED,
            run_id=None,
            derived_by="t",
        )
    c = make_relation(
        View.CAUSAL,
        RelType.CAUSES,
        ["a"],
        ["b"],
        basis=Basis.INTERVENTIONAL,
        run_id=None,
        derived_by="t",
        evidence_class=EvidenceClass.INTERVENTIONAL,
    )
    g2 = Graph([c])
    assert g2.ancestors("b", min_evidence=EvidenceClass.VERIFIED) == []
    assert len(g2.ancestors("b", min_evidence=EvidenceClass.OBSERVATIONAL)) == 1


def test_retry_and_repeat_motifs(ws):
    inst = ws.derived("motif_instance", run_by(ws, 1))
    ids = {m["motif_id"] for m in inst}
    assert ids == {"M001", "M002"}
    retry = next(m for m in inst if m["motif_id"] == "M001")
    assert retry["measures"]["attempts"] == 3 and retry["measures"]["recovered"] is True
    assert not ws.derived("motif_instance", run_by(ws, 0))


def test_every_motif_has_a_definition_and_is_experimental():
    for d in REGISTRY.definitions.values():
        assert len(d.definition) > 40 and d.maturity.value == "EXPERIMENTAL"


def _motif_run(engine, sink, body):
    with aw.run("motif-probe"):
        body()
    engine.ingest(sink.drafts)
    ws = Workspace(engine)
    return {
        m["motif_id"]: m for m in ws.derived("motif_instance", ws.resolve_run("latest")["run_id"])
    }


def test_delegation_ping_pong(engine, sink):
    def body():
        for _ in range(2):
            aw.delegate("agent:a", "agent:b", "task")
            aw.delegate("agent:b", "agent:a", "task back")

    assert "M003" in _motif_run(engine, sink, body)


def test_retrieval_echo(engine, sink):
    text = "The quarterly revenue grew by twelve percent driven by subscription renewals in Europe."

    @aw.model("m")
    def gen(p):
        return text

    @aw.retriever("idx")
    def search(q):
        return [
            {"text": text},
            {"text": "an unrelated passage about the weather in coastal towns this week"},
        ]

    def body():
        gen("write summary")
        search("revenue")

    assert "M004" in _motif_run(engine, sink, body)


def test_context_expansion(engine, sink):
    @aw.model("m", actor="agent:a")
    def gen(p):
        return "ok"

    def body():
        ctx = "the agent keeps the whole conversation history in its working context"
        for turn in range(4):
            ctx = ctx + f" turn {turn} adds another observation to the growing context window"
            gen(ctx)

    m = _motif_run(engine, sink, body)
    assert "M005" in m and m["M005"]["measures"]["growth"] >= 1.5


def test_context_expansion_ignores_independent_actors(engine, sink):
    """Regression (held-out AWBench): v1 fired when different workers called one model with
    successively larger but unrelated prompts."""

    def body():
        for i, words in enumerate([12, 20, 35, 60]):

            @aw.model("m", actor=f"agent:worker{i}")
            def gen(p):
                return "ok"

            gen(" ".join(f"w{i}x{k}" for k in range(words)))

    assert "M005" not in _motif_run(engine, sink, body)


def test_hypothesis_evidence_class_is_computed(ws):
    h = propose(ws, cause="event:x", effect="event:y", statement="x causes y", proposer="llm")
    assert h["status"] == "PROPOSED" and h["evidence_class"] is None
    add_evidence(
        ws,
        h["hypothesis_id"],
        kind=EvidenceKind.DEPENDENCY,
        direction="supports",
        summary="y is downstream of x",
    )
    h = get(ws, h["hypothesis_id"])
    assert h["evidence_class"] == "OBSERVATIONAL" and h["status"] == "PROPOSED"
    exp1 = ws.store.put_experiment(ws.tenant_id, "branch_result", {"note": "t1"})
    exp2 = ws.store.put_experiment(ws.tenant_id, "branch_result", {"note": "t2"})
    add_evidence(
        ws,
        h["hypothesis_id"],
        kind="INTERVENTION",
        direction="supports",
        summary="changed x, y changed",
        experiment_id=exp1,
        reproduction_confidence=0.95,
    )
    assert get(ws, h["hypothesis_id"])["evidence_class"] == "INTERVENTIONAL"
    add_evidence(
        ws,
        h["hypothesis_id"],
        kind="INTERVENTION",
        direction="supports",
        summary="replicated",
        experiment_id=exp2,
        reproduction_confidence=0.9,
    )
    h = get(ws, h["hypothesis_id"])
    assert h["evidence_class"] == "VERIFIED" and h["status"] == "SUPPORTED"
    with pytest.raises(ValueError):
        add_evidence(
            ws,
            h["hypothesis_id"],
            kind="INTERVENTION",
            direction="supports",
            summary="no experiment",
        )
    with pytest.raises(ValueError):
        propose(ws, cause="a", effect="b", statement="s", proposer="oracle")


def test_causes_separates_sections(ws):
    rid = run_by(ws, 0)
    target = next(e for e in ws.events(rid) if e["operation"] == "write_artifact:report.md")
    res = causes(ws, target["event_id"])
    assert set(res) >= {"dependencies", "correlations", "hypotheses", "interventions", "legend"}
    assert all(d["evidence_class"] == "OBSERVATIONAL" for d in res["dependencies"])
    assert any(d["label"] == "RETRIEVAL kb" for d in res["dependencies"])
    assert res["correlations"]["status"] == "insufficient_data"
    eff = effects(ws, ws.events(rid, kind="RETRIEVAL")[0]["event_id"])
    assert eff["dependents"]


def _profile(**feats):
    from agentwatch.behaviour.profile import FEATURES

    base = dict.fromkeys(FEATURES, 1.0)
    base.update(feats)
    return {
        "run_id": "r",
        "features": base,
        "kind_distribution": {"TOOL_INVOCATION": 1.0},
        "motif_counts": {"M001": 0},
    }


def test_drift_detects_shift_and_respects_min_runs():
    a = [_profile(retry_rate=0.0 + i * 0.01) for i in range(10)]
    b = [_profile(retry_rate=0.5 + i * 0.01) for i in range(10)]
    res = drift(a, b)
    assert res["status"] == "tested" and "retry_rate" in res["drifted_features"]
    assert "tool_calls" not in res["drifted_features"]
    small = drift(a[:3], b[:3])
    assert small["status"] == "insufficient_data" and "drifted_features" not in small
    # 6 vs 6 cannot reach significance across all features, even with perfect separation
    under = drift(a[:6], b[:6])
    assert under["status"] == "underpowered" and under["min_achievable_q"] >= 0.05


def test_benjamini_hochberg_monotone():
    q = benjamini_hochberg({"a": 0.01, "b": 0.02, "c": 0.5})
    assert q["a"] <= q["b"] <= q["c"] and q["a"] == pytest.approx(0.03)


def test_states_and_forecast_report_insufficient_data(ws):
    assert infer_states(ws, window=4)["status"] == "insufficient_data"
    assert forecast(ws, "latest")["status"] == "insufficient_data"


def test_states_estimated_with_enough_windows(engine, sink):
    for i in range(6):
        research_run(fail_tool=i % 3)
    engine.ingest(sink.drafts)
    res = infer_states(Workspace(engine), window=2)
    assert res["status"] == "estimated" and 2 <= res["k"] <= 5
    assert all(s["name"] for s in res["states"])


def test_query_routing_and_evidence(ws):
    a, b = run_by(ws, 0), run_by(ws, 1)
    assert (
        compile_question(f"why did {b[:8]} take longer than {a[:8]}?")[0]
        == f"compare {a[:8]} {b[:8]}"
    )
    ans = ask(ws, f"Why did {b[:8]} take longer than {a[:8]}?")
    assert ans["answered"] and any("Earliest divergence" in line for line in ans["answer"])
    assert a in ans["evidence"] and b in ans["evidence"]
    assert ask(ws, "where did report.md come from?")["answered"]
    assert not ask(ws, "what is the meaning of life")["answered"]
    res = execute(ws, f"events {a[:8]} kind=TOOL_INVOCATION")
    assert res["evidence"] and all(e["kind"] == "TOOL_INVOCATION" for e in res["result"])


def test_stale_memory_read_is_not_a_transfer(engine, sink):
    """Regression: a read of the same key that returns different content is not information
    flow from the write (it previously produced a KEY_MATCH TRANSFERS relation)."""
    with aw.run("mem"):
        aw.memory_write(
            "notes", "k", "fresh summary of the research findings for the report", actor="agent:a"
        )
        aw.memory_read(
            "notes",
            "k",
            "an old note that was cached before the research happened",
            actor="agent:b",
        )
        aw.memory_write("notes", "k2", "value two", actor="agent:a")
        aw.memory_read("notes", "k2", "value two", actor="agent:b")
    engine.ingest(sink.drafts)
    ws = Workspace(engine)
    rels = [r for r in ws.relations(ws.resolve_run("latest")["run_id"]) if r["type"] == "TRANSFERS"]
    assert len(rels) == 1 and rels[0]["attributes"]["key"] == "k2"
    assert (
        rels[0]["attributes"]["value_match"] == "identical" and rels[0]["basis"] == "CONTENT_MATCH"
    )


def test_traversal_respects_time_through_shared_artifacts():
    """Regression: an artifact consumed early and produced later by another event must not let
    information 'flow' back to the earlier consumer."""
    rels = [
        make_relation(
            View.INFORMATION,
            RelType.CONSUMES,
            ["artifact:x"],
            ["event:early"],
            basis=Basis.DECLARED,
            run_id=None,
            derived_by="t",
        ),
        make_relation(
            View.INFORMATION,
            RelType.PRODUCES,
            ["event:late"],
            ["artifact:x"],
            basis=Basis.DECLARED,
            run_id=None,
            derived_by="t",
        ),
    ]
    g = Graph(rels, times={"event:early": 1.0, "event:late": 5.0})
    assert "event:early" not in {s.node for s in g.descendants("event:late")}
    assert "event:late" not in {s.node for s in g.ancestors("event:early")}
    untimed = Graph(rels)
    assert "event:early" in {s.node for s in untimed.descendants("event:late")}


def test_most_recent_producer_disambiguates_identical_content():
    """Regression (held-out AWBench, fan-out): two workers retrieve the same document; the
    second worker's model call must trace to its own retrieval, not the earlier identical one."""

    def rel(t, tail, head):
        return make_relation(
            View.INFORMATION, t, [tail], [head], basis=Basis.DECLARED, run_id=None, derived_by="t"
        )

    rels = [
        rel(RelType.PRODUCES, "event:r0", "artifact:list0"),
        rel(RelType.CONTAINS_ITEM, "artifact:list0", "artifact:doc"),
        rel(RelType.PRODUCES, "event:r1", "artifact:list1"),
        rel(RelType.CONTAINS_ITEM, "artifact:list1", "artifact:doc"),
        rel(RelType.CONSUMES, "artifact:doc", "event:m0"),
        rel(RelType.CONSUMES, "artifact:doc", "event:m1"),
    ]
    g = Graph(rels, times={"event:r0": 1.0, "event:m0": 2.0, "event:r1": 3.0, "event:m1": 4.0})
    assert {s.node for s in g.descendants("event:r0") if s.node.startswith("event:")} == {
        "event:m0"
    }
    assert {s.node for s in g.descendants("event:r1") if s.node.startswith("event:")} == {
        "event:m1"
    }
    assert {s.node for s in g.ancestors("event:m1") if s.node.startswith("event:")} == {"event:r1"}
    assert {s.node for s in g.ancestors("event:m0") if s.node.startswith("event:")} == {"event:r0"}


def test_identical_retrievals_are_matches_not_derivations(engine, sink):
    """Regression (held-out AWBench): content retrieved independently twice is a content
    match, not information flow from the first retrieval to the second."""
    text = "Solar photovoltaic panels convert sunlight into direct current electricity using silicon cells."

    @aw.retriever("idx")
    def search(q):
        return [
            {"id": "D1", "text": text},
            {"id": "D2", "text": q + " is an unrelated second document about wind"},
        ]

    with aw.run("twice"):
        search("first query words here")
        search("second query words here")
    engine.ingest(sink.drafts)
    ws = Workspace(engine)
    retrievals = ws.events(ws.resolve_run("latest")["run_id"], kind="RETRIEVAL")
    g = ws.graph(ws.resolve_run("latest")["run_id"])
    down = {
        s.node
        for s in g.descendants(
            f"event:{retrievals[0]['event_id']}",
            types=["PRODUCES", "CONSUMES", "DERIVES_FROM", "CONTAINS_ITEM", "TRANSFERS"],
        )
    }
    assert f"event:{retrievals[1]['event_id']}" not in down
