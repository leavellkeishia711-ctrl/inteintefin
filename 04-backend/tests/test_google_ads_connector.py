import pytest
import uuid
import json
from decimal import Decimal
from datetime import datetime, timezone, date
from unittest.mock import patch, MagicMock, AsyncMock
import httpx

from sqlalchemy import select

from app.db.session import system_session
from app.db.models.companies import Company
from app.db.models.users import User
from app.db.models.campaigns import ExternalCampaignMapping, Campaign, CampaignRun, CampaignRunStat, AdAccount
from app.connectors.google_ads import GoogleAdsConnector
from app.connectors.base import UnauthorizedError

class DummyConfig:
    def __init__(self, company_id, connector_name="google_ads"):
        self.connector_name = connector_name
        self.company_id = company_id
        self.settings = {}

def create_valid_creds() -> str:
    return json.dumps({
        "developer_token": "dev_token_123",
        "client_id": "client_123",
        "client_secret": "secret_123",
        "refresh_token": "refresh_123",
        "customer_id": "123-456-7890",
        "login_customer_id": " 098-765-4321 "
    })

@pytest.fixture
def valid_connector():
    config = DummyConfig(uuid.uuid4(), connector_name="google_ads")
    return GoogleAdsConnector(config, create_valid_creds())

def mock_response(status_code: int, json_data: dict = None) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    if json_data is not None:
        resp.json.return_value = json_data
    return resp

def mock_http_error(status_code: int) -> httpx.HTTPStatusError:
    return httpx.HTTPStatusError(
        str(status_code),
        request=MagicMock(),
        response=mock_response(status_code)
    )

@pytest.mark.asyncio
@patch("httpx.AsyncClient.post")
async def test_google_ads_test_connection_success(mock_post):
    connector = GoogleAdsConnector(DummyConfig(uuid.uuid4()), create_valid_creds())
    connector.access_token = "valid_token"
    
    # Mock successful GAQL query
    mock_post.return_value = mock_response(200, {"results": []})
    
    result = await connector.test_connection()
    assert result is True
    
    mock_post.assert_called_once()
    args, kwargs = mock_post.call_args
    assert "https://googleads.googleapis.com/v25/customers/1234567890/googleAds:search" in args[0]
    
    # Assert headers
    headers = kwargs.get("headers", {})
    assert headers.get("Authorization") == "Bearer valid_token"
    assert headers.get("developer-token") == "dev_token_123"
    assert headers.get("login-customer-id") == "0987654321"
    
    # Assert query
    payload = kwargs.get("json", {})
    assert "SELECT customer.id" in payload.get("query", "")

@pytest.mark.asyncio
@patch("httpx.AsyncClient.post")
async def test_google_ads_test_connection_auth_failure(mock_post, monkeypatch):
    monkeypatch.setattr("app.connectors.base.asyncio.sleep", AsyncMock())
    connector = GoogleAdsConnector(DummyConfig(uuid.uuid4()), create_valid_creds())
    connector.access_token = "invalid_token"
    
    mock_post.side_effect = mock_http_error(401)
    
    with pytest.raises(UnauthorizedError) as exc_info:
        await connector.test_connection()
        
    err_msg = str(exc_info.value)
    # Ensure no secrets in the error message
    assert "dev_token_123" not in err_msg
    assert "secret_123" not in err_msg
    assert "invalid_token" not in err_msg
    assert "refresh_123" not in err_msg
    assert "Unauthorized" in err_msg

@pytest.mark.asyncio
@patch("httpx.AsyncClient.post")
async def test_google_ads_fetch_ad_accounts(mock_post):
    connector = GoogleAdsConnector(DummyConfig(uuid.uuid4()), create_valid_creds())
    connector.access_token = "valid_token"
    
    mock_post.return_value = mock_response(200, {
        "results": [
            {
                "customer": {
                    "id": "1234567890",
                    "descriptiveName": "Test Account",
                    "currencyCode": "USD",
                    "status": "ENABLED"
                }
            }
        ]
    })
    
    raw = await connector.fetch_ad_accounts()
    norm = connector.normalize_ad_accounts(raw)
    
    assert len(norm) == 1
    assert norm[0].platform == "google_ads"
    assert norm[0].external_account_id == "1234567890"
    assert norm[0].status == "active"
    assert norm[0].name == "Test Account"

