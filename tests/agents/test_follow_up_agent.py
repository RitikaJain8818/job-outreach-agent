"""
Unit tests for FollowUpAgent — Phase 4.
"""
from __future__ import annotations

import pytest

from app.agents.base import AgentContext
from app.agents.follow_up import FollowUpAgent
from tests.conftest import MockLLMProvider


def _make_context(**metadata) -> AgentContext:
    return AgentContext(
        campaign_id="camp-1",
        target_id="tgt-1",
        contact_id="con-1",
        company_id="co-1",
        metadata=metadata,
    )


@pytest.fixture
def follow_up_agent() -> FollowUpAgent:
    llm = MockLLMProvider(
        response_json=(
            '{"subject": "Re: Quick question about your ML team", '
            '"body": "Hi Jane, just checking if you had a chance to see my previous email. '
            'Would love to connect for 15 minutes!", '
            '"tokens_used": 120}'
        )
    )
    return FollowUpAgent(llm=llm)


_VALID_METADATA = {
    "sender_name": "Ritika Jain",
    "contact_name": "Jane Doe",
    "company_name": "Acme Corp",
    "original_subject": "Quick question about your ML team",
    "original_body": "Hi Jane, I noticed Acme is scaling fast...",
    "follow_up_number": "1",
    "days_since_last_email": "3",
}


@pytest.mark.asyncio
async def test_generates_followup_number_1(follow_up_agent: FollowUpAgent) -> None:
    ctx = _make_context(**_VALID_METADATA)
    result = await follow_up_agent.execute(ctx)

    assert result.success is True
    assert result.agent_name == "FollowUpAgent"
    assert "subject" in result.output
    assert "body" in result.output
    assert len(str(result.output["subject"])) > 0
    assert result.tokens_used == 120


@pytest.mark.asyncio
async def test_missing_contact_name_returns_error(follow_up_agent: FollowUpAgent) -> None:
    """Omitting contact_name should return a failure result describing the missing key."""
    metadata = {k: v for k, v in _VALID_METADATA.items() if k != "contact_name"}
    ctx = _make_context(**metadata)
    result = await follow_up_agent.execute(ctx)

    assert result.success is False
    assert "contact_name" in (result.error or "")


@pytest.mark.asyncio
async def test_missing_multiple_keys_returns_error(follow_up_agent: FollowUpAgent) -> None:
    """When multiple required keys are absent, all should be mentioned in the error."""
    ctx = _make_context(sender_name="Ritika")  # only one of many required keys
    result = await follow_up_agent.execute(ctx)

    assert result.success is False
    assert result.error is not None
