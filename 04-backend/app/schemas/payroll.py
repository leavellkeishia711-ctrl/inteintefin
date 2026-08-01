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
