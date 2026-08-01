import pytest
from app.ai.analyst import ask_financial_analyst
import uuid
from app.db.session import system_session

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
