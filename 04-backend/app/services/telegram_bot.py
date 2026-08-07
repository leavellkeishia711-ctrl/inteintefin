import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from app.db.models import User, Company
from app.db.session import tenant_session
from app.services.pnl import calculate_pnl
from app.services.cashflow import calculate_cashflow
from typing import Optional
from decimal import Decimal
import redis.asyncio as redis
from redis.exceptions import ConnectionError, TimeoutError
from app.core.config import settings

logger = logging.getLogger(__name__)

# Global redis client (initialized lazily)
_redis_client = None

import time
import asyncio
from collections import defaultdict

_local_limits = defaultdict(list)
_local_limits_lock = asyncio.Lock()
LOCAL_LIMIT_MAX_KEYS = 10000

async def check_local_rate_limit(chat_id: int) -> bool:
    now = time.monotonic()
    async with _local_limits_lock:
        if chat_id not in _local_limits and len(_local_limits) >= LOCAL_LIMIT_MAX_KEYS:
            logger.warning("Local rate limiter at max capacity, denying new chat_id.")
            return False
            
        history = _local_limits.get(chat_id, [])
        history = [ts for ts in history if now - ts < 60]
        
        if len(history) >= 5:
            _local_limits[chat_id] = history
            return False
            
        history.append(now)
        _local_limits[chat_id] = history
        return True

async def get_redis():
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(settings.REDIS_URL or "redis://localhost:6379")
    return _redis_client

async def check_rate_limit(chat_id: int) -> bool:
    """Returns True if allowed, False if rate limited"""
    try:
        r = await get_redis()
        key = f"rate_limit:telegram:{chat_id}"
        
        current = await r.incr(key)
        if current == 1:
            await r.expire(key, 60)
            
        if current > 5:
            return False
    except (ConnectionError, TimeoutError):
        logger.warning("Redis is unavailable. Local rate limiter used for non-critical fallback.")
        return await check_local_rate_limit(chat_id)
        
    return True

async def handle_telegram_message(db: AsyncSession, chat_id: int, text_str: str) -> Optional[str]:
    """
    Handle incoming Telegram message and return a response string, or None if no response is needed.
    """
    if not text_str.startswith('/'):
        return None
        
    # /link commands fail closed if rate limited
    if text_str.startswith('/link '):
        try:
            r = await get_redis()
            key = f"rate_limit:telegram:{chat_id}"
            current = await r.incr(key)
            if current == 1:
                await r.expire(key, 60)
            if current > 5:
                from fastapi import HTTPException
                raise HTTPException(status_code=429, detail="Too many requests.")
        except (ConnectionError, TimeoutError):
            from fastapi import HTTPException
            logger.warning("Redis is unavailable. Telegram linking disabled (fail-closed).")
            raise HTTPException(status_code=503, detail="Our systems are temporarily overloaded.")
            
        token = text_str.split(' ')[1].strip()
        try:
            user_id_bytes = await r.get(f"telegram_link:{token}")
        except (ConnectionError, TimeoutError):
            from fastapi import HTTPException
            logger.warning("Redis is unavailable. Telegram linking disabled (fail-closed).")
            raise HTTPException(status_code=503, detail="Our systems are temporarily overloaded.")
            
        if not user_id_bytes:
            return "Invalid or expired link token."
            
        user_id = user_id_bytes.decode('utf-8')
        
        # We need to fetch the user by user_id and update their chat_id
        from uuid import UUID
        user = await db.get(User, UUID(user_id))
        if not user:
            return "User not found."
            
        user.telegram_chat_id = chat_id
        await db.commit()
        await r.delete(f"telegram_link:{token}")
        
        return "Your Telegram account has been successfully linked!"
        
    # For other commands like /status, use standard rate limit check with local fallback
    if not await check_rate_limit(chat_id):
        return "Too many requests. Please wait a minute."



    if not text_str.startswith('/status'):
        return None

    result = await db.execute(select(User).where(User.telegram_chat_id == chat_id))
    user = result.scalars().first()

    if not user:
        return "I'm sorry, I don't recognize you. Please link your Telegram account using the /link command with a token from the web app."

    company = await db.get(Company, user.company_id)
    if not company:
        return "Your account is not associated with a valid company."
        
    async with tenant_session(str(user.company_id)) as tenant_db:
        # Enforce RLS for this specific user's queries
        await tenant_db.execute(text("SELECT set_config('app.user_id', :uid, true)"), {"uid": str(user.id)})
        
        from datetime import datetime, timedelta
        from app.core.i18n import translate
        
        start_date = datetime.utcnow().date() - timedelta(days=30)
        
        # Scoping logic: Only user-specific metrics
        user_id_obj = user.id
                
        pnl = await calculate_pnl(tenant_db, company.id, start_date=start_date, team_id=None, user_id=user_id_obj)
        cf = await calculate_cashflow(tenant_db, company.id)
        
        roi = "0"
        if pnl.ad_spend > 0:
            roi = str((pnl.net_profit / pnl.ad_spend * Decimal("100")).quantize(Decimal("0.01")))
            
        lang = user.preferred_language or company.default_language or "en"
        
        # We translate the title (could translate everything, but demonstrating alert locale via user settings)
        status_title = translate("alert_30_day_status", lang) if translate("alert_30_day_status", lang) != "alert_30_day_status" else "30-Day Status"
        
        message = (
            f"📊 *{status_title}*\n\n"
            f"Revenue: {pnl.revenue}\n"
            f"Spend: {pnl.ad_spend}\n"
            f"ROI: {roi}%\n"
            f"Runway: {cf.runway_days} days\n"
        )
        return message
