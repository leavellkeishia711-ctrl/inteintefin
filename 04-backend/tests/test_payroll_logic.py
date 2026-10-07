import pytest
import uuid
from decimal import Decimal
from datetime import date
from app.db.models.system import CompensationPlan
from app.db.models.campaigns import CampaignRunStat, CampaignRun
from app.db.models import User
from app.services.payroll import calculate_payroll_run
from app.db.session import system_session

@pytest.mark.asyncio
async def test_payroll_fixed_base_salary():
    async with system_session() as db_session:
        company_id = uuid.uuid4()
        from app.db.models.companies import Company
        c1 = Company(id=company_id, name='PayrollCo', base_currency='EUR')
        db_session.add(c1)
        
        user_id = uuid.uuid4()
        user = User(id=user_id, company_id=company_id, email=f'{uuid.uuid4()}@x.com', password_hash='x', name='P1', role='buyer')
        db_session.add(user)
        await db_session.flush()
        
        comp = CompensationPlan(
            company_id=company_id,
            user_id=user_id,
            effective_from=date(2023, 1, 1),
            base_salary=Decimal('5000'),
            currency='USD',
            fx_rate_to_base=Decimal('0.9'), # 5000 USD * 0.9 = 4500 EUR
            bonus_basis='Fixed',
            bonus_percent=Decimal('0')
        )
        db_session.add(comp)
        await db_session.commit()
        
        run = await calculate_payroll_run(db_session, company_id, date(2023, 1, 1), date(2023, 1, 31))
        
        assert run.currency == 'EUR'
        assert run.total_amount == Decimal('4500.0000')
