from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Tuple
from datetime import date
import uuid
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.pnl import calculate_pnl
from app.services.cashflow import calculate_cashflow
from app.db.models import CampaignRunStat

def normalize_margin(margin: Optional[Decimal]) -> Decimal:
    """
    Normalizes Margin (0 to 0.20+) to a score of 0 to 100.
    - < 0% margin = 0
    - > 20% margin = 100
    - between 0% and 20% = linear scale (margin * 500)
    """
    if margin is None or margin < 0:
        return Decimal("0")
    if margin >= Decimal("0.20"):
        return Decimal("100")
    return margin * Decimal("500")

def normalize_runway(runway_days: Optional[int]) -> Decimal:
    """
    Normalizes Cash Runway (0 to 180+ days) to a score of 0 to 100.
    - < 30 days = 0
    - > 180 days = 100
    - between 30 and 180 = linear scale ((days - 30) / 150 * 100)
    """
    if runway_days is None or runway_days < 30:
        return Decimal("0")
    if runway_days >= 180:
        return Decimal("100")
    return Decimal(runway_days - 30) / Decimal("150") * Decimal("100")

def calculate_trend_score(current_margin: Optional[Decimal], previous_margin: Optional[Decimal]) -> Decimal:
    """
    Compares current vs previous margin.
    Neutral (no change or no data) = 50.
    +5% improvement = 100
    -5% decline = 0
    """
    if current_margin is None or previous_margin is None:
        return Decimal("50")
    diff = current_margin - previous_margin
    # Scale: -0.05 to +0.05 maps to 0 to 100
    score = Decimal("50") + (diff * Decimal("1000"))
    if score > 100:
        return Decimal("100")
    if score < 0:
        return Decimal("0")
    return score

async def get_health_score(
    db: AsyncSession, 
    company_id: uuid.UUID,
    as_of_date: Optional[date] = None
) -> int:
    """
    Calculates the Health Score (0..100) based on:
    - 40% Margin Score
    - 40% Runway Score
    - 20% Trend Score (Month over month margin change)
    """
    if not as_of_date:
        as_of_date = date.today()
        
    pnl = await calculate_pnl(db, company_id, end_date=as_of_date)
    cashflow = await calculate_cashflow(db, company_id, as_of_date=as_of_date)
    
    # We ideally need previous month's PnL for trend score, but keeping it simple for MVP if missing
    margin_score = normalize_margin(pnl.margin)
    runway_score = normalize_runway(cashflow.runway_days)
    
    # Simple static trend score for now to avoid multiple deep queries
    trend_score = Decimal("50")
    
    health_score = (Decimal("0.4") * margin_score) + (Decimal("0.4") * runway_score) + (Decimal("0.2") * trend_score)
    
    final_score = int(health_score.to_integral_value(rounding=ROUND_HALF_UP))
    return max(0, min(100, final_score))

async def get_spend_discrepancy(
    db: AsyncSession,
    company_id: uuid.UUID,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
) -> Tuple[Decimal, Decimal, Decimal]:
    """
    Diagnostics: Discrepancy between Tracker Spend (campaign_run_stats) and Actual Spend (transactions).
    Returns (tracker_spend, actual_spend, diff)
    """
    pnl = await calculate_pnl(db, company_id, start_date=start_date, end_date=end_date)
    actual_spend = pnl.ad_spend
    
    query = sa.select(sa.func.sum(CampaignRunStat.spend * CampaignRunStat.fx_rate_to_base))\
        .where(CampaignRunStat.company_id == company_id)
        
    if start_date:
        query = query.where(CampaignRunStat.stat_date >= start_date)
    if end_date:
        query = query.where(CampaignRunStat.stat_date <= end_date)
        
    res = await db.execute(query)
    val = res.scalar()
    tracker_spend = Decimal(val) if val is not None else Decimal("0")
    tracker_spend = tracker_spend.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    
    diff = tracker_spend - actual_spend
    return (tracker_spend, actual_spend, diff)

def calculate_roi(revenue: Decimal, cost: Decimal) -> Decimal:
    """Calculates ROI = (Revenue - Cost) / Cost. Safe division."""
    if cost == 0:
        return Decimal("0.0000")
    return ((revenue - cost) / cost).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

def calculate_roas(revenue: Decimal, spend: Decimal) -> Decimal:
    """Calculates ROAS = Revenue / Spend. Safe division."""
    if spend == 0:
        return Decimal("0.0000")
    return (revenue / spend).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

def calculate_margin(revenue: Decimal, cost: Decimal) -> Decimal:
    """Calculates Margin = (Revenue - Cost) / Revenue. Safe division."""
    if revenue == 0:
        return Decimal("0.0000")
    return ((revenue - cost) / revenue).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
