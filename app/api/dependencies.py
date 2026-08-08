"""
Dependency injection for agents.

Agents are constructed here with their required services and clients.
FastAPI routes use these as Depends() to get fully assembled agents.

Design rationale:
- GmailClient is expensive to auth; in Phase 2 it's built once and cached.
- In Phase 1 (no real Gmail creds), routes that use the orchestrator will
  fail at runtime until credentials are configured — this is expected.
- LLM provider is configured based on settings.llm_provider.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.email_generator import EmailGeneratorAgent
from app.agents.follow_up import FollowUpAgent
from app.agents.gmail_agent import GmailAgent
from app.agents.memory import MemoryAgent
from app.agents.orchestrator import OrchestratorAgent
from app.agents.reply_classifier import ReplyClassifierAgent
from app.agents.research import ResearchAgent
from app.core.cache import CachingLLMProvider
from app.core.config import settings
from app.core.exceptions import ConfigurationError
from app.db.session import get_session
from app.integrations.llm.base import LLMProvider
from app.services.contact_service import ContactService
from app.services.email_thread_service import EmailThreadService
from app.services.outreach_service import OutreachService


def get_llm_provider() -> LLMProvider:
    """
    Build, cache-wrap, and return the configured LLM provider.
    Raises ConfigurationError if the provider is not configured.
    """
    if settings.llm_provider == "gemini":
        from app.integrations.llm.gemini import GeminiProvider
        if not settings.gemini_api_key:
            raise ConfigurationError("GEMINI_API_KEY is not set in environment")
        return CachingLLMProvider(GeminiProvider(api_key=settings.gemini_api_key, model=settings.gemini_model))

    if settings.llm_provider == "openai":
        from app.integrations.llm.openai import OpenAIProvider
        if not settings.openai_api_key:
            raise ConfigurationError("OPENAI_API_KEY is not set in environment")
        return CachingLLMProvider(OpenAIProvider(api_key=settings.openai_api_key))

    raise ConfigurationError(
        f"Unknown LLM_PROVIDER: {settings.llm_provider!r}. "
        "Valid values: 'gemini', 'openai'"
    )


def get_gmail_client() -> "GmailClient":  # type: ignore[name-defined]  # noqa: F821
    """
    Build and return an authenticated GmailClient.
    Raises GmailAuthError if credentials are not configured.
    """
    from app.integrations.gmail.auth import get_gmail_credentials
    from app.integrations.gmail.client import GmailClient

    creds = get_gmail_credentials(
        credentials_file=settings.gmail_credentials_file,
        token_file=settings.gmail_token_file,
    )
    return GmailClient.from_credentials(creds)


def get_orchestrator(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> OrchestratorAgent:
    """
    Assemble and return a fully wired OrchestratorAgent.

    All dependencies are constructed fresh per request (stateless agents).
    GmailClient auth happens here — will raise if credentials are absent.
    """
    llm = get_llm_provider()
    gmail_client = get_gmail_client()

    contact_svc = ContactService(session)
    outreach_svc = OutreachService(session)
    thread_svc = EmailThreadService(session)

    return OrchestratorAgent(
        memory_agent=MemoryAgent(session),
        research_agent=ResearchAgent(),
        email_generator=EmailGeneratorAgent(llm=llm, contact_service=contact_svc),
        gmail_agent=GmailAgent(
            gmail_client=gmail_client,
            outreach_service=outreach_svc,
            thread_service=thread_svc,
        ),
        reply_classifier=ReplyClassifierAgent(llm=llm),
        follow_up_agent=FollowUpAgent(llm=llm),
    )
