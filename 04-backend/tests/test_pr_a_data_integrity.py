import pytest
import uuid
import json
from decimal import Decimal
from datetime import datetime, timezone, date, timedelta
from unittest.mock import patch, AsyncMock

from app.db.models.connectors import ConnectorConfig
from app.db.models.campaigns import CampaignRunStat, CampaignRun, ExternalCampaignMapping
from app.connectors.scheduler import sync_connector_instance
from app.connectors.meta_ads import MetaAdsConnector
from app.connectors.tiktok_ads import TikTokAdsConnector
from app.connectors.google_ads import GoogleAdsConnector
from app.connectors.binom import BinomConnector
from app.connectors.voluum import VoluumConnector
from app.connectors.affise import AffiseConnector
from app.connectors.base import UnauthorizedError, NormalizedRecord
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

pytestmark = pytest.mark.asyncio

class DummyConfig:
    def __init__(self, company_id, connector_name="dummy", settings=None):
        self.company_id = company_id
        self.connector_name = connector_name
        self.settings = settings or {}
        self.id = uuid.uuid4()

async def create_campaign_run(db_session: AsyncSession, company_id: str, user_id: str) -> uuid.UUID:
    run = CampaignRun(
        company_id=uuid.UUID(company_id),
        buyer_id=uuid.UUID(user_id),
        started_at=datetime.now(timezone.utc),
        status="active"
    )
    db_session.add(run)
    await db_session.flush()
    return run.id

# 1. test_tiktok_upsert_fx_signature
async def test_tiktok_upsert_fx_signature(company_b_fixtures, db_session: AsyncSession):
    comp_id = company_b_fixtures.ids["company_id"]
    user_id = company_b_fixtures.ids["user_id"]
    run_id = await create_campaign_run(db_session, comp_id, user_id)
    
    mapping = ExternalCampaignMapping(company_id=uuid.UUID(comp_id), platform="tiktok_ads", external_id="tk123", campaign_run_id=run_id)
    db_session.add(mapping)
    await db_session.commit()

    config = DummyConfig(comp_id, "tiktok_ads")
    decrypted_secret = json.dumps({"access_token": "t", "advertiser_id": "123"})
    connector = TikTokAdsConnector(config, decrypted_secret)
    
    record = NormalizedRecord(
        source="tiktok_ads", 
        external_id="tk123", 
        stat_date=date(2023,1,1),
        spend=Decimal("10.0000"), 
        revenue=Decimal("20.0000"), 
        currency="EUR", 
        clicks=1, 
        impressions=2, 
        conversions=Decimal("3.0000")
    )

    with patch("app.connectors.tiktok_ads.resolve_fx_rate", autospec=True) as mock_fx:
        mock_fx.return_value = Decimal("1.10000000")
        await connector.upsert(db_session, [record])
        await db_session.commit()
        mock_fx.assert_awaited_once_with(db_session, "EUR", "USD", date(2023, 1, 1))

    stats = (await db_session.execute(select(CampaignRunStat).where(CampaignRunStat.external_id == "tk123"))).scalars().all()
    assert len(stats) == 1

# 2. test_connectors_resolve_fx_rate_contract
@pytest.mark.parametrize("platform, cls, curr, settings, secret", [
    ("meta", MetaAdsConnector, "EUR", {"lookback_days": 7}, "secret"),
    ("google_ads", GoogleAdsConnector, "EUR", {}, json.dumps({"client_id":"c","client_secret":"s","refresh_token":"r","customer_id":"1234567890"})),
    ("tiktok_ads", TikTokAdsConnector, "EUR", {}, json.dumps({"access_token":"t","advertiser_id":"123"})),
    ("binom", BinomConnector, "USD", {"base_url":"http://binom.test","currency":"USD"}, "secret"),
    ("voluum", VoluumConnector, "USD", {"base_url":"http://voluum.test"}, "secret"),
    ("affise", AffiseConnector, "USD", {"base_url":"http://affise.test"}, "secret"),
])
async def test_connectors_resolve_fx_rate_contract(platform, cls, curr, settings, secret, company_b_fixtures, db_session: AsyncSession):
    comp_id = company_b_fixtures.ids["company_id"]
    user_id = company_b_fixtures.ids["user_id"]
    run_id = await create_campaign_run(db_session, comp_id, user_id)
    
    ext_id = f"ext_{platform}_{uuid.uuid4().hex[:6]}"
    mapping = ExternalCampaignMapping(company_id=uuid.UUID(comp_id), platform=platform, external_id=ext_id, campaign_run_id=run_id)
    db_session.add(mapping)
    await db_session.commit()
    
    config = DummyConfig(comp_id, platform, settings)
    connector = cls(config, secret)
    
    record = NormalizedRecord(
        source=platform, 
        external_id=ext_id, 
        stat_date=date(2023,1,1), 
        spend=Decimal("10.0000"), 
        revenue=Decimal("20.0000"), 
        currency=curr, 
        clicks=1, 
        impressions=2, 
        conversions=Decimal("3.0000")
    )
    
    module_path = cls.__module__
    with patch(f"{module_path}.resolve_fx_rate", autospec=True) as mock_fx:
        mock_fx.return_value = Decimal("1.00000000")
        await connector.upsert(db_session, [record])
        await db_session.commit()
        mock_fx.assert_awaited()

    stats = (await db_session.execute(select(CampaignRunStat).where(CampaignRunStat.external_id == ext_id))).scalars().all()
    assert len(stats) == 1

