from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class LLMProvider(ABC):
    """
    Abstract interface for LLM providers.

    All agents use this interface — concrete implementations
    (Gemini, OpenAI) are injected at startup.
    """

    @abstractmethod
    async def complete(self, system: str, user: str) -> str:
        """Return a free-text completion."""

    @abstractmethod
    async def complete_structured(self, system: str, user: str, schema: type[T]) -> T:
        """
        Return a structured response validated against `schema` (a Pydantic model).
        Implementations must use JSON mode or equivalent to guarantee parsability.
        """
