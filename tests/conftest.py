from __future__ import annotations

from typing import AsyncGenerator, TypeVar
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.session import get_session
from app.integrations.llm.base import LLMProvider
from app.main import app
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

# ─── In-Memory Test Database ─────────────────────────────────────────────────

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = async_sessionmaker(bind=test_engine, expire_on_commit=False, class_=AsyncSession)


@pytest_asyncio.fixture(autouse=True)
async def setup_db() -> AsyncGenerator[None, None]:
    """Create all tables before each test, drop after."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """HTTP test client with DB session overridden to use in-memory SQLite."""

    async def override_get_session() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_session] = override_get_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


# ─── Mock LLM Provider ───────────────────────────────────────────────────────

class MockLLMProvider(LLMProvider):
    """Deterministic LLM mock. Configure `response_json` to control output."""

    def __init__(self, response_json: str) -> None:
        self._response_json = response_json

    async def complete(self, system: str, user: str) -> str:
        return self._response_json

    async def complete_structured(self, system: str, user: str, schema: type[T]) -> T:
        return schema.model_validate_json(self._response_json)


@pytest.fixture
def mock_llm_email() -> MockLLMProvider:
    return MockLLMProvider(
        response_json='{"subject": "Quick question about your ML team", '
        '"body": "Hi Jane, I noticed Acme is scaling fast...", '
        '"reasoning": "Personalized to company growth stage", '
        '"tokens_used": 150}'
    )


@pytest.fixture
def mock_llm_classify() -> MockLLMProvider:
    return MockLLMProvider(
        response_json='{"classification": "interested", "confidence": 0.92, '
        '"reasoning": "Positive reply expressing interest in connecting", '
        '"tokens_used": 80}'
    )


# ─── Mock Gmail Client ────────────────────────────────────────────────────────

class MockGmailClient:
    """Records sent messages. Returns empty replies by default."""

    def __init__(self) -> None:
        self.sent_messages: list[dict[str, str]] = []
        self.mock_replies: list[dict[str, str]] = []

    async def send(self, to: str, subject: str, body: str, html: str | None = None) -> str:
        self.sent_messages.append({"to": to, "subject": subject, "body": body})
        return "mock_thread_id_abc123"

    async def get_replies(self, thread_id: str) -> list[dict[str, str]]:
        return self.mock_replies


@pytest.fixture
def mock_gmail() -> MockGmailClient:
    return MockGmailClient()
