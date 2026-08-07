from fastapi import APIRouter, Depends
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.deps import get_tenant_session, get_current_user_company_id
from app.schemas.payroll import PayrollResponse
from app.services.payroll import get_payroll_overview
import uuid

router = APIRouter()

@router.get("/", response_model=PayrollResponse)
async def get_payroll(
    db: AsyncSession = Depends(get_tenant_session),
    company_id_str: str = Depends(get_current_user_company_id)
):
    company_id = uuid.UUID(company_id_str)
    return await get_payroll_overview(db, company_id)

from app.schemas.payroll import PayrollRunCreate, PayrollRunOut
from app.db.models import PayrollRun, PayrollLineItem
from sqlalchemy.orm import selectinload

@router.post("/runs", response_model=PayrollRunOut)
async def create_payroll_run(
    run_in: PayrollRunCreate,
    db: AsyncSession = Depends(get_tenant_session),
    company_id_str: str = Depends(get_current_user_company_id)
):
    from app.services.payroll import calculate_payroll_run
    company_id = uuid.UUID(company_id_str)
    run = await calculate_payroll_run(db, company_id, run_in.period_start, run_in.period_end)
    await db.commit()
    # Eager load line items for response
    await db.refresh(run, ["items"])
    return run

from fastapi import HTTPException

@router.get("/runs/{run_id}", response_model=PayrollRunOut)
async def get_payroll_run(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_tenant_session),
    company_id_str: str = Depends(get_current_user_company_id)
):
    from sqlalchemy import select
    company_id = uuid.UUID(company_id_str)
    run = await db.scalar(
        select(PayrollRun).options(selectinload(PayrollRun.items)).where(
            PayrollRun.id == run_id, 
            PayrollRun.company_id == company_id
        )
    )
    if not run:
        raise HTTPException(status_code=404, detail="PayrollRun not found")
    return run

