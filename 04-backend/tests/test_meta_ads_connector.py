import pytest
import httpx
from datetime import datetime, timezone
from decimal import Decimal
import uuid
from sqlalchemy import select
from unittest.mock import AsyncMock, patch, MagicMock
from app.connectors.meta_ads import MetaAdsConnector
from app.connectors.base import UnauthorizedError, RateLimitError
from app.db.models.campaigns import CampaignRunStat, CampaignRun, AdAccount
from app.db.models.companies import Company
from app.db.models.users import User
from app.db.session import system_session

class DummyConfig:
    def __init__(self, company_id):
        self.company_id = company_id
        self.settings = {"base_url": "https://graph.facebook.test/v19.0", "currency": "USD"}

@pytest.mark.asyncio
@patch("httpx.AsyncClient.get")
async def test_meta_test_connection_success(mock_get):
    config = DummyConfig(uuid.uuid4())
    connector = MetaAdsConnector(config, "secret_token")
    
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_get.return_value = mock_resp
    
    result = await connector.test_connection()
    assert result is True
    
    call_kwargs = mock_get.call_args[1]
    assert "Authorization" in call_kwargs["headers"]
    assert call_kwargs["headers"]["Authorization"] == "Bearer secret_token"
    assert "secret_token" not in call_kwargs.get("url", "")
    assert "secret_token" not in mock_get.call_args[0][0]

@pytest.mark.asyncio
async def test_meta_normalization_with_action_values():
    config = DummyConfig(uuid.uuid4())
    connector = MetaAdsConnector(config, "secret_token")
    
    raw_data = [
        # Normal purchase
        {"campaign_id": "100", "date_start": "2026-09-01", "spend": "10.50", "action_values": [{"action_type": "purchase", "value": "15.25"}]},
        # No revenue
        {"campaign_id": "101", "date_start": "2026-09-02", "spend": "5.0"},
        # omni_purchase + other events
        {"campaign_id": "102", "date_start": "2026-09-03", "spend": "1.0", "action_values": [{"action_type": "omni_purchase", "value": "100.00"}, {"action_type": "link_click", "value": "0.50"}]},
    ]
    
    normalized = connector.normalize(raw_data)
    
    assert len(normalized) == 3
    assert normalized[0].external_id == "100"
    assert normalized[0].revenue == Decimal("15.25")
    
    assert normalized[1].external_id == "101"
    assert normalized[1].revenue == Decimal("0")
    
    assert normalized[2].external_id == "102"
    assert normalized[2].revenue == Decimal("100.00")


@pytest.mark.asyncio
@patch("httpx.AsyncClient.get")
async def test_meta_fetch_campaigns_flattening(mock_get):
    config = DummyConfig(uuid.uuid4())
    connector = MetaAdsConnector(config, "secret_token")
    
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "data": [
            {
                "id": "act_1",
                "campaigns": {
                    "data": [
                        {"id": "camp_1", "name": "Camp 1"},
                        {"id": "camp_2", "name": "Camp 2"}
                    ]
                }
            },
            {
                "id": "act_2"
            }
        ]
    }
    mock_get.return_value = mock_resp
    
    campaigns = await connector.fetch_campaigns()
    assert len(campaigns) == 2
    assert campaigns[0]["id"] == "camp_1"
    assert campaigns[0]["account_id"] == "act_1"
    assert campaigns[1]["id"] == "camp_2"
    assert campaigns[1]["account_id"] == "act_1"

@pytest.mark.asyncio
@patch("httpx.AsyncClient.get")
async def test_meta_fetch_metrics_paging(mock_get):
    config = DummyConfig(uuid.uuid4())
    connector = MetaAdsConnector(config, "secret_token")
    
    # Mocking two pages
    resp_page_1 = MagicMock()
    resp_page_1.status_code = 200
    resp_page_1.json.return_value = {
        "data": [{"id": "act_1", "insights": {"data": [{"campaign_id": "c1", "spend": "10"}]}}],
        "paging": {"next": "https://graph.facebook.test/v19.0/me/page2"}
    }
    
    resp_page_2 = MagicMock()
    resp_page_2.status_code = 200
    resp_page_2.json.return_value = {
        "data": [{"id": "act_2", "insights": {"data": [{"campaign_id": "c2", "spend": "20"}]}}]
    }
    
    # Use side_effect to return different responses based on the URL
    def get_side_effect(*args, **kwargs):
        url = args[0]
        if "page2" in url:
            return resp_page_2
        return resp_page_1
        
    mock_get.side_effect = get_side_effect
    
    metrics = await connector.fetch_metrics()
    assert len(metrics) == 2
    assert metrics[0]["campaign_id"] == "c1"
    assert metrics[1]["campaign_id"] == "c2"

