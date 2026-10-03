import pytest
import uuid
from datetime import datetime, timezone, timedelta, date
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient, HTTPStatusError, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models.connectors import ConnectorConfig
from app.db.models.campaigns import CampaignRunStat, CampaignRun, ExternalCampaignMapping
from app.db.models.companies import Company
from app.connectors.scheduler import sync_connector_instance
from app.connectors.meta_ads import MetaAdsConnector
from app.connectors.tiktok_ads import TikTokAdsConnector
from app.connectors.binom import BinomConnector
from app.connectors.voluum import VoluumConnector
from app.connectors.affise import AffiseConnector
from app.connectors.base import UnauthorizedError
from app.api.v1.connectors import ConnectorCreate

pytestmark = pytest.mark.asyncio

class DummyConfig:
    def __init__(self, company_id, connector_name="dummy", settings=None):
        self.company_id = company_id
        self.connector_name = connector_name
        self.settings = settings or {}

# 1. test_tiktok_upsert_fx_signature
async def test_tiktok_upsert_fx_signature(company_b_fixtures, db_session: AsyncSession):
    comp_id = uuid.UUID(company_b_fixtures.ids["company_id"])
    run_id = uuid.UUID(company_b_fixtures.ids["campaign_run_id_2"])
    
    mapping = ExternalCampaignMapping(company_id=comp_id, platform="tiktok_ads", external_id="tk123", campaign_run_id=run_id)
    db_session.add(mapping)
    await db_session.commit()

    config = DummyConfig(comp_id, "tiktok_ads")
    connector = TikTokAdsConnector(config, "dummy_token")
    
    from app.connectors.base import NormalizedRecord
    record = NormalizedRecord(
        source="tiktok_ads", external_id="tk123", stat_date=date(2023,1,1),
        spend=10, revenue=20, currency="EUR", clicks=1, impressions=2, conversions=3
    )

    with patch("app.connectors.tiktok_ads.resolve_fx_rate", autospec=True) as mock_fx:
        mock_fx.return_value = 1.1
        await connector.upsert(db_session, [record])
        await db_session.commit()

    stats = (await db_session.execute(select(CampaignRunStat).where(CampaignRunStat.external_id == "tk123"))).scalars().all()
    assert len(stats) == 1

# 2. test_connectors_resolve_fx_rate_contract
async def test_connectors_resolve_fx_rate_contract(company_b_fixtures, db_session: AsyncSession):
    comp_id = uuid.UUID(company_b_fixtures.ids["company_id"])
    run_id = uuid.UUID(company_b_fixtures.ids["campaign_run_id_2"])

    connectors_info = [
        ("meta", MetaAdsConnector, "EUR"),
        ("tiktok_ads", TikTokAdsConnector, "EUR"),
        ("binom", BinomConnector, "USD"),
        ("voluum", VoluumConnector, "USD"),
        ("affise", AffiseConnector, "USD"),
    ]
    
    for platform, cls, curr in connectors_info:
        if cls is None: continue
        mapping = ExternalCampaignMapping(company_id=comp_id, platform=platform, external_id=f"ext_{platform}", campaign_run_id=run_id)
        db_session.add(mapping)
        await db_session.commit()
        
        config = DummyConfig(comp_id, platform, {"base_url": "http://x", "lookback_days": 7})
        connector = cls(config, "secret")
        
        from app.connectors.base import NormalizedRecord
        record = NormalizedRecord(source=platform, external_id=f"ext_{platform}", stat_date=date(2023,1,1), spend=10, revenue=20, currency=curr, clicks=1, impressions=2, conversions=3)
        
        module_path = cls.__module__
        with patch(f"{module_path}.resolve_fx_rate", autospec=True) as mock_fx:
            mock_fx.return_value = 1.0
            await connector.upsert(db_session, [record])
            await db_session.commit()

# 3. test_sync_rollback_on_fx_error
async def test_sync_rollback_on_fx_error(company_b_fixtures, db_session: AsyncSession):
    comp_id = uuid.UUID(company_b_fixtures.ids["company_id"])
    run_id = uuid.UUID(company_b_fixtures.ids["campaign_run_id_2"])
    
    mapping1 = ExternalCampaignMapping(company_id=comp_id, platform="meta", external_id="ext1", campaign_run_id=run_id)
    mapping2 = ExternalCampaignMapping(company_id=comp_id, platform="meta", external_id="ext2", campaign_run_id=run_id)
    db_session.add_all([mapping1, mapping2])
    
    config = ConnectorConfig(company_id=comp_id, connector_name="meta", encrypted_secret="x", status="active", retry_count=2)
    db_session.add(config)
    await db_session.commit()
    
    from app.connectors.base import NormalizedRecord
    rec1 = NormalizedRecord("meta", "ext1", date(2023,1,1), 1, 1, "USD", 1, 1, 1)
    rec2 = NormalizedRecord("meta", "ext2", date(2023,1,1), 1, 1, "EUR", 1, 1, 1)
    
    with patch("app.connectors.scheduler.get_connector_class") as mock_get_class:
        class FakeMeta(MetaAdsConnector):
            async def fetch_ad_accounts(self): return []
            def normalize_ad_accounts(self, r): return []
            async def fetch(self): return []
            def normalize(self, r): return [rec1, rec2]
            
        mock_get_class.return_value = FakeMeta
        
        with patch("app.connectors.meta_ads.resolve_fx_rate", autospec=True) as mock_fx:
            mock_fx.side_effect = [1.0, ValueError("No FX")]
            
            with patch("app.connectors.scheduler.decrypt_secret", return_value="secret"):
                await sync_connector_instance(str(comp_id), str(config.id))
                
    await db_session.refresh(config)
    assert config.retry_count == 3
    assert config.last_successful_sync is None
    
    stats = (await db_session.execute(select(CampaignRunStat).where(CampaignRunStat.company_id == comp_id))).scalars().all()
    assert len(stats) == 0

