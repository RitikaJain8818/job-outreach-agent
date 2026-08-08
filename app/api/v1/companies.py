from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import CompanyNotFoundError
from app.db.session import get_session
from app.services.company_service import CompanyService

router = APIRouter(prefix="/companies", tags=["Companies"])


class CompanyCreate(BaseModel):
    name: str
    domain: str | None = None
    industry: str | None = None
    size_range: str | None = None
    location: str | None = None
    description: str | None = None
    linkedin_url: str | None = None
    website_url: str | None = None


class CompanyResponse(BaseModel):
    id: str
    name: str
    domain: str | None
    industry: str | None
    size_range: str | None
    location: str | None
    description: str | None
    linkedin_url: str | None
    website_url: str | None

    model_config = {"from_attributes": True}


@router.post("", response_model=CompanyResponse, status_code=status.HTTP_201_CREATED)
async def create_company(
    body: CompanyCreate,
    session: AsyncSession = Depends(get_session),
) -> CompanyResponse:
    svc = CompanyService(session)
    company = await svc.create(**body.model_dump())
    return CompanyResponse.model_validate(company)


@router.get("", response_model=list[CompanyResponse])
async def list_companies(
    page: int = 1,
    size: int = 20,
    session: AsyncSession = Depends(get_session),
) -> list[CompanyResponse]:
    svc = CompanyService(session)
    companies = await svc.list(page=page, size=size)
    return [CompanyResponse.model_validate(c) for c in companies]


@router.get("/{company_id}", response_model=CompanyResponse)
async def get_company(
    company_id: str,
    session: AsyncSession = Depends(get_session),
) -> CompanyResponse:
    svc = CompanyService(session)
    try:
        company = await svc.get(company_id)
    except CompanyNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    return CompanyResponse.model_validate(company)
