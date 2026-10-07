from fastapi import APIRouter, Depends
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.deps import get_tenant_session, get_current_user_company_id
from app.schemas.partners import PartnersResponse
from app.services.partners import get_partners_overview
import uuid

router = APIRouter()

@router.get("/", response_model=PartnersResponse)
async def get_partners(
    db: AsyncSession = Depends(get_tenant_session),
    company_id_str: str = Depends(get_current_user_company_id)
):
    company_id = uuid.UUID(company_id_str)
    return await get_partners_overview(db, company_id)

