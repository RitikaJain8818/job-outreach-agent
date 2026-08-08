from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.companies import router as companies_router
from app.api.v1.contacts import router as contacts_router
from app.api.v1.outreach import router as outreach_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(companies_router)
api_router.include_router(contacts_router)
api_router.include_router(outreach_router)
