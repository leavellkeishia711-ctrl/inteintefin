import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Protocol, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models import Alert
from app.services.cashflow import calculate_cashflow
from app.services.pnl import calculate_pnl
from decimal import Decimal

logger = logging.getLogger(__name__)

class Notifier(Protocol):
    async def notify(self, alert: Alert):
        ...

class LoggingNotifier(Notifier):
    async def notify(self, alert: Alert):
        logger.warning(f"ALERT [{alert.risk_level}]: {alert.message} (Company: {alert.company_id})")

class TelegramNotifier(Notifier):
    def __init__(self, db: AsyncSession):
        self.db = db
        
    async def notify(self, alert: Alert):
        import os
        import httpx
        from app.db.models import User
        
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not bot_token:
            return
            
        # Find users in the company with telegram linked
        result = await self.db.execute(
            select(User).where(
                User.company_id == alert.company_id,
                User.telegram_chat_id.is_not(None)
            )
        )
        users = result.scalars().all()
        
        if not users:
            return
            
        message = f"СЂСџС™РЃ *{alert.risk_level.upper()} ALERT*\n\n{alert.message}"
        
        async with httpx.AsyncClient() as client:
            for user in users:
                try:
                    await client.post(
                        f"https://api.telegram.org/bot{bot_token}/sendMessage",
                        json={
                            "chat_id": user.telegram_chat_id,
                            "text": message,
                            "parse_mode": "Markdown"
                        },
                        timeout=5
                    )
                except Exception as e:
                    logger.error(f"Failed to send telegram alert to {user.id}: {e}")

async def get_active_alerts(db: AsyncSession, company_id: uuid.UUID) -> List[Alert]:
    result = await db.execute(
        select(Alert).where(
            Alert.company_id == company_id,
            Alert.acknowledged_at.is_(None)
        ).order_by(Alert.triggered_at.desc())
    )
    return list(result.scalars().all())

async def trigger_alert(
    db: AsyncSession,
    company_id: uuid.UUID,
    type: str,
    risk_level: str,
    message: str,
    dedup_key: str,
    cooldown_hours: int = 24,
    notifiers: List[Notifier] = None
):
    if notifiers is None:
        notifiers = [LoggingNotifier()]

    # Deduplication check
    result = await db.execute(
        select(Alert).where(
            Alert.company_id == company_id,
            Alert.dedup_key == dedup_key
        ).order_by(Alert.triggered_at.desc()).limit(1)
    )
    last_alert = result.scalars().first()

    now = datetime.now(timezone.utc)
    if last_alert:
        # Check cooldown
        if last_alert.cooldown_until and last_alert.cooldown_until > now:
            return None # Skip, still in cooldown
        if last_alert.acknowledged_at is None:
            # Already active and unacknowledged, don't re-trigger unless cooldown logic dictates
            return None

    # Create new alert
    alert = Alert(
        company_id=company_id,
        type=type,
        risk_level=risk_level,
        message=message,
        dedup_key=dedup_key,
        triggered_at=now,
        cooldown_until=now + timedelta(hours=cooldown_hours)
    )
    
    db.add(alert)
    await db.flush()

    for notifier in notifiers:
        try:
            await notifier.notify(alert)
        except Exception as e:
            logger.error(f"Failed to send notification via {notifier}: {e}")

    return alert

async def check_financial_alerts(db: AsyncSession, company_id: uuid.UUID):
    notifiers = [LoggingNotifier(), TelegramNotifier(db)]
    from app.core.i18n import translate
    # Try to find owner's preferred language for the company alerts
    from app.db.models import User, Company
    
    company = await db.get(Company, company_id)
    if not company:
        return
        
    result = await db.execute(select(User).where(User.company_id == company_id, User.role == "owner").limit(1))
    owner = result.scalars().first()
    lang = owner.preferred_language if owner and owner.preferred_language else company.default_language

    # 1. Check Cash Runway
    cf = await calculate_cashflow(db, company_id)
    if cf.runway_days is not None and cf.runway_days < company.alert_runway_threshold_days:
        await trigger_alert(
            db, company_id,
            type="financial",
            risk_level="warning",
            message=translate("alert_cash_runway", lang, days=cf.runway_days),
            dedup_key="cash_runway_low",
            notifiers=notifiers
        )
        
    # 2. Check overall ROI
    # Use PnL for the last 30 days
    start_date = datetime.now(timezone.utc).date() - timedelta(days=30)
    pnl = await calculate_pnl(db, company_id, start_date=start_date, end_date=datetime.now(timezone.utc).date())
    
    # ROI = Net Profit / Ad Spend
    roi = Decimal("0")
    if pnl.ad_spend > 0:
        roi = pnl.net_profit / pnl.ad_spend * Decimal("100")
        
    if roi < company.alert_roi_threshold:
        await trigger_alert(
            db, company_id,
            type="financial",
            risk_level="warning",
            message=translate("alert_roi_negative", lang, roi=roi),
            dedup_key="roi_negative_30d",
            notifiers=notifiers
        )



