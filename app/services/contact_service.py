from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import ContactNotFoundError
from app.core.logging import get_logger
from app.models.contact import Contact

logger = get_logger(__name__)


class ContactService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        company_id: str,
        first_name: str,
        last_name: str,
        email: str,
        title: str | None = None,
        linkedin_url: str | None = None,
        notes: str | None = None,
    ) -> Contact:
        contact = Contact(
            company_id=company_id,
            first_name=first_name,
            last_name=last_name,
            email=email,
            title=title,
            linkedin_url=linkedin_url,
            notes=notes,
        )
        self._session.add(contact)
        await self._session.commit()
        await self._session.refresh(contact)
        logger.info("contact.created", contact_id=contact.id, email=contact.email)
        return contact

    async def get(self, contact_id: str) -> Contact:
        contact = await self._session.get(Contact, contact_id)
        if contact is None:
            raise ContactNotFoundError(f"Contact {contact_id!r} not found")
        return contact

    async def get_with_company(self, contact_id: str) -> Contact | None:
        """Load contact with its company pre-fetched (avoids N+1 in agents)."""
        stmt = (
            select(Contact)
            .where(Contact.id == contact_id)
            .options(selectinload(Contact.company))
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list(
        self, company_id: str | None = None, page: int = 1, size: int = 20
    ) -> list[Contact]:
        stmt = select(Contact)
        if company_id:
            stmt = stmt.where(Contact.company_id == company_id)
        offset = (page - 1) * size
        stmt = stmt.offset(offset).limit(size)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_email(self, email: str) -> Contact | None:
        stmt = select(Contact).where(Contact.email == email)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