@pytest.mark.asyncio
@patch("httpx.AsyncClient.post")
async def test_google_ads_fetch_campaigns(mock_post):
    connector = GoogleAdsConnector(DummyConfig(uuid.uuid4()), create_valid_creds())
    connector.access_token = "valid_token"
    
    mock_post.return_value = mock_response(200, {
        "results": [
            {
                "campaign": {
                    "id": "camp1",
                    "name": "Campaign 1",
                    "status": "ENABLED"
                }
            },
            {
                "campaign": {
                    "id": "camp2",
                    "name": "Campaign 2",
                    "status": "PAUSED"
                }
            }
        ]
    })
    
    raw = await connector.fetch_campaigns()
    assert len(raw) == 2
    assert raw[0]["campaign"]["id"] == "camp1"
    assert raw[1]["campaign"]["id"] == "camp2"

def test_google_ads_fetch_metrics_converts_micros_to_decimal(valid_connector):
    raw_data = [
        {
            "campaign": {"id": "c1"},
            "segments": {"date": "2026-09-10"},
            "metrics": {"costMicros": "1250000", "conversionsValue": "5.5", "conversions": "0", "clicks": "0", "impressions": "0", "conversions": "0", "clicks": "0", "impressions": "0"},
            "customer": {"currencyCode": "EUR"}
        }
    ]
    
    norm = valid_connector.normalize(raw_data)
    assert len(norm) == 1
    record = norm[0]
    
    # Assert type is exactly Decimal, not float
    assert type(record.spend) is Decimal
    assert type(record.revenue) is Decimal
    
    assert record.spend == Decimal("1.25")
    assert record.revenue == Decimal("5.5")

def test_google_ads_metrics_include_stat_date(valid_connector):
    raw_data = [
        {
            "campaign": {"id": "c1"},
            "segments": {"date": "2026-09-10"},
            "metrics": {"costMicros": "1250000", "conversionsValue": "5.5", "conversions": "0", "clicks": "0", "impressions": "0", "conversions": "0", "clicks": "0", "impressions": "0"},
            "customer": {"currencyCode": "EUR"}
        }
    ]
    
    norm = valid_connector.normalize(raw_data)
    assert len(norm) == 1
    assert norm[0].stat_date == date(2026, 9, 10)

def test_google_ads_external_id_is_deterministic(valid_connector):
    raw_data = [
        {
            "campaign": {"id": "c1"},
            "segments": {"date": "2026-09-10"},
            "metrics": {"costMicros": "1000000", "conversionsValue": "500", "conversions": "0", "clicks": "0", "impressions": "0"},
            "customer": {"currencyCode": "EUR"}
        }
    ]
    
    norm1 = valid_connector.normalize(raw_data)
    norm2 = valid_connector.normalize(raw_data)
    
    assert norm1[0].external_id == "c1"
    assert norm1[0].external_id == norm2[0].external_id

@pytest.mark.asyncio
@patch("httpx.AsyncClient.post")
async def test_google_ads_pagination(mock_post):
    connector = GoogleAdsConnector(DummyConfig(uuid.uuid4()), create_valid_creds())
    connector.access_token = "valid_token"
    
    page1 = mock_response(200, {
        "results": [{"campaign": {"id": "p1"}}],
        "nextPageToken": "token2"
    })
    
    page2 = mock_response(200, {
        "results": [{"campaign": {"id": "p2"}}],
        "nextPageToken": None
    })
    
    mock_post.side_effect = [page1, page2]
    
    results = await connector.fetch_metrics()
    assert len(results) == 2
    assert results[0]["campaign"]["id"] == "p1"
    assert results[1]["campaign"]["id"] == "p2"
    
    # Assert pageToken was sent on 2nd call
    assert mock_post.call_count == 2
    args2, kwargs2 = mock_post.call_args_list[1]
    assert kwargs2["json"]["pageToken"] == "token2"

