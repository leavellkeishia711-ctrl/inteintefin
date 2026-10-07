import pytest
from datetime import date
from decimal import Decimal
import httpx
from unittest.mock import patch, AsyncMock
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.services.fx_ecb import parse_ecb_xml, sync_ecb_rates, ECB_URL
from app.db.models.finance import FxRate
from app.services.fx import get_fx_rate
from app.workers.tasks import celery_app

VALID_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<gesmes:Envelope xmlns:gesmes="http://www.gesmes.org/xml/2002-08-01" xmlns="http://www.ecb.int/vocabulary/2002-08-01/eurofxref">
    <gesmes:subject>Reference rates</gesmes:subject>
    <gesmes:Sender>
        <gesmes:name>European Central Bank</gesmes:name>
    </gesmes:Sender>
    <Cube>
        <Cube time="2026-10-06">
            <Cube currency="USD" rate="1.1000"/>
            <Cube currency="GBP" rate="0.8500"/>
        </Cube>
        <Cube time="2026-10-05">
            <Cube currency="USD" rate="1.0950"/>
            <Cube currency="GBP" rate="0.8400"/>
            <Cube currency="JPY" rate="149.00"/>
        </Cube>
    </Cube>
</gesmes:Envelope>"""

INVALID_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<gesmes:Envelope xmlns:gesmes="http://www.gesmes.org/xml/2002-08-01" xmlns="http://www.ecb.int/vocabulary/2002-08-01/eurofxref">
    <Cube>
        <Cube time="2026-10-06">
            <Cube currency="USD" rate="-1.1000"/>
            <Cube currency="GBP" rate="not-a-number"/>
            <Cube currency="RU" rate="100.0"/>
            <Cube currency="X" rate="100.0"/>
            <Cube currency="000" rate="100.0"/>
            <Cube currency="USD" rate="0"/>
        </Cube>
        <Cube time="invalid-date">
            <Cube currency="USD" rate="1.1000"/>
        </Cube>
    </Cube>
</gesmes:Envelope>"""


def test_parse_ecb_xml_valid():
    results, dates_count, skipped = parse_ecb_xml(VALID_XML)
    assert dates_count == 2
    assert skipped == 0
    assert len(results) == 5
    
    usd_06 = next(r for r in results if r["to_currency"] == "USD" and r["rate_date"] == date(2026, 10, 6))
    assert usd_06["rate"] == Decimal("1.1000")


def test_parse_ecb_xml_invalid():
    results, dates_count, skipped = parse_ecb_xml(INVALID_XML)
    assert dates_count == 1  # 2026-10-06 was parsed, invalid-date was skipped
    assert len(results) == 0
    assert skipped == 6 # all rates in 2026-10-06 are invalid


@pytest.mark.asyncio
@patch("app.services.fx_ecb.httpx.AsyncClient.get")
async def test_sync_ecb_rates_http_errors(mock_get, system_session_context):
    mock_get.side_effect = httpx.TimeoutException("Timeout")
    async with system_session_context() as session:
        async with session.begin():
            out = await sync_ecb_rates(session)
            assert out["fetched"] == 0
            assert out["inserted"] == 0

    mock_get.side_effect = None
    mock_get.return_value = httpx.Response(500)
    async with system_session_context() as session:
        async with session.begin():
            out = await sync_ecb_rates(session)
            assert out["fetched"] == 0

    mock_get.return_value = httpx.Response(301, headers={"Location": "foo"}) # Follow redirects false
    async with system_session_context() as session:
        async with session.begin():
            out = await sync_ecb_rates(session)
            assert out["fetched"] == 0

    mock_get.return_value = httpx.Response(200, headers={"Content-Length": "3000000"})
    async with system_session_context() as session:
        async with session.begin():
            out = await sync_ecb_rates(session)
            assert out["fetched"] == 0


