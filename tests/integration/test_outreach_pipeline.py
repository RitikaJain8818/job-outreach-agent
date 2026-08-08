"""
Integration test: Full outreach send pipeline.

Tests the complete flow:
  Contact + Company in DB
  → OrchestratorAgent (with mock LLM + mock Gmail)
  → Email generated → Sent → Thread persisted → Target status = "sent"

All external I/O (LLM, Gmail) is mocked deterministically.
"""
from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import AgentContext
from app.agents.email_generator import EmailGeneratorAgent
from app.agents.follow_up import FollowUpAgent
from app.agents.gmail_agent import GmailAgent
from app.agents.memory import MemoryAgent
from app.agents.orchestrator import OrchestratorAgent
from app.agents.reply_classifier import ReplyClassifierAgent
from app.agents.research import ResearchAgent
from app.models.company import Company
from app.models.contact import Contact
from app.models.outreach import OutreachCampaign, OutreachTarget
from app.services.contact_service import ContactService
from app.services.email_thread_service import EmailThreadService
from app.services.outreach_service import OutreachService
from tests.conftest import MockGmailClient, MockLLMProvider


def build_orchestrator(
    session: AsyncSession,
    llm: MockLLMProvider,
    gmail: MockGmailClient,
) -> OrchestratorAgent:
    contact_svc = ContactService(session)
    outreach_svc = OutreachService(session)
    thread_svc = EmailThreadService(session)

    return OrchestratorAgent(
        memory_agent=MemoryAgent(session),
        research_agent=ResearchAgent(),
        email_generator=EmailGeneratorAgent(llm=llm, contact_service=contact_svc),
        gmail_agent=GmailAgent(
            gmail_client=gmail,
            outreach_service=outreach_svc,
            thread_service=thread_svc,
        ),
        reply_classifier=ReplyClassifierAgent(llm=llm),
        follow_up_agent=FollowUpAgent(llm=llm),
    )


@pytest.mark.asyncio
async def test_full_send_pipeline(
    db_session: AsyncSession,
    mock_llm_email: MockLLMProvider,
    mock_gmail: MockGmailClient,
) -> None:
    # ── Setup: create company, contact, campaign, target ──
    company = Company(name="FutureTech", industry="AI", description="We build AI tools.")
    db_session.add(company)
    await db_session.flush()

    contact = Contact(
        company_id=company.id,
        first_name="Maya",
        last_name="Patel",
        email="maya@futuretech.io",
        title="VP of Engineering",
    )
    db_session.add(contact)
    await db_session.flush()

    campaign = OutreachCampaign(
        name="AI Startup Outreach",
        sender_name="Ritika Jain",
        sender_email="ritika@example.com",
        goal="ML Engineer roles at AI startups",
    )
    db_session.add(campaign)
    await db_session.flush()

    target = OutreachTarget(
        campaign_id=campaign.id,
        contact_id=contact.id,
        status="pending",
    )
    db_session.add(target)
    await db_session.commit()

    # ── Build orchestrator with mocks ──
    orchestrator = build_orchestrator(db_session, mock_llm_email, mock_gmail)

    context = AgentContext(
        campaign_id=campaign.id,
        target_id=target.id,
        contact_id=contact.id,
        company_id=company.id,
        metadata={
            "sender_name": campaign.sender_name,
            "sender_email": campaign.sender_email,
            "sender_background": campaign.goal or "",
            "to_email": contact.email,
            "tone": "professional",
        },
    )

    # ── Act ──
    result = await orchestrator.execute(context)

    # ── Assert: orchestrator succeeded ──
    assert result.success is True, f"Orchestrator failed: {result.error}"
    assert result.output["gmail_thread_id"] == "mock_thread_id_abc123"
    assert result.output["email_subject"] == "Quick question about your ML team"

    # ── Assert: Gmail mock received the send call ──
    assert len(mock_gmail.sent_messages) == 1
    sent = mock_gmail.sent_messages[0]
    assert sent["to"] == "maya@futuretech.io"

    # ── Assert: EmailThread stored in DB ──
    thread_svc = EmailThreadService(db_session)
    thread = await thread_svc.get_thread_by_gmail_id("mock_thread_id_abc123")
    assert thread is not None
    assert thread.outreach_target_id == target.id
    assert len(thread.messages) == 1
    assert thread.messages[0].direction == "outbound"

    # ── Assert: OutreachTarget status updated ──
    await db_session.refresh(target)
    assert target.status == "sent"

    # ── Assert: Memory written ──
    from sqlalchemy import select
    from app.models.memory import AgentMemory
    stmt = select(AgentMemory).where(AgentMemory.scope == f"campaign:{campaign.id}")
    mem_result = await db_session.execute(stmt)
    memories = mem_result.scalars().all()
    assert len(memories) >= 1
