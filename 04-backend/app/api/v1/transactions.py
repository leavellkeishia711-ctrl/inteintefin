from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db_session
from app.core.deps import get_tenant_session, get_current_user, UserCtx
from app.services.transactions import create_transaction, update_transaction, delete_transaction, TransactionCreate, TransactionUpdate
from app.schemas.transactions import TransactionOut, TransactionListResponse

router = APIRouter()

@router.post("/")
async def create_tx(
    request: Request,
    data: TransactionCreate,
    db: AsyncSession = Depends(get_tenant_session),
    user: UserCtx = Depends(get_current_user)
):
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
    page: int = 1,
    per_page: int = 50,
    search: str = ""
):
    from sqlalchemy import select, func, or_
    from app.db.models import Transaction

    query = select(Transaction)
    if search:
        query = query.filter(or_(
            Transaction.description.ilike(f"%{search}%"),
            Transaction.category.ilike(f"%{search}%")
        ))
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    # Apply pagination and sorting
    query = query.order_by(Transaction.occurred_on.desc(), Transaction.created_at.desc())
    query = query.offset((page - 1) * per_page).limit(per_page)
    
    result = await db.execute(query)
    items = result.scalars().all()

    subq = query.subquery()
    total_amount_query = select(func.sum(subq.c.amount * subq.c.fx_rate_to_base))
    total_amount = await db.scalar(total_amount_query) or 0

    return {
        "items": items,
        "total": total,
        "total_amount": total_amount,
        "page": page,
        "per_page": per_page
    }

@router.get("/{id}", response_model=TransactionOut)
async def get_tx(
    id: str,
    db: AsyncSession = Depends(get_tenant_session),
    user: UserCtx = Depends(get_current_user)
):
    from app.db.models import Transaction
    import uuid
    tx = await db.get(Transaction, uuid.UUID(id))
    if not tx:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Not found")
    return tx

@router.patch("/{id}")
async def update_tx(
    request: Request,
    id: str,
    data: TransactionUpdate,
    db: AsyncSession = Depends(get_tenant_session),
    user: UserCtx = Depends(get_current_user)
):
    try:
        tx = await update_transaction(
            db, user, id, data,
            request_id=request.headers.get("x-request-id"),
            ip_address=request.client.host if request.client else None
        )
        return {"id": str(tx.id), "status": "updated"}
    except ValueError as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=str(e))

@router.delete("/{id}")
async def delete_tx(
    request: Request,
    id: str,
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
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/summary")
async def summary_tx():
    pass


