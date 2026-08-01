from pydantic import BaseModel
from typing import List
from app.schemas.types import Money
from decimal import Decimal
from datetime import date
from uuid import UUID

class AffiliateNetworkBase(BaseModel):
    id: UUID
    name: str
    payment_terms: str
    payout_model: str
    typical_hold_days: int

class PartnerPayoutItem(BaseModel):
    id: UUID
    network_id: UUID
    network_name: str
    campaign_id: UUID | None
    buyer_id: UUID | None
    expected_amount: Money
    actual_amount: Money
    scrubbed_amount: Money
    status: str
    booked_on: date
    hold_until: date | None
    paid_on: date | None

class ExpectedCashItem(BaseModel):
    date: date
    amount: Money

class PartnersResponse(BaseModel):
    kpi_total_booked: Money
    kpi_in_hold: Money
    kpi_net_confirmed: Money
    kpi_avg_scrub: Decimal
    networks: List[AffiliateNetworkBase]
    expected_cash: List[ExpectedCashItem]
    payouts: List[PartnerPayoutItem]

