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
@patch("httpx.AsyncClient.get")
async def test_meta_secret_stripping_on_paging(mock_get):
    config = DummyConfig(uuid.uuid4())
    connector = MetaAdsConnector(config, "secret_token")
    
    resp_page_1 = MagicMock()
    resp_page_1.status_code = 200
    resp_page_1.json.return_value = {
        "data": [{"account_id": "1"}],
        "paging": {"next": "https://graph.facebook.test/v19.0/me/page2?limit=10&access_token=SECRET_TOKEN&appsecret_proof=PROOF"}
    }
    
    resp_page_2 = MagicMock()
    resp_page_2.status_code = 200
    resp_page_2.json.return_value = {
        "data": [{"account_id": "2"}]
    }
    
    def get_side_effect(*args, **kwargs):
        url = args[0]
        if "page2" in url:
            return resp_page_2
        return resp_page_1
        
    mock_get.side_effect = get_side_effect
    
    accs = await connector.fetch_ad_accounts()
    assert len(accs) == 2
    
    page2_call = mock_get.call_args_list[1]
    url_used = page2_call[0][0]
    
    assert "SECRET_TOKEN" not in url_used
    assert "access_token" not in url_used
    assert "PROOF" not in url_used
    assert "limit=10" in url_used

@pytest.mark.asyncio
@patch("httpx.AsyncClient.get")
async def test_meta_nested_insights_paging(mock_get):
    config = DummyConfig(uuid.uuid4())
    connector = MetaAdsConnector(config, "secret_token")
    
    resp_accounts = MagicMock()
    resp_accounts.status_code = 200
    resp_accounts.json.return_value = {
        "data": [
            {
                "id": "act_1",
                "insights": {
                    "data": [{"campaign_id": "c1"}],
                    "paging": {"next": "https://graph.facebook.test/v19.0/act_1/page2?access_token=SEC"}
                }
            },
            {
                "id": "act_2",
                "insights": {
                    "data": [{"campaign_id": "c2"}]
                }
            }
        ]
    }
    
    resp_insights_page2 = MagicMock()
    resp_insights_page2.status_code = 200
    resp_insights_page2.json.return_value = {
        "data": [{"campaign_id": "c1_p2"}],
        "paging": {"next": "https://graph.facebook.test/v19.0/act_1/page3?access_token=SEC"}
    }

    resp_insights_page3 = MagicMock()
    resp_insights_page3.status_code = 200
    resp_insights_page3.json.return_value = {
        "data": [{"campaign_id": "c1_p3"}]
    }
    
    def get_side_effect(*args, **kwargs):
        url = args[0]
        if "page2" in url:
            return resp_insights_page2
        elif "page3" in url:
            return resp_insights_page3
        return resp_accounts
        
    mock_get.side_effect = get_side_effect
    
    metrics = await connector.fetch_metrics()
    
    assert len(metrics) == 4
    ids = [m["campaign_id"] for m in metrics]
    assert "c1" in ids
    assert "c1_p2" in ids
    assert "c1_p3" in ids
    assert "c2" in ids
    
    page2_call = mock_get.call_args_list[1]
    page3_call = mock_get.call_args_list[2]
    
    assert "SEC" not in page2_call[0][0]
    assert "SEC" not in page3_call[0][0]

