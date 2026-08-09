"""
Script to send an immediate AI response to an interested target.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.agents.base import AgentContext
from app.agents.gmail_agent import GmailAgent
from app.agents.interested_reply import InterestedReplyAgent
from app.api.dependencies import get_gmail_client, get_llm_provider
from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.db.session import AsyncSessionLocal, engine
from app.models.contact import Contact
from app.models.email_thread import EmailThread
from app.models.outreach import OutreachTarget
from app.services.company_service import CompanyService
from app.services.contact_service import ContactService
from app.services.email_thread_service import EmailThreadService
from app.services.outreach_service import OutreachService

configure_logging("INFO")
logger = get_logger(__name__)


async def main():
    print("\n🚀 Replying to Interested Target...\n")
    print(f"🔹 Gemini Model: {settings.gemini_model}")
    print(f"🔹 Sender Identity: {settings.sender_name} ({settings.sender_email})")

    llm = get_llm_provider()
    gmail_client = get_gmail_client()

    async with AsyncSessionLocal() as session:
        contact_svc = ContactService(session)
        outreach_svc = OutreachService(session)
        thread_svc = EmailThreadService(session)

        # 1. Fetch Contact & Target
        contact = await contact_svc.get_by_email("mazumdar206@gmail.com")
        if not contact:
            print("❌ Contact not found: mazumdar206@gmail.com")
            sys.exit(1)

        from sqlalchemy import select
        stmt = select(OutreachTarget).where(OutreachTarget.contact_id == contact.id)
        target = (await session.execute(stmt)).scalars().first()
        if not target:
            print(f"❌ Target not found for contact: {contact.id}")
            sys.exit(1)

        # 2. Fetch Thread & Inbound Message
        thread = await thread_svc.get_thread_by_target_id(target.id)
        if not thread:
            print(f"❌ Email thread not found for target: {target.id}")
            sys.exit(1)

        inbound_messages = [m for m in thread.messages if m.direction == "inbound"]
        recruiter_msg = inbound_messages[-1].body_text if inbound_messages else "Sure, What time are you free tomorrow?"

        print(f"📧 Contact           : {contact.full_name} ({contact.email})")
        print(f"💬 Recruiter Message : {recruiter_msg.strip()}")
        print(f"🧵 Gmail Thread ID   : {thread.gmail_thread_id}")

        # 3. Execute InterestedReplyAgent with Gemini LLM
        print("\n⏳ Generating AI response with Gemini LLM...")
        reply_agent = InterestedReplyAgent(llm=llm)
        ctx = AgentContext(
            campaign_id=target.campaign_id,
            target_id=target.id,
            contact_id=contact.id,
            company_id=contact.company_id or "",
            metadata={
                "sender_name": settings.sender_name or "Ritika Jain",
                "contact_name": contact.full_name,
                "company_name": "BNY",
                "original_subject": thread.subject,
                "recruiter_message": recruiter_msg,
                "availability_notes": "Tomorrow afternoon between 2:00 PM and 5:00 PM IST, or Wednesday morning 10:00 AM to 1:00 PM IST",
                "use_template": False,  # Force LLM generation!
            },
        )

        reply_res = await reply_agent.execute(ctx)
        if not reply_res.success:
            print(f"❌ Reply generation failed: {reply_res.error}")
            sys.exit(1)

        subj = str(reply_res.output.get("subject", f"Re: {thread.subject}"))
        body = str(reply_res.output.get("body", ""))
        reasoning = str(reply_res.output.get("reasoning", ""))

        print(f"\n✨ Gemini Generated Reply:")
        print(f"==================================================")
        print(f"TO       : {contact.email}")
        print(f"SUBJECT  : {subj}")
        print(f"REASONING: {reasoning}")
        print(f"\nBODY:\n{body}")
        print(f"==================================================")

        # 4. Deliver via GmailAgent
        print("\n⏳ Delivering reply via Gmail REST API...")
        gmail_agent = GmailAgent(
            gmail_client=gmail_client,
            outreach_service=outreach_svc,
            thread_service=thread_svc,
        )

        send_ctx = AgentContext(
            campaign_id=target.campaign_id,
            target_id=target.id,
            contact_id=contact.id,
            company_id=contact.company_id or "",
            metadata={
                "mode": "send",
                "to_email": contact.email,
                "email_subject": subj,
                "email_body": body,
                "gmail_thread_id": thread.gmail_thread_id,
            },
        )

        send_res = await gmail_agent.execute(send_ctx)
        if not send_res.success:
            print(f"❌ Sending reply failed: {send_res.error}")
            sys.exit(1)

        print(f"\n🎉 SUCCESS!")
        print(f"   Reply successfully sent to: {contact.email}")
        print(f"   Gmail Thread ID: {send_res.output.get('gmail_thread_id')}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
