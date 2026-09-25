"""Built-in analyzers run by the engine after graph construction."""

from __future__ import annotations

from agentwatch.analysis.base import Analyzer


def builtin_analyzers() -> list[Analyzer]:
    return []
