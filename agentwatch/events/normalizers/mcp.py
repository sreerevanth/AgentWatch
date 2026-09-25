"""Normalizer for MCP JSON-RPC messages (paired by server session + JSON-RPC id)."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from agentwatch.events.model import (
    DeclaredLink,
    Diagnostic,
    Effect,
    EffectKind,
    EntityRef,
    EventKind,
    EventStatus,
)
from agentwatch.events.normalize import (
    EventBuilder,
    NormalizeContext,
    Normalizer,
    NormalizeResult,
    source_order,
    temporal,
)
from agentwatch.evidence.model import RawObservation


class MCPNormalizer(Normalizer):
    name = "mcp"
    version = "1"
    source_kinds = frozenset({"mcp.message"})
    maturity = "EXPERIMENTAL"

    def normalize(self, observations: Sequence[RawObservation], ctx: NormalizeContext) -> NormalizeResult:
        result = NormalizeResult()
        pairs: dict[tuple[str, str], dict[str, RawObservation]] = {}
        notes: list[RawObservation] = []
        for obs in source_order(observations):
            p = obs.payload()
            msg = p.get("message") or {}
            jid = obs.declared("jsonrpc_id")
            if jid is None:
                notes.append(obs)
                continue
            key = (obs.declared("mcp_session") or "", jid)
            slot = "request" if "method" in msg else "response"
            pairs.setdefault(key, {})[slot] = obs
        for (session, jid), parts in pairs.items():
            result.events.append(self._call(session, jid, parts, ctx, result))
        for obs in notes:
            b = EventBuilder(self, ctx, [obs])
            p = obs.payload()
            b.kind = EventKind.MESSAGE
            b.operation = f"notification:{(p.get('message') or {}).get('method')}"
            b.object = EntityRef("mcp_server", str(p.get("server")))
            b.input(p.get("message"), role="message")
            b.status = EventStatus.OK
            b.time = temporal(obs)
            result.events.append(b.build())
        return result

    def _call(self, session: str, jid: str, parts: dict[str, RawObservation], ctx: NormalizeContext, result: NormalizeResult) -> Any:
        req, res = parts.get("request"), parts.get("response")
        obs = [o for o in (req, res) if o]
        b = EventBuilder(self, ctx, obs)
        rq = (req.payload().get("message") or {}) if req else {}
        rs = (res.payload().get("message") or {}) if res else {}
        server = (req or res).payload().get("server")  # type: ignore[union-attr]
        method = rq.get("method", "unknown")
        params = rq.get("params") or {}
        if method == "tools/call":
            b.kind = EventKind.TOOL_INVOCATION
            b.operation = str(params.get("name"))
            b.object = EntityRef("tool", f"mcp/{server}/{params.get('name')}")
            b.input(params.get("arguments") or {}, role="arguments")
        elif method in ("resources/read", "prompts/get"):
            b.kind = EventKind.RETRIEVAL
            b.operation = method
            b.object = EntityRef("mcp_server", str(server))
            b.input(params, role="query")
            b.effects.append(Effect(EffectKind.READ, b.object.canonical))
        else:
            b.kind = EventKind.EXTERNAL_IO
            b.operation = method
            b.object = EntityRef("mcp_server", str(server))
            if params:
                b.input(params, role="params")
        if "result" in rs:
            b.output(rs["result"], role="result")
            b.status = EventStatus.ERROR if (rs.get("result") or {}).get("isError") else EventStatus.OK
        elif "error" in rs:
            b.status = EventStatus.ERROR
            b.error = rs["error"]
        else:
            b.status = EventStatus.UNKNOWN
            result.diagnostics.append(Diagnostic((req or res).obs_id, "warning", "no_response", f"MCP request {jid} without response"))  # type: ignore[union-attr]
        anchor = req or res
        assert anchor is not None
        b.source_ids = [("mcp.call", f"{session}/{jid}")]
        if anchor.declared("parent_span_id"):
            b.parents.append(DeclaredLink("parent", "native.span", anchor.declared("parent_span_id") or ""))
        if anchor.declared("run_id"):
            b.run_key = ("native.run", anchor.declared("run_id") or "")
        b.time = temporal(req, res) if req else temporal(res, None)
        return b.build()
