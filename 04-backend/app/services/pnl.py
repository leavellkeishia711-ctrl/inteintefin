from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Any, Optional
from datetime import date
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
import uuid

from app.db.models import Transaction

from app.schemas.types import Money, Ratio

class PnLResult(BaseModel):
    revenue: Money
    ad_spend: Money
    gross_profit: Money
    consumables: Money
    operating_expenses: Money
    ebitda: Money
    depreciation: Money
    ebit: Money
    interest: Money
    ebt: Money
    tax: Money
    net_profit: Money
    gross_margin: Optional[Ratio]
    ebitda_margin: Optional[Ratio]
    ebit_margin: Optional[Ratio]
    ebt_margin: Optional[Ratio]
    net_margin: Optional[Ratio]
    margin: Optional[Ratio] # keeping for backwards compatibility / tests

def round_money(val: Decimal) -> Decimal:
    return val.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

def round_ratio(val: Decimal) -> Decimal:
    return val.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

async def calculate_pnl(
    db: AsyncSession, 
    company_id: uuid.UUID,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    team_id: Optional[uuid.UUID] = None,
    user_id: Optional[uuid.UUID] = None
) -> PnLResult:
    
    query = sa.select(
        Transaction.category, 
        sa.func.sum(Transaction.amount * Transaction.fx_rate_to_base).label('total')
    ).where(Transaction.company_id == company_id)

    if start_date:
        query = query.where(Transaction.occurred_on >= start_date)
    if end_date:
        query = query.where(Transaction.occurred_on <= end_date)
    if team_id:
        query = query.where(Transaction.team_id == team_id)
    # user_id typically filtering? user_id is the user fetching. 
    # Actually, in our schema, transactions don't have user_id, only team_id.
    # So we ignore user_id for transaction aggregations unless there's an assigned buyer.

    query = query.group_by(Transaction.category)
    result = await db.execute(query)
    rows = result.all()
    
    data = {row.category: Decimal(str(row.total or 0)) for row in rows}
    
    raw_rev = data.get('payout_incoming', Decimal(0)) + data.get('sales', Decimal(0))
    revenue = round_money(raw_rev)
    raw_ad = data.get('ad_spend', Decimal(0))
    ad_spend = round_money(raw_ad)
    
    raw_gp = raw_rev - raw_ad
    gross_profit = round_money(raw_gp)
    
    raw_cons = data.get('consumables', Decimal(0))
    consumables = round_money(raw_cons)
    raw_opex = data.get('salary', Decimal(0)) + data.get('infra', Decimal(0)) + data.get('other', Decimal(0)) + data.get('payout_outgoing', Decimal(0))
    operating_expenses = round_money(raw_opex)
    
    raw_ebitda = raw_gp - raw_cons - raw_opex
    ebitda = round_money(raw_ebitda)
    
    raw_dep = data.get('depreciation', Decimal(0))
    depreciation = round_money(raw_dep)
    
    raw_ebit = raw_ebitda - raw_dep
    ebit = round_money(raw_ebit)
    
    raw_int = data.get('interest', Decimal(0))
    interest = round_money(raw_int)
    
    raw_ebt = raw_ebit - raw_int
    ebt = round_money(raw_ebt)
    
    raw_tax = data.get('tax', Decimal(0))
    tax = round_money(raw_tax)
    
    raw_np = raw_ebt - raw_tax
    net_profit = round_money(raw_np)
    
    # Calculate margins safely
    def safe_margin(profit: Decimal, rev: Decimal) -> Optional[Decimal]:
        if rev > 0:
            return round_ratio(profit / rev)
        return None
        
    gross_margin = safe_margin(raw_gp, raw_rev)
    ebitda_margin = safe_margin(raw_ebitda, raw_rev)
    ebit_margin = safe_margin(raw_ebit, raw_rev)
    ebt_margin = safe_margin(raw_ebt, raw_rev)
    net_margin = safe_margin(raw_np, raw_rev)
    
    return PnLResult(
        revenue=revenue,
        ad_spend=ad_spend,
        gross_profit=gross_profit,
        consumables=consumables,
        operating_expenses=operating_expenses,
        ebitda=ebitda,
        depreciation=depreciation,
        ebit=ebit,
        interest=interest,
        ebt=ebt,
        tax=tax,
        net_profit=net_profit,
        gross_margin=gross_margin,
        ebitda_margin=ebitda_margin,
        ebit_margin=ebit_margin,
        ebt_margin=ebt_margin,
        net_margin=net_margin,
        margin=net_margin # For tests
    )


