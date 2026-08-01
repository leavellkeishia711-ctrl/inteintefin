from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db_session
from app.core.deps import get_tenant_session, get_current_user, UserCtx
from app.ai.analyst import ask_financial_analyst
from pydantic import BaseModel
from typing import List

router = APIRouter()

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    message: str

@router.post("/", response_model=ChatResponse)
async def chat_with_analyst(
    request: ChatRequest,
    db: AsyncSession = Depends(get_tenant_session),
    user: UserCtx = Depends(get_current_user)
):
    try:
        response = await ask_financial_analyst(db, user.company_id, request.message)
        return ChatResponse(message=response)
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Chat endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
