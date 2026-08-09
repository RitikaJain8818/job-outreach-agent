"""
Dependency injection for agents.
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
    if settings.llm_provider == "gemini":
        from app.integrations.llm.fallback import FallbackLLMProvider
        from app.integrations.llm.gemini import GeminiProvider

        if not settings.gemini_api_key:
            raise ConfigurationError("GEMINI_API_KEY is not set in environment")

        primary = GeminiProvider(api_key=settings.gemini_api_key, model=settings.gemini_model)
        fallbacks: list[LLMProvider] = []

        # Add fallback Gemini model if configured (e.g. gemini-3.1-flash-lite)
        if settings.llm_fallback_provider and settings.llm_fallback_provider != settings.gemini_model:
            fallbacks.append(
                GeminiProvider(api_key=settings.gemini_api_key, model=settings.llm_fallback_provider)
            )

        # Add OpenAI as fallback if API key is provided
        if settings.openai_api_key:
            from app.integrations.llm.openai import OpenAIProvider
            fallbacks.append(OpenAIProvider(api_key=settings.openai_api_key))

        provider = FallbackLLMProvider(primary, fallbacks) if fallbacks else primary
        return CachingLLMProvider(provider)

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
