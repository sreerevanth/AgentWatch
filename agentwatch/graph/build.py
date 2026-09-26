"""Graph builders: events → EXECUTION and INFORMATION relations.

Nothing here creates CAUSAL relations. Declared parents that do not resolve to an
observed event are reported, not guessed.
"""

from __future__ import annotations

import json
import math
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
INFO_BUILDER = "graph.information@4"

SHINGLE = 5
MIN_SHINGLES = 3
CONTAINMENT_THRESHOLD = 0.6
MAX_LIST_ITEMS = 100
_WORD = re.compile(r"[\w']+", re.UNICODE)


def event_order(events: Sequence[ComputationalEvent]) -> list[ComputationalEvent]:
    def key(e: ComputationalEvent) -> tuple[Any, ...]:
        return (
            e.time.start.timestamp() if e.time.start else float("inf"),
            e.time.ordering_key,
            e.event_id,
        )

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
            rels.append(
                make_relation(
                    View.EXECUTION,
                    rtype,
                    [node_event(target)],
                    [node_event(ev.event_id)],
                    basis=Basis.DECLARED,
                    run_id=rid,
                    evidence=list(ev.derived_from),
                    derived_by=EXEC_BUILDER,
                    attributes={"declared_relation": link.relation, "key_space": link.key_space},
                )
            )
        if ev.actor:
            rels.append(
                make_relation(
                    View.EXECUTION,
                    RelType.PERFORMED_BY,
                    [node_entity(ev.actor.canonical)],
                    [node_event(ev.event_id)],
                    basis=Basis.DECLARED,
                    confidence=ev.confidence_attribution.value,
                    run_id=rid,
                    evidence=list(ev.derived_from),
                    derived_by=EXEC_BUILDER,
                    attributes={"attribution_basis": ev.confidence_attribution.basis},
                )
            )
        if ev.object:
            rels.append(
                make_relation(
                    View.EXECUTION,
                    RelType.TARGETS,
                    [node_event(ev.event_id)],
                    [node_entity(ev.object.canonical)],
                    basis=Basis.DECLARED,
                    run_id=rid,
                    evidence=list(ev.derived_from),
                    derived_by=EXEC_BUILDER,
                )
            )
        if ev.kind == EventKind.DELEGATION and ev.actor and ev.object:
            rels.append(
                make_relation(
                    View.EXECUTION,
                    RelType.DELEGATES_TO,
                    [node_entity(ev.actor.canonical)],
                    [node_entity(ev.object.canonical)],
                    basis=Basis.DECLARED,
                    run_id=rid,
                    evidence=[node_event(ev.event_id)],
                    derived_by=EXEC_BUILDER,
                    attributes={"event_id": ev.event_id},
                )
            )
    rels.extend(_retries(events, run_of, source_index))
    return _dedupe(rels)


def _parent_of(ev: ComputationalEvent, source_index: dict[tuple[str, str], str]) -> str | None:
    for link in ev.parents:
        if link.relation == "parent":
            return source_index.get((link.key_space, link.value))
    return None


