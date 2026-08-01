from fastapi import APIRouter, Depends
from datetime import date
from typing import Annotated, Optional
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from app.core.deps import get_current_user_company_id, get_tenant_session

from app.services.pnl import calculate_pnl, PnLResult
from app.services.cashflow import calculate_cashflow, CashFlowResult
from app.services.metrics import get_health_score, get_spend_discrepancy
from app.schemas.reports import HealthScoreResult, SpendDiscrepancyResult

router = APIRouter(prefix="/reports", tags=["reports"])

@router.get("/pnl", response_model=PnLResult)
async def pnl_report(
    start_date: date,
    end_date: date,
    company_id: Annotated[str, Depends(get_current_user_company_id)],
    db: AsyncSession = Depends(get_tenant_session)
):
    return await calculate_pnl(db, uuid.UUID(company_id), start_date=start_date, end_date=end_date)

@router.get("/cash-flow", response_model=CashFlowResult)
async def cash_flow_report(
    as_of_date: Optional[date] = None,
    company_id: Annotated[str, Depends(get_current_user_company_id)] = None,
    db: AsyncSession = Depends(get_tenant_session)
):
    if not as_of_date:
        as_of_date = date.today()
    return await calculate_cashflow(db, uuid.UUID(company_id), as_of_date=as_of_date)

@router.get("/health", response_model=HealthScoreResult)
async def health_score_report(
    as_of_date: Optional[date] = None,
    company_id: Annotated[str, Depends(get_current_user_company_id)] = None,
    db: AsyncSession = Depends(get_tenant_session)
):
    score = await get_health_score(db, uuid.UUID(company_id), as_of_date=as_of_date)
    return {"health_score": score}

@router.get("/diagnostics/spend", response_model=SpendDiscrepancyResult)
async def spend_discrepancy_report(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    company_id: Annotated[str, Depends(get_current_user_company_id)] = None,
    db: AsyncSession = Depends(get_tenant_session)
):
    tracker, actual, diff = await get_spend_discrepancy(db, uuid.UUID(company_id), start_date=start_date, end_date=end_date)
    return SpendDiscrepancyResult(
        tracker_spend=tracker,
        actual_spend=actual,
        discrepancy=diff
    )
