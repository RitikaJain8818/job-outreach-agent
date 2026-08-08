# Architecture — Job Outreach Agent

## System Overview

A modular, multi-agent pipeline that automates personalized job outreach via Gmail, with LLM-powered email generation, reply classification, and follow-up management.

---

## Agent Pipeline

```
[Trigger: API / CLI / Scheduler]
         │
         ▼
  ┌─────────────────┐
  │  Orchestrator   │  ← coordinates the pipeline
  └────────┬────────┘
           │
     ┌─────┴──────┐
     ▼            ▼
┌──────────┐  ┌──────────────────┐
│ Research │  │  Memory Agent    │  ← loads past context & lessons
│  Agent   │  │  (read phase)    │
└────┬─────┘  └──────────────────┘
     │
     ▼
┌───────────────────┐
│ EmailGenerator    │  ← LLM call with personalization context
│     Agent         │
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│   Gmail Agent     │  ← sends email, logs thread ID
│   (send phase)    │
└────────┬──────────┘
         │
     [time passes]
         │
         ▼
┌───────────────────┐
│   Gmail Agent     │  ← polls for replies
│   (poll phase)    │
└────────┬──────────┘
         │
         ▼
┌───────────────────────┐
│  ReplyClassifier      │  ← LLM classifies intent
│       Agent           │
└──────────┬────────────┘
           │
     ┌─────┴──────┐
     ▼            ▼
┌──────────┐  ┌──────────────┐
│FollowUp  │  │ Memory Agent │  ← stores outcome, learnings
│  Agent   │  │ (write phase)│
└──────────┘  └──────────────┘
```

---

## Component Map

```
/app
  /core
    config.py          ← Pydantic BaseSettings (env vars)
    logging.py         ← Structured logger
    exceptions.py      ← Typed application exceptions

  /db
    session.py         ← Async SQLAlchemy engine + session
    base.py            ← Declarative Base

  /models              ← SQLAlchemy ORM models
    company.py
    contact.py
    job_opening.py
    outreach.py        ← OutreachCampaign, OutreachTarget
    email_thread.py    ← EmailThread, EmailMessage

  /agents              ← Business logic agents
    base.py            ← BaseAgent abstract class
    orchestrator.py
    research.py
    email_generator.py
    gmail_agent.py
    reply_classifier.py
    follow_up.py
    memory.py

  /prompts             ← Versioned prompt templates
    email_generation_v1.py
    reply_classification_v1.py
    follow_up_v1.py

  /integrations
    /gmail
      auth.py          ← OAuth2 flow
      client.py        ← Gmail API wrapper
    /llm
      base.py          ← LLMProvider ABC
      gemini.py        ← Gemini implementation
      openai.py        ← OpenAI implementation

  /services            ← Data access layer (used by agents + API)
    company_service.py
    contact_service.py
    outreach_service.py

  /api
    /v1
      companies.py
      contacts.py
      jobs.py
      outreach.py
      router.py
    main.py            ← FastAPI app

/tests
  conftest.py          ← Fixtures (mock DB, mock LLM, mock Gmail)
  /agents
  /services

/docs                  ← Project knowledge base
/skills                ← Domain skill guides
/migrations            ← Alembic migrations
```

---

## Data Flow: New Outreach

1. User POSTs to `/api/v1/outreach/start` with campaign config.
2. `OutreachService` creates `OutreachCampaign` + `OutreachTarget` records.
3. `OrchestratorAgent` picks up targets, invokes:
   - `ResearchAgent` → enriches contact/company data.
   - `MemoryAgent` → loads relevant past outcomes for this domain.
   - `EmailGeneratorAgent` → generates personalized email via LLM.
   - `GmailAgent` → sends email, stores `EmailThread` + `EmailMessage`.
4. Background scheduler polls for replies via `GmailAgent`.
5. `ReplyClassifierAgent` classifies each reply and updates `OutreachTarget.status`.
6. `FollowUpAgent` triggers follow-up emails based on status + elapsed time.
7. `MemoryAgent` writes outcome and lessons to the DB.

---

## Key Principles

- **No business logic in route handlers** — only delegation to services.
- **No direct DB access in agents** — always go through services.
- **Typed I/O between agents** — Pydantic models for all inter-agent contracts.
- **LLM calls only in agents** — never in services or route handlers.
- **All external I/O is mockable** — Gmail + LLM inject via constructor.

---

## Scalability Path

| Current | When to upgrade |
|---|---|
| SQLite | >1 user or concurrent writes |
| In-process orchestration | Multiple workers / async jobs |
| Single-process polling | High volume → add Celery + Redis |
| Single-tenant | SaaS → add tenant isolation + auth |
