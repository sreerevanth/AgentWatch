"""Workspace: the single read model used by the API, CLI and frontend.

Everything the interfaces show comes from here, so the three surfaces cannot drift into
separate interpretations of the same evidence.
"""

from __future__ import annotations

from collections.abc import Iterable
from functools import cached_property
from typing import Any

from agentwatch.graph.traverse import Graph
from agentwatch.runtime.engine import Engine
from agentwatch.storage.store import Store


class NotFound(LookupError):
    pass


class Ambiguous(LookupError):
    pass


class Workspace:
    def __init__(self, engine: Engine | Store | str | None = None, tenant_id: str = "default", *, process: bool = True) -> None:
        self.engine = engine if isinstance(engine, Engine) else Engine(engine)
        self.store = self.engine.store
        self.tenant_id = tenant_id
        if process:
            self.engine.process(tenant_id)
        self.interp_id = self.engine.interp_id_for(tenant_id)

    # ── runs ──────────────────────────────────────────────────────────────
    def runs(self, limit: int | None = None) -> list[dict[str, Any]]:
        return self.store.runs(self.interp_id, limit=limit)

    def resolve_run(self, ref: str) -> dict[str, Any]:
        runs = self.runs()
        if not runs:
            raise NotFound("no runs recorded yet")
        if ref.startswith("latest"):
            offset = int(ref.split("~", 1)[1]) if "~" in ref else 0
            ordered = sorted(runs, key=lambda r: r.get("started_at") or "", reverse=True)
            if offset >= len(ordered):
                raise NotFound(f"only {len(ordered)} runs exist")
            return ordered[offset]
        exact = [r for r in runs if r["run_id"] == ref]
        if exact:
            return exact[0]
        pref = [r for r in runs if r["run_id"].startswith(ref)]
        if len(pref) == 1:
            return pref[0]
        if len(pref) > 1:
            raise Ambiguous(f"run prefix {ref!r} matches {len(pref)} runs")
        named = [r for r in runs if r.get("name") == ref]
        if named:
            return sorted(named, key=lambda r: r.get("started_at") or "", reverse=True)[0]
        raise NotFound(f"no run matches {ref!r}")

    # ── events ────────────────────────────────────────────────────────────
    def events(self, run_id: str | None = None, kind: str | None = None) -> list[dict[str, Any]]:
        return self.store.events(self.interp_id, run_id=run_id, kind=kind)

    @cached_property
    def all_events(self) -> dict[str, dict[str, Any]]:
        return {e["event_id"]: e for e in self.store.events(self.interp_id)}

    def event(self, ref: str) -> dict[str, Any]:
        ref = ref.removeprefix("event:")
        ev = self.store.event(self.interp_id, ref)
        if ev:
            return ev
        matches = [e for eid, e in self.all_events.items() if eid.startswith(ref)]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            raise Ambiguous(f"event prefix {ref!r} matches {len(matches)} events")
        raise NotFound(f"no event matches {ref!r}")

    def event_evidence(self, event_id: str) -> list[dict[str, Any]]:
        ev = self.event(event_id)
        out = []
        for oid in ev["derived_from"]:
            obs = self.store.get_observation(oid)
            if obs:
                out.append(obs.to_dict())
        return out

    # ── graph ─────────────────────────────────────────────────────────────
    def relations(self, run_id: str | None = None, view: str | None = None) -> list[dict[str, Any]]:
        if run_id is None:
            return self.store.relations(self.interp_id, view=view, all_runs=True)
        return self.store.relations(self.interp_id, run_id=run_id, view=view)

    def graph(self, run_id: str | None = None, views: Iterable[str] | None = None) -> Graph:
        rels = self.relations(run_id)
        vs = set(views) if views else None
        return Graph([r for r in rels if vs is None or r["view"] in vs])

    # ── artifacts / nodes ─────────────────────────────────────────────────
    def artifact(self, ref: str, with_content: bool = True) -> dict[str, Any]:
        aid = self.resolve_artifact_id(ref)
        art = self.store.artifact(self.tenant_id, aid, with_content=with_content)
        if art is None:
            raise NotFound(f"artifact {ref!r} not found")
        art["labels"] = sorted({a.get("label") for e in self.all_events.values() for a in e["outputs"] + e["inputs"] if a["artifact_id"] == aid and a.get("label")})
        return art

    def resolve_artifact_id(self, ref: str) -> str:
        ref = ref.removeprefix("artifact:")
        if self.store.artifact(self.tenant_id, ref, with_content=False):
            return ref
        by_label = {a["artifact_id"] for e in self.all_events.values() for a in e["outputs"] if a.get("label") == ref}
        if len(by_label) == 1:
            return by_label.pop()
        if len(by_label) > 1:
            # the most recently produced version of a labelled artifact
            order = sorted(self.all_events.values(), key=lambda e: e["time"]["start"] or "")
            for e in reversed(order):
                for a in e["outputs"]:
                    if a.get("label") == ref:
                        return str(a["artifact_id"])
        if len(ref) >= 6:
            matches = self.store.artifacts_by_prefix(self.tenant_id, ref)
            if len(matches) == 1:
                return matches[0]
            if len(matches) > 1:
                raise Ambiguous(f"artifact prefix {ref!r} matches {len(matches)} artifacts")
        raise NotFound(f"no artifact matches {ref!r}")

    def resolve_node(self, ref: str) -> str:
        if ref.startswith("entity:"):
            return ref
        if ref.startswith("artifact:"):
            return f"artifact:{self.resolve_artifact_id(ref)}"
        if ref.startswith("event:"):
            return f"event:{self.event(ref)['event_id']}"
        try:
            return f"event:{self.event(ref)['event_id']}"
        except (NotFound, Ambiguous):
            return f"artifact:{self.resolve_artifact_id(ref)}"

    def describe_node(self, node: str) -> dict[str, Any]:
        kind, _, ident = node.partition(":")
        if kind == "event":
            e = self.all_events.get(ident) or self.event(ident)
            return {"node": node, "type": "event", "label": f"{e['kind']} {e['operation']}", "actor": e.get("actor"), "status": e["status"],
                    "start": e["time"]["start"], "run_id": e.get("run_id")}
        if kind == "artifact":
            art = self.store.artifact(self.tenant_id, ident, with_content=False) or {}
            labels = sorted({a.get("label") for e in self.all_events.values() for a in e["outputs"] + e["inputs"] if a["artifact_id"] == ident and a.get("label")})
            roles = sorted({a.get("role") for e in self.all_events.values() for a in e["outputs"] + e["inputs"] if a["artifact_id"] == ident})
            return {"node": node, "type": "artifact", "label": labels[0] if labels else (art.get("preview") or "")[:60], "roles": roles,
                    "preview": art.get("preview"), "size_bytes": art.get("size_bytes")}
        return {"node": node, "type": "entity", "label": ident}

    def entities(self) -> list[dict[str, Any]]:
        return self.store.entities(self.interp_id)

    def diagnostics(self) -> list[dict[str, Any]]:
        return self.store.diagnostics(self.interp_id)

    def derived(self, record_type: str, scope: str | None = None) -> list[dict[str, Any]]:
        return self.store.derived(self.interp_id, record_type, scope)
