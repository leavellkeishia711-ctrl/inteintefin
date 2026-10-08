import pytest
import uuid
from decimal import Decimal
from datetime import date
from app.db.models.system import PartnerPayout, AffiliateNetwork
from app.db.models.companies import Company
from app.services.partners import get_partners_overview
from app.db.session import system_session

@pytest.mark.asyncio
async def test_partner_kpi_fx_conversion():
    async with system_session() as db_session:
        company_id = uuid.uuid4()
        c1 = Company(id=company_id, name='Test Company KPI', base_currency='USD')
        db_session.add(c1)

        net1 = AffiliateNetwork(id=uuid.uuid4(), company_id=company_id, name='Net1', payment_terms='net30', payout_model='cpa')
        db_session.add(net1)
        await db_session.flush()

        # 100 EUR * 1.1 = 110 USD
        p1 = PartnerPayout(
            id=uuid.uuid4(),
            company_id=company_id,
            network_id=net1.id,
            campaign_id=None,
            buyer_id=None,
            amount=Decimal('100'),
            expected_amount=Decimal('100'),
            actual_amount=Decimal('100'),
            scrubbed_amount=Decimal('0'),
            currency='EUR',
            fx_rate_to_base=Decimal('1.1000'),
            status='paid',
            booked_on=date.today()
        )
        # 100 USD * 1.0 = 100 USD
        p2 = PartnerPayout(
            id=uuid.uuid4(),
            company_id=company_id,
            network_id=net1.id,
            campaign_id=None,
            buyer_id=None,
            amount=Decimal('100'),
            expected_amount=Decimal('100'),
            actual_amount=Decimal('100'),
            scrubbed_amount=Decimal('0'),
            currency='USD',
            fx_rate_to_base=Decimal('1.0000'),
            status='paid',
            booked_on=date.today()
        )

        db_session.add(p1)
        db_session.add(p2)
        await db_session.commit()

        overview = await get_partners_overview(db_session, company_id)
        assert overview.kpi_total_booked == Decimal('210.0000')
        assert overview.kpi_net_confirmed == Decimal('210.0000')
