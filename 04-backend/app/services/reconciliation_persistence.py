import uuid
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging

from app.db.models.campaigns import CampaignRunStat, CampaignRunReconciliation
from app.services.reconciliation import reconcile_stat_group, ReconciliationDecision

logger = logging.getLogger(__name__)

async def upsert_reconciliation_for_group(
    session: AsyncSession,
    company_id: uuid.UUID,
    campaign_run_id: uuid.UUID,
    stat_date: date
) -> CampaignRunReconciliation:
    """
    Loads all active stats for a given (company_id, campaign_run_id, stat_date),
    reconciles them using the pure logic, and performs an atomic upsert 
    on CampaignRunReconciliation.
    
    Preconditions:
    - session is tenant-scoped (RLS active).
    - caller manages commit/flush (no commit inside this function).
    """
    
    # Load all active stats for the group
    stmt = select(CampaignRunStat).where(
        CampaignRunStat.company_id == company_id,
        CampaignRunStat.campaign_run_id == campaign_run_id,
        CampaignRunStat.stat_date == stat_date,
        CampaignRunStat.deleted_at.is_(None)
    )
    result = await session.execute(stmt)
    stats = result.scalars().all()
    
    # Compute decision
    decision: ReconciliationDecision = reconcile_stat_group(stats)
    
    # Upsert into CampaignRunReconciliation
    from sqlalchemy.dialects.postgresql import insert
    import sqlalchemy as sa
    
    insert_stmt = (
        insert(CampaignRunReconciliation)
        .values(
            company_id=company_id,
            campaign_run_id=campaign_run_id,
            stat_date=stat_date,
            status=decision.status,
            chosen_source=decision.chosen_source,
            chosen_stat_id=decision.chosen_stat_id,
            canonical_spend=decision.canonical_spend,
            canonical_revenue=decision.canonical_revenue,
            canonical_clicks=decision.canonical_clicks,
            canonical_impressions=decision.canonical_impressions,
            canonical_conversions=decision.canonical_conversions,
            canonical_currency=decision.canonical_currency,
            observed_source_count=decision.observed_source_count,
            conflict_fields=decision.conflict_fields,
            source_snapshot=decision.source_snapshot,
            decision_reason=decision.decision_reason
        )
    )
    
    upsert_stmt = insert_stmt.on_conflict_do_update(
        index_elements=[
            CampaignRunReconciliation.company_id,
            CampaignRunReconciliation.campaign_run_id,
            CampaignRunReconciliation.stat_date
        ],
        index_where=sa.text("deleted_at IS NULL"),
        set_={
            CampaignRunReconciliation.status: insert_stmt.excluded.status,
            CampaignRunReconciliation.chosen_source: insert_stmt.excluded.chosen_source,
            CampaignRunReconciliation.chosen_stat_id: insert_stmt.excluded.chosen_stat_id,
            CampaignRunReconciliation.canonical_spend: insert_stmt.excluded.canonical_spend,
            CampaignRunReconciliation.canonical_revenue: insert_stmt.excluded.canonical_revenue,
            CampaignRunReconciliation.canonical_clicks: insert_stmt.excluded.canonical_clicks,
            CampaignRunReconciliation.canonical_impressions: insert_stmt.excluded.canonical_impressions,
            CampaignRunReconciliation.canonical_conversions: insert_stmt.excluded.canonical_conversions,
            CampaignRunReconciliation.canonical_currency: insert_stmt.excluded.canonical_currency,
            CampaignRunReconciliation.observed_source_count: insert_stmt.excluded.observed_source_count,
            CampaignRunReconciliation.conflict_fields: insert_stmt.excluded.conflict_fields,
            CampaignRunReconciliation.source_snapshot: insert_stmt.excluded.source_snapshot,
            CampaignRunReconciliation.decision_reason: insert_stmt.excluded.decision_reason,
            CampaignRunReconciliation.updated_at: sa.func.now(),
        }
    ).returning(CampaignRunReconciliation)
    
    upsert_res = await session.execute(upsert_stmt, execution_options={"populate_existing": True})
    return upsert_res.scalars().first()
