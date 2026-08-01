from fastapi import APIRouter, Request, Header, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import system_session
from app.core.config import settings
from app.services.telegram_bot import handle_telegram_message

router = APIRouter()

@router.post("/telegram")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str = Header(None)
):
    if not settings.TELEGRAM_WEBHOOK_SECRET:
        raise HTTPException(status_code=500, detail="Telegram integration not configured")
        
    if x_telegram_bot_api_secret_token != settings.TELEGRAM_WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail="Invalid secret token")
        
    update = await request.json()
    
    if "message" in update and "text" in update["message"]:
        chat_id = update["message"]["chat"]["id"]
        text = update["message"]["text"]
        
        async with system_session() as db:
            response = await handle_telegram_message(db, chat_id, text)
            
            if response:
                import httpx
                bot_token = settings.TELEGRAM_BOT_TOKEN
                if bot_token:
                    async with httpx.AsyncClient() as client:
                        await client.post(
                            f"https://api.telegram.org/bot{bot_token}/sendMessage",
                            json={
                                "chat_id": chat_id,
                                "text": response,
                                "parse_mode": "Markdown"
                            },
                            timeout=5
                        )
    
    return {"status": "ok"}

