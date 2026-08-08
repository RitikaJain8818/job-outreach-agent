# Coding Guidelines — Job Outreach Agent

## Python Version

Python 3.11+ required. Use `match` statements, `ExceptionGroup`, and `tomllib` where appropriate.

---

## Type Annotations

- All function parameters and return types must be annotated.
- Use `from __future__ import annotations` in every module.
- Use `X | None` instead of `Optional[X]`.
- Use `list[X]`, `dict[K, V]` (lowercase) — no `List`, `Dict` from `typing`.

```python
# Correct
def get_contact(contact_id: str) -> Contact | None:
    ...

# Wrong
def get_contact(contact_id) -> Optional[Contact]:
    ...
```

---

## Async

- All I/O operations must be async.
- Use `async def` for all service methods and agent methods.
- Never use `time.sleep()` — use `asyncio.sleep()`.
- Use `asyncio.gather()` for parallel independent operations.

---

## Error Handling

- Never catch bare `Exception` without re-raising or logging.
- Use typed exceptions from `app/core/exceptions.py`.
- Always provide a message with context.

```python
# Correct
raise OutreachError(f"Failed to send email to {contact.email}: {e}") from e

# Wrong
except Exception:
    pass
```

---

## Logging

- Use the structured logger from `app.core.logging`.
- Log at entry points and error paths — not inside every line.
- Include relevant context (IDs, statuses) in log records.

```python
logger.info("email.sent", contact_id=str(contact.id), thread_id=thread_id)
logger.error("gmail.send_failed", contact_email=contact.email, error=str(e))
```

---

## File & Module Organization

- One class or one cohesive set of functions per file.
- Max ~200 lines per file. Split if larger.
- No circular imports — use `TYPE_CHECKING` guard if needed.
- Business logic lives in services and agents — NOT in routes or models.

---

## Database Access

- All DB access through services only.
- Use async sessions with context managers.
- Avoid N+1 queries — use `selectinload` / `joinedload`.
- Never commit inside agent logic — services own transactions.

---

## Naming Conventions

| Item | Convention | Example |
|---|---|---|
| Files | snake_case | `email_generator.py` |
| Classes | PascalCase | `EmailGeneratorAgent` |
| Functions | snake_case | `generate_email()` |
| Constants | UPPER_SNAKE | `MAX_FOLLOW_UPS` |
| Env vars | UPPER_SNAKE | `GMAIL_CLIENT_ID` |
| DB tables | snake_case plural | `outreach_targets` |

---

## Dependency Injection

- External clients (Gmail, LLM) are injected via constructor.
- Agents receive services via constructor — never import globally.
- This ensures full testability via mocks.

---

## Testing Rules

- Every agent must have at least one unit test with mocked I/O.
- Every service must have at least one DB integration test.
- No `time.sleep()` in tests — use `pytest-asyncio` and `AsyncMock`.
- Tests must be deterministic — seed data, no random IDs in assertions.

---

## Linting & Formatting

```bash
ruff check .         # lint
ruff format .        # format
mypy app/            # type check
```

Ruff replaces isort + flake8 + black. No separate black config needed.

---

## Commit Message Format

```
feat: add ReplyClassifierAgent with Gemini integration
fix: handle Gmail 429 rate limit with exponential backoff
docs: update database.md with agent_memory table
test: add deterministic unit test for EmailGeneratorAgent
refactor: extract prompt context builder into separate module
```
