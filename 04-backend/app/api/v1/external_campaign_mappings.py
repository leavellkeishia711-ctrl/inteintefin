from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import List, Optional
import uuid
from datetime import datetime, timezone

from app.core.deps import get_db, require_roles
from app.db.models.campaigns import ExternalCampaignMapping
from pydantic import BaseModel, ConfigDict
from sqlalchemy.exc import IntegrityError

router = APIRouter()

class ExternalCampaignMappingCreate(BaseModel):
    platform: str
    external_id: str
    campaign_run_id: uuid.UUID

class ExternalCampaignMappingResponse(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    platform: str
    external_id: str
    campaign_run_id: uuid.UUID
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

@router.post("/", response_model=ExternalCampaignMappingResponse, status_code=201)
async def create_mapping(
    mapping_in: ExternalCampaignMappingCreate,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_roles("owner"))
):
    new_mapping = ExternalCampaignMapping(
        company_id=user.company_id,
        platform=mapping_in.platform,
        external_id=mapping_in.external_id,
        campaign_run_id=mapping_in.campaign_run_id
    )
    db.add(new_mapping)
    try:
        await db.flush()
        # Do not commit here, let tenant_session handle it
        # flush is enough to trigger IntegrityError
        # also we need to return the object which will be committed later
        return new_mapping
    except IntegrityError:
        raise HTTPException(status_code=409, detail="Mapping already exists")

@router.get("/", response_model=List[ExternalCampaignMappingResponse])
async def get_mappings(
    platform: Optional[str] = Query(None),
    campaign_run_id: Optional[uuid.UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    user=Depends(require_roles("owner"))
):
    conditions = [
        ExternalCampaignMapping.company_id == user.company_id,
        ExternalCampaignMapping.deleted_at.is_(None)
    ]
    if platform:
        conditions.append(ExternalCampaignMapping.platform == platform)
    if campaign_run_id:
        conditions.append(ExternalCampaignMapping.campaign_run_id == campaign_run_id)
        
    stmt = select(ExternalCampaignMapping).where(and_(*conditions))
    res = await db.execute(stmt)
    return res.scalars().all()

@router.delete("/{mapping_id}", status_code=204)
async def delete_mapping(
    mapping_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_roles("owner"))
):
    stmt = select(ExternalCampaignMapping).where(
        and_(
            ExternalCampaignMapping.id == mapping_id,
            ExternalCampaignMapping.company_id == user.company_id,
            ExternalCampaignMapping.deleted_at.is_(None)
        )
    )
    res = await db.execute(stmt)
    mapping = res.scalars().first()
    
    if not mapping:
        raise HTTPException(status_code=404, detail="Mapping not found")
        
    mapping.deleted_at = datetime.now(timezone.utc)
    await db.flush()
    return None
