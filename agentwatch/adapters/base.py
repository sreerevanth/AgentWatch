"""
Base adapter utilities. Semantic caching removed in v0.3.0.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Note: SemanticCache and cost tracking removed in v0.3.0
# Keeping stub functions for backward compatibility


def get_semantic_cache() -> None:
    """Semantic cache removed in v0.3.0. Always returns None."""
    return None


def set_semantic_cache(cache: Any | None) -> None:
    """Semantic cache removed in v0.3.0. No-op for backward compatibility."""
    logger.debug("set_semantic_cache called but semantic cache removed in v0.3.0")


async def before_provider_call(prompt: str, cache: Any | None = None) -> str | None:
    """
    Semantic cache removed in v0.3.0. Always returns None (cache miss).
    """
    return None


async def after_provider_call(
    prompt: str,
    response: str,
    metadata: dict[str, Any] | None = None,
    cache: Any | None = None,
) -> None:
    """
    Semantic cache removed in v0.3.0. No-op for backward compatibility.
    """
    pass
