"""LangChain / LangGraph callback sensor.

Unlike the v0.2 adapter, this handler preserves ``run_id`` and ``parent_run_id`` on
every callback so the execution structure LangChain declares can be reconstructed.
It records raw callback payloads only; pairing and mapping happen in the normalizer.
"""

from __future__ import annotations

from typing import Any

from agentwatch.evidence.canonical import to_jsonable
from agentwatch.sensors.base import ObservationSink, Sensor

try:  # inherit from the real base class when LangChain is installed
    from langchain_core.callbacks import BaseCallbackHandler as _Base
except ImportError:  # pragma: no cover - optional dependency
    _Base = object  # type: ignore[assignment,misc]


def _safe(value: Any) -> Any:
    try:
        return to_jsonable(value)
    except (TypeError, ValueError):
        return repr(value)


def _generations(response: Any) -> dict[str, Any]:
    out: dict[str, Any] = {}
    gens = getattr(response, "generations", None)
    if gens:
        texts = []
        for batch in gens:
            for g in batch:
                text = getattr(g, "text", None)
                if not text and getattr(g, "message", None) is not None:
                    text = getattr(g.message, "content", None)
                texts.append(_safe(text))
        out["generations"] = texts
    llm_output = getattr(response, "llm_output", None)
    if llm_output:
        out["llm_output"] = _safe(llm_output)
    return out


def _documents(docs: Any) -> list[Any]:
    items = []
    for d in docs or []:
        items.append({"page_content": getattr(d, "page_content", _safe(d)), "metadata": _safe(getattr(d, "metadata", {}))})
    return items


class AgentWatchLangChainSensor(Sensor, _Base):  # type: ignore[misc,valid-type]
    sensor_type = "langchain"
    version = "1"
    raise_error = False
    run_inline = True

    def __init__(self, sink: ObservationSink, tenant_id: str = "default") -> None:
        Sensor.__init__(self, sink, tenant_id)

    def _emit(self, callback: str, payload: dict[str, Any], run_id: Any, parent_run_id: Any, **extra_ids: Any) -> None:
        ids = {"run_id": str(run_id) if run_id else None, "parent_run_id": str(parent_run_id) if parent_run_id else None}
        ids.update({k: str(v) for k, v in extra_ids.items() if v})
        self.ctx.emit(f"langchain.{callback}", payload, declared_ids=ids)

    # LLMs
    def on_llm_start(self, serialized: dict[str, Any], prompts: list[str], *, run_id: Any, parent_run_id: Any = None, tags: Any = None, metadata: Any = None, **kw: Any) -> None:
        self._emit("llm_start", {"serialized": _safe(serialized), "prompts": _safe(prompts), "tags": _safe(tags), "metadata": _safe(metadata), "invocation_params": _safe(kw.get("invocation_params"))}, run_id, parent_run_id)

    def on_chat_model_start(self, serialized: dict[str, Any], messages: list[list[Any]], *, run_id: Any, parent_run_id: Any = None, tags: Any = None, metadata: Any = None, **kw: Any) -> None:
        msgs = [[{"type": getattr(m, "type", None), "content": _safe(getattr(m, "content", m))} for m in batch] for batch in messages]
        self._emit("chat_model_start", {"serialized": _safe(serialized), "messages": msgs, "tags": _safe(tags), "metadata": _safe(metadata), "invocation_params": _safe(kw.get("invocation_params"))}, run_id, parent_run_id)

    def on_llm_end(self, response: Any, *, run_id: Any, parent_run_id: Any = None, **kw: Any) -> None:
        self._emit("llm_end", _generations(response), run_id, parent_run_id)

    def on_llm_error(self, error: BaseException, *, run_id: Any, parent_run_id: Any = None, **kw: Any) -> None:
        self._emit("llm_error", {"error": {"type": type(error).__name__, "message": str(error)}}, run_id, parent_run_id)

    # chains / graphs
    def on_chain_start(self, serialized: dict[str, Any], inputs: Any, *, run_id: Any, parent_run_id: Any = None, tags: Any = None, metadata: Any = None, **kw: Any) -> None:
        self._emit("chain_start", {"serialized": _safe(serialized), "inputs": _safe(inputs), "name": kw.get("name"), "tags": _safe(tags), "metadata": _safe(metadata)}, run_id, parent_run_id)

    def on_chain_end(self, outputs: Any, *, run_id: Any, parent_run_id: Any = None, **kw: Any) -> None:
        self._emit("chain_end", {"outputs": _safe(outputs)}, run_id, parent_run_id)

    def on_chain_error(self, error: BaseException, *, run_id: Any, parent_run_id: Any = None, **kw: Any) -> None:
        self._emit("chain_error", {"error": {"type": type(error).__name__, "message": str(error)}}, run_id, parent_run_id)

    # tools
    def on_tool_start(self, serialized: dict[str, Any], input_str: str, *, run_id: Any, parent_run_id: Any = None, tags: Any = None, metadata: Any = None, inputs: Any = None, **kw: Any) -> None:
        self._emit("tool_start", {"serialized": _safe(serialized), "input_str": _safe(input_str), "inputs": _safe(inputs), "tags": _safe(tags), "metadata": _safe(metadata)}, run_id, parent_run_id, tool_call_id=kw.get("tool_call_id"))

    def on_tool_end(self, output: Any, *, run_id: Any, parent_run_id: Any = None, **kw: Any) -> None:
        self._emit("tool_end", {"output": _safe(getattr(output, "content", output))}, run_id, parent_run_id)

    def on_tool_error(self, error: BaseException, *, run_id: Any, parent_run_id: Any = None, **kw: Any) -> None:
        self._emit("tool_error", {"error": {"type": type(error).__name__, "message": str(error)}}, run_id, parent_run_id)

    # retrievers
    def on_retriever_start(self, serialized: dict[str, Any], query: str, *, run_id: Any, parent_run_id: Any = None, tags: Any = None, metadata: Any = None, **kw: Any) -> None:
        self._emit("retriever_start", {"serialized": _safe(serialized), "query": query, "tags": _safe(tags), "metadata": _safe(metadata)}, run_id, parent_run_id)

    def on_retriever_end(self, documents: Any, *, run_id: Any, parent_run_id: Any = None, **kw: Any) -> None:
        self._emit("retriever_end", {"documents": _documents(documents)}, run_id, parent_run_id)

    def on_retriever_error(self, error: BaseException, *, run_id: Any, parent_run_id: Any = None, **kw: Any) -> None:
        self._emit("retriever_error", {"error": {"type": type(error).__name__, "message": str(error)}}, run_id, parent_run_id)

    # agents
    def on_agent_action(self, action: Any, *, run_id: Any, parent_run_id: Any = None, **kw: Any) -> None:
        self._emit("agent_action", {"tool": getattr(action, "tool", None), "tool_input": _safe(getattr(action, "tool_input", None)), "log": getattr(action, "log", None)}, run_id, parent_run_id)

    def on_agent_finish(self, finish: Any, *, run_id: Any, parent_run_id: Any = None, **kw: Any) -> None:
        self._emit("agent_finish", {"return_values": _safe(getattr(finish, "return_values", None)), "log": getattr(finish, "log", None)}, run_id, parent_run_id)
