from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Any, Optional
from datetime import date, timedelta
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
import uuid

from app.db.models import Transaction
from app.db.models.system import PartnerPayout

from app.schemas.types import Money

class CashFlowResult(BaseModel):
    transaction_balance: Money
    held_payouts: Money
    available_balance: Money
    average_daily_spend_30d: Optional[Money]
    runway_days: Optional[int]

def round_money(val: Decimal) -> Decimal:
    return val.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

async def calculate_cashflow(
    db: AsyncSession, 
    company_id: uuid.UUID,
    as_of_date: Optional[date] = None
) -> CashFlowResult:
    """
    Calculates cash flow, available balance, and runway based on 30-day historical average daily spend.
    """
    if as_of_date is None:
        as_of_date = date.today()
        
    # 1. Calculate total transaction balance
    balance_query = sa.select(Transaction.type, sa.func.sum(Transaction.amount * Transaction.fx_rate_to_base).label("total"))\
        .where(Transaction.company_id == company_id)\
        .where(Transaction.occurred_on <= as_of_date)\
        .where(Transaction.deleted_at.is_(None))\
        .group_by(Transaction.type)
        
    res_bal = await db.execute(balance_query)
    
    total_in = Decimal("0")
    total_out = Decimal("0")
    
    for row in res_bal.fetchall():
        if row.type == "income":
            total_in += Decimal(row.total or 0)
        elif row.type == "expense":
            total_out += Decimal(row.total or 0)
            
    transaction_balance = total_in - total_out
    
    # 2. Calculate held payouts (booked/in_hold)
    held_query = sa.select(sa.func.sum(PartnerPayout.amount * PartnerPayout.fx_rate_to_base))\
        .where(PartnerPayout.company_id == company_id)\
        .where(PartnerPayout.status.in_(["booked", "in_hold"]))\
        .where(PartnerPayout.deleted_at.is_(None))\
        .where(PartnerPayout.booked_on <= as_of_date)
        
    res_held = await db.execute(held_query)
    held_val = res_held.scalar()
    held_payouts = Decimal(held_val) if held_val is not None else Decimal("0")
    
    available_balance = transaction_balance - held_payouts
    
    # 3. Calculate 30-day historical average daily spend
    window_start = as_of_date - timedelta(days=30)
    spend_query = sa.select(sa.func.sum(Transaction.amount * Transaction.fx_rate_to_base))\
        .where(Transaction.company_id == company_id)\
        .where(Transaction.type == "expense")\
        .where(Transaction.occurred_on > window_start)\
        .where(Transaction.occurred_on <= as_of_date)\
        .where(Transaction.deleted_at.is_(None))
        
    res_spend = await db.execute(spend_query)
    spend_val = res_spend.scalar()
    spend_30d = Decimal(spend_val) if spend_val is not None else Decimal("0")
    
    if spend_30d > 0:
        avg_daily_spend = spend_30d / Decimal("30")
        runway_days = int((available_balance / avg_daily_spend).to_integral_value(rounding=ROUND_HALF_UP))
        if runway_days < 0:
            runway_days = 0 # No negative runway
    else:
        avg_daily_spend = None
        runway_days = None
        
    return CashFlowResult(
        transaction_balance=round_money(transaction_balance),
        held_payouts=round_money(held_payouts),
        available_balance=round_money(available_balance),
        average_daily_spend_30d=round_money(avg_daily_spend) if avg_daily_spend is not None else None,
        runway_days=runway_days
    )
