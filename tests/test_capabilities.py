from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from agentwatch.core.capabilities import AgentCapabilities, Capability


def test_capability_instantiation():
    cap = Capability(name="read")
    assert cap.name == "read"


def test_agent_capabilities_instantiation():
    caps = AgentCapabilities(
        read_paths=frozenset({Path("data")}),
        write_paths=frozenset({Path("output")}),
        network_domains=frozenset({"example.com"}),
        db_tables=frozenset({("users", "read")}),
        exec_binaries=frozenset({"python"}),
    )

    assert Path("data") in caps.read_paths
    assert "example.com" in caps.network_domains


def test_agent_capabilities_are_immutable():
    caps = AgentCapabilities()

    with pytest.raises(FrozenInstanceError):
        caps.read_paths = frozenset()