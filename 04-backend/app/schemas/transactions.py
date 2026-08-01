from pydantic import BaseModel, ConfigDict
from datetime import date
from app.schemas.types import Money
import uuid

class TransactionOut(BaseModel):
    id: uuid.UUID
    type: str
    category: str
    amount: Money
    currency: str
    occurred_on: date
    description: str | None = None
    
    model_config = ConfigDict(from_attributes=True)

class TransactionListResponse(BaseModel):
    items: list[TransactionOut]
    total: int
    total_amount: Money
    page: int
    per_page: int
