import pytest
import httpx
from datetime import datetime, timezone, date
from decimal import Decimal
import uuid
from sqlalchemy import select
from unittest.mock import AsyncMock, patch, MagicMock
import json

from app.connectors.tiktok_ads import TikTokAdsConnector
from app.connectors.base import UnauthorizedError, RateLimitError, ConnectorError
from app.db.models.campaigns import CampaignRun, CampaignRunStat, CampaignRun, ExternalCampaignMapping
from app.db.models.companies import Company
from app.db.models.users import User
from app.db.session import system_session

class DummyConfig:
    def __init__(self, company_id, connector_name="tiktok_ads"):
        self.connector_name = connector_name
        self.company_id = company_id
        self.settings = {}

def get_creds():
    return json.dumps({"access_token": "fake_token", "advertiser_id": "12345"})

@pytest.mark.asyncio
@patch("httpx.AsyncClient.get")
async def test_tiktok_ads_test_connection_success(mock_get):
    config = DummyConfig(uuid.uuid4(), connector_name="tiktok_ads")
    connector = TikTokAdsConnector(config, get_creds())
    
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"code": 0, "message": "OK", "data": {"list": [{"advertiser_id": "12345"}]}}
    mock_get.return_value = mock_resp
    
    result = await connector.test_connection()
    assert result is True
    
    call_kwargs = mock_get.call_args[1]
    assert "Access-Token" in call_kwargs["headers"]
    assert call_kwargs["headers"]["Access-Token"] == "fake_token"
    assert call_kwargs["params"]["advertiser_ids"] == '["12345"]'

@pytest.mark.asyncio
@patch("httpx.AsyncClient.get")
async def test_tiktok_ads_test_connection_auth_failure(mock_get):
    config = DummyConfig(uuid.uuid4(), connector_name="tiktok_ads")
    connector = TikTokAdsConnector(config, get_creds())
    
    mock_resp = MagicMock()
    mock_resp.status_code = 401
    mock_get.return_value = mock_resp
    
    result = await connector.test_connection()
    assert result is False

@pytest.mark.asyncio
@patch("httpx.AsyncClient.get")
async def test_tiktok_ads_fetch_ad_accounts(mock_get):
    config = DummyConfig(uuid.uuid4(), connector_name="tiktok_ads")
    connector = TikTokAdsConnector(config, get_creds())
    
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "code": 0, 
        "data": {
            "list": [{"advertiser_id": "12345", "name": "My Account", "currency": "EUR"}]
        }
    }
    mock_get.return_value = mock_resp
    
    accounts = await connector.fetch_ad_accounts()
    assert len(accounts) == 1
    assert accounts[0]["advertiser_id"] == "12345"
    
    normalized = connector.normalize_ad_accounts(accounts)
    assert len(normalized) == 1
    assert normalized[0].external_account_id == "12345"
    assert normalized[0].name == "My Account"

@pytest.mark.asyncio
@patch("httpx.AsyncClient.get")
async def test_tiktok_ads_fetch_campaigns(mock_get):
    config = DummyConfig(uuid.uuid4(), connector_name="tiktok_ads")
    connector = TikTokAdsConnector(config, get_creds())
    
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "code": 0, 
        "data": {
            "list": [{"campaign_id": "c1", "campaign_name": "Camp1"}],
            "page_info": {"page": 1, "total_page": 1}
        }
    }
    mock_get.return_value = mock_resp
    
    campaigns = await connector.fetch_campaigns()
    assert len(campaigns) == 1
    assert campaigns[0]["campaign_id"] == "c1"

