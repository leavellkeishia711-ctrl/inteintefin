from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid
from typing import List

from app.core.deps import get_tenant_session, get_current_user_company_id, get_current_user, UserCtx
from app.db.models.campaigns import Consumable
from app.schemas.campaigns import ConsumableCreate, ConsumableUpdate, ConsumableOut
from app.services.audit import record_user_audit
from datetime import date

router = APIRouter(prefix="/consumables", tags=["consumables"])

@router.post("/", response_model=ConsumableOut)
async def create_consumable(
    request: Request,
    consumable_in: ConsumableCreate,
    db: AsyncSession = Depends(get_tenant_session),
    user: UserCtx = Depends(get_current_user)
):
    consumable = Consumable(
        **consumable_in.model_dump(),
        company_id=uuid.UUID(user.company_id)
    )
    db.add(consumable)
    await db.flush()
    
    await record_user_audit(
        session=db, user=user, entity_type="consumable", entity_id=consumable.id, action="create", 
        old_state=None, new_state=consumable_in.model_dump(mode="json"), request_id=request.headers.get("x-request-id"), ip_address=request.client.host if request.client else None
    )
    return consumable

@router.get("/", response_model=List[ConsumableOut])
async def list_consumables(
    db: AsyncSession = Depends(get_tenant_session),
    company_id: str = Depends(get_current_user_company_id)
):
    result = await db.execute(select(Consumable))
    return result.scalars().all()

@router.get("/{consumable_id}", response_model=ConsumableOut)
async def get_consumable(
    consumable_id: uuid.UUID,
    db: AsyncSession = Depends(get_tenant_session),
    company_id: str = Depends(get_current_user_company_id)
):
    consumable = await db.get(Consumable, consumable_id)
    if not consumable:
        raise HTTPException(status_code=404, detail="Consumable not found")
    return consumable

@router.patch("/{consumable_id}", response_model=ConsumableOut)
async def update_consumable(
    request: Request,
    consumable_id: uuid.UUID,
    consumable_in: ConsumableUpdate,
    db: AsyncSession = Depends(get_tenant_session),
    user: UserCtx = Depends(get_current_user)
):
    consumable = await db.get(Consumable, consumable_id)
    if not consumable:
        raise HTTPException(status_code=404, detail="Consumable not found")
        
    update_data = consumable_in.model_dump(exclude_unset=True)
    old_state = {k: getattr(consumable, k) for k in update_data.keys()}
    
    for field, value in update_data.items():
        setattr(consumable, field, value)
        
    await db.flush()
    await record_user_audit(
        session=db, user=user, entity_type="consumable", entity_id=consumable.id, action="update", 
        old_state=old_state, new_state=update_data, request_id=request.headers.get("x-request-id"), ip_address=request.client.host if request.client else None
    )
    return consumable
