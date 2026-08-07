import pytest
from app.ai.analyst import ask_financial_analyst
from app.ai.tools import execute_tool
import uuid
from app.db.session import system_session
import datetime
from sqlalchemy.ext.asyncio import AsyncSession

@pytest.mark.asyncio
async def test_ai_analyst_tool_enforcement():
    company_id = uuid.uuid4()
    
    class MockClient:
        async def complete_with_tools(self, messages, tools):
            return {"role": "assistant", "content": "I am answering directly without tool calls.", "tool_calls": []}
            
    import app.ai.analyst
    original_get_client = app.ai.analyst.get_llm_client
    app.ai.analyst.get_llm_client = lambda: MockClient()
    
    try:
        async with system_session() as db_session:
            response = await ask_financial_analyst(db_session, company_id, "What is my revenue?")
            assert "unable to answer this question without accessing the database" in response
    finally:
        app.ai.analyst.get_llm_client = original_get_client

@pytest.mark.asyncio
async def test_ai_analyst_tool_error_prevents_response():
    company_id = uuid.uuid4()
    
    class MockClient:
        async def complete_with_tools(self, messages, tools):
            if len(messages) > 2 and messages[-1]["role"] == "user":
                return {"role": "assistant", "content": "Sneaky answer", "tool_calls": []}
            
            return {
                "role": "assistant",
                "content": "",
                "tool_calls": [{"id": "123", "name": "get_pnl", "arguments": {"date_from": "invalid"}}]
            }
            
    import app.ai.analyst
    original_get_client = app.ai.analyst.get_llm_client
    app.ai.analyst.get_llm_client = lambda: MockClient()
    
    try:
        async with system_session() as db_session:
            response = await ask_financial_analyst(db_session, company_id, "What is my revenue?")
            assert "unable to answer this question without accessing the database" in response
            assert "Sneaky answer" not in response
    finally:
        app.ai.analyst.get_llm_client = original_get_client

@pytest.mark.asyncio
async def test_ai_analyst_cross_tenant_ad_account():
    c1 = uuid.uuid4()
    ad_account = uuid.uuid4()
    
    async with system_session() as db_session:
        ok, res = await execute_tool("get_consumables_cost", {
            "date_from": str(datetime.date.today()),
            "date_to": str(datetime.date.today()),
            "ad_account_id": str(ad_account)
        }, db_session, str(c1))
        
        assert ok is True
        assert res["consumables_cost"] == 0

@pytest.mark.asyncio
async def test_ai_analyst_no_sensitive_fields():
    c1 = uuid.uuid4()
    async with system_session() as db_session:
        ok, res = await execute_tool("get_transactions", {
            "date_from": str(datetime.date.today() - datetime.timedelta(days=1)),
            "date_to": str(datetime.date.today()),
            "limit": 10
        }, db_session, str(c1))
        
        assert ok is True
        if len(res) > 0:
            for item in res:
                assert "identifier" not in item
                assert "password_hash" not in item
                assert "_sa_instance_state" not in item
