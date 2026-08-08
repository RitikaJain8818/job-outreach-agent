from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.db.session import engine
from app.models import *  # noqa: F401, F403 — ensures all models are imported for Alembic
from app.db.base import Base

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application startup and shutdown lifecycle."""
    configure_logging(settings.log_level)
    logger.info("app.starting", env=settings.app_env, version=settings.app_version)

    # In development with SQLite, auto-create tables so the app works without Alembic
    if settings.is_development and settings.is_sqlite:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("db.tables_created", mode="auto (sqlite dev)")

    yield

    logger.info("app.shutdown")
    await engine.dispose()


app = FastAPI(
    title="Job Outreach Agent",
    description="AI-powered multi-agent job outreach system",
    version=settings.app_version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.is_development else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/health", tags=["Health"])
async def health() -> dict[str, str]:
    return {"status": "ok", "version": settings.app_version}
