"""v3 performance measurements (SQLite, single process).

    python -m benchmarks.perf.v3_perf --spans 2000

Measures what exists; it does not tune anything. Results go to benchmarks/perf/results/.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path

from agentwatch import instrument as aw
from agentwatch.compare.runs import compare
from agentwatch.provenance.lineage import lineage
from agentwatch.query.workspace import Workspace
from agentwatch.runtime.engine import Engine
from agentwatch.sensors.base import ListSink

OUT = Path(__file__).resolve().parent / "results"


def workload(n_spans: int, variant: int = 0) -> None:
    """A synthetic run: batches of retrieval → model → tool under one operation each."""

    @aw.retriever("idx")
    def search(q: str) -> list[dict[str, str]]:
        return [
            {
                "id": f"d{i}",
                "text": f"document {i} about topic {q} with several words of content here",
            }
            for i in range(3)
        ]

    @aw.model("stub/m")
    def gen(p: str) -> str:
        return "answer: " + p[:120]

    @aw.tool("t")
    def tool(x: str) -> str:
        return x.upper()[: 40 + variant]

    per_batch = 4
    with aw.run("perf"):
        for b in range(max(1, n_spans // per_batch)):
            with aw.span("OPERATION", f"step{b % 7}", actor=f"agent:a{b % 3}"):
                docs = search(f"q{b}")
                out = gen(" ".join(d["text"] for d in docs))
                tool(out)


def timed(fn, repeat: int = 1) -> tuple[float, object]:
    best = None
    res = None
    for _ in range(repeat):
        t0 = time.perf_counter()
        res = fn()
        dt = time.perf_counter() - t0
        best = dt if best is None else min(best, dt)
    return best or 0.0, res


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--spans", type=int, default=2000)
    args = ap.parse_args(argv)
    results: dict[str, object] = {
        "generated_at": datetime.now(UTC).isoformat(),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "spans": args.spans,
    }

    # sensor overhead: time per instrumented call vs the same call uninstrumented
    sink = ListSink()
    aw.configure(sink)

    def plain(x: str) -> str:
        return x.upper()

    wrapped = aw.tool("bench")(plain)
    n = 5000
    with aw.run("overhead"):
        t_plain, _ = timed(lambda: [plain("abc") for _ in range(n)])
        t_wrapped, _ = timed(lambda: [wrapped("abc") for _ in range(n)])
    results["sensor_overhead_us_per_call"] = round((t_wrapped - t_plain) / n * 1e6, 2)

    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "perf.db"
        engine = Engine(f"sqlite:///{db.as_posix()}")
        sink = ListSink()
        aw.configure(sink)
        workload(args.spans)
        workload(args.spans, variant=1)
        drafts = sink.drafts
        t_ingest, _ = timed(lambda: engine.ingest(drafts))
        results["observations"] = len(drafts)
        results["ingest_obs_per_s"] = round(len(drafts) / t_ingest, 1)
        t_process, report = timed(lambda: engine.process(force=True))
        results["rebuild_s"] = round(t_process, 3)
        results["rebuild_events_per_s"] = round(report["events"] / t_process, 1)  # type: ignore[index]
        results["relations"] = report["relations"]  # type: ignore[index]
        # one more small run arriving after the big rebuild: incremental path
        sink.drafts.clear()
        workload(40, variant=2)
        engine.ingest(list(sink.drafts))
        t_inc, inc = timed(lambda: engine.process())
        results["incremental_process_s"] = round(t_inc, 3)
        results["incremental_mode"] = inc.get("mode")  # type: ignore[union-attr]
        ws = Workspace(engine)
        a, b = (
            sorted(ws.runs(), key=lambda r: r["started_at"])[0]["run_id"],
            sorted(ws.runs(), key=lambda r: r["started_at"])[1]["run_id"],
        )  # the two large runs
        t_graph, g = timed(lambda: ws._build_graph(a, None), repeat=3)  # uncached build
        results["graph_build_ms"] = round(t_graph * 1000, 1)
        start = f"event:{ws.events(a, kind='RETRIEVAL')[0]['event_id']}"
        t_trav, steps = timed(lambda: g.descendants(start), repeat=3)  # type: ignore[attr-defined]
        results["descendants_ms"] = round(t_trav * 1000, 2)
        results["descendants_reached"] = len(steps)  # type: ignore[arg-type]
        last_tool = ws.events(a, kind="TOOL_INVOCATION")[-1]
        t_prov, _ = timed(
            lambda: lineage(ws, f"event:{last_tool['event_id']}", run_id=a, max_depth=8)
        )
        results["provenance_ms"] = round(t_prov * 1000, 1)
        t_cmp, _ = timed(lambda: compare(ws, a, b))
        results["compare_ms"] = round(t_cmp * 1000, 1)
        engine.store.seal_all()
        t_ver, rep = timed(lambda: engine.store.verify())
        results["verify_s"] = round(t_ver, 3)
        engine.store.close()
        size = os.path.getsize(db) + sum(
            p.stat().st_size for p in Path(tmp).glob("perf.db*") if p != db
        )
        results["store_bytes"] = size
        results["store_bytes_per_observation"] = round(size / len(drafts), 1)
    OUT.mkdir(parents=True, exist_ok=True)
    body = json.dumps(results, indent=2)
    (OUT / "latest.json").write_text(body, encoding="utf-8")
    print(body)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
