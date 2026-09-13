
import pytest
import uuid
from decimal import Decimal
from datetime import date, datetime, timezone
from sqlalchemy.exc import IntegrityError
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.campaigns import CampaignRunStat, CampaignRun
from app.db.session import system_session, tenant_engine
from app.services.campaigns import get_campaign_stats, get_ad_account_cost
from app.services.metrics import get_spend_discrepancy
import httpx

@pytest.fixture
async def my_setup(client_a: httpx.AsyncClient):
    me_resp = await client_a.get("/api/v1/auth/me")
    assert me_resp.status_code == 200
    me_data = me_resp.json()
    company_id = uuid.UUID(me_data["company_id"])
    user_id = uuid.UUID(me_data["id"])
    
    async with system_session() as db:
        run = CampaignRun(
            company_id=company_id,
            buyer_id=user_id,
            started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        db.add(run)
        await db.commit()
        run_id = run.id
        
    return {
        "client": client_a,
        "company_id": company_id,
        "user_id": user_id,
        "run_id": run_id,
    }

@pytest.mark.asyncio
async def test_campaign_run_stat_soft_delete(my_setup):
    setup = my_setup
    company_id = setup["company_id"]
    run_id = setup["run_id"]
    client = setup["client"]
    
    # 1. Insert stat
    async with system_session() as db:
        stat = CampaignRunStat(
            company_id=company_id,
            campaign_run_id=run_id,
            stat_date=date(2026, 1, 1),
            spend=Decimal("100.0000"),
            revenue=Decimal("200.0000"),
            currency="USD",
            fx_rate_to_base=Decimal("1.00000000"),
            source="test_source",
            external_id="ext_1"
        )
        db.add(stat)
        await db.commit()
        stat_id = stat.id
        
    # Check it exists in API
    resp = await client.get("/api/v1/campaign-run-stats/")
    assert resp.status_code == 200
    assert any(s["id"] == str(stat_id) for s in resp.json())
    
    # 2. Soft delete it
    async with system_session() as db:
        res = await db.execute(sa.select(CampaignRunStat).where(CampaignRunStat.id == stat_id))
        stat = res.scalars().first()
        stat.deleted_at = datetime(2026, 1, 2, tzinfo=timezone.utc)
        db.add(stat)
        await db.commit()
        
    # 3. Assert it's gone from endpoints/services
    # api/v1/campaign_run_stats.list_campaign_run_stats
    resp = await client.get("/api/v1/campaign-run-stats/")
    assert resp.status_code == 200
    assert not any(s["id"] == str(stat_id) for s in resp.json())
    
    async with system_session() as db:
        # services.campaigns.get_campaign_stats
        stats_data = await get_campaign_stats(db, company_id, date(2026, 1, 1), date(2026, 1, 2))
        # Ensure it doesn't contain this stat
        assert not any(s["campaign_run_id"] == str(run_id) for s in stats_data)
        
        # services.metrics.get_spend_discrepancy
        discrepancy = await get_spend_discrepancy(db, company_id, date(2026, 1, 1), date(2026, 1, 2))
        assert discrepancy.get("total_source_spend", Decimal(0)) == Decimal(0)
        
    # 4. Physically exists
    async with system_session() as db:
        count_res = await db.execute(sa.text(f"SELECT COUNT(*) FROM campaign_run_stats WHERE id = '{stat_id}'"))
        count = count_res.scalar()
        assert count == 1

@pytest.mark.asyncio
async def test_campaign_run_stat_uniqueness_external_id_null(my_setup):
    setup = my_setup
    company_id = setup["company_id"]
    run_id = setup["run_id"]
    
    # 1. Insert first row (external_id=None)
    async with system_session() as db:
        stat1 = CampaignRunStat(
            company_id=company_id,
            campaign_run_id=run_id,
            stat_date=date(2026, 1, 1),
            spend=Decimal("10.0000"),
            revenue=Decimal("20.0000"),
            currency="USD",
            fx_rate_to_base=Decimal("1.00000000"),
            source="binom",
            external_id=None
        )
        db.add(stat1)
        await db.commit()
        stat1_id = stat1.id

    # 2. Try inserting duplicate -> IntegrityError
    async with system_session() as db:
        stat2 = CampaignRunStat(
            company_id=company_id,
            campaign_run_id=run_id,
            stat_date=date(2026, 1, 1),
            spend=Decimal("15.0000"),
            revenue=Decimal("25.0000"),
            currency="USD",
            fx_rate_to_base=Decimal("1.00000000"),
            source="binom",
            external_id=None
        )
        db.add(stat2)
        with pytest.raises(IntegrityError):
            await db.commit()
            
    # Verify via raw SQL COUNT = 1
    async with system_session() as db:
        count_res = await db.execute(sa.text(f"SELECT COUNT(*) FROM campaign_run_stats WHERE campaign_run_id = '{run_id}' AND stat_date = '2026-01-01' AND source = 'binom' AND external_id IS NULL"))
        assert count_res.scalar() == 1
        
    # 3. Soft delete first row
    async with system_session() as db:
        res = await db.execute(sa.select(CampaignRunStat).where(CampaignRunStat.id == stat1_id))
        stat = res.scalars().first()
        stat.deleted_at = datetime(2026, 1, 2, tzinfo=timezone.utc)
        await db.commit()
        
    # 4. Insert duplicate again -> MUST pass
    async with system_session() as db:
        stat3 = CampaignRunStat(
            company_id=company_id,
            campaign_run_id=run_id,
            stat_date=date(2026, 1, 1),
            spend=Decimal("15.0000"),
            revenue=Decimal("25.0000"),
            currency="USD",
            fx_rate_to_base=Decimal("1.00000000"),
            source="binom",
            external_id=None
        )
        db.add(stat3)
        await db.commit() # Should not raise
        
    # 5. Different source or stat_date does not conflict
    async with system_session() as db:
        stat4 = CampaignRunStat(
            company_id=company_id,
            campaign_run_id=run_id,
            stat_date=date(2026, 1, 2), # diff date
            spend=Decimal("0"), revenue=Decimal("0"), currency="USD", fx_rate_to_base=Decimal("1"), source="binom", external_id=None
        )
        stat5 = CampaignRunStat(
            company_id=company_id,
            campaign_run_id=run_id,
            stat_date=date(2026, 1, 1), 
            spend=Decimal("0"), revenue=Decimal("0"), currency="USD", fx_rate_to_base=Decimal("1"), source="other", external_id=None # diff source
        )
        db.add_all([stat4, stat5])
        await db.commit() # Should not raise

@pytest.mark.asyncio
async def test_tenant_isolation_campaign_run_stats(my_setup, client_b):
    company_a_id = my_setup["company_id"]
    run_a_id = my_setup["run_id"]
    
    # Insert for company A
    async with system_session() as db:
        stat_a = CampaignRunStat(
            company_id=company_a_id,
            campaign_run_id=run_a_id,
            stat_date=date(2026, 1, 1),
            spend=Decimal("10"), revenue=Decimal("20"), currency="USD", fx_rate_to_base=Decimal("1"),
            source="binom", external_id="ext_a"
        )
        db.add(stat_a)
        await db.commit()
        stat_a_id = stat_a.id

    # Find company B's id from client_b
    me_resp = await client_b.get("/api/v1/auth/me")
    assert me_resp.status_code == 200
    company_b_id = uuid.UUID(me_resp.json()["company_id"])
    user_b_id = uuid.UUID(me_resp.json()["id"])
    
    # Insert for company B
    async with system_session() as db:
        run_b = CampaignRun(company_id=company_b_id, buyer_id=user_b_id, started_at=datetime(2026,1,1,tzinfo=timezone.utc))
        db.add(run_b)
        await db.commit()
        run_b_id = run_b.id
        
        stat_b = CampaignRunStat(
            company_id=company_b_id,
            campaign_run_id=run_b_id,
            stat_date=date(2026, 1, 1),
            spend=Decimal("15"), revenue=Decimal("25"), currency="USD", fx_rate_to_base=Decimal("1"),
            source="binom", external_id="ext_b"
        )
        db.add(stat_b)
        await db.commit()
        stat_b_id = stat_b.id

    # Verify RLS with tenant session (requires db.begin() typically or explicit isolation)
    async with AsyncSession(tenant_engine) as session:
        # Start transaction to ensure set_config applies
        async with session.begin():
            await session.execute(sa.text(f"SELECT set_config('app.company_id', '{company_a_id}', true)"))
            
            # POSITIVE CONTROL: Can see its own stat
            res_a = await session.execute(sa.select(CampaignRunStat).where(CampaignRunStat.id == stat_a_id))
            assert res_a.scalars().first() is not None
            
            # TENANT ISOLATION: Cannot see company B's stat
            res_b = await session.execute(sa.select(CampaignRunStat).where(CampaignRunStat.id == stat_b_id))
            assert res_b.scalars().first() is None

@pytest.mark.asyncio
async def test_regression_old_index_different_external_ids(my_setup):
    company_id = my_setup["company_id"]
    run_id = my_setup["run_id"]
    
    # Insert with external_id="ext_1"
    async with system_session() as db:
        stat1 = CampaignRunStat(
            company_id=company_id,
            campaign_run_id=run_id,
            stat_date=date(2026, 1, 1),
            spend=Decimal("10"), revenue=Decimal("20"), currency="USD", fx_rate_to_base=Decimal("1"),
            source="binom", external_id="ext_1"
        )
        db.add(stat1)
        await db.commit()
        
    # Insert with external_id="ext_2" should PASS (no conflict)
    async with system_session() as db:
        stat2 = CampaignRunStat(
            company_id=company_id,
            campaign_run_id=run_id,
            stat_date=date(2026, 1, 1),
            spend=Decimal("15"), revenue=Decimal("25"), currency="USD", fx_rate_to_base=Decimal("1"),
            source="binom", external_id="ext_2"
        )
        db.add(stat2)
        await db.commit() # Should not raise
