from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import CompanyNotFoundError, DuplicateTargetError
from app.services.company_service import CompanyService
from app.services.contact_service import ContactService
from app.services.outreach_service import OutreachService


@pytest.mark.asyncio
async def test_create_and_get_company(db_session: AsyncSession) -> None:
    svc = CompanyService(db_session)
    company = await svc.create(name="Acme Corp", domain="acme.com", industry="SaaS")

    assert company.id is not None
    assert company.name == "Acme Corp"
    assert company.domain == "acme.com"

    fetched = await svc.get(company.id)
    assert fetched.id == company.id


@pytest.mark.asyncio
async def test_get_nonexistent_company_raises(db_session: AsyncSession) -> None:
    svc = CompanyService(db_session)
    with pytest.raises(CompanyNotFoundError):
        await svc.get("does-not-exist")


@pytest.mark.asyncio
async def test_create_campaign_and_add_target(db_session: AsyncSession) -> None:
    company_svc = CompanyService(db_session)
    contact_svc = ContactService(db_session)
    outreach_svc = OutreachService(db_session)

    company = await company_svc.create(name="BetaCo", domain="betaco.io")
    contact = await contact_svc.create(
        company_id=company.id,
        first_name="John",
        last_name="Smith",
        email="john@betaco.io",
    )
    campaign = await outreach_svc.create_campaign(
        name="Q3 Outreach",
        sender_name="Ritika",
        sender_email="ritika@example.com",
    )
    target = await outreach_svc.add_target(
        campaign_id=campaign.id,
        contact_id=contact.id,
    )

    assert target.id is not None
    assert target.status == "pending"
    assert target.follow_up_count == 0


@pytest.mark.asyncio
async def test_duplicate_target_raises(db_session: AsyncSession) -> None:
    company_svc = CompanyService(db_session)
    contact_svc = ContactService(db_session)
    outreach_svc = OutreachService(db_session)

    company = await company_svc.create(name="GammaCo")
    contact = await contact_svc.create(
        company_id=company.id,
        first_name="Alice",
        last_name="Lee",
        email="alice@gammaco.com",
    )
    campaign = await outreach_svc.create_campaign(
        name="Test Campaign",
        sender_name="Bob",
        sender_email="bob@example.com",
    )
    await outreach_svc.add_target(campaign_id=campaign.id, contact_id=contact.id)

    with pytest.raises(DuplicateTargetError):
        await outreach_svc.add_target(campaign_id=campaign.id, contact_id=contact.id)
