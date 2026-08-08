from __future__ import annotations

import pytest

from app.core.cache import CachingLLMProvider, cache_stats, clear_cache
from tests.conftest import MockLLMProvider
from app.prompts.email_generation_v1 import EmailGenerationOutput


@pytest.fixture(autouse=True)
def reset_cache() -> None:
    """Ensure a clean cache before each test."""
    clear_cache()


@pytest.mark.asyncio
async def test_cache_miss_calls_provider(mock_llm_email: MockLLMProvider) -> None:
    caching = CachingLLMProvider(mock_llm_email)

    result = await caching.complete_structured(
        system="system",
        user="user prompt",
        schema=EmailGenerationOutput,
    )

    assert result.subject == "Quick question about your ML team"
    assert cache_stats()["size"] == 1


@pytest.mark.asyncio
async def test_cache_hit_skips_provider() -> None:
    """Second call with same prompt returns cached result without hitting provider."""
    call_count = 0

    class CountingMock(MockLLMProvider):
        async def complete_structured(self, system: str, user: str, schema) -> object:  # type: ignore[override]
            nonlocal call_count
            call_count += 1
            return await super().complete_structured(system, user, schema)

    provider = CountingMock(
        response_json='{"subject":"Cached subject","body":"body","reasoning":"r","tokens_used":100}'
    )
    caching = CachingLLMProvider(provider)

    await caching.complete_structured("sys", "same user", EmailGenerationOutput)
    await caching.complete_structured("sys", "same user", EmailGenerationOutput)

    assert call_count == 1  # Only one real LLM call
    assert cache_stats()["size"] == 1


@pytest.mark.asyncio
async def test_different_prompts_get_different_cache_entries() -> None:
    provider = MockLLMProvider(
        response_json='{"subject":"S","body":"B","reasoning":"R","tokens_used":10}'
    )
    caching = CachingLLMProvider(provider)

    await caching.complete_structured("sys", "prompt A", EmailGenerationOutput)
    await caching.complete_structured("sys", "prompt B", EmailGenerationOutput)

    assert cache_stats()["size"] == 2


@pytest.mark.asyncio
async def test_cache_hit_returns_zero_tokens(mock_llm_email: MockLLMProvider) -> None:
    """Cache hits correctly report 0 tokens (no API call made)."""
    caching = CachingLLMProvider(mock_llm_email)

    first = await caching.complete_structured("sys", "user", EmailGenerationOutput)
    second = await caching.complete_structured("sys", "user", EmailGenerationOutput)

    assert first.tokens_used == 150   # Real call — populated by mock
    assert second.tokens_used == 0    # Cache hit — no API call
