from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
import uuid
from typing import List

from app.core.deps import get_tenant_session, get_current_user_company_id
from app.db.models.campaigns import CampaignRunStat
from app.schemas.campaigns import CampaignRunStatCreate, CampaignRunStatOut

router = APIRouter(prefix="/campaign-run-stats", tags=["campaign-run-stats"])

@router.post("/upsert", response_model=CampaignRunStatOut)
async def upsert_campaign_run_stat(
    stat_in: CampaignRunStatCreate,
    db: AsyncSession = Depends(get_tenant_session),
    company_id: str = Depends(get_current_user_company_id)
):
    from app.services.campaigns import upsert_campaign_run_stat as svc_upsert
    
    try:
        upserted_stat = await svc_upsert(
            db=db,
            company_id=uuid.UUID(company_id),
            campaign_run_id=stat_in.campaign_run_id,
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

@router.get("/", response_model=List[CampaignRunStatOut])
async def list_campaign_run_stats(
    campaign_run_id: uuid.UUID = None,
    db: AsyncSession = Depends(get_tenant_session),
    company_id: str = Depends(get_current_user_company_id)
):
    query = select(CampaignRunStat)
    if campaign_run_id:
        query = query.where(CampaignRunStat.campaign_run_id == campaign_run_id)
        
    result = await db.execute(query)
    return result.scalars().all()
