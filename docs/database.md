# Database Schema — Job Outreach Agent

## ORM: SQLAlchemy 2.0 Async
## Migration tool: Alembic
## Dev DB: SQLite (`data/dev.db`)
## Prod DB: PostgreSQL (configured via `DATABASE_URL` env var)

---

## Tables

### `companies`

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| name | VARCHAR(255) | Required |
| domain | VARCHAR(255) | Unique |
| industry | VARCHAR(100) | |
| size_range | VARCHAR(50) | e.g. "50-200" |
| location | VARCHAR(255) | |
| description | TEXT | |
| linkedin_url | VARCHAR(500) | |
| website_url | VARCHAR(500) | |
| raw_research | JSONB/TEXT | Raw enrichment data |
| created_at | TIMESTAMP | Auto |
| updated_at | TIMESTAMP | Auto |

---

### `contacts`

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| company_id | UUID FK → companies | |
| first_name | VARCHAR(100) | |
| last_name | VARCHAR(100) | |
| email | VARCHAR(255) | Unique |
| title | VARCHAR(255) | |
| linkedin_url | VARCHAR(500) | |
| notes | TEXT | |
| created_at | TIMESTAMP | Auto |
| updated_at | TIMESTAMP | Auto |

---

### `job_openings`

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| company_id | UUID FK → companies | |
| title | VARCHAR(255) | |
| description | TEXT | |
| url | VARCHAR(500) | |
| status | ENUM | `open`, `closed`, `unknown` |
| discovered_at | TIMESTAMP | |
| created_at | TIMESTAMP | Auto |

---

### `outreach_campaigns`

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| name | VARCHAR(255) | |
| goal | TEXT | e.g. "ML Engineer roles at Series B startups" |
| sender_name | VARCHAR(255) | |
| sender_email | VARCHAR(255) | |
| follow_up_days | INTEGER | Default: 3 |
| max_follow_ups | INTEGER | Default: 2 |
| status | ENUM | `draft`, `active`, `paused`, `completed` |
| created_at | TIMESTAMP | Auto |
| updated_at | TIMESTAMP | Auto |

---

### `outreach_targets`

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| campaign_id | UUID FK → outreach_campaigns | |
| contact_id | UUID FK → contacts | |
| job_opening_id | UUID FK → job_openings | Nullable |
| status | ENUM | `pending`, `sent`, `replied`, `bounced`, `not_interested`, `interested`, `opted_out` |
| follow_up_count | INTEGER | Default: 0 |
| last_action_at | TIMESTAMP | |
| next_action_at | TIMESTAMP | |
| notes | TEXT | Agent notes |
| created_at | TIMESTAMP | Auto |
| updated_at | TIMESTAMP | Auto |

---

### `email_threads`

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| outreach_target_id | UUID FK → outreach_targets | |
| gmail_thread_id | VARCHAR(255) | From Gmail API |
| subject | VARCHAR(500) | |
| created_at | TIMESTAMP | Auto |

---

### `email_messages`

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| thread_id | UUID FK → email_threads | |
| gmail_message_id | VARCHAR(255) | From Gmail API |
| direction | ENUM | `outbound`, `inbound` |
| body_text | TEXT | |
| body_html | TEXT | |
| sent_at | TIMESTAMP | |
| classification | VARCHAR(50) | Null until classified |
| classification_confidence | FLOAT | 0.0–1.0 |
| created_at | TIMESTAMP | Auto |

---

### `agent_memory`

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| scope | VARCHAR(100) | e.g. `domain:fintech`, `contact:uuid` |
| key | VARCHAR(255) | |
| value | TEXT/JSON | |
| source | VARCHAR(100) | Which agent wrote it |
| created_at | TIMESTAMP | Auto |
| expires_at | TIMESTAMP | Nullable |

---

## Indexes

- `contacts.email` — UNIQUE
- `companies.domain` — UNIQUE
- `outreach_targets.(campaign_id, contact_id)` — UNIQUE
- `email_threads.gmail_thread_id` — INDEX
- `email_messages.gmail_message_id` — INDEX
- `agent_memory.(scope, key)` — INDEX
