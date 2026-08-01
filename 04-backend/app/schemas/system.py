from pydantic import BaseModel, ConfigDict
from datetime import date, datetime
import uuid
from typing import Optional
from app.schemas.types import Money, Rate, Ratio

class PartnerPayoutOut(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    network_id: uuid.UUID
    amount: Money
    currency: str
    fx_rate_to_base: Rate
    status: str
    booked_on: date
    model_config = ConfigDict(from_attributes=True)

class CompensationPlanOut(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    user_id: uuid.UUID
    base_salary: Money
    bonus_percent: Ratio
    bonus_basis: str
    quota_target: Optional[Money] = None
    rate_per_unit: Optional[Money] = None
    currency: str
    fx_rate_to_base: Rate
    effective_from: date
    effective_to: Optional[date] = None
    model_config = ConfigDict(from_attributes=True)

class PayrollRunOut(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    period_start: date
    period_end: date
    status: str
    total_amount: Money
    currency: str
    fx_rate_to_base: Rate
    model_config = ConfigDict(from_attributes=True)

class PayrollLineItemOut(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    payroll_run_id: uuid.UUID
    user_id: uuid.UUID
    base_amount: Money
    bonus_amount: Money
    total_amount: Money
    currency: str
    fx_rate_to_base: Rate
    status: str
    model_config = ConfigDict(from_attributes=True)

class DecisionRecommendationOut(BaseModel):
    recommendation_id: uuid.UUID
    company_id: uuid.UUID
    campaign_id: Optional[uuid.UUID] = None
    type: str
    vertical: Optional[str] = None
    geo: Optional[str] = None
    field: str
    current_value: Optional[Money] = None
    recommended_value: Money
    change_percent: Optional[Ratio] = None
    reasoning: str
    confidence_score: Ratio
    status: str
    created_by: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)
