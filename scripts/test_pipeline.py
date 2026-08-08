"""
End-to-end pipeline test.

Uses REAL Gemini API + REAL Gmail to:
  1. Start the FastAPI app (via httpx AsyncClient)
  2. Create a company + contact
  3. Create a campaign
  4. Add yourself as a target
  5. Run the campaign → AI generates email → Gmail sends it

Check your inbox after running this.

Usage:
    python scripts/test_pipeline.py

Requirements:
    - GEMINI_API_KEY in .env
    - token.json present (run scripts/gmail_auth.py first)
    - SENDER_NAME, SENDER_EMAIL, SENDER_BACKGROUND in .env
"""
from __future__ import annotations

import asyncio
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx
from app.core.config import settings
from app.core.logging import configure_logging, get_logger

configure_logging("INFO")
logger = get_logger(__name__)

BASE_URL = "http://127.0.0.1:8000"


async def run() -> None:
    print("\n🚀 Job Outreach Agent — End-to-End Pipeline Test\n")

    # Validate config before starting
    missing = []
    if not settings.gemini_api_key:
        missing.append("GEMINI_API_KEY")
    if not settings.sender_name:
        missing.append("SENDER_NAME")
    if not settings.sender_email:
        missing.append("SENDER_EMAIL")
    if not settings.sender_background:
        missing.append("SENDER_BACKGROUND")
    if missing:
        print(f"❌ Missing required .env variables: {', '.join(missing)}")
        print("\nAdd these to your .env file and try again.")
        sys.exit(1)

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=60.0) as client:
        # 1. Health check
        r = await client.get("/health")
        if r.status_code != 200:
            print(f"❌ Server not running. Start it with: uvicorn app.main:app --reload")
            sys.exit(1)
        print(f"✅ Server is up (v{r.json()['version']})")

        # 2. Create company
        unique_suffix = uuid.uuid4().hex[:6]
        r = await client.post("/api/v1/companies", json={
            "name": "Test Corp (Self-Test)",
            "domain": f"testcorp-{unique_suffix}.example.com",
            "industry": "Technology",
            "description": "A test company used for validating the outreach pipeline.",
        })
        r.raise_for_status()
        company = r.json()
        print(f"✅ Company created: {company['name']} ({company['id'][:8]}...)")

        # 3. Create contact (yourself — safe for testing)
        r = await client.post("/api/v1/contacts", json={
            "company_id": company["id"],
            "first_name": settings.sender_name.split()[0] if settings.sender_name else "Test",
            "last_name": "User",
            "email": settings.sender_email,
            "title": "Engineering Manager",
        })
        if r.status_code == 409:
            list_r = await client.get("/api/v1/contacts")
            list_r.raise_for_status()
            contact = [c for c in list_r.json() if c["email"] == settings.sender_email][0]
            print(f"ℹ️ Contact already exists, using existing: {contact['email']} ({contact['id'][:8]}...)")
        else:
            r.raise_for_status()
            contact = r.json()
            print(f"✅ Contact created: {contact['email']} ({contact['id'][:8]}...)")

        # 4. Create campaign
        r = await client.post("/api/v1/outreach/campaigns", json={
            "name": "Pipeline Self-Test",
            "sender_name": settings.sender_name,
            "sender_email": settings.sender_email,
            "goal": settings.sender_background,
        })
        r.raise_for_status()
        campaign = r.json()
        print(f"✅ Campaign created: {campaign['name']} ({campaign['id'][:8]}...)")

        # 5. Add target
        r = await client.post(f"/api/v1/outreach/campaigns/{campaign['id']}/targets", json={
            "contact_id": contact["id"],
        })
        r.raise_for_status()
        target = r.json()
        print(f"✅ Target added: status={target['status']}")

        # 6. Run campaign
        print(f"\n⏳ Running campaign (generating email + sending via Gmail)...")
        r = await client.post(f"/api/v1/outreach/campaigns/{campaign['id']}/run")
        r.raise_for_status()
        result = r.json()

        print(f"\n📊 Campaign Run Results:")
        print(f"   Processed : {result['processed']}")
        print(f"   Sent      : {result['sent']}")
        print(f"   Skipped   : {result['skipped']}")
        if result['errors']:
            print(f"   Errors    :")
            for err in result['errors']:
                print(f"     - {err}")

        if result['sent'] > 0:
            print(f"\n✅ Success! Check your inbox: https://mail.google.com")
            print(f"   The AI-generated email was sent to: {settings.sender_email}")
        else:
            print(f"\n❌ No emails sent. Check errors above.")
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(run())
