import pytest
import httpx
from datetime import datetime, timezone
from decimal import Decimal
import uuid
from sqlalchemy import select
from unittest.mock import AsyncMock, patch, MagicMock
from app.connectors.affise import AffiseConnector
from app.connectors.base import UnauthorizedError, RateLimitError
from app.db.models.campaigns import CampaignRunStat, CampaignRun
from app.db.models.companies import Company
from app.db.models.users import User
from app.db.session import system_session

class DummyConfig:
    def __init__(self, company_id):
        self.company_id = company_id
        self.settings = {"base_url": "https://api.affise.test", "currency": "USD"}

@pytest.mark.asyncio
@patch("httpx.AsyncClient.get")
async def test_affise_test_connection_success(mock_get):
    config = DummyConfig(uuid.uuid4())
    connector = AffiseConnector(config, "secret_key")
    
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_get.return_value = mock_resp
    
    result = await connector.test_connection()
    assert result is True
    
    # Verify auth header does not leak in URL
    call_kwargs = mock_get.call_args[1]
    assert "API-Key" in call_kwargs["headers"]
    assert call_kwargs["headers"]["API-Key"] == "secret_key"

@pytest.mark.asyncio
@patch("httpx.AsyncClient.get")
async def test_affise_test_connection_fail(mock_get):
    config = DummyConfig(uuid.uuid4())
    connector = AffiseConnector(config, "secret_key")
    
    mock_resp = MagicMock()
    mock_resp.status_code = 401
    mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError("401", request=MagicMock(), response=mock_resp)
    mock_get.return_value = mock_resp
    
    result = await connector.test_connection()
    assert result is False

@pytest.mark.asyncio
async def test_affise_normalization():
    config = DummyConfig(uuid.uuid4())
    connector = AffiseConnector(config, "secret_key")
    
    raw_data = [
        {"offer_id": "100", "date": "2026-09-01", "cost": "10.50", "revenue": "20.75"},
        {"campaign_id": "101", "date": "2026-09-02", "cost": "0", "revenue": "1.00"},
        {"invalid": "data"},
        {"id": "102"}
    ]
    
    normalized = connector.normalize(raw_data)
    
    assert len(normalized) == 3
    assert normalized[0].external_id == "100"
    assert normalized[0].stat_date == datetime(2026, 9, 1, tzinfo=timezone.utc).date()
    assert normalized[0].spend == Decimal("10.50")
    assert normalized[0].revenue == Decimal("20.75")
    assert normalized[0].source == "affise"
    assert normalized[0].currency == "USD"
    
    assert normalized[1].external_id == "101"

    # The item "102" is parsed but has no date string, so it falls back to today
    assert normalized[2].external_id == "102"
    assert normalized[2].stat_date == datetime.now(timezone.utc).date()


