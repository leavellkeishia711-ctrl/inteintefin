import pytest
import uuid
from decimal import Decimal
from datetime import date
from sqlalchemy import text
from app.services.campaigns import get_ad_account_cost, upsert_campaign_run_stat
from app.db.models import Company, User, AdAccount, Consumable, CampaignRun

@pytest.mark.asyncio
async def test_get_ad_account_cost(app, client_a):
    from app.db.session import tenant_session, system_session
    import uuid
    
    company_id = uuid.uuid4()
    ad_account_id = uuid.uuid4()
    
    async with system_session() as db:
        async with db.begin():
            company = Company(id=company_id, name="Test Company", base_currency="USD")
            db.add(company)
            await db.flush()
            
            acc = AdAccount(id=ad_account_id, company_id=company_id, platform="facebook", status="active")
            db.add(acc)
            await db.flush()
            
            c1 = Consumable(company_id=company_id, type="proxy", ad_account_id=ad_account_id, cost=Decimal("10.00"), currency="USD", fx_rate_to_base=Decimal("1.0"), purchased_on=date.today())
            c2 = Consumable(company_id=company_id, type="other", ad_account_id=ad_account_id, cost=Decimal("5.00"), currency="EUR", fx_rate_to_base=Decimal("1.1"), purchased_on=date.today())
            
            db.add_all([c1, c2])
            
    async with tenant_session(str(company_id)) as db:
        cost = await get_ad_account_cost(db, company_id, ad_account_id)
        # 10.00 * 1.0 + 5.00 * 1.1 = 15.50
        assert cost == Decimal("15.5000")

@pytest.mark.asyncio
async def test_upsert_campaign_run_stat(app):
    from app.db.session import tenant_session, system_session
    company_id = uuid.uuid4()
    user_id = uuid.uuid4()
    run_id = uuid.uuid4()
    
    async with system_session() as db:
        async with db.begin():
            company = Company(id=company_id, name="Test Company", base_currency="USD")
            db.add(company)
            user = User(id=user_id, company_id=company_id, email="test@upsert.com", password_hash="h", name="t", role="owner")
            db.add(user)
            await db.flush()
            
            run = CampaignRun(id=run_id, company_id=company_id, buyer_id=user_id, started_at=text("now()"))
            db.add(run)

    async with tenant_session(str(company_id)) as db:
        stat1 = await upsert_campaign_run_stat(
            db, company_id, run_id, date.today(), "facebook", "ext1",
            spend=Decimal("100"), revenue=Decimal("150"), currency="USD", fx_rate_to_base=Decimal("1")
        )
        assert stat1.spend == Decimal("100")
        
        # Upsert with new spend
        stat2 = await upsert_campaign_run_stat(
            db, company_id, run_id, date.today(), "facebook", "ext1",
            spend=Decimal("120"), revenue=Decimal("150"), currency="USD", fx_rate_to_base=Decimal("1")
        )
        assert stat2.id == stat1.id
        assert stat2.spend == Decimal("120")
