from pydantic import BaseModel
from typing import List
from app.schemas.types import Money
from datetime import date
from uuid import UUID

class EmployeePayroll(BaseModel):
    user_id: UUID
    name: str
    role: str
    base_salary: Money
    bonus_amount: Money
    total_amount: Money
    status: str
    model_type: str = "Fixed"

class PayrollResponse(BaseModel):
    total_payroll: Money
    active_employees: int
    pending_approval: int
    employees: List[EmployeePayroll]

class PayrollRunCreate(BaseModel):
    period_start: date
    period_end: date
    
class PayrollLineItemOut(BaseModel):
    id: UUID
    user_id: UUID
    base_amount: Money
    bonus_amount: Money
    total_amount: Money
    currency: str
    status: str
    
    model_config = {"from_attributes": True}

class PayrollRunOut(BaseModel):
    id: UUID
    company_id: UUID
    period_start: date
    period_end: date
    total_amount: Money
    currency: str
    status: str
    items: List[PayrollLineItemOut] = []
    
    model_config = {"from_attributes": True}
