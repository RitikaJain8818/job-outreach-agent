from __future__ import annotations

import json
from typing import TypeVar

import httpx
from pydantic import BaseModel

from app.core.exceptions import LLMProviderError
from app.core.logging import get_logger
from app.integrations.llm.base import LLMProvider

logger = get_logger(__name__)
T = TypeVar("T", bound=BaseModel)

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta"
DEFAULT_MODEL = "gemini-3.6-flash"


class GeminiProvider(LLMProvider):
    """
    Google Gemini provider using the REST API via httpx.

    Uses gemini-1.5-flash by default (fast + cheap).
    Override model in constructor for higher-quality use cases.
    """

    def __init__(self, api_key: str, model: str = DEFAULT_MODEL) -> None:
        if not api_key:
            raise LLMProviderError("GEMINI_API_KEY is not configured")
        self._api_key = api_key
        self._model = model
        self._client = httpx.AsyncClient(timeout=60.0)

    async def complete(self, system: str, user: str) -> str:
        payload = self._build_payload(system, user)
        text, _ = await self._call(payload)
        return text

    async def complete_structured(self, system: str, user: str, schema: type[T]) -> T:
        schema_json = json.dumps(schema.model_json_schema(), indent=2)
        augmented_user = (
            f"{user}\n\n"
            f"Respond ONLY with valid JSON matching this schema:\n{schema_json}"
        )
        payload = self._build_payload(system, augmented_user)
        raw, tokens_used = await self._call(payload)

        # Strip markdown code fences if present
        clean = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        try:
            result = schema.model_validate_json(clean)
        except Exception as e:
            raise LLMProviderError(
                f"Failed to parse Gemini response as {schema.__name__}: {e}\nRaw: {clean[:300]}"
            ) from e

        # Inject real token count if the schema supports it
        if hasattr(result, "tokens_used"):
            result.tokens_used = tokens_used

        return result

    def _build_payload(self, system: str, user: str) -> dict:
        return {
            "system_instruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {"temperature": 0.7, "maxOutputTokens": 2048},
        }

    async def _call(self, payload: dict) -> tuple[str, int]:
        """
        Returns (response_text, total_tokens_used).
        Token count extracted from usageMetadata in the Gemini response.
        """
        url = f"{GEMINI_API_BASE}/models/{self._model}:generateContent?key={self._api_key}"
        try:
            response = await self._client.post(url, json=payload)
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                raise LLMProviderError("Gemini rate limit hit (429). Retry with backoff.") from e
            raise LLMProviderError(
                f"Gemini API error {e.response.status_code}: {e.response.text}"
            ) from e
        except httpx.RequestError as e:
            raise LLMProviderError(f"Gemini request failed: {e}") from e

        data = response.json()
        try:
            text = data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError) as e:
            raise LLMProviderError(f"Unexpected Gemini response shape: {data}") from e

        # Extract real token usage from Gemini response
        tokens_used = data.get("usageMetadata", {}).get("totalTokenCount", 0)

        logger.debug(
            "gemini.response",
            model=self._model,
            chars=len(text),
            tokens=tokens_used,
        )
        return text, tokens_used

    async def close(self) -> None:
        await self._client.aclose()