@pytest.mark.asyncio
@patch("app.services.fx_ecb.httpx.AsyncClient.get")
async def test_sync_ecb_rates_idempotent_and_conflict(mock_get, system_session_context):
    mock_get.return_value = httpx.Response(200, content=VALID_XML)
    
    async with system_session_context() as session:
        async with session.begin():
            out1 = await sync_ecb_rates(session)
            assert out1["inserted"] == 5
            assert out1["conflicts"] == 0
            
    # Second run: Idempotent
    async with system_session_context() as session:
        async with session.begin():
            out2 = await sync_ecb_rates(session)
            assert out2["inserted"] == 0
            assert out2["conflicts"] == 5
            
    # Modify an existing one to test conflict (different value, same key)
    async with system_session_context() as session:
        async with session.begin():
            # Add conflicting manual row
            session.add(FxRate(
                rate_date=date(2026, 10, 7),
                from_currency="EUR",
                to_currency="USD",
                rate=Decimal("1.2"),
                source="ecb"
            ))
            
    mock_get.return_value = httpx.Response(200, content=b"""<?xml version="1.0" encoding="UTF-8"?>
    <gesmes:Envelope xmlns:gesmes="http://www.gesmes.org/xml/2002-08-01" xmlns="http://www.ecb.int/vocabulary/2002-08-01/eurofxref">
        <Cube><Cube time="2026-10-07"><Cube currency="USD" rate="1.5"/></Cube></Cube>
    </gesmes:Envelope>""")
    
    async with system_session_context() as session:
        async with session.begin():
            out3 = await sync_ecb_rates(session)
            assert out3["inserted"] == 0
            assert out3["conflicts"] == 1
            
            # Value should NOT be updated
            stmt = select(FxRate).where(FxRate.rate_date == date(2026, 10, 7))
            res = await session.execute(stmt)
            row = res.scalars().first()
            assert row.rate == Decimal("1.2")


@pytest.mark.asyncio
@patch("app.services.fx_ecb.httpx.AsyncClient.get")
async def test_sync_ecb_rates_db_error_rollback(mock_get, system_session_context):
    mock_get.return_value = httpx.Response(200, content=VALID_XML)
    
    with patch("app.services.fx_ecb.insert") as mock_insert:
        mock_insert.side_effect = Exception("DB ERROR")
        
        async with system_session_context() as session:
            async with session.begin():
                with pytest.raises(Exception):
                    await sync_ecb_rates(session)
                    
        # Check nothing inserted
        async with system_session_context() as session:
            res = await session.execute(select(FxRate).where(FxRate.rate_date == date(2026, 10, 6)))
            assert len(res.scalars().all()) == 0


@pytest.mark.asyncio
async def test_get_fx_rate_triangulation(system_session_context):
    async with system_session_context() as session:
        async with session.begin():
            session.add_all([
                # Common date 2026-10-06 (GBP missing this day to test 'latest common day' logic)
                FxRate(rate_date=date(2026, 10, 6), from_currency="EUR", to_currency="USD", rate=Decimal("1.10"), source="ecb"),
                
                # Common date 2026-10-05 (Both exist)
                FxRate(rate_date=date(2026, 10, 5), from_currency="EUR", to_currency="USD", rate=Decimal("1.08"), source="ecb"),
                FxRate(rate_date=date(2026, 10, 5), from_currency="EUR", to_currency="GBP", rate=Decimal("0.84"), source="ecb"),
                
                # Direct rate just in case
                FxRate(rate_date=date(2026, 10, 1), from_currency="JPY", to_currency="USD", rate=Decimal("0.007"), source="manual"),
            ])
            
    async with system_session_context() as session:
        # Triangulation GBP -> USD on 2026-10-06. GBP has no 2026-10-06 rate, so it should fall back to 2026-10-05
        rate = await get_fx_rate(session, "GBP", "USD", date(2026, 10, 6))
        # rate_to (USD on 05) = 1.08
        # rate_from (GBP on 05) = 0.84
        # 1.08 / 0.84 = 1.2857142857... -> 1.28571429
        assert rate == Decimal("1.28571429")
        
        # Test missing one leg entirely
        rate_none = await get_fx_rate(session, "GBP", "JPY", date(2026, 10, 6))
        assert rate_none is None
        
        # Test weekend fallback (asking for 10-07, latest is 10-05 within 7 days)
        rate_weekend = await get_fx_rate(session, "GBP", "USD", date(2026, 10, 7))
        assert rate_weekend == Decimal("1.28571429")
        
        # Test direct
        rate_direct = await get_fx_rate(session, "JPY", "USD", date(2026, 10, 2))
        assert rate_direct == Decimal("0.007")
        
        # Test inverse
        rate_inv = await get_fx_rate(session, "USD", "JPY", date(2026, 10, 2))
        # 1 / 0.007 = 142.85714286
        assert rate_inv == Decimal("142.85714286")


def test_beat_schedule_contains_ecb():
    schedule = celery_app.conf.beat_schedule
    assert 'fetch-ecb-rates-daily' in schedule
    entry = schedule['fetch-ecb-rates-daily']
    assert entry['task'] == 'fetch_ecb_rates_task'
    assert entry['schedule'].hour == {16}
    assert entry['schedule'].minute == {30}
