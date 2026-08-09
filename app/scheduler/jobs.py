"""
Background scheduler jobs — Phase 4.

Two jobs:
  - poll_replies_job: Polls Gmail for new inbound replies on all active threads,
    classifies each new reply via LLM, updates OutreachTarget status, and
    automatically triggers InterestedReplyAgent if the recruiter expresses interest.
  - send_follow_ups_job: Finds targets due for a follow-up, generates a follow-up
    email via FollowUpAgent, sends via GmailAgent, and bumps follow_up_count.

Both jobs create their own DB sessions from the engine so they are safe to run
independently from FastAPI request sessions.
"""
from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.base import AgentContext
from app.agents.follow_up import FollowUpAgent
from app.agents.gmail_agent import GmailAgent
from app.agents.reply_classifier import ReplyClassifierAgent
from app.core.cache import CachingLLMProvider
from app.core.config import settings
from app.core.logging import get_logger
from app.services.contact_service import ContactService
from app.services.email_thread_service import EmailThreadService
from app.services.outreach_service import OutreachService

logger = get_logger(__name__)

_DUMMY_CAMPAIGN_ID = "scheduler"
_DUMMY_CONTACT_ID = "scheduler"
_DUMMY_COMPANY_ID = "scheduler"


def _make_session_factory(engine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)


def _get_llm():
    """Build LLM provider from settings (same logic as dependencies.py)."""
    if settings.llm_provider == "gemini":
        from app.integrations.llm.gemini import GeminiProvider
        return CachingLLMProvider(
            GeminiProvider(api_key=settings.gemini_api_key, model=settings.gemini_model)
        )
    if settings.llm_provider == "openai":
        from app.integrations.llm.openai import OpenAIProvider
        return CachingLLMProvider(OpenAIProvider(api_key=settings.openai_api_key))
    raise RuntimeError(f"Unknown LLM_PROVIDER: {settings.llm_provider!r}")


def _get_gmail_client():
    """Build Gmail client from credentials files."""
    from app.integrations.gmail.auth import get_gmail_credentials
    from app.integrations.gmail.client import GmailClient
    creds = get_gmail_credentials(
        credentials_file=settings.gmail_credentials_file,
        token_file=settings.gmail_token_file,
    )
    return GmailClient.from_credentials(creds)


# ──────────────────────────────────────────────────────────────────────────────
# Job 1: Poll replies + classify + auto-respond to interested contacts
# ──────────────────────────────────────────────────────────────────────────────

