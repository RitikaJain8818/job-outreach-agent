from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.db.session import engine
from app.models import *  # noqa: F401, F403
from app.db.base import Base

logger = get_logger(__name__)

_scheduler: AsyncIOScheduler | None = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    global _scheduler

    configure_logging(settings.log_level)
    logger.info("app.starting", env=settings.app_env, version=settings.app_version)

    if settings.is_development and settings.is_sqlite:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("db.tables_created", mode="auto (sqlite dev)")

    # ── Start background scheduler ──────────────────────────────────────────
    from app.scheduler.jobs import poll_replies_job, send_follow_ups_job

    _scheduler = AsyncIOScheduler()
    interval = settings.scheduler_interval_minutes

    _scheduler.add_job(
        poll_replies_job,
        trigger="interval",
        minutes=interval,
        args=[engine],
        id="poll_replies",
        name="Poll Gmail replies & classify",
        replace_existing=True,
    )
    _scheduler.add_job(
        send_follow_ups_job,
        trigger="interval",
        minutes=interval,
        args=[engine],
        id="send_follow_ups",
        name="Send follow-up emails",
        replace_existing=True,
    )
    _scheduler.start()
    logger.info(
        "scheduler.started",
        interval_minutes=interval,
        jobs=["poll_replies", "send_follow_ups"],
    )

    yield

    # ── Graceful shutdown ────────────────────────────────────────────────
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("scheduler.stopped")

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
