from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, validator
from app.db.session import get_db_session
from app.core.deps import get_tenant_session, get_current_user
from app.db.models import Consumable, User
import uuid

router = APIRouter()

def luhn_check(card_number: str) -> bool:
    digits = [int(x) for x in str(card_number) if x.isdigit()]
    if not digits:
        return False
    odd_digits = digits[-1::-2]
    even_digits = [sum(divmod(2 * d, 10)) for d in digits[-2::-2]]
    return (sum(odd_digits) + sum(even_digits)) % 10 == 0

from app.schemas.types import Money

from pydantic import BaseModel, field_validator

class ConsumableCreate(BaseModel):
    type: str
    identifier: str | None = None
    cost: Money
    currency: str
    
    @field_validator("identifier")
    @classmethod
    def validate_identifier(cls, v: str | None) -> str | None:
        if v:
            # 1. Reject PAN (Luhn check) if it looks like a card number
            digits_only = ''.join(filter(str.isdigit, v))
            if len(digits_only) >= 13 and luhn_check(digits_only):
                raise ValueError("PCI violation: PAN-like strings are prohibited. Use only masked identifiers.")
            
            # 2. Cut anything longer than 8 chars (we only need last 4 or bin+last4)
            if len(v) > 8:
                v = v[-8:]
        return v

class ConsumableOut(BaseModel):
    status: str
    identifier: str | None = None

@router.post("/", response_model=ConsumableOut)
async def create_consumable(
    item: ConsumableCreate,
    db: AsyncSession = Depends(get_tenant_session),
    current_user: User = Depends(get_current_user)
):
    from app.core.deps import UserCtx
    from app.services.audit import record_user_audit
    
    # In a real app we'd fetch fx rate and insert to db
    # For now we'll just log the attempt as a mutation
    
    user_ctx = UserCtx(user_id=str(current_user.id), company_id=str(current_user.company_id))
    
    await record_user_audit(
        session=db, user=user_ctx, entity_type="consumable", entity_id=None, action="create", 
        old_state=None, new_state=item.model_dump()
    )
    await db.commit()
    
    return {"status": "ok", "identifier": item.identifier}
