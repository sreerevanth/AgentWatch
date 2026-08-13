from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Capability:
    """Represents a single capability permission."""

    name: str


@dataclass(frozen=True)
class AgentCapabilities:
    """Immutable collection of agent capabilities."""

    read_paths: frozenset[Path] = field(default_factory=frozenset)
    write_paths: frozenset[Path] = field(default_factory=frozenset)
    network_domains: frozenset[str] = field(default_factory=frozenset)
    db_tables: frozenset[tuple[str, str]] = field(default_factory=frozenset)
    exec_binaries: frozenset[str] = field(default_factory=frozenset)


__all__ = ["Capability", "AgentCapabilities"]