# 3. test_sync_rollback_on_fx_error
async def test_sync_rollback_on_fx_error(company_b_fixtures, db_session: AsyncSession):
    comp_id = company_b_fixtures.ids["company_id"]
    user_id = company_b_fixtures.ids["user_id"]
    run_id = await create_campaign_run(db_session, comp_id, user_id)
    
    mapping1 = ExternalCampaignMapping(company_id=uuid.UUID(comp_id), platform="meta", external_id="ext1_re", campaign_run_id=run_id)
    mapping2 = ExternalCampaignMapping(company_id=uuid.UUID(comp_id), platform="meta", external_id="ext2_re", campaign_run_id=run_id)
    db_session.add_all([mapping1, mapping2])
    
    config = ConnectorConfig(company_id=uuid.UUID(comp_id), connector_name="meta", encrypted_secret="x", status="active", retry_count=2, sync_interval_minutes=60)
    db_session.add(config)
    await db_session.commit()
    config_id = str(config.id)
    
    rec1 = NormalizedRecord(source="meta", external_id="ext1_re", stat_date=date(2023,1,1), spend=Decimal("1.0"), revenue=Decimal("1.0"), currency="USD", clicks=1, impressions=1, conversions=Decimal("1.0"))
    rec2 = NormalizedRecord(source="meta", external_id="ext2_re", stat_date=date(2023,1,1), spend=Decimal("1.0"), revenue=Decimal("1.0"), currency="EUR", clicks=1, impressions=1, conversions=Decimal("1.0"))
    
    with patch("app.connectors.scheduler.get_connector_class") as mock_get_class:
        class FakeMeta(MetaAdsConnector):
            def __init__(self, c, s): self.config = c
            async def fetch_ad_accounts(self): return []
            def normalize_ad_accounts(self, r): return []
            async def fetch(self): return []
            def normalize(self, r): return [rec1, rec2]
            
        mock_get_class.return_value = FakeMeta
        
        with patch("app.connectors.meta_ads.resolve_fx_rate", autospec=True) as mock_fx:
            mock_fx.side_effect = [Decimal("1.0"), ValueError("No FX")]
            
            with patch("app.connectors.scheduler.decrypt_secret", return_value="secret"), \
                 patch("app.connectors.scheduler.acquire_lock", return_value="token"), \
                 patch("app.connectors.scheduler.release_lock"):
                await sync_connector_instance(comp_id, config_id)
                
    await db_session.refresh(config)
    assert config.retry_count == 3
    assert config.status == "active"
    assert config.last_successful_sync is None
    
    stats = (await db_session.execute(select(CampaignRunStat).where(CampaignRunStat.external_id.in_(["ext1_re", "ext2_re"])))).scalars().all()
    assert len(stats) == 0

# 4. test_sync_rollback_on_unauthorized
async def test_sync_rollback_on_unauthorized(company_b_fixtures, db_session: AsyncSession):
    comp_id = company_b_fixtures.ids["company_id"]
    user_id = company_b_fixtures.ids["user_id"]
    run_id = await create_campaign_run(db_session, comp_id, user_id)
    mapping = ExternalCampaignMapping(company_id=uuid.UUID(comp_id), platform="meta", external_id="ext_ua", campaign_run_id=run_id)
    db_session.add(mapping)
    config = ConnectorConfig(company_id=uuid.UUID(comp_id), connector_name="meta", encrypted_secret="x", status="active", sync_interval_minutes=60)
    db_session.add(config)
    await db_session.commit()
    config_id = str(config.id)
    
    rec1 = NormalizedRecord(source="meta", external_id="ext_ua", stat_date=date(2023,1,1), spend=Decimal("1.0"), revenue=Decimal("1.0"), currency="USD", clicks=1, impressions=1, conversions=Decimal("1.0"))
    
    with patch("app.connectors.scheduler.get_connector_class") as mock_get_class:
        class FakeConn(MetaAdsConnector):
            def __init__(self, c, s): self.config = c
            async def sync(self, db):
                await self.upsert(db, [rec1])
                raise UnauthorizedError("unauth")
        mock_get_class.return_value = FakeConn
        with patch("app.connectors.meta_ads.resolve_fx_rate", autospec=True) as mock_fx:
            mock_fx.return_value = Decimal("1.0")
            with patch("app.connectors.scheduler.decrypt_secret", return_value="secret"), \
                 patch("app.connectors.scheduler.acquire_lock", return_value="token"), \
                 patch("app.connectors.scheduler.release_lock"):
                await sync_connector_instance(comp_id, config_id)
            
    await db_session.refresh(config)
    assert config.status == "unauthorized"
    assert config.next_sync_at is None
    stats = (await db_session.execute(select(CampaignRunStat).where(CampaignRunStat.external_id == "ext_ua"))).scalars().all()
    assert len(stats) == 0

