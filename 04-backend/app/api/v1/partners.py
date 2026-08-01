from fastapi import APIRouter, Depends
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_tenant_db
from app.schemas.partners import PartnersResponse
from app.services.partners import get_partners_overview
import uuid

router = APIRouter()

@router.get("/", response_model=PartnersResponse)
async def get_partners(db: AsyncSession = Depends(get_tenant_db)):
    company_id = uuid.UUID(db.info.get("company_id"))
    return await get_partners_overview(db, company_id)

