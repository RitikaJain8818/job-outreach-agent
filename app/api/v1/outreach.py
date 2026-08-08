from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import AgentContext
from app.agents.orchestrator import OrchestratorAgent
from app.api.dependencies import get_orchestrator
from app.core.config import settings
from app.core.exceptions import CampaignNotFoundError, DuplicateTargetError
from app.db.session import get_session
from app.services.contact_service import ContactService
from app.services.outreach_service import OutreachService

router = APIRouter(prefix="/outreach", tags=["Outreach"])


class CampaignCreate(BaseModel):
    name: str
    sender_name: str
    sender_email: str
    goal: str | None = None
    follow_up_days: int = 3
    max_follow_ups: int = 2


class CampaignResponse(BaseModel):
    id: str
    name: str
    sender_name: str
    sender_email: str
    goal: str | None
    follow_up_days: int
    max_follow_ups: int
    status: str

    model_config = {"from_attributes": True}


class AddTargetRequest(BaseModel):
    contact_id: str
    job_opening_id: str | None = None


class TargetResponse(BaseModel):
    id: str
    campaign_id: str
    contact_id: str
    job_opening_id: str | None
    status: str
    follow_up_count: int

    model_config = {"from_attributes": True}


class RunResult(BaseModel):
    campaign_id: str
    processed: int
    sent: int
    skipped: int
    errors: list[str]


@router.post("/campaigns", response_model=CampaignResponse, status_code=status.HTTP_201_CREATED)
async def create_campaign(
    body: CampaignCreate,
    session: AsyncSession = Depends(get_session),
) -> CampaignResponse:
    svc = OutreachService(session)
    campaign = await svc.create_campaign(**body.model_dump())
    return CampaignResponse.model_validate(campaign)


@router.get("/campaigns/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(
    campaign_id: str,
    session: AsyncSession = Depends(get_session),
) -> CampaignResponse:
    svc = OutreachService(session)
    try:
        campaign = await svc.get_campaign(campaign_id)
    except CampaignNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    return CampaignResponse.model_validate(campaign)


@router.post(
    "/campaigns/{campaign_id}/targets",
    response_model=TargetResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_target(
    campaign_id: str,
    body: AddTargetRequest,
    session: AsyncSession = Depends(get_session),
) -> TargetResponse:
    svc = OutreachService(session)
    try:
        target = await svc.add_target(
            campaign_id=campaign_id,
            contact_id=body.contact_id,
            job_opening_id=body.job_opening_id,
        )
    except CampaignNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except DuplicateTargetError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e
    return TargetResponse.model_validate(target)


@router.post("/campaigns/{campaign_id}/run", response_model=RunResult)
async def run_campaign(
    campaign_id: str,
    session: AsyncSession = Depends(get_session),
    orchestrator: OrchestratorAgent = Depends(get_orchestrator),
) -> RunResult:
    outreach_svc = OutreachService(session)
    contact_svc = ContactService(session)

    try:
        campaign = await outreach_svc.get_campaign(campaign_id)
    except CampaignNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e

    pending = await outreach_svc.get_pending_targets(campaign_id)

    sent = 0
    skipped = 0
    errors: list[str] = []

    for target in pending:
        contact = await contact_svc.get_with_company(target.contact_id)
        if contact is None:
            skipped += 1
            errors.append(f"Target {target.id}: contact {target.contact_id} not found — skipped")
            continue

        context = AgentContext(
            campaign_id=campaign_id,
            target_id=target.id,
            contact_id=target.contact_id,
            company_id=contact.company_id,
            metadata={
                "sender_name": campaign.sender_name or settings.sender_name,
                "sender_email": campaign.sender_email or settings.sender_email,
                "sender_background": settings.sender_background or campaign.goal or "",
                "to_email": contact.email,
                "tone": settings.sender_tone,
            },
        )

        result = await orchestrator.execute(context)

        if result.success:
            sent += 1
        else:
            errors.append(f"Target {target.id} ({contact.email}): {result.error}")

    return RunResult(
        campaign_id=campaign_id,
        processed=len(pending),
        sent=sent,
        skipped=skipped,
        errors=errors,
    )