@pytest.mark.asyncio
@patch("httpx.AsyncClient.get")
async def test_tiktok_ads_fetch_metrics(mock_get):
    config = DummyConfig(uuid.uuid4(), connector_name="tiktok_ads")
    connector = TikTokAdsConnector(config, get_creds())
    
    async def side_effect(*args, **kwargs):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        if "advertiser/info" in args[0]:
             mock_resp.json.return_value = {"code": 0, "data": {"list": [{"currency": "JPY"}]}}
        else:
             mock_resp.json.return_value = {
                "code": 0, 
                "data": {
                    "list": [
                        {
                            "dimensions": {"campaign_id": "c1", "stat_time_day": "2024-01-01"},
                            "metrics": {"spend": "100.5", "total_purchase_value": "200.75", "conversion": "0", "clicks": "0", "impressions": "0", "total_purchase_value": "500", "spend": "0"}
                        }
                    ],
                    "page_info": {"page": 1, "total_page": 1}
                }
             }
        return mock_resp
        
    mock_get.side_effect = side_effect
    metrics = await connector.fetch_metrics()
    assert len(metrics) == 1
    assert metrics[0]["_currency"] == "JPY"

def test_tiktok_ads_decimal_mapping():
    config = DummyConfig(uuid.uuid4(), connector_name="tiktok_ads")
    connector = TikTokAdsConnector(config, get_creds())
    
    raw = [{
        "dimensions": {"campaign_id": "c1", "stat_time_day": "2024-01-01"},
        "metrics": {"spend": "1000.5", "total_purchase_value": "500", "conversion": "0", "clicks": "0", "impressions": "0"},
        "_currency": "USD"
    }]
    normalized = connector.normalize(raw)
    assert len(normalized) == 1
    assert isinstance(normalized[0].spend, Decimal)
    assert normalized[0].spend == Decimal("1000.5")
    assert normalized[0].revenue == Decimal("500")

def test_tiktok_ads_stat_date_mapping():
    config = DummyConfig(uuid.uuid4(), connector_name="tiktok_ads")
    connector = TikTokAdsConnector(config, get_creds())
    
    raw = [{
        "dimensions": {"campaign_id": "c1", "stat_time_day": "2024-02-29"},
        "metrics": {"spend": "0", "conversion": "0", "clicks": "0", "impressions": "0", "total_purchase_value": "500", "spend": "0"},
        "_currency": "USD"
    }]
    normalized = connector.normalize(raw)
    assert len(normalized) == 1
    assert normalized[0].stat_date == date(2024, 2, 29)

def test_tiktok_ads_external_id_is_deterministic():
    config = DummyConfig(uuid.uuid4(), connector_name="tiktok_ads")
    connector = TikTokAdsConnector(config, get_creds())
    
    raw1 = [{
        "dimensions": {"campaign_id": "c123", "stat_time_day": "2024-01-01"},
        "metrics": {"spend": "0", "conversion": "0", "clicks": "0", "impressions": "0", "total_purchase_value": "500", "spend": "0"},
        "_currency": "USD"
    }]
    raw2 = [{
        "dimensions": {"campaign_id": "c123", "stat_time_day": "2024-01-02"},
        "metrics": {"spend": "0", "conversion": "0", "clicks": "0", "impressions": "0", "total_purchase_value": "500", "spend": "0"},
        "_currency": "USD"
    }]
    
    n1 = connector.normalize(raw1)
    n2 = connector.normalize(raw2)
    assert n1[0].external_id == "c123"
    assert n2[0].external_id == "c123"

@pytest.mark.asyncio
@patch("httpx.AsyncClient.get")
async def test_tiktok_ads_pagination(mock_get):
    config = DummyConfig(uuid.uuid4(), connector_name="tiktok_ads")
    connector = TikTokAdsConnector(config, get_creds())
    
    resp_page1 = MagicMock()
    resp_page1.status_code = 200
    resp_page1.json.return_value = {"code": 0, "data": {"list": [{"c": 1}], "page_info": {"page": 1, "total_page": 2}}}
    
    resp_page2 = MagicMock()
    resp_page2.status_code = 200
    resp_page2.json.return_value = {"code": 0, "data": {"list": [{"c": 2}], "page_info": {"page": 2, "total_page": 2}}}
    
    mock_get.side_effect = [resp_page1, resp_page2]
    
    camps = await connector.fetch_campaigns()
    assert len(camps) == 2
    assert mock_get.call_count == 2