@pytest.mark.asyncio
async def test_meta_ad_accounts_status_mapping(company_b_fixtures):
    company_id_a = uuid.uuid4()
    
    async with system_session() as db_session:
        comp_a = Company(id=company_id_a, name="Company A Ad Acc", base_currency="USD")
        db_session.add(comp_a)
        await db_session.flush()
        await db_session.commit()
        
        config = DummyConfig(company_id_a)
        connector = MetaAdsConnector(config, "secret_token")
        
        raw_accounts = [
            {"account_id": "1", "account_status": 1}, # ACTIVE -> active
            {"account_id": "2", "account_status": 2}, # DISABLED -> banned
            {"account_id": "3", "account_status": 3}, # UNSETTLED -> suspended
            {"account_id": "7", "account_status": 7}, # PENDING -> suspended
            {"account_id": "100", "account_status": 100}, # PENDING_CLOSURE -> banned
            {"account_id": "999", "account_status": 999} # UNKNOWN -> banned
        ]
        
        norm_accs = connector.normalize_ad_accounts(raw_accounts)
        assert norm_accs[0].status == "active"
        assert norm_accs[1].status == "banned"
        assert norm_accs[2].status == "suspended"
        assert norm_accs[3].status == "suspended"
        assert norm_accs[4].status == "banned"
        assert norm_accs[5].status == "banned"

@pytest.mark.asyncio
async def test_meta_tenant_isolation(company_b_fixtures):
    company_id_a = uuid.uuid4()
    user_id_a = uuid.uuid4()
    
    company_id_b = uuid.UUID(company_b_fixtures.ids["company_id"])
    user_id_b = uuid.UUID(company_b_fixtures.ids["user_id"])
    
    async with system_session() as db_session:
        comp_a = Company(
            id=company_id_a,
            name="Company A Meta 2",
            base_currency="USD"
        )
        db_session.add(comp_a)
        await db_session.flush()
        
        user_a = User(
            id=user_id_a,
            company_id=company_id_a,
            name="User A 2",
            email="user_a_meta2@test.com",
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
        connector = MetaAdsConnector(config, "secret_token")
        
        raw_data = [
            {"campaign_id": "500", "date_start": "2026-09-01", "spend": "99.00"}
        ]
        normalized = connector.normalize(raw_data)
        
        await connector.upsert(db_session, normalized)
        await db_session.commit()
        
        stmt_a = select(CampaignRunStat).where(CampaignRunStat.campaign_run_id == run_a.id)
        res_a = await db_session.execute(stmt_a)
        stats_a = res_a.scalars().all()
        assert len(stats_a) == 1
        
        stmt_b = select(CampaignRunStat).where(CampaignRunStat.campaign_run_id == run_b.id)
        res_b = await db_session.execute(stmt_b)
        stats_b = res_b.scalars().all()
        assert len(stats_b) == 0

@pytest.mark.asyncio
async def test_meta_upsert_idempotency(company_b_fixtures):
    company_id = uuid.UUID(company_b_fixtures.ids["company_id"])
    user_id = uuid.UUID(company_b_fixtures.ids["user_id"])
    config = DummyConfig(company_id)
    connector = MetaAdsConnector(config, "secret_token")
    
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
            {"campaign_id": "200", "date_start": "2026-09-01", "spend": "50.00"}
        ]
        
        normalized = connector.normalize(raw_data)
        
        await connector.upsert(db_session, normalized)
        await db_session.commit()
        
        stmt = select(CampaignRunStat).where(CampaignRunStat.campaign_run_id == run.id)
        res = await db_session.execute(stmt)
        stats = res.scalars().all()
        assert len(stats) == 1
        assert stats[0].spend == Decimal("50.00")
        
        raw_data_update = [
            {"campaign_id": "200", "date_start": "2026-09-01", "spend": "60.00"}
        ]
        normalized_update = connector.normalize(raw_data_update)
        await connector.upsert(db_session, normalized_update)
        await db_session.commit()
        
        res = await db_session.execute(stmt)
        stats = res.scalars().all()
        assert len(stats) == 1
        assert stats[0].spend == Decimal("60.00")

@pytest.mark.asyncio
@patch("httpx.AsyncClient.get")
async def test_meta_retry_429(mock_get, monkeypatch):
    config = DummyConfig(uuid.uuid4())
    connector = MetaAdsConnector(config, "secret_token")
    
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
        await connector.fetch_metrics()

@pytest.mark.asyncio
@patch("httpx.AsyncClient.get")
async def test_meta_retry_5xx_success(mock_get, monkeypatch):
    config = DummyConfig(uuid.uuid4())
    connector = MetaAdsConnector(config, "secret_token")
    
    resp_500 = MagicMock()
    resp_500.status_code = 500
    
    resp_200 = MagicMock()
    resp_200.status_code = 200
    resp_200.json.return_value = {"data": [{"insights": {"data": [{"campaign_id": "300", "date_start": "2026-09-01", "spend": "5.0"}]}}]}
    
    mock_get.side_effect = [
        httpx.HTTPStatusError("500", request=MagicMock(), response=resp_500),
        resp_200
    ]
    
    monkeypatch.setattr("app.connectors.base.asyncio.sleep", AsyncMock())
    
    data = await connector.fetch_metrics()
    assert len(data) == 1
    assert data[0]["campaign_id"] == "300"

@pytest.mark.asyncio
@patch("httpx.AsyncClient.get")
async def test_meta_unauthorized(mock_get, monkeypatch):
    config = DummyConfig(uuid.uuid4())
    connector = MetaAdsConnector(config, "secret_token")
    
    resp_401 = MagicMock()
    resp_401.status_code = 401
    mock_get.side_effect = httpx.HTTPStatusError("401", request=MagicMock(), response=resp_401)
    
    monkeypatch.setattr("app.connectors.base.asyncio.sleep", AsyncMock())
    
    with pytest.raises(UnauthorizedError):
        await connector.fetch_metrics()
