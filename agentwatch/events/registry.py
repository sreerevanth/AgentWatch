"""Registry of normalizers. New normalizers register here (or via entry points)."""

from __future__ import annotations

import logging
from importlib.metadata import entry_points

from agentwatch.events.normalize import Normalizer


def builtin_normalizers() -> list[Normalizer]:
    from agentwatch.events.normalizers.anthropic import AnthropicNormalizer
    from agentwatch.events.normalizers.claude_code import ClaudeCodeNormalizer
    from agentwatch.events.normalizers.langchain import LangChainNormalizer
    from agentwatch.events.normalizers.legacy import LegacyNormalizer
    from agentwatch.events.normalizers.mcp import MCPNormalizer
    from agentwatch.events.normalizers.native import NativeNormalizer
    from agentwatch.events.normalizers.openai import OpenAINormalizer
    from agentwatch.events.normalizers.otel import OTelNormalizer

    return [
        NativeNormalizer(),
        LegacyNormalizer(),
        OTelNormalizer(),
        LangChainNormalizer(),
        ClaudeCodeNormalizer(),
        OpenAINormalizer(),
        AnthropicNormalizer(),
        MCPNormalizer(),
    ]


def all_normalizers() -> list[Normalizer]:
    found = builtin_normalizers()
    names = {n.name for n in found}
    try:
        for ep in entry_points(group="agentwatch.normalizers"):
            obj = ep.load()()
            if isinstance(obj, Normalizer) and obj.name not in names:
                found.append(obj)
                names.add(obj.name)
    except Exception:  # pragma: no cover - broken third-party plugin must not break core
        logging.getLogger(__name__).warning("failed to load third-party normalizers", exc_info=True)
    return found