def _retries(
    events: Sequence[ComputationalEvent],
    run_of: dict[str, str | None],
    source_index: dict[tuple[str, str], str],
) -> list[dict[str, Any]]:
    """HEURISTIC: a failed call followed by a call with the same kind, operation and
    object under the same parent is labelled a retry (confidence 0.7)."""
    rels = []
    last: dict[tuple[Any, ...], ComputationalEvent] = {}
    for ev in event_order(events):
        if ev.kind not in (
            EventKind.TOOL_INVOCATION,
            EventKind.MODEL_INVOCATION,
            EventKind.RETRIEVAL,
            EventKind.EXTERNAL_IO,
        ):
            continue
        key = (
            run_of.get(ev.event_id),
            _parent_of(ev, source_index),
            ev.kind,
            ev.operation,
            ev.object.canonical if ev.object else None,
        )
        prev = last.get(key)
        if prev is not None and prev.status in (EventStatus.ERROR, EventStatus.TIMEOUT):
            rels.append(
                make_relation(
                    View.EXECUTION,
                    RelType.RETRIES,
                    [node_event(prev.event_id)],
                    [node_event(ev.event_id)],
                    basis=Basis.HEURISTIC,
                    confidence=0.7,
                    run_id=run_of.get(ev.event_id),
                    evidence=[node_event(prev.event_id), node_event(ev.event_id)],
                    derived_by=EXEC_BUILDER,
                    attributes={
                        "rule": "same kind/operation/object under same parent after failure"
                    },
                )
            )
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
            rels.append(
                make_relation(
                    View.INFORMATION,
                    RelType.PRODUCES,
                    [node_event(ev.event_id)],
                    [node_artifact(ref.artifact_id)],
                    basis=Basis.DECLARED,
                    run_id=rid,
                    evidence=list(ev.derived_from),
                    derived_by=INFO_BUILDER,
                    attributes={"role": ref.role, "label": ref.label},
                )
            )
        for ref in ev.inputs:
            rels.append(
                make_relation(
                    View.INFORMATION,
                    RelType.CONSUMES,
                    [node_artifact(ref.artifact_id)],
                    [node_event(ev.event_id)],
                    basis=Basis.DECLARED,
                    run_id=rid,
                    evidence=list(ev.derived_from),
                    derived_by=INFO_BUILDER,
                    attributes={"role": ref.role, "label": ref.label},
                )
            )
        for eff in ev.effects:
            if eff.kind.value == "WRITE":
                rels.append(
                    make_relation(
                        View.INFORMATION,
                        RelType.WRITES_TO,
                        [node_event(ev.event_id)],
                        [node_entity(eff.target)],
                        basis=Basis.DECLARED,
                        run_id=rid,
                        evidence=list(ev.derived_from),
                        derived_by=INFO_BUILDER,
                    )
                )
            elif eff.kind.value == "READ":
                rels.append(
                    make_relation(
                        View.INFORMATION,
                        RelType.READS_FROM,
                        [node_entity(eff.target)],
                        [node_event(ev.event_id)],
                        basis=Basis.DECLARED,
                        run_id=rid,
                        evidence=list(ev.derived_from),
                        derived_by=INFO_BUILDER,
                    )
                )

    # 2. list artifacts decompose into item artifacts (retrieval result sets etc.), per run:
    #    artifacts are content-addressed and may appear in several runs.
    first_seen: dict[tuple[str | None, str], int] = {}
    for ev in ordered:
        rid = run_of.get(ev.event_id)
        for ref in [*ev.inputs, *ev.outputs]:
            first_seen.setdefault((rid, ref.artifact_id), position[ev.event_id])
    item_parent: dict[tuple[str | None, str], str] = {}
    item_cache: dict[str, list[str]] = {}
    for (rid, aid), pos in list(first_seen.items()):
        if aid not in item_cache:
            item_cache[aid] = []
            content = artifacts.get(aid)
            if content is not None:
                value = json.loads(content.content_json)
                if isinstance(value, list) and 1 < len(value) <= MAX_LIST_ITEMS:
                    item_cache[aid] = [register(item, "item") for item in value]
        for i, iid in enumerate(item_cache[aid]):
            if iid == aid:
                continue
            item_parent.setdefault((rid, iid), aid)
            first_seen.setdefault((rid, iid), pos)
            rels.append(
                make_relation(
                    View.INFORMATION,
                    RelType.CONTAINS_ITEM,
                    [node_artifact(aid)],
                    [node_artifact(iid)],
                    basis=Basis.CONTENT_MATCH,
                    run_id=rid,
                    evidence=[node_artifact(aid)],
                    derived_by=INFO_BUILDER,
                    attributes={"index": i},
                )
            )

    # 3. memory transfer by declared store + key
    writes: dict[tuple[Any, ...], ComputationalEvent] = {}
    for ev in ordered:
        if ev.kind != EventKind.MEMORY_ACCESS or ev.object is None:
            continue
        attrs = ev.attributes
        key = (run_of.get(ev.event_id), ev.object.canonical, attrs.get("key"))
        if attrs.get("access") == "write" or "write" in ev.facets:
            writes[key] = ev
        elif (
            (attrs.get("access") == "read" or "read" in ev.facets)
            and key in writes
            and attrs.get("key") is not None
        ):
            w = writes[key]
            written = {a.artifact_id for a in w.inputs if a.role == "value"} or {
                a.artifact_id for a in w.inputs
            }
            read = {a.artifact_id for a in ev.outputs if a.role == "value"} or {
                a.artifact_id for a in ev.outputs
            }
            if read and written and not (read & written):
                # same key, different content: the read did not return what was written
                # (stale or overwritten elsewhere) — no information flowed from this write
                continue
            verified = bool(read & written)
            rels.append(
                make_relation(
                    View.INFORMATION,
                    RelType.TRANSFERS,
                    [node_event(w.event_id)],
                    [node_event(ev.event_id)],
                    basis=Basis.CONTENT_MATCH if verified else Basis.KEY_MATCH,
                    confidence=1.0 if verified else 0.5,
                    run_id=run_of.get(ev.event_id),
                    evidence=[node_event(w.event_id), node_event(ev.event_id)],
                    derived_by=INFO_BUILDER,
                    attributes={
                        "memory": ev.object.canonical,
                        "key": attrs.get("key"),
                        "via": "memory",
                        "value_match": "identical" if verified else "unverified",
                    },
                )
            )

    # 4. content containment: an artifact whose text contains an earlier artifact's text
    sh_cache: dict[str, frozenset[str]] = {}

    def shingles_of(aid: str) -> frozenset[str]:
        if aid not in sh_cache:
            content = artifacts.get(aid)
            sh_cache[aid] = (
                shingles(text_of(json.loads(content.content_json))) if content else frozenset()
            )
        return sh_cache[aid]

    # Lists decomposed into items are represented by their items for content matching.
    decomposed = {aid for aid, items in item_cache.items() if items}
    # Artifacts whose content entered from outside the system cannot derive from earlier
    # in-system artifacts; a content match into them is recorded as MATCHES_CONTENT.
    external: set[tuple[str | None, str]] = set()
    for ev in ordered:
        if ev.kind in (EventKind.RETRIEVAL, EventKind.EXTERNAL_IO, EventKind.EXTERNAL_INPUT):
            for ref in ev.outputs:
                external.add((run_of.get(ev.event_id), ref.artifact_id))
    for (rid, iid), parent in item_parent.items():
        if (rid, parent) in external:
            external.add((rid, iid))
    by_run: dict[str | None, list[str]] = defaultdict(list)
    for rid, aid in first_seen:
        if aid not in decomposed and len(shingles_of(aid)) >= MIN_SHINGLES:
            by_run[rid].append(aid)
    for run_id, aids in by_run.items():
        aids.sort(key=lambda a: first_seen[(run_id, a)])
        # Exact prefix-filtered similarity join. containment(y in x) >= t requires x to contain
        # at least one of y's first |y| - ceil(t*|y|) + 1 shingles under any fixed global order
        # (pigeonhole). Ordering by rarity keeps those prefixes, and so the index, small;
        # every candidate is then verified exactly, so the result equals pairwise comparison.
        df: dict[str, int] = defaultdict(int)
        for a in aids:
            for sh in shingles_of(a):
                df[sh] += 1
        index: dict[str, list[str]] = defaultdict(list)
        pending: list[str] = []
        pending_pos: int | None = None
        for x in aids:
            fx = first_seen[(run_id, x)]
            if pending_pos is not None and fx != pending_pos:
                for y in pending:  # artifacts become candidates only for strictly later ones
                    sy = shingles_of(y)
                    keep = len(sy) - math.ceil(CONTAINMENT_THRESHOLD * len(sy)) + 1
                    for sh in sorted(sy, key=lambda k: (df[k], k))[:keep]:
                        index[sh].append(y)
                pending = []
            pending_pos = fx
            pending.append(x)
            sx = shingles_of(x)
            candidates: set[str] = set()
            for sh in sx:
                candidates.update(index.get(sh, ()))
            for y in sorted(candidates):
                if item_parent.get((run_id, y)) == x or item_parent.get((run_id, x)) == y:
                    continue
                sy = shingles_of(y)
                containment = len(sx & sy) / len(sy)
                if containment >= CONTAINMENT_THRESHOLD:
                    rtype = (
                        RelType.MATCHES_CONTENT if (run_id, x) in external else RelType.DERIVES_FROM
                    )
                    rels.append(
                        make_relation(
                            View.INFORMATION,
                            rtype,
                            [node_artifact(y)],
                            [node_artifact(x)],
                            basis=Basis.CONTENT_MATCH,
                            confidence=round(containment, 3),
                            run_id=run_id,
                            evidence=[node_artifact(y), node_artifact(x)],
                            derived_by=INFO_BUILDER,
                            attributes={
                                "method": f"word-{SHINGLE}gram containment",
                                "containment": round(containment, 3),
                            },
                        )
                    )
    return _dedupe(rels)


def _dedupe(rels: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: dict[str, dict[str, Any]] = {}
    for r in rels:
        seen.setdefault(r["rel_id"], r)
    return list(seen.values())