def test_google_ads_optional_metrics(valid_connector):
    raw_data = [
        {
            "campaign": {"id": "c1"},
            "segments": {"date": "2026-09-10"},
            "metrics": {"costMicros": "1000000", "conversions": "0", "clicks": "0", "impressions": "0"},
            "customer": {"currencyCode": "USD"}
        }
    ]
    norm = valid_connector.normalize(raw_data)
    assert len(norm) == 0
    
@pytest.mark.asyncio
async def test_google_ads_persistence_uses_atomic_upsert(company_b_fixtures):
    # company_b_fixtures is used to prove we don't need to reinvent fixtures, but we'll create explicit data
    company_id = uuid.uuid4()
    user_id = uuid.uuid4()
    
    async with system_session() as db:
        comp = Company(id=company_id, name="GA Test", base_currency="USD")
        db.add(comp)
        
        u = User(id=user_id, name="ga_test", email="ga@test.com", password_hash="hash", company_id=company_id, role="admin")
        db.add(u)
        await db.flush()
        
        c = Campaign(id=uuid.uuid4(), company_id=company_id, assigned_user_id=user_id)
        db.add(c)
        await db.flush()
        
        run = CampaignRun(
            company_id=company_id,
            campaign_id=c.id,
            buyer_id=user_id,
            started_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
            note="ga_camp_1"
        )
        db.add(run)
        await db.flush()
        mapping = ExternalCampaignMapping(
            company_id=company_id,
            platform="google_ads",
            external_id="ga_camp_1",
            campaign_run_id=run.id
        )
        db.add(mapping)
        await db.commit()
        
        connector = GoogleAdsConnector(DummyConfig(company_id), create_valid_creds())
        
        raw_data = [
            {
                "campaign": {"id": "ga_camp_1"},
                "segments": {"date": "2026-09-10"},
                "metrics": {"costMicros": "1000000", "conversionsValue": "5.0", "conversions": "0", "clicks": "0", "impressions": "0"},
                "customer": {"currencyCode": "USD"}
            }
        ]
        
        # First sync
        norm = connector.normalize(raw_data)
        await connector.upsert(db, norm)
        await db.commit()
        
        stmt = select(CampaignRunStat).where(CampaignRunStat.campaign_run_id == run.id)
        rows = (await db.execute(stmt)).scalars().all()
        assert len(rows) == 1
        assert rows[0].spend == Decimal("1.00")
        assert rows[0].revenue == Decimal("5.00")
        
        # Second sync (Duplicate but updated data)
        raw_data[0]["metrics"]["costMicros"] = "2500000"
        norm2 = connector.normalize(raw_data)
        await connector.upsert(db, norm2)
        await db.commit()
        
        rows2 = (await db.execute(stmt)).scalars().all()
        assert len(rows2) == 1
        assert rows2[0].spend == Decimal("2.50")

