import hashlib
import json
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert
from app.db.models import ImportBatch, Transaction, Company
from app.core.deps import UserCtx
from app.core.money import q, to_base
from app.services.fx import get_fx_rate
from app.services import audit
from pydantic import BaseModel

class CommitResult(BaseModel):
    imported: int
    duplicates: int

def row_fingerprint(p: dict) -> str:
    # Hash of essential fields to detect duplicates
    key = f"{p.get('occurred_on')}:{p.get('amount')}:{p.get('currency')}:{p.get('type')}:{p.get('category')}:{p.get('description', '')}"
    return hashlib.sha256(key.encode('utf-8')).hexdigest()

class Conflict(Exception):
    pass

async def commit_batch(session: AsyncSession, batch_id: UUID, user: UserCtx) -> CommitResult:
    batch = await session.get(ImportBatch, batch_id)
    if not batch or str(batch.company_id) != user.company_id:
        raise ValueError("Батч не найден")
        
    if batch.status == "committed":
        raise Conflict("батч уже импортирован")

    # stmt = select(ImportRow).where(ImportRow.batch_id == batch_id, ImportRow.status == "valid")
    # result = await session.execute(stmt)
    # rows = result.scalars().all()
    rows = []
    
    imported, duplicates = 0, 0

    company = await session.get(Company, batch.company_id)
    
    for row in rows:
        p = row.parsed
        external_id = p.get("external_id") or row_fingerprint(p)
        fx = None
        if p["currency"] != company.base_currency:
            fx = await get_fx_rate(session, p["currency"], company.base_currency, p["occurred_on"])
            if fx is None:
                # row.status, row.errors = "error", {"fx": f"Missing FX rate for {p['currency']} on {p['occurred_on']}"}
                continue

        # PostgreSQL 'insert' with on_conflict_do_nothing
        stmt_insert = insert(Transaction).values(
            company_id=batch.company_id,
            type=p["type"], 
            category=p["category"],
            amount=q(p["amount"]), 
            currency=p["currency"],
            fx_rate_to_base=fx,
            occurred_on=p["occurred_on"],
            description=p.get("description"),
            source="csv", 
            external_id=external_id,
            import_batch_id=batch.id, 
            created_by=user.user_id,
        ).on_conflict_do_nothing(
            index_elements=["company_id", "source", "external_id"],
            index_where=sa.text("external_id IS NOT NULL")
        ).returning(Transaction.id)

        tx_result = await session.execute(stmt_insert)
        tx_id = tx_result.scalar_one_or_none()
        
        if tx_id:
            imported = imported + 1
        else:
            duplicates = duplicates + 1

    batch.status, batch.imported_rows = "committed", imported
    await audit.record_user_audit(session, user, "import_batch", batch.id, "commit", None, {"status": "committed", "imported": imported, "duplicates": duplicates})
                       
    await session.commit()
    return CommitResult(imported=imported, duplicates=duplicates)

async def rollback_batch(session: AsyncSession, batch_id: UUID, user: UserCtx):
    batch = await session.get(ImportBatch, batch_id)
    if not batch or str(batch.company_id) != user.company_id:
        raise ValueError("Батч не найден")
        
    if batch.status != "committed":
        raise Conflict("Батч не был импортирован")
        
    stmt = select(Transaction).where(Transaction.import_batch_id == batch_id)
    result = await session.execute(stmt)
    txs = result.scalars().all()
    
    for tx in txs:
        await session.delete(tx)
        
    batch.status = "rolled_back"
    
    await audit.record_user_audit(
        session, user, "import_batch", batch.id, "rollback",
        old_state={"status": "committed"},
        new_state={"status": "rolled_back", "deleted_transactions": len(txs)}
    )
    
    await session.commit()
    return {"status": "rolled_back", "deleted_transactions": len(txs)}
