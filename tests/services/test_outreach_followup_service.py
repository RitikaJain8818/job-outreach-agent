"""
Integration tests for Phase 4 OutreachService follow-up methods.
Uses in-memory SQLite from conftest.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company
from app.models.contact import Contact
from app.models.outreach import OutreachCampaign, OutreachTarget
from app.services.outreach_service import OutreachService


async def _seed_campaign(session, follow_up_days=3, max_follow_ups=2):
    campaign = OutreachCampaign(
        name="Test Campaign",
        sender_name="Ritika",
        sender_email="ritika@test.com",
        follow_up_days=follow_up_days,
        max_follow_ups=max_follow_ups,
    )
    session.add(campaign)
    await session.commit()
    await session.refresh(campaign)
    return campaign


async def _seed_contact(session):
    company = Company(name="Acme Corp", domain="acme.com")
    session.add(company)
    await session.commit()
    await session.refresh(company)

    contact = Contact(
        first_name="Jane",
        last_name="Doe",
        email="jane@acme.com",
        company_id=company.id,
    )
    session.add(contact)
    await session.commit()
    await session.refresh(contact)
    return contact


async def _seed_sent_target(
    session,
    campaign_id,
    contact_id,
    *,
    next_action_at=None,
    created_at=None,
    follow_up_count=0,
):
    target = OutreachTarget(
        campaign_id=campaign_id,
        contact_id=contact_id,
        status="sent",
        follow_up_count=follow_up_count,
        next_action_at=next_action_at,
    )
    session.add(target)
    await session.commit()
    await session.refresh(target)
    if created_at is not None:
        target.created_at = created_at
        await session.commit()
        await session.refresh(target)
    return target


@pytest.mark.asyncio
async def test_target_due_when_created_before_cutoff(db_session):
    campaign = await _seed_campaign(db_session, follow_up_days=3)
    contact = await _seed_contact(db_session)
    old = datetime.now(UTC) - timedelta(days=4)
    await _seed_sent_target(db_session, campaign.id, contact.id, created_at=old)
    svc = OutreachService(db_session)
    due = await svc.get_sent_targets_due_for_followup(campaign.id)
    assert len(due) == 1


@pytest.mark.asyncio
async def test_target_not_due_when_created_recently(db_session):
    campaign = await _seed_campaign(db_session, follow_up_days=3)
    contact = await _seed_contact(db_session)
    recent = datetime.now(UTC) - timedelta(days=1)
    await _seed_sent_target(db_session, campaign.id, contact.id, created_at=recent)
    svc = OutreachService(db_session)
    due = await svc.get_sent_targets_due_for_followup(campaign.id)
    assert len(due) == 0


@pytest.mark.asyncio
async def test_target_due_when_next_action_at_in_past(db_session):
    campaign = await _seed_campaign(db_session)
    contact = await _seed_contact(db_session)
    past = datetime.now(UTC) - timedelta(hours=1)
    await _seed_sent_target(db_session, campaign.id, contact.id, next_action_at=past, follow_up_count=1)
    svc = OutreachService(db_session)
    due = await svc.get_sent_targets_due_for_followup(campaign.id)
    assert len(due) == 1


@pytest.mark.asyncio
async def test_target_not_due_when_next_action_at_in_future(db_session):
    campaign = await _seed_campaign(db_session)
    contact = await _seed_contact(db_session)
    future = datetime.now(UTC) + timedelta(days=2)
    await _seed_sent_target(db_session, campaign.id, contact.id, next_action_at=future, follow_up_count=1)
    svc = OutreachService(db_session)
    due = await svc.get_sent_targets_due_for_followup(campaign.id)
    assert len(due) == 0


@pytest.mark.asyncio
async def test_max_follow_ups_respected(db_session):
    campaign = await _seed_campaign(db_session, follow_up_days=1, max_follow_ups=2)
    contact = await _seed_contact(db_session)
    past = datetime.now(UTC) - timedelta(hours=1)
    await _seed_sent_target(db_session, campaign.id, contact.id, next_action_at=past, follow_up_count=2)
    svc = OutreachService(db_session)
    due = await svc.get_sent_targets_due_for_followup(campaign.id)
    assert len(due) == 0


@pytest.mark.asyncio
async def test_increment_follow_up_bumps_count(db_session):
    campaign = await _seed_campaign(db_session, follow_up_days=3)
    contact = await _seed_contact(db_session)
    target = await _seed_sent_target(db_session, campaign.id, contact.id)
    svc = OutreachService(db_session)
    updated = await svc.increment_follow_up(target.id, follow_up_days=3)
    assert updated.follow_up_count == 1
    assert updated.next_action_at is not None
    now = datetime.now(UTC)
    delta = updated.next_action_at.replace(tzinfo=UTC) - now
    assert timedelta(days=2, hours=23) < delta < timedelta(days=3, hours=1)


@pytest.mark.asyncio
async def test_increment_follow_up_twice(db_session):
    campaign = await _seed_campaign(db_session, follow_up_days=3)
    contact = await _seed_contact(db_session)
    target = await _seed_sent_target(db_session, campaign.id, contact.id)
    svc = OutreachService(db_session)
    await svc.increment_follow_up(target.id, follow_up_days=3)
    updated = await svc.increment_follow_up(target.id, follow_up_days=3)
    assert updated.follow_up_count == 2


@pytest.mark.asyncio
async def test_mark_replied_interested(db_session):
    campaign = await _seed_campaign(db_session)
    contact = await _seed_contact(db_session)
    target = await _seed_sent_target(db_session, campaign.id, contact.id)
    svc = OutreachService(db_session)
    updated = await svc.mark_replied(target.id, "interested")
    assert updated.status == "interested"


@pytest.mark.asyncio
async def test_mark_replied_auto_reply_stays_sent(db_session):
    campaign = await _seed_campaign(db_session)
    contact = await _seed_contact(db_session)
    target = await _seed_sent_target(db_session, campaign.id, contact.id)
    svc = OutreachService(db_session)
    updated = await svc.mark_replied(target.id, "auto_reply")
    assert updated.status == "sent"
