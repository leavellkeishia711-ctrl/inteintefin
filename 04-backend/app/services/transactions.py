from pydantic import BaseModel, Field
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import Transaction, Company
from app.core.deps import UserCtx
from app.core.money import q, to_base
from app.services.fx import resolve_fx_rate
from app.services.audit import record_user_audit
import uuid
from decimal import Decimal

from app.schemas.types import Money

class TransactionCreate(BaseModel):
    type: str
    category: str
    amount: Money
    currency: str
    occurred_on: date
    team_id: uuid.UUID | None = None
    description: str | None = None

async def create_transaction(db: AsyncSession, user: UserCtx, data: TransactionCreate, request_id: str | None = None, ip_address: str | None = None) -> Transaction:
    company = await db.get(Company, uuid.UUID(user.company_id))
    
    if data.currency == company.base_currency:
        fx_rate = Decimal('1.0')
    else:
        fx_rate = await resolve_fx_rate(db, data.currency, company.base_currency, data.occurred_on)
        
    amount_q = q(data.amount)
    amount_in_base = to_base(amount_q, fx_rate) if fx_rate else amount_q

    tx = Transaction(
        company_id=uuid.UUID(user.company_id),
        type=data.type,
        category=data.category,
        amount=amount_q,
        currency=data.currency,
        fx_rate_to_base=fx_rate,
        
        occurred_on=data.occurred_on,
        team_id=data.team_id,
        description=data.description,
        source="manual",
        created_by=uuid.UUID(user.user_id),
    )
    db.add(tx)
    await db.flush()
    await record_user_audit(
        session=db, user=user, entity_type="transaction", entity_id=tx.id, action="create", 
        old_state=None, new_state=data.model_dump(), request_id=request_id, ip_address=ip_address
    )
    return tx

class TransactionUpdate(BaseModel):
    category: str | None = None
    description: str | None = None
    team_id: uuid.UUID | None = None

async def update_transaction(db: AsyncSession, user: UserCtx, tx_id: str, data: TransactionUpdate, request_id: str | None = None, ip_address: str | None = None) -> Transaction:
    tx = await db.get(Transaction, uuid.UUID(tx_id))
    if not tx:
        raise ValueError("Transaction not found")
        
    old_state = {"category": tx.category, "description": tx.description, "team_id": tx.team_id}
    
    if data.category is not None:
        tx.category = data.category
    if data.description is not None:
        tx.description = data.description
    if data.team_id is not None:
        tx.team_id = data.team_id
        
    new_state = {"category": tx.category, "description": tx.description, "team_id": tx.team_id}
    
    await db.flush()
    await record_user_audit(
        session=db, user=user, entity_type="transaction", entity_id=tx.id, action="update", 
        old_state=old_state, new_state=new_state, request_id=request_id, ip_address=ip_address
    )
    return tx

async def delete_transaction(db: AsyncSession, user: UserCtx, tx_id: str, request_id: str | None = None, ip_address: str | None = None):
    tx = await db.get(Transaction, uuid.UUID(tx_id))
    if not tx:
        raise ValueError("Transaction not found")
        
    await db.delete(tx)
    await db.flush()
    await record_user_audit(
        session=db, user=user, entity_type="transaction", entity_id=tx.id, action="delete", 
        old_state=None, new_state=None, request_id=request_id, ip_address=ip_address
    )

async def get_transactions(
    db: AsyncSession, 
    company_id: uuid.UUID, 
    date_from: date, 
    date_to: date, 
    category: str | None = None, 
    type_: str | None = None, 
    limit: int = 100
):
    import sqlalchemy as sa
    stmt = sa.select(Transaction).where(
        Transaction.company_id == company_id,
        Transaction.deleted_at.is_(None),
        Transaction.occurred_on >= date_from,
        Transaction.occurred_on <= date_to
    )
    if category:
        stmt = stmt.where(Transaction.category == category)
    if type_:
        stmt = stmt.where(Transaction.type == type_)
        
    stmt = stmt.order_by(Transaction.occurred_on.desc()).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


