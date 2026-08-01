from decimal import Decimal
import uuid
from typing import List, Optional
from datetime import date
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import AdAccount, Consumable, CampaignRun, CampaignRunStat

async def get_ad_account_cost(db: AsyncSession, ad_account_id: uuid.UUID) -> Decimal:
    """
    Calculate the total cost of all consumables associated with an ad_account.
    Returns value in the base currency of the company (using fx_rate_to_base at time of purchase).
    """
    result = await db.execute(
        sa.select(sa.func.sum(Consumable.cost * Consumable.fx_rate_to_base))
        .where(Consumable.ad_account_id == ad_account_id)
        .where(Consumable.deleted_at.is_(None))
    )
    total = result.scalar()
    if total is None:
        return Decimal('0.0000')
    return Decimal(total)

async def upsert_campaign_run_stat(
    db: AsyncSession,
    company_id: uuid.UUID,
    campaign_run_id: uuid.UUID,
    stat_date: date,
    source: str,
    external_id: str,
    spend: Decimal,
    revenue: Decimal,
    currency: str,
    fx_rate_to_base: Decimal
) -> CampaignRunStat:
    """
    Upserts a CampaignRunStat, ensuring idempotency based on (company_id, campaign_run_id, stat_date, source, external_id).
    If it exists, updates spend and revenue.
    """
    from sqlalchemy.dialects.postgresql import insert
    
    stmt = insert(CampaignRunStat).values(
        company_id=company_id,
        campaign_run_id=campaign_run_id,
        stat_date=stat_date,
        spend=spend,
        revenue=revenue,
        currency=currency,
        fx_rate_to_base=fx_rate_to_base,
        source=source,
        external_id=external_id
    )
    
    update_stmt = stmt.on_conflict_do_update(
        index_elements=["company_id", "campaign_run_id", "stat_date", "source", "external_id"],
        index_where=sa.text("external_id IS NOT NULL"),
        set_={
            "spend": stmt.excluded.spend,
            "revenue": stmt.excluded.revenue,
            "fx_rate_to_base": stmt.excluded.fx_rate_to_base
        }
    ).returning(CampaignRunStat)
    
    result = await db.execute(update_stmt.execution_options(populate_existing=True))
    stat = result.scalar_one()
    
    from app.services.audit import record_system_audit
    await record_system_audit(
        session=db,
        company_id=company_id,
        task_name="campaign_sync", # Default or should be passed
        entity_type="campaign_run_stat",
        entity_id=stat.id,
        action="upsert",
        old_state=None,
        new_state={"spend": str(spend), "revenue": str(revenue)}
    )
    
    return stat

async def get_campaign_stats(
    db: AsyncSession,
    company_id: uuid.UUID,
    date_from: date,
    date_to: date,
    ad_account_id: uuid.UUID | None = None,
    campaign_run_id: uuid.UUID | None = None,
    limit: int = 100
):
    stmt = sa.select(CampaignRunStat).where(
        CampaignRunStat.company_id == company_id,
        CampaignRunStat.deleted_at.is_(None),
        CampaignRunStat.stat_date >= date_from,
        CampaignRunStat.stat_date <= date_to
    )
    if campaign_run_id:
        stmt = stmt.where(CampaignRunStat.campaign_run_id == campaign_run_id)
    if ad_account_id:
        # Join with CampaignRun to filter by ad_account_id
        stmt = stmt.join(CampaignRun, CampaignRunStat.campaign_run_id == CampaignRun.id)
        stmt = stmt.where(CampaignRun.ad_account_id == ad_account_id)
        
    stmt = stmt.order_by(CampaignRunStat.stat_date.desc()).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()

