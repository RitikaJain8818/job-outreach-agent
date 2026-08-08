"""
LLM Response Cache

Simple in-memory cache for deterministic LLM outputs.
Prevents regenerating emails for the same contact + prompt version combination.

Design:
- Key: SHA256(prompt_version + system_prompt + user_prompt)
- Value: raw JSON string of the structured response
- Scope: process lifetime (resets on restart)
- Thread-safe: dict operations are GIL-protected in CPython

Upgrade path:
- Phase 5+: persist cache to `agent_memory` table for cross-restart reuse
- SaaS: use Redis for shared cache across workers
"""
from __future__ import annotations

import hashlib
from typing import TypeVar

from pydantic import BaseModel

from app.core.logging import get_logger
from app.integrations.llm.base import LLMProvider

logger = get_logger(__name__)
T = TypeVar("T", bound=BaseModel)

# Global in-memory cache: key → raw JSON string
_cache: dict[str, str] = {}


def _make_key(system: str, user: str) -> str:
    """Deterministic SHA256 key from prompt content."""
    content = f"{system}|||{user}"
    return hashlib.sha256(content.encode()).hexdigest()


def cache_stats() -> dict[str, int]:
    return {"size": len(_cache)}


def clear_cache() -> None:
    """Clear the cache — useful in tests."""
    _cache.clear()


class CachingLLMProvider(LLMProvider):
    """
    Wraps any LLMProvider with transparent caching.

    Only `complete_structured` is cached — free-text completions
    are not deterministic enough to cache reliably.

    Cache hits skip the LLM call entirely and return 0 tokens_used,
    which is accurate since no API call was made.
    """

    def __init__(self, provider: LLMProvider) -> None:
        self._provider = provider

    async def complete(self, system: str, user: str) -> str:
        # Free-text completions are not cached (non-deterministic use cases)
        return await self._provider.complete(system, user)

    async def complete_structured(self, system: str, user: str, schema: type[T]) -> T:
        key = _make_key(system, user)

        if key in _cache:
            logger.debug("llm.cache_hit", schema=schema.__name__, key=key[:16])
            return schema.model_validate_json(_cache[key])

        result = await self._provider.complete_structured(system, user, schema)

        # Store the result as JSON (excluding tokens_used so cache is provider-agnostic)
        cached_result = result.model_copy(update={"tokens_used": 0} if hasattr(result, "tokens_used") else {})
        _cache[key] = cached_result.model_dump_json()

        logger.debug(
            "llm.cache_miss",
            schema=schema.__name__,
            key=key[:16],
            tokens=getattr(result, "tokens_used", 0),
        )
        return result
