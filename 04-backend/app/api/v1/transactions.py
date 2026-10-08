import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db_session
from app.core.deps import get_tenant_session, get_current_user, UserCtx
from app.services.transactions import (
    create_transaction, update_transaction, delete_transaction, get_active_transaction,
    TransactionCreate, TransactionUpdate,
)
from app.schemas.transactions import TransactionOut, TransactionListResponse

router = APIRouter()

@router.post("/")
async def create_tx(
    request: Request,
    data: TransactionCreate,
    db: AsyncSession = Depends(get_tenant_session),
    user: UserCtx = Depends(get_current_user)
):
    from app.services.validation import validate_fk
    from app.db.models.users import Team
    company_uuid = uuid.UUID(user.company_id)
    await validate_fk(db, Team, data.team_id, company_uuid, "team_id")

    tx = await create_transaction(
        db, user, data,
        request_id=request.headers.get("x-request-id"),
        ip_address=request.client.host if request.client else None
    )
    return {"id": str(tx.id), "status": "created"}

@router.get("/", response_model=TransactionListResponse)
async def list_tx(
    db: AsyncSession = Depends(get_tenant_session),
    user: UserCtx = Depends(get_current_user),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    search: str = ""
):
    from decimal import Decimal
    from sqlalchemy import select, func, or_
    from app.db.models import Transaction

    query = select(Transaction).where(
        Transaction.company_id == uuid.UUID(user.company_id),
        Transaction.deleted_at.is_(None),
    )
    if search:
        escaped = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        pattern = f"%{escaped}%"
        query = query.where(or_(
            Transaction.description.ilike(pattern, escape="\\"),
            Transaction.category.ilike(pattern, escape="\\")
        ))

    # Totals are computed over the whole filtered set, not the current page.
    filtered = query.subquery()
    total = await db.scalar(select(func.count()).select_from(filtered))
    total_amount = await db.scalar(
        select(func.sum(filtered.c.amount * filtered.c.fx_rate_to_base))
    )

    # Apply pagination and sorting
    page_query = query.order_by(Transaction.occurred_on.desc(), Transaction.created_at.desc())
    page_query = page_query.offset((page - 1) * per_page).limit(per_page)

    result = await db.execute(page_query)
    items = result.scalars().all()

    return {
        "items": items,
        "total": total or 0,
        "total_amount": total_amount if total_amount is not None else Decimal("0"),
        "page": page,
        "per_page": per_page
    }

@router.get("/{id}", response_model=TransactionOut)
async def get_tx(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_tenant_session),
    user: UserCtx = Depends(get_current_user)
):
    tx = await get_active_transaction(db, user, id)
    if not tx:
        raise HTTPException(status_code=404, detail="Not found")
    return tx

@router.patch("/{id}")
async def update_tx(
    request: Request,
    id: uuid.UUID,
    data: TransactionUpdate,
    db: AsyncSession = Depends(get_tenant_session),
    user: UserCtx = Depends(get_current_user)
):
    from app.services.validation import validate_fk
    from app.db.models.users import Team
    company_uuid = uuid.UUID(user.company_id)
    if data.team_id is not None:
        await validate_fk(db, Team, data.team_id, company_uuid, "team_id")

    try:
        tx = await update_transaction(
            db, user, id, data,
            request_id=request.headers.get("x-request-id"),
            ip_address=request.client.host if request.client else None
        )
        return {"id": str(tx.id), "status": "updated"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.delete("/{id}")
async def delete_tx(
    request: Request,
    id: uuid.UUID,
    db: AsyncSession = Depends(get_tenant_session),
    user: UserCtx = Depends(get_current_user)
):
    try:
        await delete_transaction(
            db, user, id,
            request_id=request.headers.get("x-request-id"),
            ip_address=request.client.host if request.client else None
        )
        return {"status": "deleted"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

