# Project Memory — Job Outreach Agent

> Living document. Append only. Never duplicate existing content.

---

## Architecture Decisions

| # | Decision | Rationale |
|---|---|---|
| 1 | Python 3.11+ / FastAPI | Async-first, Pydantic v2 native, excellent DX |
| 2 | SQLite (dev) → PostgreSQL (prod) | Zero-setup locally; Alembic handles migration to Postgres |
| 3 | SQLAlchemy 2.0 async ORM | First-class async support, type-safe queries |
| 4 | Multi-agent via Python classes | Deterministic, debuggable, no framework lock-in |
| 5 | Agent communication via Pydantic models | Typed I/O contracts between agents |
| 6 | LLM provider abstraction | Swap Gemini/OpenAI/Anthropic without changing agent logic |
| 7 | Prompt versioning in `/app/prompts/` | Traceable prompt changes, A/B testable |
| 8 | No external message broker (Phase 1) | Simplicity; add Celery/Redis when SaaS scale requires it |

---

## Completed Features

### Phase 1 — Foundation
- Project scaffolding, all ORM models, BaseAgent + 7 agents, FastAPI app, test fixtures

### Phase 3 — LLM Email Generation
- `GeminiProvider` upgraded to `gemini-3.6-flash` with token tracking (`usageMetadata`)
- `CachingLLMProvider` in `app/core/cache.py` for SHA256 prompt response caching (0 token usage on hits)
- Configurable sender profile (`SENDER_NAME`, `SENDER_EMAIL`, `SENDER_BACKGROUND`, `SENDER_TONE`)
- Dynamic personalization context injection into `email_generation_v1` prompt
- End-to-end live test script (`scripts/test_pipeline.py`) verified real LLM generation + Gmail delivery (1,470 tokens used)
- 18 tests passing cleanly

---

## Pending Work

- Phase 3: LLM email generation (prompt engineering, Gemini/OpenAI wiring, caching)
- Phase 4: Reply classification & follow-up scheduling
- Phase 5: Memory & learning engine
- Phase 6: Research agent (LinkedIn, Hunter.io)
- Phase 7+: API auth, multi-tenant, SaaS

---

## Known Bugs

*(none yet)*

---

## Lessons Learned

- **Gemini model selection**: Defaulted to `gemini-3.6-flash` for high performance and active quota.
- **Token tracking**: Extracted `totalTokenCount` directly from Gemini `usageMetadata`.
- **LLM caching**: `CachingLLMProvider` hashes `(system_prompt, user_prompt)` to avoid duplicate LLM calls during testing/reruns.

---

## Common Commands

```bash
# Install dependencies
pip install -e ".[dev]"

# Run development server
uvicorn app.main:app --reload

# Run tests
pytest

# Run linter
ruff check .

# Run type checker
mypy app/

# Apply DB migrations
alembic upgrade head

# Create new migration
alembic revision --autogenerate -m "description"
```

---

## Coding Standards

- All functions are typed (return types + params)
- Async everywhere in I/O paths
- Never catch bare `Exception` — use typed errors
- Structured logging via `app.core.logging`
- No business logic in route handlers (delegate to services)
- No direct DB access in agents (go through services)
- Prompt templates always in `/app/prompts/`
- Tests must be deterministic — mock all external I/O

---

## Frequently Used Prompts

*(append as they evolve)*

---

## Known API Limitations

- Gmail API: 250 quota units per user per second
- Gmail send: 100 recipients/message max
- Gemini: Rate limits vary by tier — handle 429 with backoff
