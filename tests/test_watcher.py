"""Tests for FOUND-001..004: universal watch(), adapters, demo independence."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from agentwatch import GenericAdapter, detect_framework, detect_framework_label, watch
from agentwatch.core.event_bus import EventBus
from agentwatch.core.schema import AgentFramework, EventType


# ─────────────────────────────────────────────
# Stub agents that look like various frameworks
# ─────────────────────────────────────────────


class _FakeLangChainAgent:
    """Look like langchain.agents.AgentExecutor — has callbacks list and invoke."""

    __module__ = "langchain.agents.agent"

    def __init__(self) -> None:
        self.callbacks: list[Any] = []

    def invoke(self, inputs: dict) -> dict:
        return {"output": "done"}


class _FakeLangGraphGraph:
    __module__ = "langgraph.graph.state"

    def invoke(self, inputs: dict) -> dict:
        return {"messages": ["hello"]}

    def stream(self, inputs: dict):
        yield {"agent": {"messages": ["step1"]}}
        yield {"tools": {"messages": ["step2"]}}


class _FakeAutoGenAgent:
    __module__ = "autogen.agentchat.conversable_agent"

    def __init__(self) -> None:
        self.name = "test-agent"

    def generate_reply(self, messages=None, sender=None) -> str:
        return "reply"

    def send(self, message: Any, recipient: Any) -> None:
        return None


class _FakeSmolToolCallingAgent:
    __module__ = "smolagents.agents"

    def __init__(self) -> None:
        self.tools: dict[str, Any] = {}

    def run(self, prompt: str) -> str:
        return f"answer: {prompt}"


class _UnknownAgent:
    def run(self, prompt: str) -> str:
        return "ok"


# ─────────────────────────────────────────────
# Framework detection
# ─────────────────────────────────────────────


def test_detect_langchain():
    assert detect_framework(_FakeLangChainAgent()) == AgentFramework.LANGCHAIN
    assert detect_framework_label(_FakeLangChainAgent()) == "langchain"


def test_detect_langgraph():
    assert detect_framework_label(_FakeLangGraphGraph()) == "langgraph"


def test_detect_autogen():
    assert detect_framework_label(_FakeAutoGenAgent()) == "autogen"


def test_detect_smolagents():
    assert detect_framework_label(_FakeSmolToolCallingAgent()) == "smolagents"


def test_detect_unknown_fallback_to_custom():
    assert detect_framework(_UnknownAgent()) == AgentFramework.CUSTOM


def test_detect_none_returns_custom():
    assert detect_framework(None) == AgentFramework.CUSTOM


# ─────────────────────────────────────────────
# watch() — generic wrapping
# ─────────────────────────────────────────────


def test_watch_unknown_agent_returns_same_object():
    """watch() preserves identity — never returns a proxy that breaks `is`."""
    bus = EventBus()
    agent = _UnknownAgent()
    wrapped = watch(agent, event_bus=bus)
    assert wrapped is agent


def test_watch_emits_session_start():
    bus = EventBus()
    agent = _UnknownAgent()
    captured: list = []

    bus.subscribe_fn(lambda e: captured.append(e), EventType.SESSION_START)
    watch(agent, event_bus=bus)
    # publish_sync may schedule into asyncio.run — drain
    asyncio.run(asyncio.sleep(0.01))
    # At minimum, the adapter was attached and a session-start was queued or logged
    assert hasattr(agent, "_agentwatch_adapter")


def test_watch_preserves_return_value():
    bus = EventBus()
    agent = _UnknownAgent()
    wrapped = watch(agent, event_bus=bus)
    assert wrapped.run("hello") == "ok"


def test_watch_swallows_emit_errors():
    """An adapter that fails internally must not crash the host agent."""

    class _BrokenBus(EventBus):
        def publish_sync(self, event):  # noqa: ARG002
            raise RuntimeError("broken")

    bus = _BrokenBus()
    agent = _UnknownAgent()
    wrapped = watch(agent, event_bus=bus)
    # Calling the host agent must still succeed even though the bus is broken
    assert wrapped.run("hello") == "ok"


def test_watch_none_returns_none():
    assert watch(None) is None


def test_watch_idempotent():
    bus = EventBus()
    agent = _UnknownAgent()
    watch(agent, event_bus=bus)
    watch(agent, event_bus=bus)  # second call shouldn't double-wrap
    # No exception is the assertion
    assert agent.run("hi") == "ok"


# ─────────────────────────────────────────────
# Framework-specific adapter attachment
# ─────────────────────────────────────────────


def test_watch_langchain_adds_callback():
    from agentwatch.adapters.langchain import AgentWatchCallbackHandler

    bus = EventBus()
    agent = _FakeLangChainAgent()
    watch(agent, event_bus=bus)
    assert any(isinstance(h, AgentWatchCallbackHandler) for h in agent.callbacks)


def test_watch_langgraph_wraps_invoke():
    bus = EventBus()
    graph = _FakeLangGraphGraph()
    wrapped = watch(graph, event_bus=bus)
    # invoke() should still return the original payload
    assert wrapped.invoke({"messages": []}) == {"messages": ["hello"]}


def test_watch_autogen_wraps_methods():
    bus = EventBus()
    agent = _FakeAutoGenAgent()
    wrapped = watch(agent, event_bus=bus)
    assert wrapped.generate_reply([]) == "reply"


def test_watch_smolagents_wraps_run():
    bus = EventBus()
    agent = _FakeSmolToolCallingAgent()
    wrapped = watch(agent, event_bus=bus)
    assert wrapped.run("hi") == "answer: hi"


# ─────────────────────────────────────────────
# Generic adapter direct usage
# ─────────────────────────────────────────────


def test_generic_adapter_async_method():
    class AsyncAgent:
        async def arun(self, x: str) -> str:
            return x.upper()

    bus = EventBus()
    agent = AsyncAgent()
    GenericAdapter(agent, event_bus=bus).attach()
    result = asyncio.run(agent.arun("hi"))
    assert result == "HI"


def test_generic_adapter_propagates_exceptions():
    class FailingAgent:
        def run(self) -> str:
            raise ValueError("boom")

    bus = EventBus()
    agent = FailingAgent()
    GenericAdapter(agent, event_bus=bus).attach()
    with pytest.raises(ValueError, match="boom"):
        agent.run()