async def _poll_replies_async(engine) -> None:
    """Async implementation of reply polling, classification, and immediate interested auto-reply."""
    session_factory = _make_session_factory(engine)
    llm = _get_llm()
    gmail_client = _get_gmail_client()
    classifier = ReplyClassifierAgent(llm=llm)

    async with session_factory() as session:
        thread_svc = EmailThreadService(session)
        outreach_svc = OutreachService(session)

        threads = await thread_svc.get_threads_for_active_targets()
        logger.info("scheduler.poll_replies.start", threads_count=len(threads))

        for thread in threads:
            target_id = thread.outreach_target_id
            try:
                gmail_agent = GmailAgent(
                    gmail_client=gmail_client,
                    outreach_service=outreach_svc,
                    thread_service=thread_svc,
                )
                ctx = AgentContext(
                    campaign_id=_DUMMY_CAMPAIGN_ID,
                    target_id=target_id,
                    contact_id=_DUMMY_CONTACT_ID,
                    company_id=_DUMMY_COMPANY_ID,
                    metadata={
                        "mode": "poll",
                        "gmail_thread_id": thread.gmail_thread_id,
                        "thread_db_id": thread.id,
                    },
                )
                poll_result = await gmail_agent.execute(ctx)
                if not poll_result.success:
                    logger.error(
                        "scheduler.poll_replies.poll_failed",
                        thread_id=thread.id,
                        error=poll_result.error,
                    )
                    continue

                new_count = int(poll_result.output.get("new_reply_count", 0))
                if new_count == 0:
                    continue

                await session.refresh(thread)
                unclassified = [
                    m for m in thread.messages
                    if m.direction == "inbound" and m.classification is None
                ]

                for msg in unclassified:
                    classify_ctx = AgentContext(
                        campaign_id=_DUMMY_CAMPAIGN_ID,
                        target_id=target_id,
                        contact_id=_DUMMY_CONTACT_ID,
                        company_id=_DUMMY_COMPANY_ID,
                        metadata={
                            "reply_body": msg.body_text or "",
                            "original_subject": thread.subject,
                        },
                    )
                    classify_result = await classifier.execute(classify_ctx)
                    if not classify_result.success:
                        logger.error(
                            "scheduler.poll_replies.classify_failed",
                            message_id=msg.id,
                            error=classify_result.error,
                        )
                        continue

                    classification = str(classify_result.output.get("classification", "needs_review"))
                    confidence = float(classify_result.output.get("confidence", 0.0))

                    await thread_svc.update_message_classification(
                        message_id=msg.id,
                        classification=classification,
                        confidence=confidence,
                    )
                    await outreach_svc.mark_replied(
                        target_id=target_id,
                        classification=classification,
                    )
                    logger.info(
                        "scheduler.reply_classified",
                        target_id=target_id,
                        classification=classification,
                        confidence=confidence,
                    )

                    # Auto-reply immediately if the recruiter expressed interest
                    if classification == "interested":
                        from app.agents.interested_reply import InterestedReplyAgent
                        from app.models.outreach import OutreachTarget
                        contact_svc = ContactService(session)
                        target_obj = await session.get(OutreachTarget, target_id)
                        contact_obj = await contact_svc.get_with_company(target_obj.contact_id) if target_obj else None

                        if contact_obj:
                            reply_agent = InterestedReplyAgent(llm=llm)
                            reply_ctx = AgentContext(
                                campaign_id=_DUMMY_CAMPAIGN_ID,
                                target_id=target_id,
                                contact_id=contact_obj.id,
                                company_id=contact_obj.company_id or "",
                                metadata={
                                    "sender_name": settings.sender_name or "Applicant",
                                    "contact_name": contact_obj.full_name,
                                    "company_name": contact_obj.company.name if contact_obj.company else "",
                                    "original_subject": thread.subject,
                                    "recruiter_message": msg.body_text or "",
                                },
                            )
                            reply_res = await reply_agent.execute(reply_ctx)
                            if reply_res.success:
                                auto_subj = str(reply_res.output.get("subject", f"Re: {thread.subject}"))
                                auto_body = str(reply_res.output.get("body", ""))
                                send_ctx = AgentContext(
                                    campaign_id=_DUMMY_CAMPAIGN_ID,
                                    target_id=target_id,
                                    contact_id=contact_obj.id,
                                    company_id=contact_obj.company_id or "",
                                    metadata={
                                        "mode": "send",
                                        "to_email": contact_obj.email,
                                        "email_subject": auto_subj,
                                        "email_body": auto_body,
                                    },
                                )
                                send_res = await gmail_agent.execute(send_ctx)
                                if send_res.success:
                                    logger.info(
                                        "scheduler.interested_auto_reply_sent",
                                        target_id=target_id,
                                        to=contact_obj.email,
                                    )

            except Exception as exc:  # noqa: BLE001
                logger.error(
                    "scheduler.poll_replies.error",
                    thread_id=thread.id,
                    error=str(exc),
                )

    logger.info("scheduler.poll_replies.done")


def poll_replies_job(engine) -> None:
    """APScheduler entry point."""
    asyncio.get_event_loop().run_until_complete(_poll_replies_async(engine))


# ──────────────────────────────────────────────────────────────────────────────
# Job 2: Send follow-ups
# ──────────────────────────────────────────────────────────────────────────────

