import logging
from typing import Protocol, List, Dict, Any
import anthropic
from app.core.config import settings
import json

logger = logging.getLogger(__name__)

class LLMClient(Protocol):
    async def complete_with_tools(self, messages: List[Dict[str, Any]], tools: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Sends messages and tool definitions to the LLM and returns the raw response message object or dict,
        containing either a text response or tool calls.
        """
        ...

class AnthropicClient:
    def __init__(self):
        if not settings.AI_API_KEY:
            raise ValueError("AI_API_KEY is missing")
        self.client = anthropic.AsyncAnthropic(api_key=settings.AI_API_KEY)
        self.model = settings.AI_MODEL

    async def complete_with_tools(self, messages: List[Dict[str, Any]], tools: List[Dict[str, Any]]) -> Dict[str, Any]:
        try:
            # Anthropic expects tools in a specific format
            anthropic_tools = []
            for t in tools:
                anthropic_tools.append({
                    "name": t["name"],
                    "description": t["description"],
                    "input_schema": t["input_schema"]
                })
            
            # Map common message format to Anthropic's format
            system_prompt = ""
            anthropic_messages = []
            for msg in messages:
                if msg["role"] == "system":
                    system_prompt += msg["content"] + "\n"
                else:
                    anthropic_messages.append(msg)
                    
            response = await self.client.messages.create(
                model=self.model,
                system=system_prompt,
                messages=anthropic_messages,
                tools=anthropic_tools,
                max_tokens=2048,
            )
            
            # Translate Anthropic response back to a neutral format
            neutral_response = {
                "role": "assistant",
                "content": "",
                "tool_calls": []
            }
            for block in response.content:
                if block.type == "text":
                    neutral_response["content"] += block.text
                elif block.type == "tool_use":
                    neutral_response["tool_calls"].append({
                        "id": block.id,
                        "name": block.name,
                        "arguments": block.input
                    })
            return neutral_response
            
        except Exception as e:
            logger.error(f"Anthropic API Error: {e}")
            raise e

def get_llm_client() -> LLMClient:
    provider = settings.AI_PROVIDER.lower()
    if provider == "anthropic":
        return AnthropicClient()
    raise NotImplementedError(f"AI provider {provider} is not supported.")
