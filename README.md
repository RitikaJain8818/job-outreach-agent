# Job Outreach Agent 🚀

An AI-powered, multi-agent automated job outreach system built with **FastAPI**, **Async SQLAlchemy**, **Google Gemini 3.6 Flash**, and the **Gmail API**.

Designed with a modular, multi-agent architecture suitable for personal job automation and scalable SaaS deployment.

---

## 🌟 Key Features

- **Multi-Agent Pipeline**: Sequentially coordinates research, memory retrieval, personalized email generation, Gmail sending, reply classification, and follow-ups.
- **AI-Powered Cold Outreach**: Generates personalized, high-converting cold emails tailored to specific hiring managers, roles, and company contexts using **Gemini 3.6 Flash**.
- **Native Gmail Integration**: Full OAuth2 flow supporting plain-text and HTML emails, thread tracking, and reply polling without third-party email tools.
- **LLM Caching & Token Tracking**: Built-in SHA256 prompt response caching (`CachingLLMProvider`) to prevent redundant LLM calls and track real token usage.
- **Production-Ready Architecture**: Async SQLAlchemy 2.0 ORM, strict Pydantic contract validation, structured logging, dependency injection, and clean exception handling.

---

## 🏗️ Multi-Agent Architecture

```
                               ┌───────────────────────────┐
                               │     OrchestratorAgent     │
                               └─────────────┬─────────────┘
                                             │
      ┌──────────────────┬───────────────────┼───────────────────┬──────────────────┐
      │                  │                   │                   │                  │
┌─────▼──────┐    ┌──────▼──────┐     ┌──────▼──────┐     ┌──────▼──────┐    ┌──────▼──────┐
│MemoryAgent │    │ResearchAgent│     │  EmailGen   │     │ GmailAgent  │    │ Classifier  │
│  (DB/Logs) │    │(Enrichment) │     │ (Gemini 3.6)│     │(Send/Poll)  │    │ & Follow-Up │
└────────────┘    └─────────────┘     └─────────────┘     └─────────────┘    └─────────────┘
```

1. **MemoryAgent**: Reads past outcomes and campaign history for context.
2. **ResearchAgent**: Enriches target contact and company metadata.
3. **EmailGeneratorAgent**: Generates subject and personalized body using Gemini LLM.
4. **GmailAgent**: Sends outreach emails via Gmail API and records `EmailThread` / `EmailMessage` records in SQLite/PostgreSQL.
5. **ReplyClassifierAgent**: Classifies recipient responses (`interested`, `not_interested`, `out_of_office`).
6. **FollowUpAgent**: Automates follow-up timing and message generation.

---

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.10+
- Google Cloud OAuth 2.0 Desktop credentials (`credentials.json`)
- Gemini API key from [aistudio.google.com](https://aistudio.google.com)

### 2. Installation
```bash
# Clone repository
git clone https://github.com/RitikaJain8818/job-outreach-agent.git
cd job-outreach-agent

# Create virtual environment & install dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### 3. Environment Configuration
Copy `.env.example` to `.env` and set your credentials:
```bash
cp .env.example .env
```
Fill in `.env`:
```env
GEMINI_API_KEY=your_gemini_api_key
SENDER_NAME="Your Name"
SENDER_EMAIL="your_email@gmail.com"
SENDER_BACKGROUND="ML Engineer with 4+ years experience in Python, LLMs, and backend systems."
```

### 4. Authorize Gmail API
Place your `credentials.json` in the root directory, then authorize:
```bash
python scripts/gmail_auth.py
```
This generates `token.json` for Gmail API authentication.

### 5. Run the Server
```bash
uvicorn app.main:app --reload
```
Interactive API documentation available at: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## 🧪 Testing

Run unit & integration tests with pytest:
```bash
# Run unit test suite (18 tests)
pytest tests/ -v

# Run live end-to-end pipeline test (creates company/contact and sends real email)
python scripts/test_pipeline.py
```

---

## 📊 API Endpoint Overview

- `POST /api/v1/companies` — Register target companies
- `POST /api/v1/contacts` — Add hiring contacts
- `POST /api/v1/outreach/campaigns` — Create outreach campaigns
- `POST /api/v1/outreach/campaigns/{id}/targets` — Enroll contacts in campaign
- `POST /api/v1/outreach/campaigns/{id}/run` — Execute multi-agent outreach pipeline

---

## 📄 License

MIT License. Designed and built by [Ritika Jain](https://github.com/RitikaJain8818).
