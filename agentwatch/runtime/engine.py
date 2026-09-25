"""The v3 processing engine.

    evidence (immutable) ─► normalize ─► resolve entities ─► segment runs
                         ─► build EXECUTION + INFORMATION relations ─► analyzers

An interpretation is identified by the versions of every component in the pipeline.
Changing any component version yields a new interpretation; the previous one is kept
(``superseded``) and raw evidence is never touched. Processing is a deterministic
rebuild, so it is idempotent and any process sharing the store gets the same result.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Iterable, Sequence
from typing import Any

from agentwatch.analysis.base import AnalysisInput, Analyzer
from agentwatch.entities.resolve import RESOLVER, RESOLVER_VERSION, resolve_entities
from agentwatch.events.model import ComputationalEvent, Diagnostic
from agentwatch.events.normalize import ArtifactContent, NormalizeContext, Normalizer
from agentwatch.events.registry import all_normalizers
from agentwatch.evidence.canonical import canonical_json, sha256_hex
from agentwatch.evidence.model import ObservationDraft, RawObservation
from agentwatch.evidence.redaction import DEFAULT_POLICY, PayloadPolicy
from agentwatch.graph.build import EXEC_BUILDER, INFO_BUILDER, build_execution, build_information
from agentwatch.runs.segment import build_source_index, segment
from agentwatch.sensors.legacy.translator import LegacyTranslator, TranslationResult
from agentwatch.storage.store import AppendResult, Store

logger = logging.getLogger(__name__)
PIPELINE_VERSION = "1"


def default_analyzers() -> list[Analyzer]:
    from agentwatch.analysis.registry import builtin_analyzers

    return builtin_analyzers()


class Engine:
    def __init__(
        self,
        store: Store | str | None = None,
        *,
        policy: PayloadPolicy = DEFAULT_POLICY,
        normalizers: Sequence[Normalizer] | None = None,
        analyzers: Sequence[Analyzer] | None = None,
    ) -> None:
        self.store = store if isinstance(store, Store) else Store(store)
        self.policy = policy
        self.normalizers = list(normalizers) if normalizers is not None else all_normalizers()
        self.analyzers = list(analyzers) if analyzers is not None else default_analyzers()

    # ── ingestion ──────────────────────────────────────────────────────────
    def ingest(self, drafts: Sequence[ObservationDraft], policy: PayloadPolicy | None = None) -> AppendResult:
        return self.store.append(drafts, policy or self.policy)

    def ingest_legacy(self, events: Iterable[Any], tenant_id: str = "default") -> tuple[list[TranslationResult], AppendResult]:
        translator = LegacyTranslator(tenant_id=tenant_id)
        results = [translator.translate(e, tenant_id=tenant_id) for e in events]
        drafts = [r.draft for r in results if r.draft is not None]
        return results, self.ingest(drafts)

    # ── interpretation identity ────────────────────────────────────────────
    def pipeline(self) -> dict[str, Any]:
        return {
            "pipeline": PIPELINE_VERSION,
            "normalizers": {n.name: n.version for n in sorted(self.normalizers, key=lambda n: n.name)},
            "resolver": f"{RESOLVER}@{RESOLVER_VERSION}",
            "graph": [EXEC_BUILDER, INFO_BUILDER],
            "analyzers": {a.name: a.version for a in sorted(self.analyzers, key=lambda a: a.name)},
            "policy": {"capture": self.policy.capture, "redact_secrets": self.policy.redact_secrets, "redact_pii": self.policy.redact_pii},
        }

    def interp_id_for(self, tenant_id: str) -> str:
        return f"{tenant_id}:{sha256_hex(canonical_json(self.pipeline()))[:16]}"

    def current_interp(self, tenant_id: str = "default", *, process: bool = True) -> str:
        interp_id = self.interp_id_for(tenant_id)
        if process:
            self.process(tenant_id)
        return interp_id

    def is_stale(self, tenant_id: str = "default") -> bool:
        interp = self.store.get_interpretation(self.interp_id_for(tenant_id))
        latest = self.store.latest_obs_id(tenant_id)
        return interp is None or interp.get("processed_through") != latest or interp.get("status") != "active"

    # ── processing ─────────────────────────────────────────────────────────
    def process(self, tenant_id: str = "default", *, force: bool = False) -> dict[str, Any]:
        interp_id = self.interp_id_for(tenant_id)
        if not force and not self.is_stale(tenant_id):
            interp = self.store.get_interpretation(interp_id) or {}
            return {"interp_id": interp_id, "skipped": True, **(interp.get("stats") or {})}
        t0 = time.perf_counter()
        through = self.store.latest_obs_id(tenant_id)
        observations = list(self.store.iter_all_observations(tenant_id)) if through else []
        observations = [o for o in observations if through is None or o.obs_id <= through]
        self.store.activate_interpretation(tenant_id, interp_id, self.pipeline(), sha256_hex(canonical_json(self.pipeline())))
        built = self.build(tenant_id, interp_id, observations)
        t_build = time.perf_counter()
        event_docs = []
        for ev in built["events"]:
            d = ev.to_dict()
            d["run_id"] = built["run_of"].get(ev.event_id)
            d["run_basis"] = built["run_basis"].get(ev.event_id)
            event_docs.append(d)
        derived = built["derived"]
        stats = {
            "observations": len(observations),
            "events": len(event_docs),
            "runs": len(built["runs"]),
            "entities": len(built["entities"]),
            "relations": len(built["relations"]),
            "artifacts": len(built["artifacts"]),
            "diagnostics": len(built["diagnostics"]),
            "derived_records": len(derived),
            "build_ms": round((t_build - t0) * 1000, 1),
        }
        self.store.write_interpretation(
            interp_id,
            tenant_id,
            events=event_docs,
            diagnostics=[{k: v for k, v in d.to_dict().items()} for d in built["diagnostics"]],
            artifacts=artifact_rows(built["artifacts"]),
            entities=built["entities"],
            runs=list(built["runs"].values()),
            relations=built["relations"],
            processed_through=through,
            stats=stats,
        )
        if derived:
            self.store.put_derived(interp_id, tenant_id, derived)
        stats["total_ms"] = round((time.perf_counter() - t0) * 1000, 1)
        return {"interp_id": interp_id, "skipped": False, **stats}

    def build(self, tenant_id: str, interp_id: str, observations: Sequence[RawObservation]) -> dict[str, Any]:
        """Pure derivation from evidence (no store writes). Used by process() and replay."""
        ctx = NormalizeContext(tenant_id=tenant_id, interp_id=interp_id, artifact_key=self.store.artifact_key(tenant_id))
        events: list[ComputationalEvent] = []
        diagnostics: list[Diagnostic] = []
        by_normalizer: dict[str, list[RawObservation]] = {n.name: [] for n in self.normalizers}
        for obs in observations:
            target = next((n for n in self.normalizers if n.accepts(obs)), None)
            if target is None:
                diagnostics.append(Diagnostic(obs.obs_id, "warning", "no_normalizer", f"no normalizer accepts source_kind {obs.source_kind!r}"))
                continue
            by_normalizer[target.name].append(obs)
        for n in self.normalizers:
            batch = by_normalizer.get(n.name) or []
            if not batch:
                continue
            try:
                res = n.normalize(batch, ctx)
            except Exception as exc:  # a broken normalizer must not take down the pipeline
                logger.exception("normalizer %s failed", n.name)
                diagnostics.extend(Diagnostic(o.obs_id, "error", "normalizer_failed", f"{n.name}: {exc}") for o in batch)
                continue
            events.extend(res.events)
            diagnostics.extend(res.diagnostics)
        # invariant: every observation is represented by an event or a diagnostic
        covered = {o for e in events for o in e.derived_from} | {d.obs_id for d in diagnostics if d.obs_id}
        for obs in observations:
            if obs.obs_id not in covered:
                diagnostics.append(Diagnostic(obs.obs_id, "error", "unaccounted_observation", "normalizer neither mapped nor reported this observation"))
        events = _unique(events, diagnostics)
        seg = segment(events, tenant_id)
        index = build_source_index(events)
        entities = resolve_entities(events, tenant_id, seg.run_of)

        def register(value: Any, role: str) -> str:
            return ctx.artifact(value, role).artifact_id

        relations = build_execution(events, seg.run_of, index) + build_information(events, seg.run_of, ctx.artifacts, register)
        derived: list[dict[str, Any]] = []
        data = AnalysisInput(tenant_id, interp_id, events, seg.run_of, seg.runs, relations, ctx.artifacts)
        for analyzer in self.analyzers:
            try:
                derived.extend(analyzer.analyze(data))
            except Exception as exc:
                logger.exception("analyzer %s failed", analyzer.ref)
                diagnostics.append(Diagnostic(None, "error", "analyzer_failed", f"{analyzer.ref}: {exc}"))
        return {
            "events": events,
            "diagnostics": diagnostics,
            "run_of": seg.run_of,
            "run_basis": seg.basis,
            "runs": seg.runs,
            "entities": entities,
            "relations": relations,
            "artifacts": ctx.artifacts,
            "derived": derived,
        }


def _unique(events: list[ComputationalEvent], diagnostics: list[Diagnostic]) -> list[ComputationalEvent]:
    seen: dict[str, ComputationalEvent] = {}
    for ev in events:
        if ev.event_id in seen:
            diagnostics.append(Diagnostic(ev.derived_from[0] if ev.derived_from else None, "error", "duplicate_event_id", f"event id {ev.event_id} produced twice"))
            continue
        seen[ev.event_id] = ev
    return list(seen.values())


def artifact_rows(artifacts: dict[str, ArtifactContent]) -> list[dict[str, Any]]:
    return [{s: getattr(a, s) for s in a.__slots__} for a in artifacts.values()]
