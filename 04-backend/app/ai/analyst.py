import logging
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any
from uuid import UUID
from app.ai.client import get_llm_client
from app.ai.tools import get_tools_spec, execute_tool, make_json, truncate_response

logger = logging.getLogger(__name__)

async def ask_financial_analyst(db: AsyncSession, company_id: UUID | str, prompt: str) -> str:
    client = get_llm_client()
    tools = get_tools_spec()
    
    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": "You are a Financial Analyst AI for a media buying company. Answer user questions based ONLY on data from the database. You MUST use the provided tools to fetch data. If you don't call a tool, you cannot answer the question."},
        {"role": "user", "content": prompt}
    ]
    
    max_iterations = 5
    iteration = 0
    has_used_tool = False
    
    while iteration < max_iterations:
        iteration += 1
        
        try:
            response = await client.complete_with_tools(messages, tools)
        except Exception as e:
            logger.error(f"LLM API Error: {e}")
            return "Internal Error: Could not reach AI service."
            
        messages.append(response)
        
        # Check if tools were called
        if not response.get("tool_calls"):
            if not has_used_tool:
                if iteration == 1:
                    # Policy: First pass without tool call -> prompt again strongly
                    messages.append({
                        "role": "user", 
                        "content": "You MUST use a tool to fetch data before answering. Please call an appropriate tool now."
                    })
                    continue
                else:
                    # Policy: Second failure -> polite error to user and log violation
                    logger.warning("AI Violation: Model refused to use tools after explicit instruction.")
                    return "I am unable to answer this question without accessing the database, which I failed to do. Please try rephrasing."
            else:
                # Normal completion after having used tools successfully
                return response.get("content") or "No response provided."
                
        # Execute tools
        tool_results = []
        any_success = False
        
        for tool_call in response["tool_calls"]:
            ok, payload = await execute_tool(tool_call["name"], tool_call["arguments"], db, company_id)
            if ok:
                any_success = True
                content = truncate_response(make_json(payload))
            else:
                content = str(payload)
                
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool_call["id"],
                "content": content,
                "is_error": not ok
            })
            
        if any_success:
            has_used_tool = True
            
        messages.append({
            "role": "user",
            "content": tool_results
        })
            
    return "Failed to analyze data after multiple attempts (iteration limit reached)."
