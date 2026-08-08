# API Contracts — Job Outreach Agent

Base URL: `/api/v1`
Content-Type: `application/json`

---

## Companies

### `POST /companies`
Create a company.

**Request**:
```json
{
  "name": "Acme Corp",
  "domain": "acme.com",
  "industry": "SaaS",
  "size_range": "50-200",
  "location": "San Francisco, CA",
  "description": "B2B SaaS company...",
  "website_url": "https://acme.com",
  "linkedin_url": "https://linkedin.com/company/acme"
}
```
**Response**: `201` — Company object with `id`.

### `GET /companies`
List companies. Supports `?page=1&size=20`.

### `GET /companies/{id}`
Get company by ID.

### `PATCH /companies/{id}`
Update company fields.

---

## Contacts

### `POST /contacts`
Create a contact.

**Request**:
```json
{
  "company_id": "uuid",
  "first_name": "Jane",
  "last_name": "Doe",
  "email": "jane@acme.com",
  "title": "Head of Engineering",
  "linkedin_url": "https://linkedin.com/in/janedoe"
}
```
**Response**: `201` — Contact object with `id`.

### `GET /contacts`
List contacts. Supports `?company_id=uuid&page=1&size=20`.

### `GET /contacts/{id}`
Get contact by ID.

---

## Job Openings

### `POST /jobs`
Create a job opening.

### `GET /jobs`
List job openings. Supports `?company_id=uuid&status=open`.

---

## Outreach Campaigns

### `POST /outreach/campaigns`
Create a campaign.

**Request**:
```json
{
  "name": "ML Engineer Outreach Q3",
  "goal": "Get interviews at Series B AI startups",
  "sender_name": "Ritika Jain",
  "sender_email": "ritika@example.com",
  "follow_up_days": 3,
  "max_follow_ups": 2
}
```

### `POST /outreach/campaigns/{id}/targets`
Add a contact as an outreach target.

**Request**:
```json
{
  "contact_id": "uuid",
  "job_opening_id": "uuid"
}
```

### `POST /outreach/campaigns/{id}/run`
Trigger the orchestrator to process pending targets.

**Response**:
```json
{
  "campaign_id": "uuid",
  "processed": 5,
  "sent": 4,
  "skipped": 1,
  "errors": []
}
```

### `GET /outreach/campaigns/{id}`
Get campaign status and target summary.

### `GET /outreach/targets/{id}`
Get single target details including email thread history.

---

## Health

### `GET /health`
**Response**: `200`
```json
{ "status": "ok", "version": "0.1.0" }
```
