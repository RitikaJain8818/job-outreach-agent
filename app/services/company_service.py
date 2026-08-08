from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import CompanyNotFoundError
from app.core.logging import get_logger
from app.models.company import Company

logger = get_logger(__name__)


class CompanyService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        name: str,
        domain: str | None = None,
        industry: str | None = None,
        size_range: str | None = None,
        location: str | None = None,
        description: str | None = None,
        linkedin_url: str | None = None,
        website_url: str | None = None,
    ) -> Company:
        company = Company(
            name=name,
            domain=domain,
            industry=industry,
            size_range=size_range,
            location=location,
            description=description,
            linkedin_url=linkedin_url,
            website_url=website_url,
        )
        self._session.add(company)
        await self._session.commit()
        await self._session.refresh(company)
        logger.info("company.created", company_id=company.id, name=company.name)
        return company

    async def get(self, company_id: str) -> Company:
        company = await self._session.get(Company, company_id)
        if company is None:
            raise CompanyNotFoundError(f"Company {company_id!r} not found")
        return company

    async def get_by_domain(self, domain: str) -> Company | None:
        stmt = select(Company).where(Company.domain == domain)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list(self, page: int = 1, size: int = 20) -> list[Company]:
        offset = (page - 1) * size
        stmt = select(Company).offset(offset).limit(size)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def update(self, company_id: str, **fields: str | None) -> Company:
        company = await self.get(company_id)
        for key, value in fields.items():
            if hasattr(company, key):
                setattr(company, key, value)
        await self._session.commit()
        await self._session.refresh(company)
        return company
