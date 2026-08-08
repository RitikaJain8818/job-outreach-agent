# Integrations — Job Outreach Agent

## Gmail API

### Authentication

**Development**: Desktop OAuth2 flow.

1. Download `credentials.json` from Google Cloud Console.
2. On first run, browser opens for consent — token saved to `token.json`.
3. Token refreshed automatically on expiry.

**Production / SaaS**: Service Account with domain-wide delegation OR per-user OAuth stored in DB (encrypted).

### Required Scopes

```
https://www.googleapis.com/auth/gmail.send
https://www.googleapis.com/auth/gmail.readonly
https://www.googleapis.com/auth/gmail.modify
```

### Rate Limits

| Limit | Value |
|---|---|
| Quota units/user/second | 250 |
| Send per day (free Gmail) | 500 messages |
| Send per day (Workspace) | 2,000 messages |

### Retry Strategy

- Retry on: `429 Too Many Requests`, `503 Service Unavailable`
- Backoff: exponential, max 3 attempts, base 2s
- Never retry on: `400 Bad Request`, `401 Unauthorized`

---

## LLM Provider Abstraction

### Interface (`app/integrations/llm/base.py`)

```python
class LLMProvider(ABC):
    async def complete(self, system: str, user: str) -> str: ...
    async def complete_structured(self, system: str, user: str, schema: type[T]) -> T: ...
```

### Supported Providers

| Provider | Class | Config Key |
|---|---|---|
| Google Gemini | `GeminiProvider` | `LLM_PROVIDER=gemini` |
| OpenAI | `OpenAIProvider` | `LLM_PROVIDER=openai` |

### Token Optimization Rules

1. Reuse system prompts — don't rebuild on every call.
2. Cache deterministic responses (same contact + template → same email).
3. Use structured output (JSON mode) — avoids parsing retry.
4. Track token usage per agent run in `agent_memory`.

### Fallback Strategy

If primary provider fails (500, timeout):
- Log the error with full context.
- Raise `LLMProviderError` — do not silently fall back.
- Operator can configure fallback provider via `LLM_FALLBACK_PROVIDER` env var.

---

## Future Integrations (Planned)

| Integration | Purpose | Phase |
|---|---|---|
| LinkedIn (RapidAPI / Playwright) | Contact enrichment | Phase 6 |
| Hunter.io | Email discovery | Phase 6 |
| Clearbit | Company enrichment | Phase 6 |
| Hacker News API | Job discovery | Phase 6 |
| Stripe | Billing (SaaS) | Phase 8 |
| Datadog / Grafana | Observability | Phase 8 |
