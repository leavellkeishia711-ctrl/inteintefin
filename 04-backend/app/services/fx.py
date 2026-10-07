from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models import FxRate
from app.core.money import q

async def get_fx_rate(session: AsyncSession, from_currency: str, to_currency: str, target_date: date) -> Decimal | None:
    """
    1. Direct search
    2. Inverse search
    3. Triangulation via EUR
    """
    if from_currency == to_currency:
        return Decimal("1.00000000")
        
    stmt = (
        select(FxRate)
        .where(
            FxRate.from_currency == from_currency,
            FxRate.to_currency == to_currency,
            FxRate.rate_date <= target_date,
            FxRate.rate_date >= target_date - timedelta(days=7)
        )
        .order_by(FxRate.rate_date.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    rate_row = result.scalars().first()
    
    if rate_row:
        return rate_row.rate
        
    stmt_inverse = (
        select(FxRate)
        .where(
            FxRate.from_currency == to_currency,
            FxRate.to_currency == from_currency,
            FxRate.rate_date <= target_date,
            FxRate.rate_date >= target_date - timedelta(days=7)
        )
        .order_by(FxRate.rate_date.desc())
        .limit(1)
    )
    result_inv = await session.execute(stmt_inverse)
    rate_inv = result_inv.scalars().first()
    
    if rate_inv and rate_inv.rate != Decimal("0"):
        return Decimal("1.00000000") / rate_inv.rate
        
    if from_currency != "EUR" and to_currency != "EUR":
        stmt_tri = (
            select(FxRate)
            .where(
                FxRate.from_currency == "EUR",
                FxRate.to_currency.in_([from_currency, to_currency]),
                FxRate.source == "ecb",
                FxRate.rate_date <= target_date,
                FxRate.rate_date >= target_date - timedelta(days=7)
            )
            .order_by(FxRate.rate_date.desc())
        )
        result_tri = await session.execute(stmt_tri)
        tri_rows = result_tri.scalars().all()
        
        rates_by_date = {}
        for r in tri_rows:
            if r.rate_date not in rates_by_date:
                rates_by_date[r.rate_date] = {}
            rates_by_date[r.rate_date][r.to_currency] = r.rate
            
        for d in sorted(rates_by_date.keys(), reverse=True):
            day_rates = rates_by_date[d]
            if from_currency in day_rates and to_currency in day_rates:
                rate_from = day_rates[from_currency]
                rate_to = day_rates[to_currency]
                if rate_from != Decimal("0"):
                    cross_rate = rate_to / rate_from
                    return cross_rate.quantize(Decimal("1.00000000"), rounding=ROUND_HALF_UP)
                    
    return None

async def resolve_fx_rate(session: AsyncSession, from_currency: str, to_currency: str, target_date: date) -> Decimal:
    rate = await get_fx_rate(session, from_currency, to_currency, target_date)
    if rate is None:
        raise ValueError(f"FX rate not found for {from_currency}->{to_currency} around {target_date}")
    return rate

def fetch_ecb_rates():
    pass
