import hashlib
import json
from uuid import UUID
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert
from app.db.models import ImportBatch, ImportRow, Transaction, Company
from app.core.deps import UserCtx
from app.core.money import q, to_base
from app.services.fx import get_fx_rate
from app.services import audit
from pydantic import BaseModel

class CommitResult(BaseModel):
    imported: int
    duplicates: int
    errors: int

def row_fingerprint(p: dict) -> str:
    # Hash of essential fields to detect duplicates
    key = f"{p.get('occurred_on')}:{p.get('amount')}:{p.get('currency')}:{p.get('type')}:{p.get('category')}:{p.get('description', '')}"
    return hashlib.sha256(key.encode('utf-8')).hexdigest()

class Conflict(Exception):
    pass

async def commit_batch(session: AsyncSession, batch_id: UUID, user: UserCtx, column_mapping: dict) -> CommitResult:
    batch = await session.get(ImportBatch, batch_id)
    if not batch or str(batch.company_id) != user.company_id:
        raise ValueError("Batch not found")
        
    if batch.status not in ["pending", "processing"]:
        raise Conflict("Batch already committed or failed")

    batch.status = "processing"
    
    stmt = select(ImportRow).where(ImportRow.batch_id == batch_id).order_by(ImportRow.row_index)
    result = await session.execute(stmt)
    rows = result.scalars().all()
    
    imported, duplicates, errors = 0, 0, 0

    company = await session.get(Company, batch.company_id)
    
    for row in rows:
        if row.status == "imported":
            continue
            
        raw = row.row_data
        
        try:
            # Apply mapping
            p = {
                "type": raw.get(column_mapping.get("type", "")),
                "category": raw.get(column_mapping.get("category", "")),
                "amount": raw.get(column_mapping.get("amount", "")),
                "currency": raw.get(column_mapping.get("currency", "")),
                "occurred_on": raw.get(column_mapping.get("occurred_on", "")),
                "description": raw.get(column_mapping.get("description", "")),
                "external_id": raw.get(column_mapping.get("external_id", ""))
            }
            
            # Validation
            if not p["type"] or p["type"] not in ["income", "expense"]:
                raise ValueError("Invalid type")
            if not p["category"] or p["category"] not in ['ad_spend', 'salary', 'infra', 'tax', 'payout_incoming', 'payout_outgoing', 'consumables', 'depreciation', 'interest', 'other']:
                raise ValueError("Invalid category")
            if not p["currency"]:
                raise ValueError("Missing currency")
            if not p["occurred_on"]:
                raise ValueError("Missing date")
                
            try:
                date_val = datetime.strptime(p["occurred_on"], "%Y-%m-%d").date()
            except ValueError:
                raise ValueError("Invalid date format, expected YYYY-MM-DD")
                
            try:
                amt_val = Decimal(str(p["amount"]))
            except (InvalidOperation, TypeError, ValueError):
                raise ValueError("Invalid amount format")

            external_id = p.get("external_id") or row_fingerprint(p)
            fx = Decimal("1.00000000")
            if p["currency"] != company.base_currency:
                fx_val = await get_fx_rate(session, p["currency"], company.base_currency, date_val)
                if fx_val is None:
                    raise ValueError(f"Missing FX rate for {p['currency']} on {date_val}")
                fx = fx_val

            stmt_insert = insert(Transaction).values(
                company_id=batch.company_id,
                type=p["type"], 
                category=p["category"],
                amount=q(amt_val), 
                currency=p["currency"],
                fx_rate_to_base=fx,
                occurred_on=date_val,
                description=p.get("description"),
                source="csv", 
                external_id=external_id,
                import_batch_id=batch.id, 
                created_by=user.user_id,
            ).on_conflict_do_nothing(
                index_elements=["company_id", "source", "external_id"],
                index_where=sa.text("external_id IS NOT NULL AND deleted_at IS NULL")
            ).returning(Transaction.id)

            tx_result = await session.execute(stmt_insert)
            tx_id = tx_result.scalar_one_or_none()
            
            if tx_id:
                imported += 1
            else:
                duplicates += 1
                
            row.status = "imported"
            row.error_message = None
            
        except ValueError as e:
            row.status = "error"
            row.error_message = str(e)
            errors += 1

    batch.error_count = errors
    if errors > 0 and imported == 0:
        batch.status = "failed"
    elif errors > 0 and imported > 0:
        batch.status = "completed_with_errors"
    else:
        batch.status = "completed"
        
    batch.completed_at = datetime.now(timezone.utc)
    
    await audit.record_user_audit(session, user, "import_batch", batch.id, "commit", None, {"status": batch.status, "imported": imported, "duplicates": duplicates, "errors": errors})
                       
    await session.commit()
    return CommitResult(imported=imported, duplicates=duplicates, errors=errors)

async def rollback_batch(session: AsyncSession, batch_id: UUID, user: UserCtx):
    batch = await session.get(ImportBatch, batch_id)
    if not batch or str(batch.company_id) != user.company_id:
        raise ValueError("Batch not found")
        
    if batch.status not in ["completed", "completed_with_errors"]:
        raise Conflict("Batch cannot be rolled back")
        
    stmt = select(Transaction).where(Transaction.import_batch_id == batch_id)
    result = await session.execute(stmt)
    txs = result.scalars().all()
    
    for tx in txs:
        if tx.deleted_at is None:
            tx.deleted_at = datetime.now(timezone.utc)
        
    # Also update import rows to reset them or leave them as rolled back?
    # Usually we just keep them as is and mark batch as rolled_back
    batch.status = "rolled_back"
    
    await audit.record_user_audit(
        session, user, "import_batch", batch.id, "rollback",
        old_state={"status": "completed"},
        new_state={"status": "rolled_back", "deleted_transactions": len(txs)}
    )
    
    await session.commit()
    return {"status": "rolled_back", "deleted_transactions": len(txs)}
