# Testing Strategy — Job Outreach Agent

## Principles

- Tests must be deterministic — no random IDs in assertions, no network calls.
- All external I/O (Gmail, LLM) is mocked via injected adapters.
- Test DB uses SQLite in-memory — no file created, no cleanup needed.
- Each test is isolated — no shared state between tests.

---

## Test Layers

### Unit Tests (`tests/agents/`, `tests/services/`)

- Test one function or agent method at a time.
- Mock all dependencies (LLM client, Gmail client, DB session).
- Fast — run in milliseconds.
- Cover: happy path, empty inputs, error cases.

### Integration Tests (`tests/integration/`)

- Test a full agent pipeline with in-memory SQLite DB.
- Mock only network I/O (Gmail API, LLM API).
- Verify: DB records created correctly, state transitions correct.

### Manual Verification

- Run `uvicorn app.main:app --reload` and check `/docs`.
- Send a test outreach via the API to a controlled Gmail account.

---

## Mock Strategy

### LLM Mock

```python
class MockLLMProvider(LLMProvider):
    def __init__(self, response: str):
        self._response = response

    async def complete(self, system: str, user: str) -> str:
        return self._response

    async def complete_structured(self, system: str, user: str, schema: type[T]) -> T:
        return schema.model_validate_json(self._response)
```

### Gmail Mock

```python
class MockGmailClient:
    sent_messages: list[dict] = []

    async def send(self, to: str, subject: str, body: str) -> str:
        self.sent_messages.append({"to": to, "subject": subject, "body": body})
        return "mock_thread_id_123"

    async def get_replies(self, thread_id: str) -> list[dict]:
        return []
```

---

## Fixtures (`tests/conftest.py`)

```python
@pytest.fixture
async def db_session() -> AsyncSession:
    # In-memory SQLite, creates all tables, yields session, drops all after

@pytest.fixture
def mock_llm() -> MockLLMProvider:
    # Returns mock with default valid JSON response

@pytest.fixture
def mock_gmail() -> MockGmailClient:
    # Returns fresh mock with empty sent_messages
```

---

## Running Tests

```bash
pytest                          # all tests
pytest tests/agents/            # agent unit tests only
pytest -k "test_email_gen"      # specific test
pytest --cov=app --cov-report=term-missing  # with coverage
```

---

## Coverage Targets

| Layer | Target |
|---|---|
| Agents | 85%+ |
| Services | 90%+ |
| API routes | 70%+ |
| Integrations | 60%+ (mocked) |
