"""
Script to trigger automated follow-up processing right now.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.db.session import engine
from app.scheduler.jobs import _send_follow_ups_async

configure_logging("INFO")
logger = get_logger(__name__)


async def main():
    print("\n🚀 Executing Automated Follow-Up Job Right Now...\n")
    print(f"🔹 Gemini Model: {settings.gemini_model}")

    # Inspect current targets in DB before follow-up
    from sqlalchemy import select
    from app.db.session import AsyncSessionLocal
    from app.models.outreach import OutreachTarget, OutreachCampaign
    from app.models.contact import Contact

    async with AsyncSessionLocal() as session:
        targets = (await session.execute(select(OutreachTarget))).scalars().all()
        print("📋 Targets in Database:")
        for t in targets:
            c = await session.get(Contact, t.contact_id)
            print(f"   - Target ID: {t.id[:8]}... | Contact: {c.full_name if c else 'N/A'} ({c.email if c else 'N/A'}) | Status: {t.status} | Follow-ups Sent: {t.follow_up_count}")

    print("\n⏳ Running Follow-Up Job (`_send_follow_ups_async`)...")
    await _send_follow_ups_async(engine)

    # Re-inspect targets
    async with AsyncSessionLocal() as session:
        targets = (await session.execute(select(OutreachTarget))).scalars().all()
        print("\n📋 Targets Status After Follow-Up Job:")
        for t in targets:
            c = await session.get(Contact, t.contact_id)
            print(f"   - Target ID: {t.id[:8]}... | Contact: {c.full_name if c else 'N/A'} | Status: {t.status} | Follow-ups Sent: {t.follow_up_count} | Next Action At: {t.next_action_at}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
