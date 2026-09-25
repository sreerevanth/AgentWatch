"""Deterministic entity resolution.

Entities are identified by canonical keys that the source declared (``model:<name>``,
``tool:<name>``, ``memory:<store>`` ...). Resolution is exact-key only, so confidence is
1.0 with basis ``EXACT_KEY``. No fuzzy merging is performed; aliasing is left to a
future, separately versioned resolver.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any

from agentwatch.events.model import ComputationalEvent, EntityRef

ENTITY_NAMESPACE = uuid.UUID("3c9e1f0a-2b4d-5e6f-8a7b-9c0d1e2f3a4b")
RESOLVER = "exact_key"
RESOLVER_VERSION = "1"


def entity_id_for(tenant_id: str, canonical: str) -> str:
    return str(uuid.uuid5(ENTITY_NAMESPACE, f"{tenant_id}|{canonical}"))


def resolve_entities(events: Sequence[ComputationalEvent], tenant_id: str, run_of: dict[str, str | None]) -> list[dict[str, Any]]:
    found: dict[str, dict[str, Any]] = {}

    def touch(ref: EntityRef, role: str, ev: ComputationalEvent) -> None:
        key = ref.canonical
        rec = found.get(key)
        if rec is None:
            rec = found[key] = {
                "entity_id": entity_id_for(tenant_id, key),
                "kind": ref.kind,
                "canonical_key": key,
                "name": ref.key,
                "roles": {},
                "event_count": 0,
                "runs": set(),
                "first_seen": None,
                "last_seen": None,
                "resolution": {"basis": "EXACT_KEY", "confidence": 1.0, "resolver": f"{RESOLVER}@{RESOLVER_VERSION}"},
            }
        rec["roles"][role] = rec["roles"].get(role, 0) + 1
        rec["event_count"] += 1
        rid = run_of.get(ev.event_id)
        if rid:
            rec["runs"].add(rid)
        ts = ev.time.start.isoformat() if ev.time.start else None
        if ts:
            rec["first_seen"] = min(filter(None, [rec["first_seen"], ts]))
            rec["last_seen"] = max(filter(None, [rec["last_seen"], ts]))

    for ev in events:
        if ev.actor:
            touch(ev.actor, "actor", ev)
        if ev.object:
            touch(ev.object, "object", ev)
        for eff in ev.effects:
            if eff.target_type == "entity" and (not ev.object or eff.target != ev.object.canonical):
                touch(EntityRef.parse(eff.target), f"effect_{eff.kind.value.lower()}", ev)
    out = []
    for rec in found.values():
        rec["runs"] = sorted(rec["runs"])
        out.append(rec)
    return sorted(out, key=lambda r: r["canonical_key"])