# 4. test_sync_rollback_on_unauthorized
async def test_sync_rollback_on_unauthorized(company_b_fixtures, db_session: AsyncSession):
    comp_id = uuid.UUID(company_b_fixtures.ids["company_id"])
    config = ConnectorConfig(company_id=comp_id, connector_name="meta", encrypted_secret="x", status="active")
    db_session.add(config)
    await db_session.commit()
    
    with patch("app.connectors.scheduler.get_connector_class") as mock_get_class:
        class FakeConn:
            def __init__(self, c, s): pass
            async def sync(self, db):
                raise UnauthorizedError("unauth")
        mock_get_class.return_value = FakeConn
        with patch("app.connectors.scheduler.decrypt_secret", return_value="secret"):
            await sync_connector_instance(str(comp_id), str(config.id))
            
    await db_session.refresh(config)
    assert config.status == "unauthorized"
    
# 5. test_meta_fetch_uses_explicit_daily_range
async def test_meta_fetch_uses_explicit_daily_range():
    config = DummyConfig(uuid.uuid4(), "meta", {"lookback_days": 3})
    connector = MetaAdsConnector(config, "secret")
    
    with patch.object(connector, "fetch_metrics") as mock_fetch:
        await connector.fetch()
        mock_fetch.assert_called_once()
        args, kwargs = mock_fetch.call_args
        assert len(args) == 2
        assert args[0] is not None
        assert args[1] is not None

# 6. test_meta_fetch_metrics_requires_dates
async def test_meta_fetch_metrics_requires_dates():
    config = DummyConfig(uuid.uuid4(), "meta")
    connector = MetaAdsConnector(config, "secret")
    with pytest.raises(ValueError):
        await connector.fetch_metrics()

# 7. test_meta_normalize_drops_aggregated_rows
def test_meta_normalize_drops_aggregated_rows():
    config = DummyConfig(uuid.uuid4(), "meta")
    connector = MetaAdsConnector(config, "secret")
    raw = [
        {
            "campaign_id": "1", "date_start": "2023-01-01", "date_stop": "2023-01-01",
            "spend": 10, "action_values": [], "actions": [], "_currency": "USD", "clicks": 1, "impressions": 1
        },
        {
            "campaign_id": "2", "date_start": "2023-01-01", "date_stop": "2023-01-05",
            "spend": 10, "action_values": [], "actions": [], "_currency": "USD", "clicks": 1, "impressions": 1
        }
    ]
    norm = connector.normalize(raw)
    assert len(norm) == 1
    assert norm[0].external_id == "1"

# 8. test_meta_lookback_validation
def test_meta_lookback_validation():
    with pytest.raises(ValueError):
        MetaAdsConnector(DummyConfig(uuid.uuid4(), "meta", {"lookback_days": 0}), "secret")
    with pytest.raises(ValueError):
        MetaAdsConnector(DummyConfig(uuid.uuid4(), "meta", {"lookback_days": 91}), "secret")
        
    c = MetaAdsConnector(DummyConfig(uuid.uuid4(), "meta"), "secret")
    assert c.lookback_days == 7

# 9. test_keitaro_create_blocked
async def test_keitaro_create_blocked(auth_client, company_b_fixtures):
    resp = await auth_client.post("/api/v1/connectors/", json={"connector_name": "keitaro", "secret": "123"})
    assert resp.status_code == 422
    assert "not available yet" in resp.json()["detail"]

# 10. test_keitaro_scheduler_pauses_existing
async def test_keitaro_scheduler_pauses_existing(company_b_fixtures, db_session: AsyncSession):
    comp_id = uuid.UUID(company_b_fixtures.ids["company_id"])
    config = ConnectorConfig(company_id=comp_id, connector_name="keitaro", encrypted_secret="x", status="active")
    db_session.add(config)
    await db_session.commit()
    
    await sync_connector_instance(str(comp_id), str(config.id))
    await db_session.refresh(config)
    assert config.status == "paused"
