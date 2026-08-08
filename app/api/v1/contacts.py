from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ContactNotFoundError
from app.db.session import get_session
from app.services.contact_service import ContactService

router = APIRouter(prefix="/contacts", tags=["Contacts"])


class ContactCreate(BaseModel):
    company_id: str
    first_name: str
    last_name: str
    email: str
    title: str | None = None
    linkedin_url: str | None = None
    notes: str | None = None


class ContactResponse(BaseModel):
    id: str
    company_id: str
    first_name: str
    last_name: str
    email: str
    title: str | None
    linkedin_url: str | None

    model_config = {"from_attributes": True}


@router.post("", response_model=ContactResponse, status_code=status.HTTP_201_CREATED)
async def create_contact(
    body: ContactCreate,
    session: AsyncSession = Depends(get_session),
) -> ContactResponse:
    svc = ContactService(session)
    existing = await svc.get_by_email(body.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Contact with email {body.email!r} already exists",
        )
    contact = await svc.create(**body.model_dump())
    return ContactResponse.model_validate(contact)


@router.get("", response_model=list[ContactResponse])
async def list_contacts(
    company_id: str | None = None,
    page: int = 1,
    size: int = 20,
    session: AsyncSession = Depends(get_session),
) -> list[ContactResponse]:
    svc = ContactService(session)
    contacts = await svc.list(company_id=company_id, page=page, size=size)
    return [ContactResponse.model_validate(c) for c in contacts]


@router.get("/{contact_id}", response_model=ContactResponse)
async def get_contact(
    contact_id: str,
    session: AsyncSession = Depends(get_session),
) -> ContactResponse:
    svc = ContactService(session)
    try:
        contact = await svc.get(contact_id)
    except ContactNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    return ContactResponse.model_validate(contact)
