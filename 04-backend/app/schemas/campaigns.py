from pydantic import BaseModel, ConfigDict, Field
from app.schemas.types import Money, Rate
from typing import Optional
from datetime import date, datetime
import uuid
class AdAccountBase(BaseModel):
    platform: str
    external_account_id: Optional[str] = None
    status: str = "active"
    vertical: Optional[str] = None
    geo: Optional[str] = None
    prepared_by_user_id: Optional[uuid.UUID] = None
    assigned_buyer_id: Optional[uuid.UUID] = None

class AdAccountCreate(AdAccountBase):
    pass

class AdAccountUpdate(AdAccountBase):
    platform: Optional[str] = None
    status: Optional[str] = None

class AdAccountOut(AdAccountBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    company_id: uuid.UUID
    banned_at: Optional[datetime] = None

# CampaignRun Schemas
class CampaignRunBase(BaseModel):
    campaign_id: Optional[uuid.UUID] = None
    ad_account_id: Optional[uuid.UUID] = None
    buyer_id: uuid.UUID
    started_at: datetime
    ended_at: Optional[datetime] = None
    status: str = "active"
    note: Optional[str] = None

class CampaignRunCreate(CampaignRunBase):
    pass

class CampaignRunUpdate(CampaignRunBase):
    buyer_id: Optional[uuid.UUID] = None
    started_at: Optional[datetime] = None
    status: Optional[str] = None

class CampaignRunOut(CampaignRunBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    company_id: uuid.UUID

# CampaignRunStat Schemas
class CampaignRunStatBase(BaseModel):
    campaign_run_id: uuid.UUID
    stat_date: date
    spend: Money = "0.00"
    revenue: Money = "0.00"
    currency: str
    fx_rate_to_base: Rate
    source: str
    external_id: Optional[str] = None

class CampaignRunStatCreate(CampaignRunStatBase):
    pass

class CampaignRunStatOut(CampaignRunStatBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    company_id: uuid.UUID

from pydantic import field_validator
import re

class ConsumableBase(BaseModel):
    type: str
    ad_account_id: Optional[uuid.UUID] = None
    identifier: Optional[str] = None
    cost: Money = "0.00"
    currency: str
    fx_rate_to_base: Rate
    purchased_on: date
    expires_on: Optional[date] = None
    status: str = "active"
    transaction_id: Optional[uuid.UUID] = None

    @field_validator('identifier')
    @classmethod
    def prevent_pan_storage(cls, v: Optional[str]) -> Optional[str]:
        if v:
            digits_only = re.sub(r'\D', '', v)
            if 13 <= len(digits_only) <= 19:
                raise ValueError("PAN cannot be stored unmasked")
        return v

class ConsumableCreate(ConsumableBase):
    pass

class ConsumableUpdate(ConsumableBase):
    type: Optional[str] = None
    currency: Optional[str] = None
    fx_rate_to_base: Optional[Rate] = None
    purchased_on: Optional[date] = None

class ConsumableOut(ConsumableBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    company_id: uuid.UUID

