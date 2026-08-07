from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid
from typing import List
from datetime import date

from app.core.deps import get_tenant_session, get_current_user_company_id, get_current_user, UserCtx
from app.db.models.campaigns import AdAccount
from app.schemas.campaigns import AdAccountCreate, AdAccountUpdate, AdAccountOut
from app.services.audit import record_user_audit

router = APIRouter(prefix="/ad-accounts", tags=["ad-accounts"])

@router.post("/", response_model=AdAccountOut)
async def create_ad_account(
    request: Request,
    account_in: AdAccountCreate,
    db: AsyncSession = Depends(get_tenant_session),
    user: UserCtx = Depends(get_current_user)
):
    account = AdAccount(
        **account_in.model_dump(),
        company_id=uuid.UUID(user.company_id)
    )
    db.add(account)
    await db.flush()
    await record_user_audit(
        session=db, user=user, entity_type="ad_account", entity_id=account.id, action="create", 
        old_state=None, new_state=account_in.model_dump(), request_id=request.headers.get("x-request-id"), ip_address=request.client.host if request.client else None
    )
    return account

@router.get("/", response_model=List[AdAccountOut])
async def list_ad_accounts(
    db: AsyncSession = Depends(get_tenant_session),
    company_id: str = Depends(get_current_user_company_id)
):
    result = await db.execute(select(AdAccount))
    return result.scalars().all()

@router.get("/{account_id}", response_model=AdAccountOut)
async def get_ad_account(
    account_id: uuid.UUID,
    db: AsyncSession = Depends(get_tenant_session),
    company_id: str = Depends(get_current_user_company_id)
):
    account = await db.get(AdAccount, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="AdAccount not found")
    return account

@router.patch("/{account_id}", response_model=AdAccountOut)
async def update_ad_account(
    request: Request,
    account_id: uuid.UUID,
    account_in: AdAccountUpdate,
    db: AsyncSession = Depends(get_tenant_session),
    user: UserCtx = Depends(get_current_user)
):
    account = await db.get(AdAccount, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="AdAccount not found")
        
    update_data = account_in.model_dump(exclude_unset=True)
    old_state = {k: getattr(account, k) for k in update_data.keys()}
    
    for field, value in update_data.items():
        setattr(account, field, value)
        
    await db.flush()
    await record_user_audit(
        session=db, user=user, entity_type="ad_account", entity_id=account.id, action="update", 
        old_state=old_state, new_state=update_data, request_id=request.headers.get("x-request-id"), ip_address=request.client.host if request.client else None
    )
    return account

@router.get("/{account_id}/cost")
async def get_account_cost(
    account_id: uuid.UUID,
    date_from: date | None = None,
    date_to: date | None = None,
    db: AsyncSession = Depends(get_tenant_session),
    company_id: str = Depends(get_current_user_company_id)
):
    from app.services.campaigns import get_ad_account_cost
    
    account = await db.get(AdAccount, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="AdAccount not found")
        
    cost = await get_ad_account_cost(db, account_id, date_from, date_to)
    return {"ad_account_id": account_id, "cost": str(cost)}

