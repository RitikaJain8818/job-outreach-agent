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

OPENAI_API_BASE = "https://api.openai.com/v1"
DEFAULT_MODEL = "gpt-4o-mini"


class OpenAIProvider(LLMProvider):
    """
    OpenAI provider using the Chat Completions API.
    """

    def __init__(self, api_key: str, model: str = DEFAULT_MODEL) -> None:
        if not api_key:
            raise LLMProviderError("OPENAI_API_KEY is not configured")
        self._api_key = api_key
        self._model = model
        self._client = httpx.AsyncClient(
            base_url=OPENAI_API_BASE,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            timeout=60.0,
        )

    async def complete(self, system: str, user: str) -> str:
        payload = self._build_payload(system, user)
        text, _ = await self._call(payload)
        return text

    async def complete_structured(self, system: str, user: str, schema: type[T]) -> T:
        schema_json = json.dumps(schema.model_json_schema(), indent=2)
        augmented_system = (
            f"{system}\n\nRespond ONLY with valid JSON matching this schema:\n{schema_json}"
        )
        payload = self._build_payload(augmented_system, user, response_format="json_object")
        raw, tokens_used = await self._call(payload)
        try:
            result = schema.model_validate_json(raw)
        except Exception as e:
            raise LLMProviderError(f"Failed to parse OpenAI response as {schema.__name__}: {e}") from e

        if hasattr(result, "tokens_used"):
            result.tokens_used = tokens_used

        return result

    def _build_payload(
        self, system: str, user: str, response_format: str | None = None
    ) -> dict:
        payload: dict = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.7,
            "max_tokens": 2048,
        }
        if response_format:
            payload["response_format"] = {"type": response_format}
        return payload

    async def _call(self, payload: dict) -> tuple[str, int]:
        try:
            response = await self._client.post("/chat/completions", json=payload)
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                raise LLMProviderError("OpenAI rate limit hit (429). Retry with backoff.") from e
            raise LLMProviderError(f"OpenAI API error {e.response.status_code}: {e.response.text}") from e
        except httpx.RequestError as e:
            raise LLMProviderError(f"OpenAI request failed: {e}") from e

        data = response.json()
        try:
            text = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as e:
            raise LLMProviderError(f"Unexpected OpenAI response shape: {data}") from e

        tokens_used = data.get("usage", {}).get("total_tokens", 0)
        return text, tokens_used

    async def close(self) -> None:
        await self._client.aclose()
