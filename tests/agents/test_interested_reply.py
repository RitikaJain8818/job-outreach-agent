"""
Unit tests for InterestedReplyAgent.
"""
from __future__ import annotations

import pytest

from app.agents.base import AgentContext
from app.agents.interested_reply import InterestedReplyAgent
from tests.conftest import MockLLMProvider


@pytest.fixture
def interested_reply_agent() -> InterestedReplyAgent:
    llm = MockLLMProvider(
        response_json=(
            '{"subject": "Re: VP - Full Stack Engineer", '
            '"body": "Hi Nishan, thanks for following up! I am free tomorrow between 2 PM and 5 PM.", '
            '"reasoning": "Confirming availability", "tokens_used": 60}'
        )
    )
    return InterestedReplyAgent(llm=llm)


@pytest.mark.asyncio
async def test_interested_reply_llm_mode(interested_reply_agent: InterestedReplyAgent) -> None:
    ctx = AgentContext(
        campaign_id="c1",
        target_id="t1",
        contact_id="con1",
        company_id="co1",
        metadata={
            "sender_name": "Ritika Jain",
            "contact_name": "Nishan Mazumdar",
            "company_name": "BNY",
            "original_subject": "VP - Full Stack Engineer",
            "recruiter_message": "What time are you free tomorrow?",
        },
    )

    result = await interested_reply_agent.execute(ctx)
    assert result.success is True
    assert result.agent_name == "InterestedReplyAgent"
    assert "body" in result.output
    assert result.tokens_used == 60


@pytest.mark.asyncio
async def test_interested_reply_template_mode() -> None:
    agent = InterestedReplyAgent()
    ctx = AgentContext(
        campaign_id="c1",
        target_id="t1",
        contact_id="con1",
        company_id="co1",
        metadata={
            "use_template": True,
            "sender_name": "Ritika Jain",
            "contact_name": "Nishan Mazumdar",
            "original_subject": "VP - Full Stack Engineer",
        },
    )

    result = await agent.execute(ctx)
    assert result.success is True
    assert result.tokens_used == 0
    assert "Nishan" in str(result.output["body"])
