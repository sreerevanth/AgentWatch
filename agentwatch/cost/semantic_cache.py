"""
Semantic Caching Engine for repeated LLM queries.
"""

from __future__ import annotations

import asyncio
import datetime
import hashlib
import logging
from dataclasses import dataclass, field
from typing import Any

from agentwatch.memory.engine import EmbeddingProvider, _cosine_similarity
from agentwatch.models.cache import SemanticCacheEntry

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    query: str
    response: str
    embedding: list[float]
    metadata: dict[str, Any] | None = None
    created_at: datetime.datetime = field(
        default_factory=lambda: datetime.datetime.now(datetime.UTC)
    )


class SemanticCache:
    """Semantic cache utilizing cosine similarity bounds."""

    def __init__(
        self,
        similarity_threshold: float = 0.95,
        max_entries: int = 1000,
        embedding_provider: EmbeddingProvider | None = None,
        ttl_days: int | None = None,
        db_session=None,
    ):
        self.similarity_threshold = similarity_threshold
        self.max_entries = max_entries
        self.embedder = embedding_provider or EmbeddingProvider()
        self.ttl_days = ttl_days
        self.db_session = db_session
        self._cache: list[CacheEntry] = []
        self._lock = asyncio.Lock()

    def _hash_query(self, query: str) -> str:
        return hashlib.sha256(query.encode("utf-8")).hexdigest()

    async def get(self, query: str, ttl_days_override: int | None = None) -> str | None:
        """Get a cached response if semantic similarity is above threshold and not expired."""
        effective_ttl = ttl_days_override if ttl_days_override is not None else self.ttl_days

        query_embeddings = await self.embedder.embed([query])
        query_vec = query_embeddings[0] if query_embeddings else None

        if not query_vec:
            return None

        if self.db_session:
            # Check DB
            from sqlalchemy import select

            # Note: in a real implementation we would use pgvector's vector_cosine_ops
            # Since this is an async session, we execute the query
            # We fetch all candidates and calculate in memory for now or use the DB's cosine distance.
            # Here we'll rely on the DB if it's pgvector, otherwise we'll fetch and compare.

            # Try to fetch from DB. We'll fetch recent entries.
            now = datetime.datetime.now(datetime.UTC)
            q = select(SemanticCacheEntry)
            if effective_ttl is not None:
                cutoff = now - datetime.timedelta(days=effective_ttl)
                q = q.where(SemanticCacheEntry.created_at >= cutoff)

            # If pgvector is fully configured, we could do:
            # q = q.order_by(SemanticCacheEntry.prompt_vector.cosine_distance(query_vec)).limit(1)
            # For robustness and keeping it simple:
            try:
                # Assuming pgvector cosine distance:
                # .cosine_distance expects a list
                max_distance = 1.0 - self.similarity_threshold
                q = q.where(
                    SemanticCacheEntry.prompt_vector.cosine_distance(query_vec) <= max_distance
                )
                q = q.order_by(SemanticCacheEntry.prompt_vector.cosine_distance(query_vec)).limit(1)
                result = await self.db_session.execute(q)
                best_match_db = result.scalars().first()
                if best_match_db:
                    return best_match_db.response_text
            except Exception as e:
                logger.warning(f"Failed to use pgvector cosine distance: {e}")

        # In-memory fallback
        if not self._cache:
            return None

        now = datetime.datetime.now(datetime.UTC)

        async with self._lock:
            best_match: CacheEntry | None = None
            highest_sim = -1.0

            # Filter out expired entries if ttl_days is set
            valid_entries = []
            for entry in self._cache:
                if effective_ttl is not None:
                    if (now - entry.created_at).total_seconds() > effective_ttl * 86400:
                        continue
                valid_entries.append(entry)

            # Optional: update cache to prune expired entries
            if len(valid_entries) != len(self._cache):
                self._cache = valid_entries

            for entry in valid_entries:
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

        if self.db_session:
            db_entry = SemanticCacheEntry(
                prompt_hash=self._hash_query(query),
                prompt_vector=query_vec,
                response_text=response,
                framework=metadata.get("framework", "unknown") if metadata else "unknown",
            )
            try:
                self.db_session.add(db_entry)
                await self.db_session.commit()
            except Exception as e:
                logger.warning(f"Failed to persist cache entry to database: {e}")
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
