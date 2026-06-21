import hashlib
from dataclasses import dataclass


@dataclass
class CacheHit:
    prompt_hash: str
    response_text: str
    framework: str


class SemanticCacheManager:
    """
    Manages semantic caching of agent prompts to save API costs.
    """

    def __init__(self):
        # In-memory dictionary for the simplest pass of Behavior 1
        self._cache = {}

    async def store(self, prompt: str, response_text: str, framework: str) -> None:
        """
        Stores the response for a given prompt.
        """
        prompt_hash = self._hash_prompt(prompt)
        cache_key = f"{framework}:{prompt_hash}"
        self._cache[cache_key] = CacheHit(
            prompt_hash=prompt_hash, response_text=response_text, framework=framework
        )

    async def search(self, prompt: str, framework: str) -> CacheHit | None:
        """
        Searches the cache for an exact match or semantically similar prompt.
        """
        prompt_hash = self._hash_prompt(prompt)
        cache_key = f"{framework}:{prompt_hash}"
        return self._cache.get(cache_key)

    def _hash_prompt(self, prompt: str) -> str:
        return hashlib.sha256(prompt.encode("utf-8")).hexdigest()
