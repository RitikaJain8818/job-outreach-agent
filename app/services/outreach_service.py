from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import CampaignNotFoundError, DuplicateTargetError
from app.core.logging import get_logger
from app.models.outreach import OutreachCampaign, OutreachTarget

logger = get_logger(__name__)

# Status values that mean the target has replied — no further follow-ups needed
_TERMINAL_STATUSES = frozenset(
    {"interested", "not_interested", "replied", "opted_out", "bounced"}
)


class OutreachService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_campaign(
        self,
        name: str,
        sender_name: str,
        sender_email: str,
        goal: str | None = None,
        follow_up_days: int = 3,
        max_follow_ups: int = 2,
    ) -> OutreachCampaign:
        campaign = OutreachCampaign(
            name=name,
            goal=goal,
            sender_name=sender_name,
            sender_email=sender_email,
            follow_up_days=follow_up_days,
            max_follow_ups=max_follow_ups,
        )
        self._session.add(campaign)
        await self._session.commit()
        await self._session.refresh(campaign)
        logger.info("campaign.created", campaign_id=campaign.id, name=campaign.name)
        return campaign

    async def get_campaign(self, campaign_id: str) -> OutreachCampaign:
        campaign = await self._session.get(OutreachCampaign, campaign_id)
        if campaign is None:
            raise CampaignNotFoundError(f"Campaign {campaign_id!r} not found")
        return campaign

    async def add_target(
        self,
        campaign_id: str,
        contact_id: str,
        job_opening_id: str | None = None,
    ) -> OutreachTarget:
        await self.get_campaign(campaign_id)

        target = OutreachTarget(
            campaign_id=campaign_id,
            contact_id=contact_id,
            job_opening_id=job_opening_id,
        )
        self._session.add(target)
        try:
            await self._session.commit()
        except IntegrityError as e:
            await self._session.rollback()
            raise DuplicateTargetError(
                f"Contact {contact_id!r} already added to campaign {campaign_id!r}"
            ) from e

        await self._session.refresh(target)
        logger.info("target.added", campaign_id=campaign_id, contact_id=contact_id)
        return target

    async def get_pending_targets(self, campaign_id: str) -> list[OutreachTarget]:
        stmt = (
            select(OutreachTarget)
            .where(
                OutreachTarget.campaign_id == campaign_id,
                OutreachTarget.status == "pending",
            )
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def update_target_status(self, target_id: str, status: str) -> OutreachTarget:
        target = await self._session.get(OutreachTarget, target_id)
        if target is None:
            raise CampaignNotFoundError(f"Target {target_id!r} not found")
        target.status = status
        await self._session.commit()
        await self._session.refresh(target)
        logger.info("target.status_updated", target_id=target_id, status=status)
        return target

    # ── Phase 4: Follow-up scheduling ──────────────────────────────────────────────

    async def get_sent_targets_due_for_followup(
        self, campaign_id: str
    ) -> list[OutreachTarget]:
        """
        Returns targets eligible for a follow-up email:
          - status == "sent"  (initial email sent, no reply yet)
          - follow_up_count < campaign.max_follow_ups
          - next_action_at is NULL (first follow-up after initial send)
            OR next_action_at <= now (subsequent follow-ups)
        """
        campaign = await self.get_campaign(campaign_id)
        now = datetime.now(UTC)
        created_cutoff = now - timedelta(days=campaign.follow_up_days)

        stmt = select(OutreachTarget).where(
            OutreachTarget.campaign_id == campaign_id,
            OutreachTarget.status == "sent",
            OutreachTarget.follow_up_count < campaign.max_follow_ups,
        )
        result = await self._session.execute(stmt)
        candidates = list(result.scalars().all())

        due: list[OutreachTarget] = []
        for t in candidates:
            if t.next_action_at is None:
                if t.created_at.replace(tzinfo=UTC) <= created_cutoff:
                    due.append(t)
            else:
                next_at = t.next_action_at
                if next_at.tzinfo is None:
                    next_at = next_at.replace(tzinfo=UTC)
                if next_at <= now:
                    due.append(t)
        return due

    async def increment_follow_up(
        self, target_id: str, follow_up_days: int
    ) -> OutreachTarget:
        """Bump follow_up_count and schedule the next action timestamp."""
        target = await self._session.get(OutreachTarget, target_id)
        if target is None:
            raise CampaignNotFoundError(f"Target {target_id!r} not found")
        now = datetime.now(UTC)
        target.follow_up_count = (target.follow_up_count or 0) + 1
        target.last_action_at = now
        target.next_action_at = now + timedelta(days=follow_up_days)
        await self._session.commit()
        await self._session.refresh(target)
        logger.info(
            "target.followup_incremented",
            target_id=target_id,
            follow_up_count=target.follow_up_count,
            next_action_at=str(target.next_action_at),
        )
        return target

    async def mark_replied(self, target_id: str, classification: str) -> OutreachTarget:
        """
        Map LLM classification to a canonical OutreachTarget status and persist.

        auto_reply stays 'sent' so polling continues.
        """
        _classification_to_status: dict[str, str] = {
            "interested": "interested",
            "not_interested": "not_interested",
            "opted_out": "opted_out",
            "bounced": "bounced",
            "auto_reply": "sent",
            "question": "replied",
            "needs_review": "replied",
        }
        status = _classification_to_status.get(classification, "replied")
        return await self.update_target_status(target_id, status)

    async def get_all_targets_for_campaign(
        self, campaign_id: str
    ) -> list[OutreachTarget]:
        """Return all targets for a campaign regardless of status."""
        stmt = select(OutreachTarget).where(
            OutreachTarget.campaign_id == campaign_id
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
