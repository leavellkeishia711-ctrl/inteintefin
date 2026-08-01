from fastapi import APIRouter, Depends
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_tenant_db
from app.schemas.payroll import PayrollResponse
from app.services.payroll import get_payroll_overview
import uuid

router = APIRouter()

@router.get("/", response_model=PayrollResponse)
async def get_payroll(db: AsyncSession = Depends(get_tenant_db)):
    company_id = uuid.UUID(db.info.get("company_id"))
    return await get_payroll_overview(db, company_id)

