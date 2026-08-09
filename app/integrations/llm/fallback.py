"""
Fallback LLM Provider wrapper.

Tries primary LLM provider first. If it raises an error (e.g. rate limit 429),
automatically retries with the backup providers in sequence.
"""
from __future__ import annotations

from typing import TypeVar

from pydantic import BaseModel

from app.core.exceptions import LLMProviderError
from app.core.logging import get_logger
from app.integrations.llm.base import LLMProvider

logger = get_logger(__name__)
T = TypeVar("T", bound=BaseModel)


class FallbackLLMProvider(LLMProvider):
    def __init__(self, primary: LLMProvider, fallbacks: list[LLMProvider]) -> None:
        self._primary = primary
        self._fallbacks = fallbacks
        self._all_providers = [primary, *fallbacks]

    async def complete(self, system: str, user: str) -> str:
        last_error: Exception | None = None
        for idx, provider in enumerate(self._all_providers):
            try:
                return await provider.complete(system, user)
            except Exception as e:  # noqa: BLE001
                last_error = e
                logger.warning(
                    "llm.fallback_triggered",
                    attempt=idx + 1,
                    total=len(self._all_providers),
                    error=str(e),
                )
        raise LLMProviderError(f"All LLM providers failed. Last error: {last_error}") from last_error

    async def complete_structured(self, system: str, user: str, schema: type[T]) -> T:
        last_error: Exception | None = None
        for idx, provider in enumerate(self._all_providers):
            try:
                return await provider.complete_structured(system, user, schema)
            except Exception as e:  # noqa: BLE001
                last_error = e
                logger.warning(
                    "llm.fallback_triggered_structured",
                    attempt=idx + 1,
                    total=len(self._all_providers),
                    error=str(e),
                )
        raise LLMProviderError(f"All LLM providers failed. Last error: {last_error}") from last_error
