"""
PRT-004 — MCP Server Integration.

Expose AgentWatch as an MCP (Model Context Protocol) server.
Claude agents can query their own observability data via MCP tool calls.

Exposed tools:
    - confidence_history(session_id)
    - memory_query(question)
    - session_replay(session_id, step?)
    - safety_status()

The implementation is transport-agnostic — it can be wired into the actual
MCP stdio or HTTP transport at the API layer. Here we expose the tool
catalog + a synchronous `dispatch(tool, args)` entry point.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass
class MCPTool:
    name: str
    description: str
    input_schema: dict[str, Any]
    handler: Callable[[dict[str, Any]], Any] = field(repr=False)


@dataclass
class MCPResponse:
    ok: bool
    result: Any = None
    error: str | None = None


class AgentWatchMCPServer:
    """In-process MCP server skeleton — implements the tool catalog."""

    def __init__(self) -> None:
        self._tools: dict[str, MCPTool] = {}
        self._register_default_tools()

    # ── tool registration ──────────────────────────────────────────────
    def register(self, tool: MCPTool) -> None:
        self._tools[tool.name] = tool

    def tool_catalog(self) -> list[dict[str, Any]]:
        return [
            {
                "name": t.name,
                "description": t.description,
                "input_schema": t.input_schema,
            }
            for t in self._tools.values()
        ]

    # ── dispatch ───────────────────────────────────────────────────────
    def dispatch(self, tool_name: str, args: dict[str, Any] | None = None) -> MCPResponse:
        tool = self._tools.get(tool_name)
        if tool is None:
            return MCPResponse(ok=False, error=f"unknown tool: {tool_name}")
        try:
            result = tool.handler(args or {})
            return MCPResponse(ok=True, result=result)
        except Exception as exc:  # noqa: BLE001
            return MCPResponse(ok=False, error=f"{type(exc).__name__}: {exc}")

    # ── built-in tools ─────────────────────────────────────────────────
    def _register_default_tools(self) -> None:
        # confidence_history
        self.register(
            MCPTool(
                name="agentwatch_confidence_history",
                description="Return the confidence score history for a session.",
                input_schema={
                    "type": "object",
                    "required": ["session_id"],
                    "properties": {"session_id": {"type": "string"}},
                },
                handler=self._confidence_history,
            )
        )
        # memory_query
        self.register(
            MCPTool(
                name="agentwatch_memory_query",
                description="Query AgentWatch's persistent memory in natural language.",
                input_schema={
                    "type": "object",
                    "required": ["question"],
                    "properties": {"question": {"type": "string"}},
                },
                handler=self._memory_query,
            )
        )
        # session_replay
        self.register(
            MCPTool(
                name="agentwatch_session_replay",
                description="Retrieve a stored session for step-by-step inspection.",
                input_schema={
                    "type": "object",
                    "required": ["session_id"],
                    "properties": {
                        "session_id": {"type": "string"},
                        "step": {"type": "integer", "minimum": 0},
                    },
                },
                handler=self._session_replay,
            )
        )
        # safety_status
        self.register(
            MCPTool(
                name="agentwatch_safety_status",
                description="Return the current safety engine status and recent blocks.",
                input_schema={"type": "object", "properties": {}},
                handler=self._safety_status,
            )
        )

    # ── default handlers (overridable) ─────────────────────────────────
    # These are stubs operating against in-memory state. Wire them to the
    # real EventBus / DB / store at the API layer.
    confidence_provider: Callable[[str], list[float]] | None = None
    memory_provider: Callable[[str], list[dict[str, Any]]] | None = None
    replay_provider: Callable[[str, int | None], dict[str, Any]] | None = None
    safety_provider: Callable[[], dict[str, Any]] | None = None

    def _confidence_history(self, args: dict[str, Any]) -> list[float]:
        sid = args["session_id"]
        if self.confidence_provider:
            return self.confidence_provider(sid)
        return []

    def _memory_query(self, args: dict[str, Any]) -> list[dict[str, Any]]:
        q = args["question"]
        if self.memory_provider:
            return self.memory_provider(q)
        return []

    def _session_replay(self, args: dict[str, Any]) -> dict[str, Any]:
        sid = args["session_id"]
        step = args.get("step")
        if self.replay_provider:
            return self.replay_provider(sid, step)
        return {"session_id": sid, "step": step, "events": []}

    def _safety_status(self, args: dict[str, Any]) -> dict[str, Any]:
        if self.safety_provider:
            return self.safety_provider()
        return {"status": "ok", "blocks_last_hour": 0}


__all__ = ["AgentWatchMCPServer", "MCPTool", "MCPResponse"]
