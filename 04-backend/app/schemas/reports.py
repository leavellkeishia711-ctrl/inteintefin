from pydantic import BaseModel
from typing import Optional
from app.schemas.types import Money

class HealthScoreResult(BaseModel):
    health_score: int

class SpendDiscrepancyResult(BaseModel):
    tracker_spend: Money
    actual_spend: Money
    discrepancy: Money