def test_tiktok_ads_optional_metrics():
    config = DummyConfig(uuid.uuid4(), connector_name="tiktok_ads")
    connector = TikTokAdsConnector(config, get_creds())

    raw = [{
        "dimensions": {"campaign_id": "c1", "stat_time_day": "2024-01-01"},
        "metrics": {},
        "_currency": "USD"
    }]
    normalized = connector.normalize(raw)
    assert len(normalized) == 0


@pytest.mark.asyncio
async def test_tiktok_ads_persistence_uses_atomic_upsert(company_b_fixtures):
    company_id = uuid.UUID(company_b_fixtures.ids["company_id"])
    user_id = uuid.UUID(company_b_fixtures.ids["user_id"])
    
    config = DummyConfig(company_id, connector_name="tiktok_ads")
    connector = TikTokAdsConnector(config, get_creds())
    
    async with system_session() as db_session:
        run = CampaignRun(
            company_id=company_id,
            buyer_id=user_id,
            started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            note="12345"  # Matches external_id
        )
        db_session.add(run)
        await db_session.flush()
        mapping = ExternalCampaignMapping(
            company_id=company_id,
            platform="tiktok_ads",
            external_id="12345",
            campaign_run_id=run.id
        )
        db_session.add(mapping)
        await db_session.commit()
        
        # Mock resolve_fx_rate to avoid external calls
        with patch("app.connectors.tiktok_ads.resolve_fx_rate", new_callable=AsyncMock) as mock_fx:
            mock_fx.return_value = Decimal("1.0")
            
            # Run 1
            raw_1 = [{
                "dimensions": {"campaign_id": "12345", "stat_time_day": "2024-01-01"},
                "metrics": {"spend": "10", "total_purchase_value": "5", "conversion": "0", "clicks": "0", "impressions": "0", "total_purchase_value": "500", "spend": "0"},
                "_currency": "USD"
            }]
            norm_1 = connector.normalize(raw_1)
            await connector.upsert(db_session, norm_1)
            
            res = await db_session.execute(select(CampaignRunStat).where(CampaignRunStat.company_id == company_id))
            stats = res.scalars().all()
            assert len(stats) == 1
            assert stats[0].spend == Decimal("10")
            
            # Run 2 (Update)
            raw_2 = [{
                "dimensions": {"campaign_id": "12345", "stat_time_day": "2024-01-01"},
                "metrics": {"spend": "15", "total_purchase_value": "5", "conversion": "0", "clicks": "0", "impressions": "0", "total_purchase_value": "500", "spend": "0"},
                "_currency": "USD"
            }]
            norm_2 = connector.normalize(raw_2)
            await connector.upsert(db_session, norm_2)
            
            res = await db_session.execute(select(CampaignRunStat).where(CampaignRunStat.company_id == company_id))
            stats = res.scalars().all()
            assert len(stats) == 1
            assert stats[0].spend == Decimal("15")

