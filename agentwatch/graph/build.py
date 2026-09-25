"""Graph builders: events → EXECUTION and INFORMATION relations.

Nothing here creates CAUSAL relations. Declared parents that do not resolve to an
observed event are reported, not guessed.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from collections.abc import Callable, Sequence
from typing import Any

from agentwatch.events.model import ComputationalEvent, EventKind, EventStatus
from agentwatch.events.normalize import ArtifactContent
from agentwatch.graph.model import (
    Basis,
    RelType,
    View,
    make_relation,
    node_artifact,
    node_entity,
    node_event,
)

EXEC_BUILDER = "graph.execution@1"
INFO_BUILDER = "graph.information@1"

SHINGLE = 5
MIN_SHINGLES = 3
CONTAINMENT_THRESHOLD = 0.6
MAX_LIST_ITEMS = 100
_WORD = re.compile(r"[\w']+", re.UNICODE)


def event_order(events: Sequence[ComputationalEvent]) -> list[ComputationalEvent]:
    def key(e: ComputationalEvent) -> tuple[Any, ...]:
        return (e.time.start.timestamp() if e.time.start else float("inf"), e.time.ordering_key, e.event_id)

    return sorted(events, key=key)


def build_execution(
    events: Sequence[ComputationalEvent],
    run_of: dict[str, str | None],
    source_index: dict[tuple[str, str], str],
) -> list[dict[str, Any]]:
    rels: list[dict[str, Any]] = []
    for ev in events:
        rid = run_of.get(ev.event_id)
        for link in ev.parents:
            target = source_index.get((link.key_space, link.value))
            if target is None or target == ev.event_id:
                continue
            if link.relation == "parent":
                rtype = RelType.CONTAINS
            elif link.relation == "responds_to":
                rtype = RelType.RESPONDS_TO
            else:
                rtype = RelType.DEPENDS_ON
            rels.append(make_relation(
                View.EXECUTION, rtype, [node_event(target)], [node_event(ev.event_id)],
                basis=Basis.DECLARED, run_id=rid, evidence=list(ev.derived_from), derived_by=EXEC_BUILDER,
                attributes={"declared_relation": link.relation, "key_space": link.key_space},
            ))
        if ev.actor:
            rels.append(make_relation(
                View.EXECUTION, RelType.PERFORMED_BY, [node_entity(ev.actor.canonical)], [node_event(ev.event_id)],
                basis=Basis.DECLARED, confidence=ev.confidence_attribution.value, run_id=rid,
                evidence=list(ev.derived_from), derived_by=EXEC_BUILDER,
                attributes={"attribution_basis": ev.confidence_attribution.basis},
            ))
        if ev.object:
            rels.append(make_relation(
                View.EXECUTION, RelType.TARGETS, [node_event(ev.event_id)], [node_entity(ev.object.canonical)],
                basis=Basis.DECLARED, run_id=rid, evidence=list(ev.derived_from), derived_by=EXEC_BUILDER,
            ))
        if ev.kind == EventKind.DELEGATION and ev.actor and ev.object:
            rels.append(make_relation(
                View.EXECUTION, RelType.DELEGATES_TO, [node_entity(ev.actor.canonical)], [node_entity(ev.object.canonical)],
                basis=Basis.DECLARED, run_id=rid, evidence=[node_event(ev.event_id)], derived_by=EXEC_BUILDER,
                attributes={"event_id": ev.event_id},
            ))
    rels.extend(_retries(events, run_of, source_index))
    return _dedupe(rels)


def _parent_of(ev: ComputationalEvent, source_index: dict[tuple[str, str], str]) -> str | None:
    for link in ev.parents:
        if link.relation == "parent":
            return source_index.get((link.key_space, link.value))
    return None


def _retries(events: Sequence[ComputationalEvent], run_of: dict[str, str | None], source_index: dict[tuple[str, str], str]) -> list[dict[str, Any]]:
    """HEURISTIC: a failed call followed by a call with the same kind, operation and
    object under the same parent is labelled a retry (confidence 0.7)."""
    rels = []
    last: dict[tuple[Any, ...], ComputationalEvent] = {}
    for ev in event_order(events):
        if ev.kind not in (EventKind.TOOL_INVOCATION, EventKind.MODEL_INVOCATION, EventKind.RETRIEVAL, EventKind.EXTERNAL_IO):
            continue
        key = (run_of.get(ev.event_id), _parent_of(ev, source_index), ev.kind, ev.operation, ev.object.canonical if ev.object else None)
        prev = last.get(key)
        if prev is not None and prev.status in (EventStatus.ERROR, EventStatus.TIMEOUT):
            rels.append(make_relation(
                View.EXECUTION, RelType.RETRIES, [node_event(prev.event_id)], [node_event(ev.event_id)],
                basis=Basis.HEURISTIC, confidence=0.7, run_id=run_of.get(ev.event_id),
                evidence=[node_event(prev.event_id), node_event(ev.event_id)], derived_by=EXEC_BUILDER,
                attributes={"rule": "same kind/operation/object under same parent after failure"},
            ))
        last[key] = ev
    return rels


def text_of(value: Any) -> str:
    if isinstance(value, str):
        return value
    parts: list[str] = []

    def walk(v: Any) -> None:
        if isinstance(v, str):
            parts.append(v)
        elif isinstance(v, dict):
            for x in v.values():
                walk(x)
        elif isinstance(v, list):
            for x in v:
                walk(x)

    walk(value)
    return " ".join(parts)


def shingles(text: str) -> frozenset[str]:
    words = [w.lower() for w in _WORD.findall(text)]
    if len(words) < SHINGLE:
        return frozenset()
    return frozenset(" ".join(words[i : i + SHINGLE]) for i in range(len(words) - SHINGLE + 1))


def build_information(
    events: Sequence[ComputationalEvent],
    run_of: dict[str, str | None],
    artifacts: dict[str, ArtifactContent],
    register: Callable[[Any, str], str],
) -> list[dict[str, Any]]:
    """``register(value, role)`` returns the artifact id for a value (registering it)."""
    rels: list[dict[str, Any]] = []
    ordered = event_order(events)
    position = {e.event_id: i for i, e in enumerate(ordered)}

    # 1. declared production / consumption
    for ev in ordered:
        rid = run_of.get(ev.event_id)
        for ref in ev.outputs:
            rels.append(make_relation(
                View.INFORMATION, RelType.PRODUCES, [node_event(ev.event_id)], [node_artifact(ref.artifact_id)],
                basis=Basis.DECLARED, run_id=rid, evidence=list(ev.derived_from), derived_by=INFO_BUILDER,
                attributes={"role": ref.role, "label": ref.label},
            ))
        for ref in ev.inputs:
            rels.append(make_relation(
                View.INFORMATION, RelType.CONSUMES, [node_artifact(ref.artifact_id)], [node_event(ev.event_id)],
                basis=Basis.DECLARED, run_id=rid, evidence=list(ev.derived_from), derived_by=INFO_BUILDER,
                attributes={"role": ref.role, "label": ref.label},
            ))
        for eff in ev.effects:
            if eff.kind.value == "WRITE":
                rels.append(make_relation(View.INFORMATION, RelType.WRITES_TO, [node_event(ev.event_id)], [node_entity(eff.target)],
                                          basis=Basis.DECLARED, run_id=rid, evidence=list(ev.derived_from), derived_by=INFO_BUILDER))
            elif eff.kind.value == "READ":
                rels.append(make_relation(View.INFORMATION, RelType.READS_FROM, [node_entity(eff.target)], [node_event(ev.event_id)],
                                          basis=Basis.DECLARED, run_id=rid, evidence=list(ev.derived_from), derived_by=INFO_BUILDER))

    # 2. list artifacts decompose into item artifacts (retrieval result sets etc.)
    first_seen: dict[str, int] = {}
    appears_in_run: dict[str, str | None] = {}
    for ev in ordered:
        for ref in [*ev.inputs, *ev.outputs]:
            first_seen.setdefault(ref.artifact_id, position[ev.event_id])
            appears_in_run.setdefault(ref.artifact_id, run_of.get(ev.event_id))
    item_parent: dict[str, str] = {}
    for aid in list(first_seen):
        content = artifacts.get(aid)
        if content is None:
            continue
        value = json.loads(content.content_json)
        if isinstance(value, list) and 1 < len(value) <= MAX_LIST_ITEMS:
            for i, item in enumerate(value):
                iid = register(item, "item")
                if iid == aid:
                    continue
                item_parent.setdefault(iid, aid)
                first_seen.setdefault(iid, first_seen[aid])
                appears_in_run.setdefault(iid, appears_in_run[aid])
                rels.append(make_relation(
                    View.INFORMATION, RelType.CONTAINS_ITEM, [node_artifact(aid)], [node_artifact(iid)],
                    basis=Basis.CONTENT_MATCH, run_id=appears_in_run[aid], evidence=[node_artifact(aid)], derived_by=INFO_BUILDER,
                    attributes={"index": i},
                ))

    # 3. memory transfer by declared store + key
    writes: dict[tuple[Any, ...], ComputationalEvent] = {}
    for ev in ordered:
        if ev.kind != EventKind.MEMORY_ACCESS or ev.object is None:
            continue
        attrs = ev.attributes
        key = (run_of.get(ev.event_id), ev.object.canonical, attrs.get("key"))
        if attrs.get("access") == "write" or "write" in ev.facets:
            writes[key] = ev
        elif (attrs.get("access") == "read" or "read" in ev.facets) and key in writes and attrs.get("key") is not None:
            w = writes[key]
            rels.append(make_relation(
                View.INFORMATION, RelType.TRANSFERS, [node_event(w.event_id)], [node_event(ev.event_id)],
                basis=Basis.KEY_MATCH, run_id=run_of.get(ev.event_id), evidence=[node_event(w.event_id), node_event(ev.event_id)],
                derived_by=INFO_BUILDER, attributes={"memory": ev.object.canonical, "key": attrs.get("key"), "via": "memory"},
            ))

    # 4. content containment: an artifact whose text contains an earlier artifact's text
    sh: dict[str, frozenset[str]] = {}
    for aid in first_seen:
        content = artifacts.get(aid)
        if content is None:
            continue
        s = shingles(text_of(json.loads(content.content_json)))
        if len(s) >= MIN_SHINGLES:
            sh[aid] = s
    by_run: dict[str | None, list[str]] = defaultdict(list)
    for aid in sh:
        by_run[appears_in_run.get(aid)].append(aid)
    for run_id, aids in by_run.items():
        aids.sort(key=lambda a: first_seen[a])
        for i, x in enumerate(aids):
            sx = sh[x]
            for y in aids[:i]:
                if first_seen[y] >= first_seen[x] or item_parent.get(y) == x or item_parent.get(x) == y:
                    continue
                sy = sh[y]
                inter = len(sx & sy)
                if not inter:
                    continue
                containment = inter / len(sy)
                if containment >= CONTAINMENT_THRESHOLD:
                    rels.append(make_relation(
                        View.INFORMATION, RelType.DERIVES_FROM, [node_artifact(y)], [node_artifact(x)],
                        basis=Basis.CONTENT_MATCH, confidence=round(containment, 3), run_id=run_id,
                        evidence=[node_artifact(y), node_artifact(x)], derived_by=INFO_BUILDER,
                        attributes={"method": f"word-{SHINGLE}gram containment", "containment": round(containment, 3)},
                    ))
    return _dedupe(rels)


def _dedupe(rels: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: dict[str, dict[str, Any]] = {}
    for r in rels:
        seen.setdefault(r["rel_id"], r)
    return list(seen.values())
