import pytest
import uuid
from decimal import Decimal
from datetime import date, timedelta
from app.services.pnl import calculate_pnl
from app.services.cashflow import calculate_cashflow
from app.services.metrics import get_health_score, get_spend_discrepancy
from app.db.models import Company, User, Transaction, PartnerPayout, CampaignRunStat, AdAccount, AffiliateNetwork

@pytest.mark.asyncio
async def test_pnl_calculation_and_rounding(app):
    from app.db.session import tenant_session, system_session
    company_id = uuid.uuid4()
    user_id = uuid.uuid4()
    
    async with system_session() as db:
        async with db.begin():
            db.add(Company(id=company_id, name="Test Company", base_currency="USD"))
            db.add(User(id=user_id, company_id=company_id, email="x@x.com", password_hash="h", name="t", role="owner"))
            await db.flush()
            
            # Revenue
            db.add(Transaction(company_id=company_id, type="income", category="payout_incoming", amount=Decimal("1000.1234"), currency="USD", fx_rate_to_base=Decimal("1"), occurred_on=date.today(), created_by=user_id))
            # Ad spend
            db.add(Transaction(company_id=company_id, type="expense", category="ad_spend", amount=Decimal("500.5678"), currency="USD", fx_rate_to_base=Decimal("1"), occurred_on=date.today(), created_by=user_id))
            # Consumables
            db.add(Transaction(company_id=company_id, type="expense", category="consumables", amount=Decimal("50.00"), currency="USD", fx_rate_to_base=Decimal("1"), occurred_on=date.today(), created_by=user_id))
            # Opex (salary)
            db.add(Transaction(company_id=company_id, type="expense", category="salary", amount=Decimal("100.00"), currency="USD", fx_rate_to_base=Decimal("1"), occurred_on=date.today(), created_by=user_id))
            # Tax
            db.add(Transaction(company_id=company_id, type="expense", category="tax", amount=Decimal("10.00"), currency="USD", fx_rate_to_base=Decimal("1"), occurred_on=date.today(), created_by=user_id))
            
    async with tenant_session(str(company_id)) as db:
        pnl = await calculate_pnl(db, company_id)
        
        # Checking intermediate exact math without premature rounding
        # Rev: 1000.1234 -> rounded 1000.12
        # Ad Spend: 500.5678 -> rounded 500.57
        # Gross profit: 1000.1234 - 500.5678 = 499.5556 -> 499.56
        assert pnl.revenue == Decimal("1000.12")
        assert pnl.ad_spend == Decimal("500.57")
        assert pnl.gross_profit == Decimal("499.56")
        
        # EBITDA: 499.5556 - 150 = 349.5556 -> 349.56
        assert pnl.ebitda == Decimal("349.56")
        
        # Net Profit: 349.5556 - 10 = 339.5556 -> 339.56
        assert pnl.net_profit == Decimal("339.56")
        
        # Margin: 339.5556 / 1000.1234 = 0.3395137... -> 0.3395
        assert pnl.margin == Decimal("0.3395")

@pytest.mark.asyncio
async def test_pnl_div_by_zero(app):
    from app.db.session import tenant_session, system_session
    company_id = uuid.uuid4()
    user_id = uuid.uuid4()
    
    async with system_session() as db:
        async with db.begin():
            db.add(Company(id=company_id, name="Test Company", base_currency="USD"))
            db.add(User(id=user_id, company_id=company_id, email="y@y.com", password_hash="h", name="t", role="owner"))
            await db.flush()
            
            # Expense only
            db.add(Transaction(company_id=company_id, type="expense", category="ad_spend", amount=Decimal("500"), currency="USD", fx_rate_to_base=Decimal("1"), occurred_on=date.today(), created_by=user_id))

    async with tenant_session(str(company_id)) as db:
        pnl = await calculate_pnl(db, company_id)
        assert pnl.revenue == Decimal("0.00")
        assert pnl.net_profit == Decimal("-500.00")
        assert pnl.margin is None

@pytest.mark.asyncio
async def test_cashflow_runway(app):
    from app.db.session import tenant_session, system_session
    company_id = uuid.uuid4()
    user_id = uuid.uuid4()
    net_id = uuid.uuid4()
    
    async with system_session() as db:
        async with db.begin():
            db.add(Company(id=company_id, name="Test Company", base_currency="USD"))
            db.add(User(id=user_id, company_id=company_id, email="z@z.com", password_hash="h", name="t", role="owner"))
            db.add(AffiliateNetwork(id=net_id, company_id=company_id, name="Net", payment_terms="net30", payout_model="cpa"))
            await db.flush()
            
            # Start balance: Income 5000
            db.add(Transaction(company_id=company_id, type="income", category="payout_incoming", amount=Decimal("5000"), currency="USD", fx_rate_to_base=Decimal("1"), occurred_on=date.today(), created_by=user_id))
            
            # Spend exactly 300 over the last 30 days (daily average 10)
            db.add(Transaction(company_id=company_id, type="expense", category="ad_spend", amount=Decimal("300"), currency="USD", fx_rate_to_base=Decimal("1"), occurred_on=date.today(), created_by=user_id))
            
            # Payout in hold: 700
            db.add(PartnerPayout(company_id=company_id, network_id=net_id, amount=Decimal("700"), expected_amount=Decimal("700"), currency="USD", fx_rate_to_base=Decimal("1"), status="in_hold", booked_on=date.today()))

    async with tenant_session(str(company_id)) as db:
        cf = await calculate_cashflow(db, company_id)
        
        # transaction balance: 5000 - 300 = 4700
        assert cf.transaction_balance == Decimal("4700.00")
        
        # held: 700
        assert cf.held_payouts == Decimal("700.00")
        
        # available: 4000
        assert cf.available_balance == Decimal("4000.00")
        
        # average spend: 300 / 30 = 10
        assert cf.average_daily_spend_30d == Decimal("10.00")
        
        # runway: 4000 / 10 = 400
        assert cf.runway_days == 400

@pytest.mark.asyncio
async def test_health_score_bounds(app):
    from app.db.session import tenant_session, system_session
    company_id = uuid.uuid4()
    user_id = uuid.uuid4()
    
    async with system_session() as db:
        async with db.begin():
            db.add(Company(id=company_id, name="Test Company", base_currency="USD"))
            db.add(User(id=user_id, company_id=company_id, email="w@w.com", password_hash="h", name="t", role="owner"))
            await db.flush()

    async with tenant_session(str(company_id)) as db:
        # No data -> Score should be around 10 (Trend 50 * 0.2 = 10, margin 0, runway 0)
        score = await get_health_score(db, company_id)
        assert score == 10
