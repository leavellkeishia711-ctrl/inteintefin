import pytest
from datetime import date
from decimal import Decimal
import httpx
from unittest.mock import patch
from sqlalchemy import select
from app.db.session import system_session
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

EMPTY_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<gesmes:Envelope xmlns:gesmes="http://www.gesmes.org/xml/2002-08-01" xmlns="http://www.ecb.int/vocabulary/2002-08-01/eurofxref">
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
    assert skipped == 7 # 6 invalid currencies + 1 skipped date with 1 child


@pytest.mark.asyncio
@patch("app.services.fx_ecb.httpx.AsyncClient.stream")
async def test_sync_ecb_rates_http_errors(mock_stream):
    import contextlib
    @contextlib.asynccontextmanager
    async def mock_stream_response(*args, **kwargs):
        class MockRes:
            status_code = 500
        yield MockRes()
        
    mock_stream.side_effect = mock_stream_response
    
    async with system_session() as session:
        async with session.begin():
            out = await sync_ecb_rates(session)
            assert out["fetched"] == 0

    @contextlib.asynccontextmanager
    async def mock_stream_response_204(*args, **kwargs):
        class MockRes:
            status_code = 204
        yield MockRes()
        
    mock_stream.side_effect = mock_stream_response_204
    async with system_session() as session:
        async with session.begin():
            out = await sync_ecb_rates(session)
            assert out["fetched"] == 0

    @contextlib.asynccontextmanager
    async def mock_stream_response_large_header(*args, **kwargs):
        class MockRes:
            status_code = 200
            headers = {"Content-Length": "3000000"}
        yield MockRes()
        
    mock_stream.side_effect = mock_stream_response_large_header
    async with system_session() as session:
        async with session.begin():
            out = await sync_ecb_rates(session)
            assert out["fetched"] == 0

    @contextlib.asynccontextmanager
    async def mock_stream_response_large_body(*args, **kwargs):
        class MockRes:
            status_code = 200
            headers = {"Content-Length": "10"}
            async def aiter_bytes(self):
                yield b"a" * (2 * 1024 * 1024 + 10)
        yield MockRes()
        
    mock_stream.side_effect = mock_stream_response_large_body
    async with system_session() as session:
        async with session.begin():
            out = await sync_ecb_rates(session)
            assert out["fetched"] == 0

@pytest.mark.asyncio
@patch("app.services.fx_ecb.httpx.AsyncClient.stream")
async def test_sync_ecb_empty_valid_rates(mock_stream):
    import contextlib
    @contextlib.asynccontextmanager
    async def mock_stream_response(*args, **kwargs):
        class MockRes:
            status_code = 200
            headers = {"Content-Length": "100"}
            async def aiter_bytes(self):
                yield EMPTY_XML
        yield MockRes()
        
    mock_stream.side_effect = mock_stream_response
    async with system_session() as session:
        async with session.begin():
            out = await sync_ecb_rates(session)
            assert out["fetched"] == 0
            assert out["inserted"] == 0
            assert out["conflicts"] == 0


@pytest.mark.asyncio
@patch("app.services.fx_ecb.httpx.AsyncClient.stream")
async def test_sync_ecb_rates_idempotent_and_conflict(mock_stream):
    import contextlib
    @contextlib.asynccontextmanager
    async def mock_stream_response(*args, **kwargs):
        class MockRes:
            status_code = 200
            headers = {"Content-Length": "100"}
            async def aiter_bytes(self):
                yield VALID_XML
        yield MockRes()
        
    mock_stream.side_effect = mock_stream_response
    
    async with system_session() as session:
        async with session.begin():
            out1 = await sync_ecb_rates(session)
            assert out1["inserted"] == 5
            assert out1["conflicts"] == 0
            assert out1["unchanged"] == 0
            
    # Second run: Idempotent (all unchanged)
    async with system_session() as session:
        async with session.begin():
            out2 = await sync_ecb_rates(session)
            assert out2["inserted"] == 0
            assert out2["conflicts"] == 0
            assert out2["unchanged"] == 5
            
    # Modify an existing one to test conflict (different value, same key)
    async with system_session() as session:
        async with session.begin():
            session.add(FxRate(
                rate_date=date(2026, 10, 7),
                from_currency="EUR",
                to_currency="USD",
                rate=Decimal("1.2"),
                source="ecb"
            ))
            
    @contextlib.asynccontextmanager
    async def mock_stream_response_conflict(*args, **kwargs):
        class MockRes:
            status_code = 200
            headers = {"Content-Length": "100"}
            async def aiter_bytes(self):
                yield b"""<?xml version="1.0" encoding="UTF-8"?>
                <gesmes:Envelope xmlns:gesmes="http://www.gesmes.org/xml/2002-08-01" xmlns="http://www.ecb.int/vocabulary/2002-08-01/eurofxref">
                    <Cube><Cube time="2026-10-07"><Cube currency="USD" rate="1.5"/></Cube></Cube>
                </gesmes:Envelope>"""
        yield MockRes()
        
    mock_stream.side_effect = mock_stream_response_conflict
    
    async with system_session() as session:
        async with session.begin():
            out3 = await sync_ecb_rates(session)
            assert out3["inserted"] == 0
            assert out3["conflicts"] == 1
            assert out3["unchanged"] == 0
            
            # Value should NOT be updated
            stmt = select(FxRate).where(FxRate.rate_date == date(2026, 10, 7))
            res = await session.execute(stmt)
            row = res.scalars().first()
            assert row.rate == Decimal("1.2")


