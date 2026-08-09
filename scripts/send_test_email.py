"""
Script to test the Gemini API key and send a personalized email to a recipient.
"""
from __future__ import annotations

import asyncio
import sys
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
from app.models.company import Company
from app.models.contact import Contact
from app.services.company_service import CompanyService
from app.services.contact_service import ContactService
from app.services.email_thread_service import EmailThreadService
from app.services.outreach_service import OutreachService

configure_logging("INFO")
logger = get_logger(__name__)


async def main():
    print("\n🚀 Testing Gemini API Key & Personal Cold Email Pipeline\n")
    print(f"🔹 Gemini Model: {settings.gemini_model}")
    print(f"🔹 Sender Identity: {settings.sender_name} ({settings.sender_email})")

    # Step 0: Ensure DB tables exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Step 1: Instantiate LLM Provider & Gmail Client
    llm = get_llm_provider()
    gmail_client = get_gmail_client()

    async with AsyncSessionLocal() as session:
        company_svc = CompanyService(session)
        contact_svc = ContactService(session)
        outreach_svc = OutreachService(session)
        thread_svc = EmailThreadService(session)

        # Step 2: Create/Fetch Company (BNY)
        company = await company_svc.get_by_domain("bny.com")
        if company is None:
            company = await company_svc.create(
                name="BNY",
                domain="bny.com",
                industry="Financial Services / Investment Management",
                description="BNY (Bank of New York Mellon) is a premier global financial services company building next-gen banking & engineering platforms.",
            )
            print(f"✅ Company created: {company.name}")
        else:
            print(f"ℹ️ Company found: {company.name}")

        # Step 3: Create/Fetch Contact (Nishan Mazumdar)
        contact = await contact_svc.get_by_email("mazumdar206@gmail.com")
        if contact is None:
            contact = await contact_svc.create(
                company_id=company.id,
                first_name="Nishan",
                last_name="Mazumdar",
                email="mazumdar206@gmail.com",
                title="Vice President - Full Stack Engineer",
                notes="Targeting Vice President - Full Stack Engineer role at BNY.",
            )
            print(f"✅ Contact created: {contact.full_name} ({contact.email})")
        else:
            print(f"ℹ️ Contact found: {contact.full_name} ({contact.email})")

        # Step 4: Create Campaign & Target
        campaign_name = "Direct Test Outreach - BNY VP Full Stack"
        try:
            campaign = await outreach_svc.create_campaign(
                name=campaign_name,
                sender_name=settings.sender_name or "Ritika Jain",
                sender_email=settings.sender_email or "ritikajain49026@gmail.com",
                goal="Vice President - Full Stack Engineer Outreach",
            )
        except Exception:
            # If campaign name exists, search for existing
            from sqlalchemy import select
            from app.models.outreach import OutreachCampaign
            res = await session.execute(select(OutreachCampaign).where(OutreachCampaign.name == campaign_name))
            campaign = res.scalar_one()

        try:
            target = await outreach_svc.add_target(
                campaign_id=campaign.id,
                contact_id=contact.id,
            )
            print(f"✅ Target added: {target.id}")
        except Exception:
            from sqlalchemy import select
            from app.models.outreach import OutreachTarget
            res = await session.execute(
                select(OutreachTarget).where(
                    OutreachTarget.campaign_id == campaign.id,
                    OutreachTarget.contact_id == contact.id,
                )
            )
            target = res.scalar_one()
            print(f"ℹ️ Target existing: {target.id}")

        # Step 5: Run EmailGeneratorAgent (AI Mode)
        print("\n⏳ Calling Gemini LLM to generate personalized email...")
        email_gen_agent = EmailGeneratorAgent(llm=llm, contact_service=contact_svc)

        gen_ctx = AgentContext(
            campaign_id=campaign.id,
            target_id=target.id,
            contact_id=contact.id,
            company_id=company.id,
            metadata={
                "sender_name": settings.sender_name or "Ritika Jain",
                "sender_background": settings.sender_background or "Software Engineer with experience in Python, LLMs, and high-scale systems",
                "job_title": "Vice President - Full Stack Engineer",
                "tone": "professional",
                "use_template": False,  # Test LLM AI mode!
            },
        )

        gen_result = await email_gen_agent.execute(gen_ctx)
        if not gen_result.success:
            print(f"❌ Email generation failed: {gen_result.error}")
            sys.exit(1)

        subject = str(gen_result.output.get("subject", ""))
        body = str(gen_result.output.get("body", ""))
        reasoning = str(gen_result.output.get("reasoning", ""))

        print(f"\n✨ Gemini Generated Email:")
        print(f"--------------------------------------------------")
        print(f"SUBJECT: {subject}")
        print(f"REASONING: {reasoning}")
        print(f"\nBODY:\n{body}")
        print(f"--------------------------------------------------")

        # Step 6: Send via GmailAgent
        print("\n⏳ Delivering email via Gmail REST API...")
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
            print(f"❌ Sending email failed: {send_result.error}")
            sys.exit(1)

        print(f"\n🎉 SUCCESS!")
        print(f"   Email successfully delivered to: {contact.email}")
        print(f"   Gmail Thread ID: {send_result.output.get('gmail_thread_id')}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
