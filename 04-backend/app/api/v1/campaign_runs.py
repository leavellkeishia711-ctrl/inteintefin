from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid
from typing import List

from app.core.deps import get_tenant_session, get_current_user_company_id, get_current_user, UserCtx
from app.db.models.campaigns import CampaignRun
from app.schemas.campaigns import CampaignRunCreate, CampaignRunUpdate, CampaignRunOut
from app.services.audit import record_user_audit

router = APIRouter(prefix="/campaign-runs", tags=["campaign-runs"])

@router.post("/", response_model=CampaignRunOut)
async def create_campaign_run(
    request: Request,
    run_in: CampaignRunCreate,
    db: AsyncSession = Depends(get_tenant_session),
    user: UserCtx = Depends(get_current_user)
):
    run = CampaignRun(
        **run_in.model_dump(),
        company_id=uuid.UUID(user.company_id)
    )
    db.add(run)
    await db.flush()
    await record_user_audit(
        session=db, user=user, entity_type="campaign_run", entity_id=run.id, action="create", 
        old_state=None, new_state=run_in.model_dump(), request_id=request.headers.get("x-request-id"), ip_address=request.client.host if request.client else None
    )
    await db.commit()
    
    return run

@router.get("/", response_model=List[CampaignRunOut])
async def list_campaign_runs(
    db: AsyncSession = Depends(get_tenant_session),
    company_id: str = Depends(get_current_user_company_id)
):
    result = await db.execute(select(CampaignRun))
    return result.scalars().all()

@router.get("/{run_id}", response_model=CampaignRunOut)
async def get_campaign_run(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_tenant_session),
    company_id: str = Depends(get_current_user_company_id)
):
    run = await db.get(CampaignRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="CampaignRun not found")
    return run

@router.patch("/{run_id}", response_model=CampaignRunOut)
async def update_campaign_run(
    request: Request,
    run_id: uuid.UUID,
    run_in: CampaignRunUpdate,
    db: AsyncSession = Depends(get_tenant_session),
    user: UserCtx = Depends(get_current_user)
):
    run = await db.get(CampaignRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="CampaignRun not found")
        
    update_data = run_in.model_dump(exclude_unset=True)
    old_state = {k: getattr(run, k) for k in update_data.keys()}
    for field, value in update_data.items():
        setattr(run, field, value)
        
    await db.flush()
    await record_user_audit(
        session=db, user=user, entity_type="campaign_run", entity_id=run.id, action="update", 
        old_state=old_state, new_state=update_data, request_id=request.headers.get("x-request-id"), ip_address=request.client.host if request.client else None
    )
    await db.commit()
    
    return run

from app.schemas.campaigns import CampaignRunStatCreate, CampaignRunStatOut

@router.post("/{run_id}/stats", response_model=CampaignRunStatOut)
async def upsert_campaign_run_stat(
    run_id: uuid.UUID,
    stat_in: CampaignRunStatCreate,
    db: AsyncSession = Depends(get_tenant_session),
    company_id: str = Depends(get_current_user_company_id)
):
    from app.services.campaigns import upsert_campaign_run_stat as svc_upsert
    
    if stat_in.campaign_run_id != run_id:
        raise HTTPException(status_code=400, detail="campaign_run_id in body must match path")
        
    try:
        upserted_stat = await svc_upsert(
            db=db,
            company_id=uuid.UUID(company_id),
            campaign_run_id=run_id,
            stat_date=stat_in.stat_date,
            source=stat_in.source,
            external_id=stat_in.external_id,
            spend=stat_in.spend,
            revenue=stat_in.revenue,
            currency=stat_in.currency,
            fx_rate_to_base=stat_in.fx_rate_to_base
        )
        await db.commit()
        return upserted_stat
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to upsert CampaignRunStat: {str(e)}")
