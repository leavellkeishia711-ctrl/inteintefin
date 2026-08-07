from decimal import Decimal
import uuid
from typing import List, Optional
from datetime import date
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import AdAccount, Consumable, CampaignRun, CampaignRunStat

async def get_ad_account_cost(db: AsyncSession, company_id: uuid.UUID, ad_account_id: uuid.UUID, date_from: Optional[date] = None, date_to: Optional[date] = None) -> Decimal:
    """
    Calculate the total cost of all consumables associated with an ad_account, PLUS the ad spend.
    Returns value in the base currency of the company (using fx_rate_to_base).
    Explicitly checks company_id to enforce tenant isolation independently of RLS.
    """
    # 1. Consumables cost
    consumables_stmt = sa.select(sa.func.sum(Consumable.cost * Consumable.fx_rate_to_base)).where(
        Consumable.ad_account_id == ad_account_id,
        Consumable.company_id == company_id,
        Consumable.deleted_at.is_(None)
    )
    if date_from:
        consumables_stmt = consumables_stmt.where(Consumable.purchased_on >= date_from)
    if date_to:
        consumables_stmt = consumables_stmt.where(Consumable.purchased_on <= date_to)

    cons_result = await db.execute(consumables_stmt)
    cons_total = cons_result.scalar() or Decimal('0.0000')

    # 2. Ad Spend cost
    spend_stmt = sa.select(sa.func.sum(CampaignRunStat.spend * CampaignRunStat.fx_rate_to_base)).join(
        CampaignRun, CampaignRunStat.campaign_run_id == CampaignRun.id
    ).where(
        CampaignRun.ad_account_id == ad_account_id,
        CampaignRun.company_id == company_id,
        CampaignRunStat.company_id == company_id,
        CampaignRun.deleted_at.is_(None)
    )
    if date_from:
        spend_stmt = spend_stmt.where(CampaignRunStat.stat_date >= date_from)
    if date_to:
        spend_stmt = spend_stmt.where(CampaignRunStat.stat_date <= date_to)

    spend_result = await db.execute(spend_stmt)
    spend_total = spend_result.scalar() or Decimal('0.0000')

    return Decimal(cons_total) + Decimal(spend_total)

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
        CampaignRunStat.stat_date >= date_from,
        CampaignRunStat.stat_date <= date_to
    )
    if campaign_run_id:
        stmt = stmt.where(CampaignRunStat.campaign_run_id == campaign_run_id)
    if ad_account_id:
        # Join with CampaignRun to filter by ad_account_id
        stmt = stmt.join(CampaignRun, CampaignRunStat.campaign_run_id == CampaignRun.id)
        stmt = stmt.where(
            CampaignRun.ad_account_id == ad_account_id,
            CampaignRun.company_id == company_id
        )
        
    stmt = stmt.order_by(CampaignRunStat.stat_date.desc()).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()

