"""
Semantic Caching Engine for repeated LLM queries.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

from agentwatch.memory.engine import EmbeddingProvider, _cosine_similarity

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    query: str
    response: str
    embedding: list[float]
    metadata: dict[str, Any] | None = None


class SemanticCache:
    """Semantic cache utilizing cosine similarity bounds."""

    def __init__(
        self,
        similarity_threshold: float = 0.95,
        max_entries: int = 1000,
        embedding_provider: EmbeddingProvider | None = None,
    ):
        self.similarity_threshold = similarity_threshold
        self.max_entries = max_entries
        self.embedder = embedding_provider or EmbeddingProvider()
        self._cache: list[CacheEntry] = []
        self._lock = asyncio.Lock()

    async def get(self, query: str) -> str | None:
        """Get a cached response if semantic similarity is above threshold."""
        if not self._cache:
            return None

        query_embeddings = await self.embedder.embed([query])
        query_vec = query_embeddings[0] if query_embeddings else None

        if not query_vec:
            return None

        async with self._lock:
            best_match: CacheEntry | None = None
            highest_sim = -1.0

            for entry in self._cache:
                sim = _cosine_similarity(query_vec, entry.embedding)
                if sim >= self.similarity_threshold and sim > highest_sim:
                    highest_sim = sim
                    best_match = entry

            if best_match:
                logger.info("Semantic cache hit with similarity %.4f", highest_sim)
                return best_match.response

            return None

    async def set(self, query: str, response: str, metadata: dict[str, Any] | None = None) -> None:
        """Store a query-response pair in the semantic cache."""
        query_embeddings = await self.embedder.embed([query])
        query_vec = query_embeddings[0] if query_embeddings else None

        if not query_vec:
            return

        async with self._lock:
            self._cache.append(
                CacheEntry(
                    query=query,
                    response=response,
                    embedding=query_vec,
                    metadata=metadata,
                )
            )
            if len(self._cache) > self.max_entries:
                self._cache.pop(0)
            logger.debug("Added entry to semantic cache. Size: %d", len(self._cache))
