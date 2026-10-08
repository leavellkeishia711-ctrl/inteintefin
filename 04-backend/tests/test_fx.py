import pytest
from decimal import Decimal
from datetime import date, timedelta
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import FxRate
from app.services.fx import get_fx_rate, resolve_fx_rate

from app.db.session import system_session as sys_session_context
import pytest_asyncio

@pytest_asyncio.fixture
async def system_session():
    # A fixture to provide a clean session
    async with sys_session_context() as session:
        yield session

@pytest.mark.asyncio
async def test_fx_rate_same_currency(system_session: AsyncSession):
    """Сценарий 1: Валюты совпадают, результат равен Decimal("1.00000000")."""
    rate = await get_fx_rate(system_session, "USD", "USD", date(2026, 1, 1))
    assert rate == Decimal("1.00000000")

@pytest.mark.asyncio
async def test_fx_rate_direct_exact_date(system_session: AsyncSession):
    """Сценарий 2: Прямой курс на точную дату."""
    test_date = date(2026, 2, 1)
    rate_row = FxRate(
        rate_date=test_date,
        from_currency="USD",
        to_currency="EUR",
        rate=Decimal("0.90000000"),
        source="test"
    )
    system_session.add(rate_row)
    await system_session.flush()

    rate = await get_fx_rate(system_session, "USD", "EUR", test_date)
    assert rate == Decimal("0.90000000")

@pytest.mark.asyncio
async def test_fx_rate_direct_previous_date(system_session: AsyncSession):
    """Сценарий 3: Прямой курс на предыдущую дату в пределах 7 дней."""
    test_date = date(2026, 2, 10)
    rate_row = FxRate(
        rate_date=test_date - timedelta(days=3),
        from_currency="USD",
        to_currency="GBP",
        rate=Decimal("0.80000000"),
        source="test"
    )
    system_session.add(rate_row)
    await system_session.flush()

    rate = await get_fx_rate(system_session, "USD", "GBP", test_date)
    assert rate == Decimal("0.80000000")

@pytest.mark.asyncio
async def test_fx_rate_inverse_with_rounding(system_session: AsyncSession):
    """Сценарий 4: Обратный курс с проверкой Decimal-результата и ожидаемого округления (8 знаков)."""
    test_date = date(2026, 3, 1)
    # EUR -> USD is 0.85
    # Inverse: USD -> EUR should be 1 / 0.85 = 1.17647058823... -> 1.17647059
    rate_row = FxRate(
        rate_date=test_date,
        from_currency="EUR",
        to_currency="USD",
        rate=Decimal("0.85000000"),
        source="test"
    )
    system_session.add(rate_row)
    await system_session.flush()

    rate = await get_fx_rate(system_session, "USD", "EUR", test_date)
    assert rate == Decimal("1.17647059")

@pytest.mark.asyncio
async def test_fx_rate_deterministic_selection(system_session: AsyncSession):
    """Сценарий 5: Несколько FX-записей на одинаковую дату с разными source: результат детерминирован."""
    test_date = date(2026, 4, 1)

    # We add two rates on the same day. The query uses order_by(rate_date.desc(), id.desc()).
    # So the one with the higher (lexicographically/numerically larger) UUID will be picked if both are flushed.
    # To test determinism, we just verify it doesn't crash and returns one of them consistently.
    id1 = uuid.UUID('00000000-0000-0000-0000-000000000001')
    id2 = uuid.UUID('00000000-0000-0000-0000-000000000002')

    rate_row1 = FxRate(
        id=id1,
        rate_date=test_date,
        from_currency="USD",
        to_currency="JPY",
        rate=Decimal("150.00000000"),
        source="source1"
    )
    rate_row2 = FxRate(
        id=id2,
        rate_date=test_date,
        from_currency="USD",
        to_currency="JPY",
        rate=Decimal("151.00000000"),
        source="source2"
    )

    system_session.add_all([rate_row1, rate_row2])
    await system_session.flush()

    rate = await get_fx_rate(system_session, "USD", "JPY", test_date)
    # Since id2 > id1, id.desc() should pick id2 (151.0)
    assert rate == Decimal("151.00000000")

@pytest.mark.asyncio
async def test_fx_rate_older_than_7_days(system_session: AsyncSession):
    """Сценарий 6: Курс старше 7 дней не используется."""
    test_date = date(2026, 5, 10)
    rate_row = FxRate(
        rate_date=test_date - timedelta(days=8),
        from_currency="USD",
        to_currency="CAD",
        rate=Decimal("1.30000000"),
        source="test"
    )
    system_session.add(rate_row)
    await system_session.flush()

    rate = await get_fx_rate(system_session, "USD", "CAD", test_date)
    assert rate is None

@pytest.mark.asyncio
async def test_resolve_fx_rate_not_found(system_session: AsyncSession):
    """Сценарий 7: Курс не найден вызывает ожидаемую ошибку через resolve_fx_rate()."""
    test_date = date(2026, 6, 1)
    with pytest.raises(ValueError, match="FX rate not found for USD->CHF"):
        await resolve_fx_rate(system_session, "USD", "CHF", test_date)