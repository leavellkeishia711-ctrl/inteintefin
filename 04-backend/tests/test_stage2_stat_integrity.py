import pytest
from decimal import Decimal
from datetime import date
from sqlalchemy.exc import IntegrityError
import pytest
import uuid
from decimal import Decimal
from datetime import date
from sqlalchemy.exc import IntegrityError
import sqlalchemy as sa
from app.db.models.campaigns import CampaignRunStat, CampaignRun
from app.db.models import Company, User
from app.db.session import system_session, tenant_engine
from sqlalchemy.ext.asyncio import AsyncSession

@pytest.mark.asyncio
async def test_campaign_run_stat_soft_delete():
    company_id = uuid.uuid4()
    user_id = uuid.uuid4()
    
    async with system_session() as db:
        company = Company(id=company_id, name="Test Company A", base_currency="USD")
        user = User(id=user_id, company_id=company_id, name="User", email=f"{uuid.uuid4()}@a.com", password_hash="h", role="admin")
        db.add_all([company, user])
        await db.flush()
        
        run = CampaignRun(
            company_id=company.id,
            buyer_id=user.id,
            started_at=date(2026, 1, 1),
        )
        db.add(run)
        await db.flush()
        
        stat = CampaignRunStat(
            company_id=company.id,
            campaign_run_id=run.id,
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
        
    async with system_session() as db:
        res = await db.execute(sa.select(CampaignRunStat).where(CampaignRunStat.id == stat_id))
        stat = res.scalars().first()
        assert stat is not None
        
        stat.deleted_at = date(2026, 1, 2)
        db.add(stat)
        await db.commit()

@pytest.mark.asyncio
async def test_campaign_run_stat_uniqueness_external_id_null():
    company_id = uuid.uuid4()
    user_id = uuid.uuid4()
    
    async with system_session() as db:
        company = Company(id=company_id, name="Test Company A", base_currency="USD")
        user = User(id=user_id, company_id=company_id, name="User", email=f"{uuid.uuid4()}@a.com", password_hash="h", role="admin")
        db.add_all([company, user])
        await db.flush()
        
        run = CampaignRun(
            company_id=company.id,
            buyer_id=user.id,
            started_at=date(2026, 1, 1),
        )
        db.add(run)
        await db.commit()
        run_id = run.id
        
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

@pytest.mark.asyncio
async def test_tenant_isolation_campaign_run_stats():
    company_a_id = uuid.uuid4()
    company_b_id = uuid.uuid4()
    
    async with system_session() as db:
        ca = Company(id=company_a_id, name="A", base_currency="USD")
        cb = Company(id=company_b_id, name="B", base_currency="USD")
        ua = User(id=uuid.uuid4(), company_id=company_a_id, name="A", email=f"{uuid.uuid4()}@a.com", password_hash="h", role="admin")
        ub = User(id=uuid.uuid4(), company_id=company_b_id, name="B", email=f"{uuid.uuid4()}@b.com", password_hash="h", role="admin")
        db.add_all([ca, cb, ua, ub])
        await db.flush()
        
        run_a = CampaignRun(company_id=company_a_id, buyer_id=ua.id, started_at=date(2026,1,1))
        run_b = CampaignRun(company_id=company_b_id, buyer_id=ub.id, started_at=date(2026,1,1))
        db.add_all([run_a, run_b])
        await db.flush()
        
        stat_b = CampaignRunStat(
            company_id=company_b_id,
            campaign_run_id=run_b.id,
            stat_date=date(2026, 1, 1),
            spend=Decimal("15.0000"),
            revenue=Decimal("25.0000"),
            currency="USD",
            fx_rate_to_base=Decimal("1.00000000"),
            source="binom",
            external_id="ext_b"
        )
        db.add(stat_b)
        await db.commit()
        stat_b_id = stat_b.id
        
    async with AsyncSession(tenant_engine) as session:
        await session.execute(sa.text(f"SELECT set_config('app.company_id', '{company_a_id}', true)"))
        res = await session.execute(sa.select(CampaignRunStat).where(CampaignRunStat.id == stat_b_id))
        assert res.scalars().first() is None