# 5. test_sync_failing_after_threshold
async def test_sync_failing_after_threshold(company_b_fixtures, db_session: AsyncSession):
    comp_id = company_b_fixtures.ids["company_id"]
    config = ConnectorConfig(company_id=uuid.UUID(comp_id), connector_name="meta", encrypted_secret="x", status="active", retry_count=3, sync_interval_minutes=60)
    db_session.add(config)
    await db_session.commit()
    config_id = str(config.id)
    
    with patch("app.connectors.scheduler.get_connector_class") as mock_get_class:
        class FakeConn:
            def __init__(self, c, s): pass
            async def sync(self, db):
                raise Exception("err")
        mock_get_class.return_value = FakeConn
        with patch("app.connectors.scheduler.decrypt_secret", return_value="secret"), \
             patch("app.connectors.scheduler.acquire_lock", return_value="token"), \
             patch("app.connectors.scheduler.release_lock"):
            await sync_connector_instance(comp_id, config_id)
            
    await db_session.refresh(config)
    assert config.retry_count == 4
    assert config.status == "failing"

# 6. test_meta_fetch_uses_explicit_daily_range
async def test_meta_fetch_uses_explicit_daily_range():
    config = DummyConfig(uuid.uuid4(), "meta", {"lookback_days": 3})
    connector = MetaAdsConnector(config, "secret")
    
    with patch("app.connectors.meta_ads.datetime") as mock_dt:
        mock_dt.now.return_value = datetime(2026, 10, 3, tzinfo=timezone.utc)
        mock_dt.strptime.side_effect = datetime.strptime
        with patch.object(connector, "_fetch_all_pages", new_callable=AsyncMock) as mock_fetch_pages:
            mock_fetch_pages.return_value = []
            await connector.fetch()
            
            mock_fetch_pages.assert_awaited_once()
            url = mock_fetch_pages.call_args[0][0]
            assert "'since':'2026-10-01'" in url
            assert "'until':'2026-10-03'" in url
            assert ".time_increment(1)" in url
            assert "date_stop" in url

# 7. test_meta_fetch_metrics_requires_dates
async def test_meta_fetch_metrics_requires_dates():
    config = DummyConfig(uuid.uuid4(), "meta")
    connector = MetaAdsConnector(config, "secret")
    with pytest.raises(ValueError):
        await connector.fetch_metrics()

# 8. test_meta_normalize_drops_aggregated_rows
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
        },
        {
            "campaign_id": "3", "date_start": "2023-01-01", 
            "spend": 10, "action_values": [], "actions": [], "_currency": "USD", "clicks": 1, "impressions": 1
        }
    ]
    norm = connector.normalize(raw)
    assert len(norm) == 1
    assert norm[0].external_id == "1"

# 9. test_meta_lookback_validation
def test_meta_lookback_validation():
    with pytest.raises(ValueError):
        MetaAdsConnector(DummyConfig(uuid.uuid4(), "meta", {"lookback_days": 0}), "secret")
    with pytest.raises(ValueError):
        MetaAdsConnector(DummyConfig(uuid.uuid4(), "meta", {"lookback_days": 91}), "secret")
    with pytest.raises(ValueError):
        MetaAdsConnector(DummyConfig(uuid.uuid4(), "meta", {"lookback_days": "abc"}), "secret")
    with pytest.raises(ValueError):
        MetaAdsConnector(DummyConfig(uuid.uuid4(), "meta", {"lookback_days": None}), "secret")
    with pytest.raises(ValueError):
        MetaAdsConnector(DummyConfig(uuid.uuid4(), "meta", {"lookback_days": 7.5}), "secret")
        
    c = MetaAdsConnector(DummyConfig(uuid.uuid4(), "meta", {}), "secret")
    assert c.lookback_days == 7

# 10. test_keitaro_create_blocked
async def test_keitaro_create_blocked(auth_client, company_b_fixtures):
    resp = await auth_client.post("/api/v1/connectors/", json={"connector_name": "keitaro", "secret": "123"})
    assert resp.status_code == 422
    assert "not available yet" in resp.json()["detail"]

# 11. test_keitaro_scheduler_pauses_existing
async def test_keitaro_scheduler_pauses_existing(company_b_fixtures, db_session: AsyncSession):
    comp_id = company_b_fixtures.ids["company_id"]
    config = ConnectorConfig(company_id=uuid.UUID(comp_id), connector_name="keitaro", encrypted_secret="x", status="active", sync_interval_minutes=60)
    db_session.add(config)
    await db_session.commit()
    config_id = str(config.id)
    
    with patch("app.connectors.scheduler.get_connector_class") as mock_get_class:
        with patch("app.connectors.scheduler.acquire_lock", return_value="token"), \
             patch("app.connectors.scheduler.release_lock"):
            await sync_connector_instance(comp_id, config_id)
        mock_get_class.assert_not_called()
        
    await db_session.refresh(config)
    assert config.status == "paused"
    assert config.next_sync_at is None
