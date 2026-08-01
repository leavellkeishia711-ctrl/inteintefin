from datetime import date, timedelta
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models import FxRate
from app.core.money import q

async def get_fx_rate(session: AsyncSession, from_currency: str, to_currency: str, target_date: date) -> Decimal | None:
    """
    Получить курс. Если валюты совпадают — 1.0.
    Точная дата -> ближайшая предыдущая (до 7 дней назад) -> None
    """
    if from_currency == to_currency:
        return Decimal("1.00000000")
        
    stmt = (
        select(FxRate)
        .where(
            FxRate.base_currency == from_currency,
            FxRate.quote_currency == to_currency,
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
        
    # Пытаемся найти обратный курс
    stmt_inverse = (
        select(FxRate)
        .where(
            FxRate.base_currency == to_currency,
            FxRate.quote_currency == from_currency,
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
        
    return None

async def resolve_fx_rate(session: AsyncSession, from_currency: str, to_currency: str, target_date: date) -> Decimal:
    """
    Как get_fx_rate, но бросает ошибке, если курс не найден.
    """
    rate = await get_fx_rate(session, from_currency, to_currency, target_date)
    if rate is None:
        raise ValueError(f"FX rate not found for {from_currency}->{to_currency} around {target_date}")
    return rate

# celery.task - заглушка, так как Celery не настроен полностью
def fetch_ecb_rates():
    pass