async def _send_follow_ups_async(engine) -> None:
    """Async implementation of follow-up email generation and delivery."""
    session_factory = _make_session_factory(engine)
    llm = _get_llm()
    gmail_client = _get_gmail_client()
    follow_up_agent = FollowUpAgent(llm=llm)

    async with session_factory() as session:
        outreach_svc = OutreachService(session)
        thread_svc = EmailThreadService(session)
        contact_svc = ContactService(session)

        from sqlalchemy import select
        from app.models.outreach import OutreachTarget
        stmt = select(OutreachTarget.campaign_id).distinct()
        result = await session.execute(stmt)
        campaign_ids = [row[0] for row in result.all()]

        logger.info("scheduler.send_followups.start", campaigns=len(campaign_ids))

        for campaign_id in campaign_ids:
            campaign = await outreach_svc.get_campaign(campaign_id)
            due_targets = await outreach_svc.get_sent_targets_due_for_followup(campaign_id)

            for target in due_targets:
                contact = await contact_svc.get_with_company(target.contact_id)
                if contact is None:
                    logger.warning(
                        "scheduler.send_followups.contact_not_found",
                        target_id=target.id,
                        contact_id=target.contact_id,
                    )
                    continue

                thread = await thread_svc.get_thread_by_target_id(target.id)
                original_body = ""
                original_subject = ""
                if thread:
                    outbound = [m for m in thread.messages if m.direction == "outbound"]
                    if outbound:
                        original_body = outbound[0].body_text or ""
                    original_subject = thread.subject

                follow_up_number = (target.follow_up_count or 0) + 1
                sender_name = campaign.sender_name or settings.sender_name

                ctx = AgentContext(
                    campaign_id=campaign_id,
                    target_id=target.id,
                    contact_id=target.contact_id,
                    company_id=contact.company_id or "",
                    metadata={
                        "sender_name": sender_name,
                        "contact_name": contact.full_name,
                        "company_name": contact.company.name if contact.company else "",
                        "original_subject": original_subject,
                        "original_body": original_body,
                        "follow_up_number": str(follow_up_number),
                        "days_since_last_email": str(campaign.follow_up_days),
                    },
                )

                try:
                    fu_result = await follow_up_agent.execute(ctx)
                    if not fu_result.success:
                        logger.error(
                            "scheduler.send_followups.gen_failed",
                            target_id=target.id,
                            error=fu_result.error,
                        )
                        continue

                    gmail_agent = GmailAgent(
                        gmail_client=gmail_client,
                        outreach_service=outreach_svc,
                        thread_service=thread_svc,
                    )
                    send_ctx = AgentContext(
                        campaign_id=campaign_id,
                        target_id=target.id,
                        contact_id=target.contact_id,
                        company_id=contact.company_id or "",
                        metadata={
                            "mode": "send",
                            "to_email": contact.email,
                            "email_subject": str(fu_result.output.get("subject", "")),
                            "email_body": str(fu_result.output.get("body", "")),
                        },
                    )
                    send_result = await gmail_agent.execute(send_ctx)
                    if not send_result.success:
                        logger.error(
                            "scheduler.send_followups.send_failed",
                            target_id=target.id,
                            error=send_result.error,
                        )
                        continue

                    await outreach_svc.increment_follow_up(
                        target_id=target.id,
                        follow_up_days=campaign.follow_up_days,
                    )
                    logger.info(
                        "scheduler.followup_sent",
                        target_id=target.id,
                        follow_up_number=follow_up_number,
                        to=contact.email,
                    )

                except Exception as exc:  # noqa: BLE001
                    logger.error(
                        "scheduler.send_followups.error",
                        target_id=target.id,
                        error=str(exc),
                    )

    logger.info("scheduler.send_followups.done")


def send_follow_ups_job(engine) -> None:
    """APScheduler entry point."""
    asyncio.get_event_loop().run_until_complete(_send_follow_ups_async(engine))