@pytest.mark.asyncio
async def test_meta_normalization_with_action_values():
    config = DummyConfig(uuid.uuid4())
    connector = MetaAdsConnector(config, "secret_token")
    
    raw_data = [
        {"campaign_id": "100", "date_start": "2026-09-01", "spend": "10.50", "action_values": [{"action_type": "purchase", "value": "15.25"}]},
        {"campaign_id": "101", "date_start": "2026-09-02", "spend": "5.0"},
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
            {"account_id": "1", "account_status": 1},
            {"account_id": "2", "account_status": 2},
            {"account_id": "3", "account_status": 3},
            {"account_id": "7", "account_status": 7},
            {"account_id": "100", "account_status": 100},
            {"account_id": "999", "account_status": 999}
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


@pytest.mark.asyncio
@patch("httpx.AsyncClient.get")
async def test_meta_fetch_campaigns_nested_paging_and_safety(mock_get):
    config = DummyConfig(uuid.uuid4())
    connector = MetaAdsConnector(config, "secret_token")
    
    resp_accounts = MagicMock()
    resp_accounts.status_code = 200
    resp_accounts.json.return_value = {
        "data": [
            {
                "id": "act_1",
                "campaigns": {
                    "data": [{"id": "camp_1"}],
                    "paging": {"next": "https://graph.facebook.test/v19.0/act_1/camp_page2?access_token=SEC&token=TOK&appsecret_proof=PROOF"}
                }
            },
            {
                "id": "act_2",
                "campaigns": {
                    "data": [{"id": "camp_3"}]
                }
            }
        ]
    }
    
    resp_camp_page2 = MagicMock()
    resp_camp_page2.status_code = 200
    resp_camp_page2.json.return_value = {
        "data": [{"id": "camp_2"}],
        "paging": {"next": "https://graph.facebook.test/v19.0/act_1/camp_page2?access_token=SEC"}  # simulates repeating URL, should break infinite loop
    }
    
    def get_side_effect(*args, **kwargs):
        url = args[0]
        if "camp_page2" in url:
            return resp_camp_page2
        return resp_accounts
        
    mock_get.side_effect = get_side_effect
    
    campaigns = await connector.fetch_campaigns()
    assert len(campaigns) == 3
    
    # 1. Check all IDs
    c_ids = [c["id"] for c in campaigns]
    assert set(c_ids) == {"camp_1", "camp_2", "camp_3"}
    
    # 2. Check account_id separation
    act1_camps = [c for c in campaigns if c["account_id"] == "act_1"]
    assert len(act1_camps) == 2
    
    act2_camps = [c for c in campaigns if c["account_id"] == "act_2"]
    assert len(act2_camps) == 1
    assert act2_camps[0]["id"] == "camp_3"
    
    # 3. Check secrets stripping from paging.next
    page2_call = mock_get.call_args_list[1]
    url_used = page2_call[0][0]
    assert "SEC" not in url_used
    assert "TOK" not in url_used
    assert "PROOF" not in url_used

@pytest.mark.asyncio
async def test_meta_upsert_fx_rate_success_and_failure(company_b_fixtures):
    company_id_a = uuid.uuid4()
    user_id_a = uuid.uuid4()
    
    async with system_session() as db_session:
        comp_a = Company(
            id=company_id_a,
            name="Company FX Test",
            base_currency="EUR"
        )
        db_session.add(comp_a)
        await db_session.flush()
        
        from app.db.models.users import User
        u = User(id=user_id_a, name="testfx", email="testfx@test.com", password_hash="hash", company_id=company_id_a, role="admin")
        db_session.add(u)
        await db_session.flush()
        
        from app.db.models.campaigns import Campaign
        c1 = Campaign(id=uuid.uuid4(), company_id=company_id_a, assigned_user_id=user_id_a)
        c2 = Campaign(id=uuid.uuid4(), company_id=company_id_a, assigned_user_id=user_id_a)
        db_session.add(c1)
        db_session.add(c2)
        await db_session.flush()
        
        run_a = CampaignRun(
            company_id=company_id_a,
            campaign_id=c1.id,
            buyer_id=user_id_a,
            started_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
            note="fx_camp_1"
        )
        db_session.add(run_a)
        
        run_b = CampaignRun(
            company_id=company_id_a,
            campaign_id=c2.id,
            buyer_id=user_id_a,
            started_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
            note="fx_camp_2"
        )
        db_session.add(run_b)
        await db_session.commit()
        
        config = DummyConfig(company_id_a)
        connector = MetaAdsConnector(config, "secret_token")
        
        # 1. Success FX rate test
        from app.db.models import FxRate
        rate = FxRate(rate_date=datetime(2026, 9, 1, tzinfo=timezone.utc).date(), from_currency="USD", to_currency="EUR", rate=Decimal("0.85"), source="manual")
        db_session.add(rate)
        await db_session.commit()
        
        raw_data = [
            {"campaign_id": "fx_camp_1", "date_start": "2026-09-01", "spend": "100.00"}
        ]
        norm = connector.normalize(raw_data)
        await connector.upsert(db_session, norm)
        await db_session.commit()
        
        stmt = select(CampaignRunStat).where(CampaignRunStat.campaign_run_id == run_a.id)
        stat = (await db_session.execute(stmt)).scalars().first()
        assert stat is not None
        assert stat.fx_rate_to_base == Decimal("0.85")
        
        # 2. Failure FX rate test
        raw_data_2 = [
            {"campaign_id": "fx_camp_2", "date_start": "2026-09-02", "spend": "50.00"}
        ]
        norm_2 = connector.normalize(raw_data_2)
        with pytest.raises(ValueError):
            await connector.upsert(db_session, norm_2)
        
        stmt_2 = select(CampaignRunStat).where(CampaignRunStat.campaign_run_id == run_b.id)
        stat_2 = (await db_session.execute(stmt_2)).scalars().first()
        assert stat_2 is None

@pytest.mark.asyncio
@patch("httpx.AsyncClient.get")
async def test_meta_test_connection_401_403(mock_get, monkeypatch):
    from app.connectors.base import UnauthorizedError
    config = DummyConfig(uuid.uuid4())
    connector = MetaAdsConnector(config, "secret_token")
    monkeypatch.setattr("app.connectors.base.asyncio.sleep", AsyncMock())
    
    # 401
    resp_401 = MagicMock()
    resp_401.status_code = 401
    mock_get.side_effect = httpx.HTTPStatusError("401", request=MagicMock(), response=resp_401)
    
    with pytest.raises(UnauthorizedError):
        await connector.test_connection()
        
    # 403
    resp_403 = MagicMock()
    resp_403.status_code = 403
    mock_get.side_effect = httpx.HTTPStatusError("403", request=MagicMock(), response=resp_403)
    
    with pytest.raises(UnauthorizedError):
        await connector.test_connection()

@pytest.mark.asyncio
@patch("app.connectors.base.Connector.sync")
async def test_meta_scheduler_unauthorized_state(mock_sync):
    from app.connectors.scheduler import sync_connector_instance
    from app.db.models.connectors import ConnectorConfig
    from app.connectors.base import UnauthorizedError
    
    company_id = uuid.uuid4()
    async with system_session() as db_session:
        comp = Company(id=company_id, name="Sched Test", base_currency="USD")
        db_session.add(comp)
        
        conn = ConnectorConfig(
            company_id=company_id,
            connector_name="meta",
            
            status="active",
            encrypted_secret="fake"
        )
        db_session.add(conn)
        await db_session.commit()
        
        mock_sync.side_effect = UnauthorizedError("Token invalid")
        
        with patch("app.connectors.scheduler.decrypt_secret", return_value="fake_secret"), \
             patch("app.connectors.scheduler.acquire_lock", return_value=True):
            await sync_connector_instance(str(company_id), str(conn.id))
        
        async with system_session() as new_session:
            from sqlalchemy import text
            stmt = text("SELECT status FROM connector_configs WHERE id = :id")
            res = await new_session.execute(stmt, {"id": conn.id})
            status = res.scalar()
            assert status == "unauthorized", f"Expected unauthorized, got {status}"
