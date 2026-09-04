import logging
import uuid
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.db.models import Transaction, CampaignRunStat
from app.services.alerts import trigger_alert, LoggingNotifier, TelegramNotifier

logger = logging.getLogger(__name__)

async def monitor_stalled_data(db: AsyncSession, company_id: uuid.UUID):
    """
    Checks if there has been any new data ingested within the last `alert_stalled_data_days` days.
    If not, triggers an operational alert.
    """
    from app.db.models import Company
    company = await db.get(Company, company_id)
    if not company:
        return
        
    days_threshold = company.alert_stalled_data_days
    now = datetime.now(timezone.utc)
    threshold_date = now - timedelta(days=days_threshold)
    
    # Check latest transaction
    result = await db.execute(
        select(func.max(Transaction.created_at)).where(Transaction.company_id == company_id)
    )
    last_tx_date = result.scalar()
    
    # Check latest campaign run stat
    result = await db.execute(
        select(func.max(CampaignRunStat.created_at)).where(CampaignRunStat.company_id == company_id)
    )
    last_stat_date = result.scalar()
    
    # Alert if BOTH transactions and campaign stats are stale
    # (Or just if transactions are stale, but let's check both for robust monitoring)
    stalled = False
    
    if last_tx_date is None or last_tx_date < threshold_date:
        if last_stat_date is None or last_stat_date < threshold_date:
            stalled = True
            
    if stalled:
        
        from app.core.i18n import translate
        from app.db.models import User
        
        result = await db.execute(select(User).where(User.company_id == company_id, User.role == "owner").limit(1))
        owner = result.scalars().first()
        lang = owner.preferred_language if owner and owner.preferred_language else "en"

        await trigger_alert(
            db, company_id,
            type="operational",
            risk_level="warning",
            message=translate("alert_stalled_data", lang, days=days_threshold),
            dedup_key=f"stalled_data_{days_threshold}d",
            cooldown_hours=48, # Don't alert every day if it's already triggered
            notifiers=[LoggingNotifier(), TelegramNotifier(db)]
        )

    from app.db.models.connectors import ConnectorConfig
    # Monitor Connectors
    result = await db.execute(select(ConnectorConfig).where(ConnectorConfig.company_id == company_id))
    connectors = result.scalars().all()
    
    for conn in connectors:
        if conn.status == 'active':
            # Check if it has a successful sync
            if conn.last_successful_sync is None:
                await trigger_alert(
                    db, company_id,
                    type='operational',
                    risk_level='warning',
                    message=f"Connector {conn.connector_name} is active but has no successful syncs.",
                    dedup_key=f"connector_no_sync_{conn.id}",
                    cooldown_hours=24,
                    notifiers=[LoggingNotifier(), TelegramNotifier(db)]
                )
            else:
                # DQ alert: consider it stale if 3x the interval has passed without a successful sync
                stale_threshold_minutes = conn.sync_interval_minutes * 3
                # Minimum threshold of 2 hours just to avoid false positives on quick intervals
                stale_threshold_minutes = max(stale_threshold_minutes, 120)
                
                delta_minutes = (now - conn.last_successful_sync).total_seconds() / 60
                
                if delta_minutes > stale_threshold_minutes:
                    await trigger_alert(
                        db, company_id,
                        type='operational',
                        risk_level='warning',
                        message=f"Data Quality Alert: Connector {conn.connector_name} is stale. Last successful sync was {int(delta_minutes/60)} hours ago.",
                        dedup_key=f"connector_stale_dq_{conn.id}",
                        cooldown_hours=24,
                        notifiers=[LoggingNotifier(), TelegramNotifier(db)]
                    )
        elif conn.status in ('failing', 'unauthorized'):
            await trigger_alert(
                db, company_id,
                type='operational',
                risk_level='critical',
                message=f"Connector {conn.connector_name} is in status {conn.status}.",
                dedup_key=f"connector_status_{conn.id}_{conn.status}",
                cooldown_hours=12,
                notifiers=[LoggingNotifier(), TelegramNotifier(db)]
            )
