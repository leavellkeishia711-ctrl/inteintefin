import pytest
from app.db.session import tenant_session
from app.db.models.connectors import ConnectorConfig
from sqlalchemy import select

@pytest.mark.asyncio
async def test_api_persistence_create(client_a):
    resp = await client_a.post("/api/v1/connectors/", json={
        "connector_name": "keitaro",
        "secret": "my-secret-key-123",
        "sync_interval_minutes": 60
    })
    assert resp.status_code == 201
    data = resp.json()
    conn_id = data["id"]
    
    # Read directly from DB in a new connection
    from jose import jwt
    from app.core.config import settings
    # decode the client token to find company_id
    token = client_a.headers["Authorization"].split(" ")[1]
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    company_id = payload.get("cid")
    
    async with tenant_session(company_id) as db:
        import uuid
        stmt = select(ConnectorConfig).where(ConnectorConfig.id == uuid.UUID(conn_id))
        res = await db.execute(stmt)
        config = res.scalars().first()
        assert config is not None
        assert config.connector_name == "keitaro"
        assert config.sync_interval_minutes == 60

@pytest.mark.asyncio
async def test_api_persistence_patch_status(client_a):
    resp = await client_a.post("/api/v1/connectors/", json={
        "connector_name": "keitaro",
        "secret": "my-secret",
        "sync_interval_minutes": 60
    })
    assert resp.status_code == 201
    conn_id = resp.json()["id"]

    resp2 = await client_a.patch(f"/api/v1/connectors/{conn_id}", json={
        "status": "paused",
        "sync_interval_minutes": 120
    })
    assert resp2.status_code == 200

    token = client_a.headers["Authorization"].split(" ")[1]
    from jose import jwt
    from app.core.config import settings
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    company_id = payload.get("cid")

    async with tenant_session(company_id) as db:
        import uuid
        stmt = select(ConnectorConfig).where(ConnectorConfig.id == uuid.UUID(conn_id))
        res = await db.execute(stmt)
        config = res.scalars().first()
        assert config.status == "paused"
        assert config.sync_interval_minutes == 120

@pytest.mark.asyncio
async def test_api_persistence_soft_delete(client_a):
    resp = await client_a.post("/api/v1/connectors/", json={
        "connector_name": "keitaro",
        "secret": "my-secret",
        "sync_interval_minutes": 60
    })
    assert resp.status_code == 201
    conn_id = resp.json()["id"]

    resp2 = await client_a.delete(f"/api/v1/connectors/{conn_id}")
    assert resp2.status_code == 204

    token = client_a.headers["Authorization"].split(" ")[1]
    from jose import jwt
    from app.core.config import settings
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    company_id = payload.get("cid")

    # DB verify
    async with tenant_session(company_id) as db:
        import uuid
        stmt = select(ConnectorConfig).where(ConnectorConfig.id == uuid.UUID(conn_id))
        res = await db.execute(stmt)
        config = res.scalars().first()
        assert config is not None
        assert config.deleted_at is not None
        assert config.status == "paused"

@pytest.mark.asyncio
async def test_sync_finds_campaign_via_mapping(client_a, monkeypatch):
    from app.db.models.campaigns import ExternalCampaignMapping, CampaignRunStat, CampaignRun
    from app.db.models.connectors import ConnectorConfig
    from sqlalchemy import select
    from app.connectors.meta_ads import MetaAdsConnector
    import uuid
    from decimal import Decimal
    from datetime import date, datetime, timezone
    from app.db.session import tenant_session, system_session
    
    me = await client_a.get("/api/v1/auth/me")
    company_id = uuid.UUID(me.json()["company_id"])
    user_id = uuid.UUID(me.json()["id"])
    run_id = uuid.uuid4()
    
    async with system_session() as db:
        run = CampaignRun(
            id=run_id,
            company_id=company_id,
            buyer_id=user_id,
            started_at=datetime.now(timezone.utc)
        )
        db.add(run)
        await db.commit()

    async with tenant_session(company_id) as db_session:
        # 1. Setup
        mapping = ExternalCampaignMapping(
            company_id=company_id,
            platform='meta',
            external_id='test_mapped_camp_xyz',
            campaign_run_id=run_id
        )
        db_session.add(mapping)
        await db_session.commit()
        
        # 2. Config
        config = ConnectorConfig(
            company_id=company_id,
            connector_name='meta',
            
            encrypted_secret='test',
            status='active'
        )
        
        # Mock fetch to return the specific external_id
        class MockMeta(MetaAdsConnector):
            async def fetch(self):
                return [{"source": "meta", "external_id": "test_mapped_camp_xyz", "stat_date": "2024-01-01", "spend": 100.0, "revenue": 50.0, "currency": "USD"}]
        
        connector = MockMeta(config, "secret")
        
        # Run sync stats part manually (mocking sync ad accounts)
        raw_data = await connector.fetch()
        normalized = connector.normalize(raw_data)
        await connector.upsert(db_session, normalized)
        
        # 3. Verify
        stmt = select(CampaignRunStat).where(
            CampaignRunStat.company_id == company_id,
            CampaignRunStat.external_id == "test_mapped_camp_xyz"
        )
        res = await db_session.execute(stmt)
        stat = res.scalars().first()
        
        assert stat is not None
        assert stat.campaign_run_id == run_id
        assert stat.spend == Decimal('100.0000')

