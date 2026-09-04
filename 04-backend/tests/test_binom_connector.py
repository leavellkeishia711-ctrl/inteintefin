import pytest
import httpx
from datetime import date
from decimal import Decimal
import uuid
from sqlalchemy import select
from unittest.mock import AsyncMock, patch, MagicMock
import asyncio

from app.connectors.binom import BinomConnector
from app.connectors.base import UnauthorizedError, RateLimitError, ConnectorError
from app.db.models.campaigns import CampaignRunStat, CampaignRun

class DummyConfig:
    def __init__(self, company_id):
        self.company_id = company_id
        self.settings = {"base_url": "https://api.binom.test"}

@pytest.mark.asyncio
@patch("httpx.AsyncClient.get")
async def test_binom_test_connection_success(mock_get):
    config = DummyConfig(uuid.uuid4())
    connector = BinomConnector(config, "secret_key")
    
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status = MagicMock()
    mock_get.return_value = mock_resp
    
    result = await connector.test_connection()
    assert result is True

@pytest.mark.asyncio
@patch("httpx.AsyncClient.get")
async def test_binom_test_connection_fail(mock_get):
    config = DummyConfig(uuid.uuid4())
    connector = BinomConnector(config, "secret_key")
    
    mock_resp = MagicMock()
    mock_resp.status_code = 401
    mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError("401", request=MagicMock(), response=mock_resp)
    mock_get.return_value = mock_resp
    
    result = await connector.test_connection()
    assert result is False

@pytest.mark.asyncio
async def test_binom_normalization():
    config = DummyConfig(uuid.uuid4())
    connector = BinomConnector(config, "secret_key")
    
    raw_data = [
        {"camp_id": "100", "date": "2026-09-01", "cost": "10.50", "revenue": "20.75"},
        {"camp_id": "101", "date": "2026-09-02", "cost": "0", "revenue": "1.00"},
        {"invalid": "data"},
        {"camp_id": "102"} # missing date
    ]
    
    normalized = connector.normalize(raw_data)
    
    assert len(normalized) == 2
    
    assert normalized[0].external_id == "100"
    assert normalized[0].stat_date == date(2026, 9, 1)
    assert normalized[0].spend == Decimal("10.50")
    assert normalized[0].revenue == Decimal("20.75")
    assert normalized[0].source == "binom"
    
    assert normalized[1].external_id == "101"

@pytest.mark.asyncio
async def test_binom_upsert_idempotency(company_b_fixtures):
    company, user = company_b_fixtures
    config = DummyConfig(company.id)
    connector = BinomConnector(config, "secret_key")
    
    from app.db.session import system_session
    async with system_session() as db_session:
        # Create a campaign run that maps to binom camp_id "200"
        run = CampaignRun(
            company_id=company.id,
            buyer_id=user.id,
            started_at=date(2026, 9, 1),
            note="200" # external_id matches here
        )
        db_session.add(run)
        await db_session.commit()
        
        raw_data = [
            {"camp_id": "200", "date": "2026-09-01", "cost": "50.00", "revenue": "100.00"}
        ]
        
        normalized = connector.normalize(raw_data)
        
        # First upsert
        await connector.upsert(db_session, normalized)
        await db_session.commit()
        
        stmt = select(CampaignRunStat).where(CampaignRunStat.campaign_run_id == run.id)
        res = await db_session.execute(stmt)
        stats = res.scalars().all()
        assert len(stats) == 1
        assert stats[0].spend == Decimal("50.00")
        
        # Second upsert (update/idempotency)
        raw_data_update = [
            {"camp_id": "200", "date": "2026-09-01", "cost": "60.00", "revenue": "120.00"}
        ]
        normalized_update = connector.normalize(raw_data_update)
        await connector.upsert(db_session, normalized_update)
        await db_session.commit()
        
        res = await db_session.execute(stmt)
        stats = res.scalars().all()
        assert len(stats) == 1
        assert stats[0].spend == Decimal("60.00")
        assert stats[0].revenue == Decimal("120.00")

@pytest.mark.asyncio
@patch("httpx.AsyncClient.get")
async def test_binom_retry_429(mock_get):
    config = DummyConfig(uuid.uuid4())
    connector = BinomConnector(config, "secret_key")
    
    # Fail 2 times with 429, then succeed
    resp_429 = MagicMock()
    resp_429.status_code = 429
    
    resp_200 = MagicMock()
    resp_200.status_code = 200
    resp_200.json.return_value = [{"camp_id": "300", "date": "2026-09-01", "cost": "5.0"}]
    
    mock_get.side_effect = [
        httpx.HTTPStatusError("429", request=MagicMock(), response=resp_429),
        httpx.HTTPStatusError("429", request=MagicMock(), response=resp_429),
        resp_200
    ]
    
    # We need to temporarily speed up sleep for the test
    import app.connectors.base
    original_sleep = asyncio.sleep
    async def mock_sleep(*args, **kwargs):
        pass
    app.connectors.base.asyncio.sleep = mock_sleep
    
    try:
        data = await connector.fetch()
        assert len(data) == 1
        assert data[0]["camp_id"] == "300"
        assert mock_get.call_count == 3
    finally:
        app.connectors.base.asyncio.sleep = original_sleep