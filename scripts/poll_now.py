"""
Script to poll Gmail for replies on active outreach threads right now.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.db.session import engine
from app.scheduler.jobs import _poll_replies_async

configure_logging("INFO")
logger = get_logger(__name__)


async def main():
    print("\n🔍 Polling Gmail for Inbound Replies on Active Outreach Threads...\n")
    print(f"🔹 Gemini Model: {settings.gemini_model}")

    await _poll_replies_async(engine)

    # Inspect messages stored in DB
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from app.db.session import AsyncSessionLocal
    from app.models.email_thread import EmailThread, EmailMessage
    from app.models.outreach import OutreachTarget
    from app.models.contact import Contact

    async with AsyncSessionLocal() as session:
        stmt = (
            select(EmailThread)
            .options(selectinload(EmailThread.messages))
        )
        threads = (await session.execute(stmt)).scalars().all()

        print("\n==================================================")
        print("📥 POLLED THREAD RESULTS:")
        print("==================================================")

        for thread in threads:
            target = await session.get(OutreachTarget, thread.outreach_target_id)
            contact = await session.get(Contact, target.contact_id) if target else None

            print(f"\n📧 Thread Subject: {thread.subject}")
            print(f"   Contact       : {contact.full_name if contact else 'Unknown'} ({contact.email if contact else 'N/A'})")
            print(f"   Target Status : {target.status if target else 'N/A'}")
            print(f"   Gmail ThreadId: {thread.gmail_thread_id}")
            print(f"   Total Messages: {len(thread.messages)}")

            inbound = [m for m in thread.messages if m.direction == "inbound"]
            if not inbound:
                print("   👉 No inbound replies received yet.")
            else:
                for idx, msg in enumerate(inbound, 1):
                    print(f"\n   💬 Inbound Reply #{idx}:")
                    print(f"      Sent At       : {msg.sent_at}")
                    print(f"      Classification: {msg.classification} (Confidence: {msg.classification_confidence})")
                    print(f"      Message Text  :\n{msg.body_text}\n")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