@pytest.mark.asyncio
async def test_affise_upsert_idempotency(company_b_fixtures):
    company_id = uuid.UUID(company_b_fixtures.ids["company_id"])
    user_id = uuid.UUID(company_b_fixtures.ids["user_id"])
    config = DummyConfig(company_id)
    connector = AffiseConnector(config, "secret_key")
    
    async with system_session() as db_session:
        run = CampaignRun(
            company_id=company_id,
            buyer_id=user_id,
            started_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
            note="200"
        )
        db_session.add(run)
        await db_session.commit()
        
        raw_data = [
            {"offer_id": "200", "date": "2026-09-01", "cost": "50.00", "revenue": "100.00"}
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
            {"offer_id": "200", "date": "2026-09-01", "cost": "60.00", "revenue": "120.00"}
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
async def test_affise_tenant_isolation(company_b_fixtures):
    company_id_a = uuid.uuid4()
    user_id_a = uuid.uuid4()
    
    company_id_b = uuid.UUID(company_b_fixtures.ids["company_id"])
    user_id_b = uuid.UUID(company_b_fixtures.ids["user_id"])
    
    async with system_session() as db_session:
        comp_a = Company(
            id=company_id_a,
            name="Company A Affise",
            base_currency="USD"
        )
        db_session.add(comp_a)
        await db_session.flush()
        
        user_a = User(
            id=user_id_a,
            company_id=company_id_a,
            name="User A",
            email="user_a_affise@test.com",
            password_hash="hash",
            role="admin"
        )
        db_session.add(user_a)
        await db_session.flush()
        
        run_a = CampaignRun(
            company_id=company_id_a,
            buyer_id=user_id_a,
            started_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
            note="500"
        )
        db_session.add(run_a)
        
        run_b = CampaignRun(
            company_id=company_id_b,
            buyer_id=user_id_b,
            started_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
            note="500"
        )
        db_session.add(run_b)
        
        await db_session.commit()
        
        config = DummyConfig(company_id_a)
        connector = AffiseConnector(config, "secret_key")
        
        raw_data = [
            {"offer_id": "500", "date": "2026-09-01", "cost": "99.00", "revenue": "99.00"}
        ]
        normalized = connector.normalize(raw_data)
        
        await connector.upsert(db_session, normalized)
        await db_session.commit()
        
        stmt_a = select(CampaignRunStat).where(CampaignRunStat.campaign_run_id == run_a.id)
        res_a = await db_session.execute(stmt_a)
        stats_a = res_a.scalars().all()
        assert len(stats_a) == 1
        assert stats_a[0].company_id == company_id_a
        
        stmt_b = select(CampaignRunStat).where(CampaignRunStat.campaign_run_id == run_b.id)
        res_b = await db_session.execute(stmt_b)
        stats_b = res_b.scalars().all()
        assert len(stats_b) == 0

@pytest.mark.asyncio
@patch("httpx.AsyncClient.get")
async def test_affise_retry_429(mock_get, monkeypatch):
    config = DummyConfig(uuid.uuid4())
    connector = AffiseConnector(config, "secret_key")
    
    resp_429 = MagicMock()
    resp_429.status_code = 429
    
    mock_get.side_effect = [
        httpx.HTTPStatusError("429", request=MagicMock(), response=resp_429),
        httpx.HTTPStatusError("429", request=MagicMock(), response=resp_429),
        httpx.HTTPStatusError("429", request=MagicMock(), response=resp_429),
        httpx.HTTPStatusError("429", request=MagicMock(), response=resp_429)
    ]
    
    monkeypatch.setattr("app.connectors.base.asyncio.sleep", AsyncMock())
    
    with pytest.raises(RateLimitError):
        await connector.fetch()

@pytest.mark.asyncio
@patch("httpx.AsyncClient.get")
async def test_affise_retry_5xx_success(mock_get, monkeypatch):
    config = DummyConfig(uuid.uuid4())
    connector = AffiseConnector(config, "secret_key")
    
    resp_500 = MagicMock()
    resp_500.status_code = 500
    
    resp_200 = MagicMock()
    resp_200.status_code = 200
    resp_200.json.return_value = {"stats": [{"offer_id": "300", "date": "2026-09-01", "cost": "5.0"}]}
    
    mock_get.side_effect = [
        httpx.HTTPStatusError("500", request=MagicMock(), response=resp_500),
        resp_200
    ]
    
    monkeypatch.setattr("app.connectors.base.asyncio.sleep", AsyncMock())
    
    data = await connector.fetch()
    assert len(data) == 1
    assert data[0]["offer_id"] == "300"

@pytest.mark.asyncio
@patch("httpx.AsyncClient.get")
async def test_affise_unauthorized(mock_get, monkeypatch):
    config = DummyConfig(uuid.uuid4())
    connector = AffiseConnector(config, "secret_key")
    
    resp_401 = MagicMock()
    resp_401.status_code = 401
    mock_get.side_effect = httpx.HTTPStatusError("401", request=MagicMock(), response=resp_401)
    
    monkeypatch.setattr("app.connectors.base.asyncio.sleep", AsyncMock())
    
    with pytest.raises(UnauthorizedError):
        await connector.fetch()

@pytest.mark.asyncio
@patch("httpx.AsyncClient.get")
async def test_affise_smoke(mock_get, company_b_fixtures):
    company_id = uuid.UUID(company_b_fixtures.ids["company_id"])
    config = DummyConfig(company_id)
    connector = AffiseConnector(config, "secret_key")
    
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"stats": []}
    mock_get.return_value = mock_resp
    
    assert await connector.test_connection() is True
    
    async with system_session() as db_session:
        raw = await connector.fetch()
        norm = connector.normalize(raw)
        await connector.upsert(db_session, norm)
        
    assert mock_get.call_count >= 1
