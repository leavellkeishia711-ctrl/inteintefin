from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException
import uuid
from typing import Type

async def validate_fk(db: AsyncSession, model: Type, fk_id: uuid.UUID | None, company_id: uuid.UUID | str, field_name: str):
    """
    Validates that a given foreign key ID exists, belongs to the same company,
    and is not soft-deleted. Returns 422 if invalid.
    """
    if not fk_id:
        return

    company_id_uuid = uuid.UUID(company_id) if isinstance(company_id, str) else company_id

    stmt = select(model).where(model.id == fk_id)
    # Check if model has company_id
    if hasattr(model, "company_id"):
        stmt = stmt.where(model.company_id == company_id_uuid)
    # Check if model has deleted_at
    if hasattr(model, "deleted_at"):
        stmt = stmt.where(model.deleted_at.is_(None))

    res = await db.execute(stmt)
    if not res.scalars().first():
        raise HTTPException(status_code=422, detail=f"Invalid or deleted foreign key: {field_name}")
