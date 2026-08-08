from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.email_generator import EmailGeneratorAgent
from app.agents.base import AgentContext
from app.models.company import Company
from app.models.contact import Contact
from app.services.contact_service import ContactService
from tests.conftest import MockLLMProvider


@pytest.mark.asyncio
async def test_email_generator_returns_email(
    db_session: AsyncSession,
    mock_llm_email: MockLLMProvider,
) -> None:
    # Arrange: create a company and contact in the test DB
    company = Company(name="Acme Corp", industry="SaaS")
    db_session.add(company)
    await db_session.flush()

    contact = Contact(
        company_id=company.id,
        first_name="Jane",
        last_name="Doe",
        email="jane@acme.com",
        title="Head of Engineering",
    )
    db_session.add(contact)
    await db_session.commit()

    svc = ContactService(db_session)
    agent = EmailGeneratorAgent(llm=mock_llm_email, contact_service=svc)

    context = AgentContext(
        campaign_id="camp-1",
        target_id="target-1",
        contact_id=contact.id,
        company_id=company.id,
        metadata={
            "sender_name": "Ritika Jain",
            "sender_background": "ML Engineer with 5 years experience",
            "tone": "professional",
        },
    )

    # Act
    result = await agent.execute(context)

    # Assert
    assert result.success is True
    assert result.agent_name == "EmailGeneratorAgent"
    assert "subject" in result.output
    assert len(result.output["subject"]) > 0
    assert "body" in result.output
    assert result.tokens_used == 150


@pytest.mark.asyncio
async def test_email_generator_fails_for_missing_contact(
    db_session: AsyncSession,
    mock_llm_email: MockLLMProvider,
) -> None:
    svc = ContactService(db_session)
    agent = EmailGeneratorAgent(llm=mock_llm_email, contact_service=svc)

    context = AgentContext(
        campaign_id="camp-1",
        target_id="target-1",
        contact_id="nonexistent-id",
        company_id="company-1",
        metadata={"sender_name": "Test", "tone": "professional"},
    )

    result = await agent.execute(context)

    assert result.success is False
    assert "not found" in (result.error or "").lower()
