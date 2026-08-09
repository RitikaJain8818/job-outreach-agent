"""
Unit tests for FallbackLLMProvider.
"""
from __future__ import annotations

import pytest
from pydantic import BaseModel

from app.core.exceptions import LLMProviderError
from app.integrations.llm.base import LLMProvider
from app.integrations.llm.fallback import FallbackLLMProvider


class FailingProvider(LLMProvider):
    async def complete(self, system: str, user: str) -> str:
        raise LLMProviderError("Primary rate limit hit 429")

    async def complete_structured(self, system: str, user: str, schema: type) -> BaseModel:
        raise LLMProviderError("Primary rate limit hit 429")


class SuccessProvider(LLMProvider):
    async def complete(self, system: str, user: str) -> str:
        return "fallback success"

    async def complete_structured(self, system: str, user: str, schema: type) -> BaseModel:
        class Dummy(BaseModel):
            msg: str = "ok"
        return Dummy()


@pytest.mark.asyncio
async def test_fallback_triggers_on_error() -> None:
    fallback = FallbackLLMProvider(
        primary=FailingProvider(),
        fallbacks=[SuccessProvider()],
    )
    result = await fallback.complete("sys", "user")
    assert result == "fallback success"


@pytest.mark.asyncio
async def test_all_failing_raises_exception() -> None:
    fallback = FallbackLLMProvider(
        primary=FailingProvider(),
        fallbacks=[FailingProvider()],
    )
    with pytest.raises(LLMProviderError) as exc_info:
        await fallback.complete("sys", "user")
    assert "All LLM providers failed" in str(exc_info.value)
