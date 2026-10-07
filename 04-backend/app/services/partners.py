from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import uuid
from decimal import Decimal
from app.db.models.system import PartnerPayout, AffiliateNetwork
from app.schemas.partners import PartnersResponse, AffiliateNetworkBase, PartnerPayoutItem, ExpectedCashItem

async def get_partners_overview(db: AsyncSession, company_id: uuid.UUID) -> PartnersResponse:
    from app.core.money import quantize_money

    # 1. Get networks
    networks_result = await db.execute(
        select(AffiliateNetwork).where(AffiliateNetwork.company_id == company_id, AffiliateNetwork.deleted_at.is_(None))
    )
    networks_db = networks_result.scalars().all()
    
    networks = []
    network_map = {}
    for net in networks_db:
        networks.append(AffiliateNetworkBase(
            id=net.id,
            name=net.name,
            payment_terms=net.payment_terms,
            payout_model=net.payout_model,
            typical_hold_days=net.typical_hold_days
        ))
        network_map[net.id] = net.name

    # 2. Get payouts
    payouts_result = await db.execute(
        select(PartnerPayout).where(PartnerPayout.company_id == company_id, PartnerPayout.deleted_at.is_(None))
    )
    payouts_db = payouts_result.scalars().all()

    kpi_total_booked = Decimal("0")
    kpi_in_hold = Decimal("0")
    kpi_net_confirmed = Decimal("0")
    total_expected = Decimal("0")
    total_scrubbed = Decimal("0")

    payouts = []
    expected_cash = []

    for p in payouts_db:
        base_expected = quantize_money(p.expected_amount * p.fx_rate_to_base)
        base_actual = quantize_money(p.actual_amount * p.fx_rate_to_base)
        base_scrubbed = quantize_money(p.scrubbed_amount * p.fx_rate_to_base)

        payouts.append(PartnerPayoutItem(
            id=p.id,
            network_id=p.network_id,
            network_name=network_map.get(p.network_id, "Unknown"),
            campaign_id=p.campaign_id,
            buyer_id=p.buyer_id,
            expected_amount=base_expected,
            actual_amount=base_actual,
            scrubbed_amount=base_scrubbed,
            status=p.status,
            booked_on=p.booked_on,
            hold_until=p.hold_until,
            paid_on=p.paid_on
        ))
        
        kpi_total_booked += base_expected
        if p.status == 'in_hold':
            kpi_in_hold += base_expected
        if p.status == 'paid':
            kpi_net_confirmed += base_actual
            
        total_expected += base_expected
        total_scrubbed += base_scrubbed
        
        if p.hold_until and p.status != 'paid':
            expected_cash.append(ExpectedCashItem(date=p.hold_until, amount=base_expected - base_scrubbed))

    kpi_avg_scrub = Decimal("0")
    if total_expected > 0:
        kpi_avg_scrub = (total_scrubbed / total_expected * Decimal("100")).quantize(Decimal("0.01"))

    # Sort expected cash by date
    expected_cash.sort(key=lambda x: x.date)

    return PartnersResponse(
        kpi_total_booked=kpi_total_booked,
        kpi_in_hold=kpi_in_hold,
        kpi_net_confirmed=kpi_net_confirmed,
        kpi_avg_scrub=kpi_avg_scrub,
        networks=networks,
        expected_cash=expected_cash,
        payouts=payouts
    )

