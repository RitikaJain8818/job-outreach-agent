# Roadmap — Job Outreach Agent

## Phase 1: Foundation ✅ *complete*

- [x] Project structure & documentation
- [x] Database schema & ORM models
- [x] Core configuration & logging
- [x] Multi-agent skeleton (base + orchestrator)
- [x] FastAPI app with health check
- [x] Test scaffolding

**Goal**: Working skeleton. All agents stubbed and wired.

---

## Phase 2: Gmail Integration ✅ *complete*

- [x] OAuth2 authentication flow (`scripts/gmail_auth.py`)
- [x] Send email (plain text + HTML via GmailClient)
- [x] Thread reply polling (GmailAgent poll mode)
- [x] EmailThread + EmailMessage persistence
- [x] New-reply deduplication (diff known message IDs)
- [x] GmailAgent — full implementation
- [x] Orchestrator pipeline bridging (email gen → gmail send → memory write)
- [x] `/outreach/campaigns/{id}/run` endpoint wired
- [x] Dependency injection layer (`app/api/dependencies.py`)
- [x] Tests: GmailAgent unit + full pipeline integration test

**Goal**: ✅ Reliably send and receive emails through Gmail API.

---

## Phase 3: LLM Email Generation ✅ *complete*

- [x] LLM provider abstraction (Gemini + OpenAI)
- [x] Gemini 3.6 Flash model integration & token tracking (`usageMetadata`)
- [x] Email generation prompt v1 (cold outreach with subject & body)
- [x] Personalization context injection (sender background, recipient role & company)
- [x] Structured output / Pydantic parsing (`EmailGenerationOutput`)
- [x] In-memory LLM response caching (`app/core/cache.py`)
- [x] EmailGenerator Agent — full implementation
- [x] Sender profile config in `.env` (`SENDER_NAME`, `SENDER_EMAIL`, `SENDER_BACKGROUND`)
- [x] End-to-end integration test (`scripts/test_pipeline.py`)

**Goal**: ✅ Generate high-quality, personalized cold emails automatically.

---

## Phase 4: Reply Classification & Follow-Ups ← *next*

- [ ] Reply classification prompt v1
- [ ] ReplyClassifier Agent — full implementation
- [ ] FollowUp Agent — timing logic + template selection
- [ ] Follow-up prompt v1
- [ ] Background scheduler (APScheduler or cron)

**Goal**: Closed-loop outreach — send, read, classify, follow up.

---

## Phase 5: Memory & Learning

- [ ] MemoryAgent — read/write to `agent_memory` table
- [ ] Outcome tracking per contact/company/campaign
- [ ] Template performance scoring
- [ ] Context injection from past learnings
- [ ] A/B tracking foundations

**Goal**: System improves over time with each campaign run.

---

## Phase 6: Research Agent

- [ ] Public data enrichment (LinkedIn scraping or API)
- [ ] Company news / recent activity lookup
- [ ] Contact role / seniority inference
- [ ] Job board integration (Hacker News Who's Hiring, LinkedIn Jobs)
- [ ] ResearchAgent — full implementation

**Goal**: Agents can discover and enrich targets autonomously.

---

## Phase 7: API & Dashboard (SaaS Foundation)

- [ ] REST API — companies, contacts, jobs, campaigns
- [ ] Campaign management UI (optional)
- [ ] Authentication (JWT / API key)
- [ ] Multi-user support
- [ ] Rate limiting & quotas
- [ ] Webhook support for incoming events

---

## Phase 8: SaaS Readiness

- [ ] Multi-tenant data isolation
- [ ] Billing hooks (Stripe)
- [ ] PostgreSQL in production
- [ ] Docker + docker-compose
- [ ] CI/CD pipeline (GitHub Actions)
- [ ] Observability (structured logs → Datadog / Grafana)
