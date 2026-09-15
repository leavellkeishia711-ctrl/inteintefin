import pytest
import uuid
from decimal import Decimal
from datetime import date
from sqlalchemy import select, text
from app.db.session import tenant_session, system_session
from app.db.models.campaigns import CampaignRunStat, CampaignRunReconciliation, ExternalCampaignMapping, CampaignRun, Campaign
from app.db.models import Company
from app.services.reconciliation_persistence import upsert_reconciliation_for_group

pytestmark = pytest.mark.asyncio

@pytest.fixture
async def setup_company_and_run():
    async with system_session() as db:
        cid = uuid.uuid4()
        comp = Company(id=cid, name="Test Company", base_currency="USD")
        db.add(comp)
        await db.commit()
        
        c = Campaign(id=uuid.uuid4(), company_id=cid, name="C1")
        db.add(c)
        await db.commit()
        
        crun = CampaignRun(
            id=uuid.uuid4(),
            company_id=cid,
            campaign_id=c.id,
            buyer_id=uuid.uuid4(),
            started_at=date(2026, 1, 1),
            platform="meta"
        )
        db.add(crun)
        await db.commit()
        
        mapping = ExternalCampaignMapping(
            company_id=cid,
            platform="meta",
            external_id="ext_1",
            campaign_run_id=crun.id
        )
        db.add(mapping)
        await db.commit()
        
    return cid, crun.id

async def test_reconciliation_persists_single_result(setup_company_and_run):
    cid, crun_id = setup_company_and_run
    stat_date = date(2026, 9, 14)
    
    async with tenant_session(str(cid)) as db:
        stat = CampaignRunStat(
            company_id=cid,
            campaign_run_id=crun_id,
            stat_date=stat_date,
            source="voluum",
            external_id="ext_1",
            spend=Decimal("10.0"),
            revenue=Decimal("20.0"),
            currency="USD",
            fx_rate_to_base=Decimal("1.0"),
            clicks=10,
            impressions=100,
            conversions=Decimal("1")
        )
        db.add(stat)
        await db.flush()
        
        rec = await upsert_reconciliation_for_group(db, cid, crun_id, stat_date)
        await db.commit()
        
        assert rec.id is not None
        assert rec.status == "partial"
        assert rec.canonical_spend == Decimal("10.0")

async def test_reconciliation_upsert_is_idempotent(setup_company_and_run):
    cid, crun_id = setup_company_and_run
    stat_date = date(2026, 9, 14)
    
    async with tenant_session(str(cid)) as db:
        stat = CampaignRunStat(company_id=cid, campaign_run_id=crun_id, stat_date=stat_date, source="voluum", external_id="ext_1", spend=Decimal("10.0"), revenue=Decimal("20.0"), currency="USD", fx_rate_to_base=Decimal("1.0"))
        db.add(stat)
        await db.flush()
        
        r1 = await upsert_reconciliation_for_group(db, cid, crun_id, stat_date)
        r2 = await upsert_reconciliation_for_group(db, cid, crun_id, stat_date)
        
        assert r1.id == r2.id

async def test_reconciliation_updates_after_source_stat_changes(setup_company_and_run):
    cid, crun_id = setup_company_and_run
    stat_date = date(2026, 9, 14)
    
    async with tenant_session(str(cid)) as db:
        stat = CampaignRunStat(company_id=cid, campaign_run_id=crun_id, stat_date=stat_date, source="voluum", external_id="ext_1", spend=Decimal("10.0"), revenue=Decimal("20.0"), currency="USD", fx_rate_to_base=Decimal("1.0"))
        db.add(stat)
        await db.flush()
        r1 = await upsert_reconciliation_for_group(db, cid, crun_id, stat_date)
        
        stat.spend = Decimal("15.0")
        db.add(stat)
        await db.flush()
        
        r2 = await upsert_reconciliation_for_group(db, cid, crun_id, stat_date)
        assert r1.id == r2.id
        assert r2.canonical_spend == Decimal("15.0")

