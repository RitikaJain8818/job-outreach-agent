"""
Script to launch a fresh outreach campaign.
"""
from __future__ import annotations

import asyncio
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.agents.base import AgentContext
from app.agents.email_generator import EmailGeneratorAgent
from app.agents.gmail_agent import GmailAgent
from app.api.dependencies import get_gmail_client, get_llm_provider
from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.db.base import Base
from app.db.session import AsyncSessionLocal, engine
from app.services.company_service import CompanyService
from app.services.contact_service import ContactService
from app.services.email_thread_service import EmailThreadService
from app.services.outreach_service import OutreachService

configure_logging("INFO")
logger = get_logger(__name__)


async def main():
    print("\n🚀 Launching Fresh Outreach Campaign...\n")
    print(f"🔹 Gemini Model: {settings.gemini_model}")
    print(f"🔹 Sender Identity: {settings.sender_name} ({settings.sender_email})")

    llm = get_llm_provider()
    gmail_client = get_gmail_client()

    async with AsyncSessionLocal() as session:
        company_svc = CompanyService(session)
        contact_svc = ContactService(session)
        outreach_svc = OutreachService(session)
        thread_svc = EmailThreadService(session)

        # 1. Company (BNY)
        company = await company_svc.get_by_domain("bny.com")
        if company is None:
            company = await company_svc.create(
                name="BNY",
                domain="bny.com",
                industry="Financial Services / Investment Management",
                description="BNY (Bank of New York Mellon) is a global leader in financial infrastructure and engineering.",
            )

        # 2. Contact
        contact = await contact_svc.get_by_email("mazumdar206@gmail.com")
        if contact is None:
            contact = await contact_svc.create(
                company_id=company.id,
                first_name="Nishan",
                last_name="Mazumdar",
                email="mazumdar206@gmail.com",
                title="Vice President - Full Stack Engineer",
            )

        # 3. Fresh Campaign & Target
        unique_tag = uuid.uuid4().hex[:4]
        campaign_name = f"BNY VP Full Stack - Automation Test {unique_tag}"
        campaign = await outreach_svc.create_campaign(
            name=campaign_name,
            sender_name=settings.sender_name or "Ritika Jain",
            sender_email=settings.sender_email or "ritikajain49026@gmail.com",
            goal="Vice President - Full Stack Engineer Outreach",
        )

        target = await outreach_svc.add_target(
            campaign_id=campaign.id,
            contact_id=contact.id,
        )
        print(f"✅ Created Campaign: {campaign.name}")
        print(f"✅ Target Created: ID {target.id}")

        # 4. Generate Personalized Email via Gemini
        print("\n⏳ Generating initial personalized email via Gemini...")
        email_gen_agent = EmailGeneratorAgent(llm=llm, contact_service=contact_svc)
        gen_ctx = AgentContext(
            campaign_id=campaign.id,
            target_id=target.id,
            contact_id=contact.id,
            company_id=company.id,
            metadata={
                "sender_name": settings.sender_name or "Ritika Jain",
                "sender_background": settings.sender_background or "Full Stack Lead Engineer specializing in Python microservices, distributed architecture, and LLM automation",
                "job_title": "Vice President - Full Stack Engineer",
                "tone": "professional",
                "use_template": False,
            },
        )
        gen_result = await email_gen_agent.execute(gen_ctx)
        if not gen_result.success:
            print(f"❌ Email generation failed: {gen_result.error}")
            sys.exit(1)

        subject = str(gen_result.output.get("subject", ""))
        body = str(gen_result.output.get("body", ""))

        print(f"\n✨ Generated Email:")
        print(f"==================================================")
        print(f"TO      : {contact.email}")
        print(f"SUBJECT : {subject}")
        print(f"\nBODY:\n{body}")
        print(f"==================================================")

        # 5. Send via Gmail REST API
        print("\n⏳ Delivering initial email via Gmail REST API...")
        gmail_agent = GmailAgent(
            gmail_client=gmail_client,
            outreach_service=outreach_svc,
            thread_service=thread_svc,
        )
        send_ctx = AgentContext(
            campaign_id=campaign.id,
            target_id=target.id,
            contact_id=contact.id,
            company_id=company.id,
            metadata={
                "mode": "send",
                "to_email": contact.email,
                "email_subject": subject,
                "email_body": body,
            },
        )
        send_result = await gmail_agent.execute(send_ctx)
        if not send_result.success:
            print(f"❌ Sending failed: {send_result.error}")
            sys.exit(1)

        print(f"\n🎉 INITIAL EMAIL SENT SUCCESSFULLY!")
        print(f"   Destination: {contact.email}")
        print(f"   Gmail Thread ID: {send_result.output.get('gmail_thread_id')}")
        print(f"   Target ID: {target.id}")
        print(f"\n⚡ Background Poller Service is running and checking Gmail every 60 seconds!")
        print(f"👉 Once the contact replies to this email, the poller will automatically classify it and send an in-thread reply!")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