@pytest.mark.asyncio
@patch("app.services.fx_ecb.httpx.AsyncClient.stream")
async def test_sync_ecb_rates_db_error_rollback(mock_stream):
    import contextlib
    @contextlib.asynccontextmanager
    async def mock_stream_response(*args, **kwargs):
        class MockRes:
            status_code = 200
            headers = {"Content-Length": "100"}
            async def aiter_bytes(self):
                yield VALID_XML
        yield MockRes()
        
    mock_stream.side_effect = mock_stream_response
    
    with patch("app.services.fx_ecb.insert") as mock_insert:
        mock_insert.side_effect = Exception("DB ERROR")
        
        async with system_session() as session:
            async with session.begin():
                with pytest.raises(Exception):
                    await sync_ecb_rates(session)
                    
        # Check nothing inserted
        async with system_session() as session:
            res = await session.execute(select(FxRate).where(FxRate.rate_date == date(2026, 10, 6)))
            assert len(res.scalars().all()) == 0


@pytest.mark.asyncio
async def test_get_fx_rate_triangulation():
    async with system_session() as session:
        async with session.begin():
            session.add_all([
                # Common date 2026-10-06
                FxRate(rate_date=date(2026, 10, 6), from_currency="EUR", to_currency="USD", rate=Decimal("1.10"), source="ecb"),
                
                # Common date 2026-10-05
                FxRate(rate_date=date(2026, 10, 5), from_currency="EUR", to_currency="USD", rate=Decimal("1.08"), source="ecb"),
                FxRate(rate_date=date(2026, 10, 5), from_currency="EUR", to_currency="GBP", rate=Decimal("0.84"), source="ecb"),
                
                # Direct rate just in case
                FxRate(rate_date=date(2026, 10, 1), from_currency="JPY", to_currency="USD", rate=Decimal("0.007"), source="manual"),
            ])
            
    async with system_session() as session:
        rate = await get_fx_rate(session, "GBP", "USD", date(2026, 10, 6))
        assert rate == Decimal("1.28571429")
        
        rate_none = await get_fx_rate(session, "GBP", "JPY", date(2026, 10, 6))
        assert rate_none is None
        
        rate_weekend = await get_fx_rate(session, "GBP", "USD", date(2026, 10, 7))
        assert rate_weekend == Decimal("1.28571429")
        
        rate_direct = await get_fx_rate(session, "JPY", "USD", date(2026, 10, 2))
        assert rate_direct == Decimal("0.007")
        
        # Test exact byte-for-byte behavior on inverse
        rate_inv = await get_fx_rate(session, "USD", "JPY", date(2026, 10, 2))
        assert rate_inv == Decimal("1.00000000") / Decimal("0.007")


def test_beat_schedule_contains_ecb():
    schedule = celery_app.conf.beat_schedule
    assert 'fetch-ecb-rates-daily' in schedule
    entry = schedule['fetch-ecb-rates-daily']
    assert entry['task'] == 'fetch_ecb_rates_task'
    assert entry['schedule'].hour == {16}
    assert entry['schedule'].minute == {30}