async def test_reconciliation_excludes_soft_deleted_source_stat(setup_company_and_run):
    cid, crun_id = setup_company_and_run
    stat_date = date(2026, 9, 14)
    
    async with tenant_session(str(cid)) as db:
        stat = CampaignRunStat(company_id=cid, campaign_run_id=crun_id, stat_date=stat_date, source="voluum", external_id="ext_1", spend=Decimal("10.0"), revenue=Decimal("20.0"), currency="USD", fx_rate_to_base=Decimal("1.0"), deleted_at=date(2026, 1, 1))
        db.add(stat)
        await db.flush()
        
        rec = await upsert_reconciliation_for_group(db, cid, crun_id, stat_date)
        assert rec.status == "no_data"
        assert rec.canonical_spend is None

async def test_reconciliation_unique_key_prevents_duplicate_results(setup_company_and_run):
    cid, crun_id = setup_company_and_run
    stat_date = date(2026, 9, 14)
    
    async with tenant_session(str(cid)) as db:
        # manual insert to test unique key
        from sqlalchemy.dialects.postgresql import insert
        stmt = insert(CampaignRunReconciliation).values(
            company_id=cid, campaign_run_id=crun_id, stat_date=stat_date,
            status="no_data", decision_reason="Test"
        )
        await db.execute(stmt)
        await db.flush()
        
        # Another insert without ON CONFLICT should fail with IntegrityError
        from sqlalchemy.exc import IntegrityError
        with pytest.raises(IntegrityError):
            await db.execute(stmt)

async def test_reconciliation_tenant_isolation(setup_company_and_run):
    cid_a, crun_id_a = setup_company_and_run
    stat_date = date(2026, 9, 14)
    
    async with system_session() as db:
        cid_b = uuid.uuid4()
        comp = Company(id=cid_b, name="Company B", base_currency="USD")
        db.add(comp)
        await db.commit()
        
    async with tenant_session(str(cid_a)) as db:
        stat = CampaignRunStat(company_id=cid_a, campaign_run_id=crun_id_a, stat_date=stat_date, source="voluum", external_id="ext_1", spend=Decimal("10.0"), revenue=Decimal("20.0"), currency="USD", fx_rate_to_base=Decimal("1.0"))
        db.add(stat)
        await db.flush()
        await upsert_reconciliation_for_group(db, cid_a, crun_id_a, stat_date)
        await db.commit()
        
    async with tenant_session(str(cid_b)) as db:
        # B should see 0 reconciliations
        res = await db.execute(select(CampaignRunReconciliation))
        assert len(res.scalars().all()) == 0

async def test_reconciliation_does_not_use_campaign_run_note(setup_company_and_run):
    cid, crun_id = setup_company_and_run
    stat_date = date(2026, 9, 14)
    
    async with tenant_session(str(cid)) as db:
        # The logic purely groups by campaign_run_id, note is irrelevant.
        res = await db.execute(select(CampaignRun).where(CampaignRun.id == crun_id))
        crun = res.scalars().first()
        crun.note = "Some note"
        await db.flush()
        
        stat = CampaignRunStat(company_id=cid, campaign_run_id=crun_id, stat_date=stat_date, source="voluum", external_id="ext_1", spend=Decimal("10.0"), revenue=Decimal("20.0"), currency="USD", fx_rate_to_base=Decimal("1.0"))
        db.add(stat)
        await db.flush()
        
        rec = await upsert_reconciliation_for_group(db, cid, crun_id, stat_date)
        assert rec.campaign_run_id == crun_id

async def test_reconciliation_uses_external_mapping_group(setup_company_and_run):
    cid, crun_id = setup_company_and_run
    stat_date = date(2026, 9, 14)
    
    async with tenant_session(str(cid)) as db:
        stat1 = CampaignRunStat(company_id=cid, campaign_run_id=crun_id, stat_date=stat_date, source="voluum", external_id="ext_1", spend=Decimal("10.0"), revenue=Decimal("20.0"), currency="USD", fx_rate_to_base=Decimal("1.0"))
        stat2 = CampaignRunStat(company_id=cid, campaign_run_id=crun_id, stat_date=stat_date, source="meta", external_id="ext_2", spend=Decimal("10.0"), revenue=Decimal("20.0"), currency="USD", fx_rate_to_base=Decimal("1.0"))
        db.add_all([stat1, stat2])
        await db.flush()
        
        rec = await upsert_reconciliation_for_group(db, cid, crun_id, stat_date)
        assert rec.observed_source_count == 2
        assert rec.status == "reconciled"