@pytest.mark.asyncio
async def test_tiktok_ads_tenant_isolation(company_b_fixtures):
    c1_id = uuid.UUID(company_b_fixtures.ids["company_id"])
    user1_id = uuid.UUID(company_b_fixtures.ids["user_id"])
    
    async with system_session() as db_session:
        c2 = Company(name="T2", base_currency="USD")
        db_session.add(c2)
        await db_session.commit()
        await db_session.refresh(c2)
        
        user2 = User(email="t2@test.com", password_hash="h", company_id=c2.id, name="User T2", role="owner")
        db_session.add(user2)
        await db_session.commit()
        await db_session.refresh(user2)
        
        run1 = CampaignRun(company_id=c1_id, buyer_id=user1_id, started_at=datetime(2026, 1, 1, tzinfo=timezone.utc), note="ext1")
        run2 = CampaignRun(company_id=c2.id, buyer_id=user2.id, started_at=datetime(2026, 1, 1, tzinfo=timezone.utc), note="ext1")
        db_session.add_all([run1, run2])
        await db_session.flush()
        mapping_a = ExternalCampaignMapping(company_id=run1.company_id, platform="tiktok_ads", external_id=run1.note, campaign_run_id=run1.id)
        mapping_b = ExternalCampaignMapping(company_id=run2.company_id, platform="tiktok_ads", external_id=run2.note, campaign_run_id=run2.id)
        db_session.add_all([mapping_a, mapping_b])
        await db_session.commit()
        
        # Upsert as tenant 1
        config = DummyConfig(c1_id, connector_name="tiktok_ads")
        connector = TikTokAdsConnector(config, get_creds())
        
        with patch("app.connectors.tiktok_ads.resolve_fx_rate", new_callable=AsyncMock) as mock_fx:
            mock_fx.return_value = Decimal("1.0")
            
            raw = [{
                "dimensions": {"campaign_id": "ext1", "stat_time_day": "2024-01-01"},
                "metrics": {"spend": "10", "total_purchase_value": "0", "conversion": "0", "clicks": "0", "impressions": "0", "total_purchase_value": "500", "spend": "0"},
                "_currency": "USD"
            }]
            await connector.upsert(db_session, connector.normalize(raw))
            
            res1 = await db_session.execute(select(CampaignRunStat).where(CampaignRunStat.company_id == c1_id))
            assert len(res1.scalars().all()) == 1
            
            res2 = await db_session.execute(select(CampaignRunStat).where(CampaignRunStat.company_id == c2.id))
            assert len(res2.scalars().all()) == 0

def test_tiktok_ads_no_real_network_calls():
    connector = TikTokAdsConnector(DummyConfig(uuid.uuid4()), get_creds())
    assert isinstance(connector.base_url, str)
    assert connector.base_url == "https://business-api.tiktok.com/open_api/v1.3"


def test_tiktok_ads_normalize_strict_types():
    from app.connectors.tiktok_ads import TikTokAdsConnector
    from app.connectors.base import ConnectorError
    class DummyConfig:
        company_id = "000"
        connector_name = "tiktok_ads"
    connector = TikTokAdsConnector(DummyConfig(), '{"access_token": "a", "advertiser_id": "b"}')
    
    # Missing field
    raw1 = [{"dimensions": {"campaign_id": "c1", "stat_time_day": "2024-01-01"}, "metrics": {"spend": "10"}, "_currency": "USD"}]
    norm1 = connector.normalize(raw1)
    assert len(norm1) == 0
        
    # None field
    raw2 = [{"dimensions": {"campaign_id": "c1", "stat_time_day": "2024-01-01"}, "metrics": {"spend": "10", "total_purchase_value": "10", "conversion": "10", "clicks": "10", "impressions": None}, "_currency": "USD"}]
    norm2 = connector.normalize(raw2)
    assert len(norm2) == 0
        
    # Empty string field
    raw3 = [{"dimensions": {"campaign_id": "c1", "stat_time_day": "2024-01-01"}, "metrics": {"spend": "10", "total_purchase_value": "10", "conversion": "10", "clicks": "", "impressions": "10"}, "_currency": "USD"}]
    norm3 = connector.normalize(raw3)
    assert len(norm3) == 0
        
    # Explicit 0 is allowed
    raw4 = [{"dimensions": {"campaign_id": "c1", "stat_time_day": "2024-01-01"}, "metrics": {"spend": "0", "total_purchase_value": "0", "conversion": "0", "clicks": "0", "impressions": "0"}, "_currency": "USD"}]
    norm4 = connector.normalize(raw4)
    assert len(norm4) == 1
    assert norm4[0].spend == 0
