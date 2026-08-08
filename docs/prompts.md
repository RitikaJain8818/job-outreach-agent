# Prompts — Job Outreach Agent

## Versioning Convention

- Prompts are Python modules in `/app/prompts/`.
- Each file is named `{purpose}_v{N}.py`.
- Never edit an existing version — create a new `vN+1` file.
- Each module exports: `SYSTEM_PROMPT`, `build_user_prompt(context) -> str`.

---

## Catalog

### `email_generation_v1`
**Purpose**: Generate a personalized cold outreach email.

**System Prompt Variables**: None (static).

**User Prompt Context**:
```python
{
    "sender_name": str,
    "sender_background": str,
    "contact_name": str,
    "contact_title": str,
    "company_name": str,
    "company_description": str,
    "company_industry": str,
    "job_title": str | None,         # if targeting a specific opening
    "personalization_notes": str,    # from ResearchAgent
    "past_performance": str,         # from MemoryAgent (what worked before)
    "tone": str,                     # "professional" | "casual" | "concise"
}
```

**Expected Output** (structured):
```json
{
    "subject": "string",
    "body": "string",
    "reasoning": "string"
}
```

---

### `reply_classification_v1`
**Purpose**: Classify the intent of an inbound email reply.

**Classes**:
- `interested` — positive signal, wants to continue
- `not_interested` — explicit rejection
- `auto_reply` — OOO or automated message
- `bounced` — delivery failure
- `question` — asking for more info
- `needs_review` — ambiguous, human review needed

**Expected Output** (structured):
```json
{
    "classification": "interested | not_interested | auto_reply | bounced | question | needs_review",
    "confidence": 0.0,
    "reasoning": "string"
}
```

---

### `follow_up_v1`
**Purpose**: Generate a follow-up email given thread context and prior outcome.

**User Prompt Context**:
```python
{
    "sender_name": str,
    "contact_name": str,
    "company_name": str,
    "original_email_subject": str,
    "original_email_body": str,
    "follow_up_number": int,         # 1 or 2
    "days_since_last_email": int,
}
```

**Expected Output** (structured):
```json
{
    "subject": "string",
    "body": "string"
}
```

---

## Prompt Engineering Rules

1. Always include a `reasoning` field in output — aids debugging.
2. Use JSON mode / structured output — never parse free-text.
3. Keep system prompts short and role-focused.
4. User prompts contain all dynamic data — system prompts are static.
5. Test every new prompt version with at least 3 diverse inputs before activating.
6. Record token counts and output quality in `agent_memory` when running campaigns.