@pytest.mark.asyncio
async def test_google_ads_tenant_isolation():
    # Use explicit new companies to ensure true isolation
    comp_a_id = uuid.uuid4()
    comp_b_id = uuid.uuid4()
    user_a_id = uuid.uuid4()
    user_b_id = uuid.uuid4()
    
    async with system_session() as db:
        db.add_all([
            Company(id=comp_a_id, name="GA Tenant A", base_currency="USD"),
            Company(id=comp_b_id, name="GA Tenant B", base_currency="USD")
        ])
        await db.flush()
        
        db.add_all([
            User(id=user_a_id, name="a", email="a@a.com", password_hash="hash", company_id=comp_a_id, role="admin"),
            User(id=user_b_id, name="b", email="b@b.com", password_hash="hash", company_id=comp_b_id, role="admin")
        ])
        await db.flush()
        
        c_a = Campaign(id=uuid.uuid4(), company_id=comp_a_id, assigned_user_id=user_a_id)
        c_b = Campaign(id=uuid.uuid4(), company_id=comp_b_id, assigned_user_id=user_b_id)
        db.add_all([c_a, c_b])
        await db.flush()
        
        run_a = CampaignRun(
            company_id=comp_a_id,
            campaign_id=c_a.id,
            buyer_id=user_a_id,
            started_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
            note="ga_shared_id"
        )
        run_b = CampaignRun(
            company_id=comp_b_id,
            campaign_id=c_b.id,
            buyer_id=user_b_id,
            started_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
            note="ga_shared_id"
        )
        db.add_all([run_a, run_b])
        await db.flush()
        mapping_a = ExternalCampaignMapping(company_id=run_a.company_id, platform="google_ads", external_id=run_a.note, campaign_run_id=run_a.id)
        mapping_b = ExternalCampaignMapping(company_id=run_b.company_id, platform="google_ads", external_id=run_b.note, campaign_run_id=run_b.id)
        db.add_all([mapping_a, mapping_b])
        await db.commit()
        
        connector_a = GoogleAdsConnector(DummyConfig(comp_a_id), create_valid_creds())
        
        raw_data = [
            {
                "campaign": {"id": "ga_shared_id"},
                "segments": {"date": "2026-09-10"},
                "metrics": {"costMicros": "1000000", "conversionsValue": "500", "conversions": "0", "clicks": "0", "impressions": "0"},
                "customer": {"currencyCode": "USD"}
            }
        ]
        norm = connector_a.normalize(raw_data)
        await connector_a.upsert(db, norm)
        await db.commit()
        
        # Verify A got the data, B did not
        res_a = (await db.execute(select(CampaignRunStat).where(CampaignRunStat.company_id == comp_a_id))).scalars().all()
        res_b = (await db.execute(select(CampaignRunStat).where(CampaignRunStat.company_id == comp_b_id))).scalars().all()
        
        assert len(res_a) == 1
        assert len(res_b) == 0


def test_google_ads_normalize_strict_types():
    from app.connectors.google_ads import GoogleAdsConnector
    from app.connectors.base import ConnectorError
    class DummyConfig:
        company_id = "000"
        connector_name = "google_ads"
    connector = GoogleAdsConnector(DummyConfig(), '{"developer_token": "a", "client_id": "b", "client_secret": "c", "refresh_token": "d", "customer_id": "e"}')
    
    # Missing field
    raw1 = [{"campaign": {"id": "c1"}, "segments": {"date": "2024-01-01"}, "customer": {"currencyCode": "USD"}, "metrics": {"costMicros": "100"}}]
    norm = connector.normalize(raw1)
    assert len(norm) == 0  # logger.warning and continue for Google
        
    # None field
    raw2 = [{"campaign": {"id": "c1"}, "segments": {"date": "2024-01-01"}, "customer": {"currencyCode": "USD"}, "metrics": {"costMicros": "10", "conversionsValue": "10", "conversions": "10", "clicks": "10", "impressions": None}}]
    norm2 = connector.normalize(raw2)
    assert len(norm2) == 0
        
    # Empty string field
    raw3 = [{"campaign": {"id": "c1"}, "segments": {"date": "2024-01-01"}, "customer": {"currencyCode": "USD"}, "metrics": {"costMicros": "10", "conversionsValue": "10", "conversions": "10", "clicks": "", "impressions": "10"}}]
    norm3 = connector.normalize(raw3)
    assert len(norm3) == 0
        
    # Explicit 0 is allowed
    raw4 = [{"campaign": {"id": "c1"}, "segments": {"date": "2024-01-01"}, "customer": {"currencyCode": "USD"}, "metrics": {"costMicros": "0", "conversionsValue": "0", "conversions": "0", "clicks": "0", "impressions": "0"}}]
    norm4 = connector.normalize(raw4)
    assert len(norm4) == 1
    assert norm4[0].spend == 0
