from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import CampaignNotFoundError, DuplicateTargetError
from app.core.logging import get_logger
from app.models.outreach import OutreachCampaign, OutreachTarget

logger = get_logger(__name__)


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
