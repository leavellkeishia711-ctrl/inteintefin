from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.deps import get_tenant_session, get_current_user_company_id
from app.db.models import Company
from pydantic import BaseModel
import uuid

router = APIRouter()

class SettingsResponse(BaseModel):
    company_name: str
    base_currency: str
    default_language: str
    integrations: list[dict]

@router.get("/", response_model=SettingsResponse)
async def get_settings(
    db: AsyncSession = Depends(get_tenant_session),
    company_id_str: str = Depends(get_current_user_company_id)
):
    company_id = uuid.UUID(company_id_str)
    
    company = await db.get(Company, company_id)
    if not company:
        # Fallback if somehow missing
        return SettingsResponse(
            company_name="Unknown",
            base_currency="USD",
            default_language="en",
            integrations=[]
        )
        
    return SettingsResponse(
        company_name=company.name,
        base_currency=company.base_currency,
        default_language=company.default_language,
        integrations=[
            {"id": "fb", "name": "Facebook Ads", "connected": True},
            {"id": "tt", "name": "TikTok Ads", "connected": False},
            {"id": "gg", "name": "Google Ads", "connected": True}
        ]
    )

