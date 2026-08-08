from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import AgentContext
from app.agents.gmail_agent import GmailAgent
from app.models.company import Company
from app.models.contact import Contact
from app.models.outreach import OutreachCampaign, OutreachTarget
from app.services.email_thread_service import EmailThreadService
from app.services.outreach_service import OutreachService
from tests.conftest import MockGmailClient


async def _setup_target(session: AsyncSession) -> tuple[OutreachTarget, Contact, str]:
    """Helper: create company, contact, campaign, and target for tests."""
    company = Company(name="TestCo", industry="Tech")
    session.add(company)
    await session.flush()

    contact = Contact(
        company_id=company.id,
        first_name="Alice",
        last_name="Smith",
        email="alice@testco.com",
    )
    session.add(contact)
    await session.flush()

    campaign = OutreachCampaign(
        name="Test Campaign",
        sender_name="Bob",
        sender_email="bob@example.com",
    )
    session.add(campaign)
    await session.flush()

    target = OutreachTarget(
        campaign_id=campaign.id,
        contact_id=contact.id,
        status="pending",
    )
    session.add(target)
    await session.commit()

    return target, contact, company.id


@pytest.mark.asyncio
async def test_gmail_agent_send_creates_thread_and_updates_status(
    db_session: AsyncSession,
    mock_gmail: MockGmailClient,
) -> None:
    target, contact, company_id = await _setup_target(db_session)

    outreach_svc = OutreachService(db_session)
    thread_svc = EmailThreadService(db_session)
    agent = GmailAgent(
        gmail_client=mock_gmail,
        outreach_service=outreach_svc,
        thread_service=thread_svc,
    )

    context = AgentContext(
        campaign_id=target.campaign_id,
        target_id=target.id,
        contact_id=contact.id,
        company_id=company_id,
        metadata={
            "mode": "send",
            "email_subject": "Quick intro",
            "email_body": "Hi Alice, reaching out about...",
            "to_email": contact.email,
        },
    )

    result = await agent.execute(context)

    # Agent succeeds
    assert result.success is True
    assert result.output["gmail_thread_id"] == "mock_thread_id_abc123"

    # EmailThread persisted
    thread = await thread_svc.get_thread_by_gmail_id("mock_thread_id_abc123")
    assert thread is not None
    assert thread.subject == "Quick intro"
    assert len(thread.messages) == 1
    assert thread.messages[0].direction == "outbound"

    # Target status updated to "sent"
    refreshed_target = await db_session.get(OutreachTarget, target.id)
    assert refreshed_target is not None
    assert refreshed_target.status == "sent"

    # Gmail client actually sent the message
    assert len(mock_gmail.sent_messages) == 1
    assert mock_gmail.sent_messages[0]["to"] == "alice@testco.com"


@pytest.mark.asyncio
async def test_gmail_agent_send_fails_without_required_fields(
    db_session: AsyncSession,
    mock_gmail: MockGmailClient,
) -> None:
    target, contact, company_id = await _setup_target(db_session)

    agent = GmailAgent(
        gmail_client=mock_gmail,
        outreach_service=OutreachService(db_session),
        thread_service=EmailThreadService(db_session),
    )

    context = AgentContext(
        campaign_id=target.campaign_id,
        target_id=target.id,
        contact_id=contact.id,
        company_id=company_id,
        metadata={
            "mode": "send",
            # Missing email_body and to_email
            "email_subject": "Hello",
        },
    )

    result = await agent.execute(context)
    assert result.success is False
    assert "missing" in (result.error or "").lower()


@pytest.mark.asyncio
async def test_gmail_agent_poll_detects_new_replies(
    db_session: AsyncSession,
    mock_gmail: MockGmailClient,
) -> None:
    target, contact, company_id = await _setup_target(db_session)

    thread_svc = EmailThreadService(db_session)

    # Pre-create a thread record
    thread = await thread_svc.create_thread(
        outreach_target_id=target.id,
        gmail_thread_id="existing_thread_123",
        subject="Quick intro",
    )
    # Record the original outbound message
    await thread_svc.record_outbound(
        thread_id=thread.id,
        gmail_message_id="existing_thread_123",
        body_text="Original email",
    )

    # Configure mock to return a new inbound reply
    mock_gmail.mock_replies = [
        {
            "gmail_message_id": "existing_thread_123",
            "body_text": "Original email",
            "direction": "inbound",
        },
        {
            "gmail_message_id": "reply_msg_456",
            "body_text": "Thanks for reaching out!",
            "direction": "inbound",
        },
    ]

    agent = GmailAgent(
        gmail_client=mock_gmail,
        outreach_service=OutreachService(db_session),
        thread_service=thread_svc,
    )

    context = AgentContext(
        campaign_id=target.campaign_id,
        target_id=target.id,
        contact_id=contact.id,
        company_id=company_id,
        metadata={
            "mode": "poll",
            "gmail_thread_id": "existing_thread_123",
            "thread_db_id": thread.id,
        },
    )

    result = await agent.execute(context)

    assert result.success is True
    # Only 1 new reply (reply_msg_456 is new; existing_thread_123 already stored)
    assert result.output["new_reply_count"] == "1"