@pytest.mark.asyncio
async def test_campaign_run_stat_persists_performance_metrics(system_session, client_a, tenant_a_id):
    # Create CampaignRun and Mapping
    from app.db.models.campaigns import CampaignRun, ExternalCampaignMapping, CampaignRunStat
    from app.connectors.base import NormalizedRecord
    from datetime import date
    
    run_id = uuid.uuid4()
    run = CampaignRun(id=run_id, company_id=tenant_a_id, campaign_name="Perf Metrics Test", status="active")
    system_session.add(run)
    await system_session.commit()
    
    mapping_id = uuid.uuid4()
    mapping = ExternalCampaignMapping(
        id=mapping_id,
        company_id=tenant_a_id,
        platform="meta_ads",
        external_id="perf-meta-1",
        campaign_run_id=run_id
    )
    system_session.add(mapping)
    await system_session.commit()
    
    # Do upsert
    from app.connectors.meta_ads import MetaAdsConnector
    class DummyConfig:
        company_id = tenant_a_id
        connector_name = "meta_ads"
    connector = MetaAdsConnector(DummyConfig(), '{"access_token":"a","account_id":"b"}')
    
    record = NormalizedRecord(
        source="meta",
        external_id="perf-meta-1",
        stat_date=date(2026, 1, 1),
        spend=Decimal("100"),
        revenue=Decimal("200"),
        currency="USD",
        clicks=150,
        impressions=10000,
        conversions=Decimal("5.5")
    )
    
    async with app.db.session.tenant_session(tenant_a_id) as session:
        await connector.upsert(session, [record])
        
        stmt = select(CampaignRunStat).where(CampaignRunStat.external_id == "perf-meta-1")
        res = await session.execute(stmt)
        stat = res.scalars().first()
        
        assert stat is not None
        assert stat.clicks == 150
        assert stat.impressions == 10000
        assert stat.conversions == Decimal("5.5")

@pytest.mark.asyncio
async def test_campaign_run_stat_atomic_update_refreshes_performance_metrics(system_session, client_a, tenant_a_id):
    from app.db.models.campaigns import CampaignRun, ExternalCampaignMapping, CampaignRunStat
    from app.connectors.base import NormalizedRecord
    from datetime import date
    
    run_id = uuid.uuid4()
    run = CampaignRun(id=run_id, company_id=tenant_a_id, campaign_name="Perf Update Test", status="active")
    system_session.add(run)
    await system_session.commit()
    
    mapping = ExternalCampaignMapping(
        id=uuid.uuid4(),
        company_id=tenant_a_id,
        platform="meta_ads",
        external_id="perf-meta-2",
        campaign_run_id=run_id
    )
    system_session.add(mapping)
    await system_session.commit()
    
    class DummyConfig:
        company_id = tenant_a_id
        connector_name = "meta_ads"
    from app.connectors.meta_ads import MetaAdsConnector
    connector = MetaAdsConnector(DummyConfig(), '{"access_token":"a","account_id":"b"}')
    
    record_a = NormalizedRecord(
        source="meta",
        external_id="perf-meta-2",
        stat_date=date(2026, 1, 1),
        spend=Decimal("100"),
        revenue=Decimal("200"),
        currency="USD",
        clicks=100,
        impressions=1000,
        conversions=Decimal("2")
    )
    
    async with app.db.session.tenant_session(tenant_a_id) as session:
        await connector.upsert(session, [record_a])
        
    record_b = NormalizedRecord(
        source="meta",
        external_id="perf-meta-2",
        stat_date=date(2026, 1, 1),
        spend=Decimal("150"),
        revenue=Decimal("250"),
        currency="USD",
        clicks=150,
        impressions=2000,
        conversions=Decimal("3")
    )
    
    async with app.db.session.tenant_session(tenant_a_id) as session:
        await connector.upsert(session, [record_b])
        
        stmt = select(CampaignRunStat).where(CampaignRunStat.external_id == "perf-meta-2")
        res = await session.execute(stmt)
        stats = res.scalars().all()
        
        assert len(stats) == 1
        stat = stats[0]
        assert stat.clicks == 150
        assert stat.impressions == 2000
        assert stat.conversions == Decimal("3")

@pytest.mark.asyncio
async def test_campaign_run_stat_legacy_rows_receive_zero_defaults(system_session, client_a, tenant_a_id):
    # This test verifies that inserting manually without specifying metrics defaults to 0
    from app.db.models.campaigns import CampaignRunStat, CampaignRun
    from datetime import date
    
    run_id = uuid.uuid4()
    run = CampaignRun(id=run_id, company_id=tenant_a_id, campaign_name="Legacy Default Test", status="active")
    system_session.add(run)
    await system_session.commit()
    
    # Direct insert simulating older code that doesn't provide clicks/impressions/conversions
    async with app.db.session.tenant_session(tenant_a_id) as session:
        stat = CampaignRunStat(
            company_id=tenant_a_id,
            campaign_run_id=run_id,
            stat_date=date(2026, 1, 2),
            spend=Decimal("50"),
            revenue=Decimal("100"),
            currency="USD",
            fx_rate_to_base=Decimal("1"),
            source="legacy",
            external_id="legacy-1"
        )
        session.add(stat)
        await session.commit()
        await session.refresh(stat)
        
        assert stat.clicks == 0
        assert stat.impressions == 0
        assert stat.conversions == Decimal("0")
