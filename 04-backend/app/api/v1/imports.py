from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any
from app.core.deps import get_tenant_session, get_current_user, UserCtx
from app.db.models import User, ImportBatch, ImportRow
import csv
import io
import uuid
from pydantic import BaseModel

router = APIRouter()

MAX_CSV_ROWS = 5000

class CommitImportRequest(BaseModel):
    batch_id: uuid.UUID
    column_mapping: Dict[str, str]

class UploadResponse(BaseModel):
    batch_id: str
    columns: list[str]
    row_count: int
    preview: list[Dict[str, Any]]

@router.post("/upload", response_model=UploadResponse)
async def upload_csv(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_tenant_session),
    current_user: UserCtx = Depends(get_current_user)
):
    """
    Step 1: Upload CSV, create ImportBatch, insert ImportRows.
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")
        
    content = await file.read()
    # Limit max size before parsing (e.g., 5MB)
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large. Max 5MB allowed.")
        
    try:
        text = content.decode('utf-8')
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be UTF-8 encoded")
        
    reader = csv.DictReader(io.StringIO(text))
    
    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail="CSV is empty or missing headers")
        
    rows = list(reader)
    if len(rows) > MAX_CSV_ROWS:
        raise HTTPException(status_code=400, detail=f"Exceeded max rows limit of {MAX_CSV_ROWS}")
    
    batch = ImportBatch(
        company_id=uuid.UUID(current_user.company_id),
        filename=file.filename,
        row_count=len(rows),
        status='pending',
        created_by=uuid.UUID(current_user.user_id)
    )
    db.add(batch)
    await db.flush()  # to get batch.id
    
    # Store rows in ImportRow
    import_rows = []
    for idx, row in enumerate(rows):
        import_rows.append(
            ImportRow(
                company_id=uuid.UUID(current_user.company_id),
                batch_id=batch.id,
                row_index=idx,
                row_data=row,
                status="pending"
            )
        )
    db.add_all(import_rows)
    await db.commit()
    
    return {
        "batch_id": str(batch.id),
        "columns": list(reader.fieldnames),
        "row_count": len(rows),
        "preview": rows[:20]
    }

from app.services.imports import commit_batch, CommitResult

@router.post("/{batch_id}/commit", response_model=CommitResult)
async def commit_import_batch(
    batch_id: uuid.UUID,
    req: CommitImportRequest,
    db: AsyncSession = Depends(get_tenant_session),
    current_user: UserCtx = Depends(get_current_user)
):
    """
    Step 2: Commit batch using column_mapping.
    Calls the commit_batch service.
    """
    if req.batch_id != batch_id:
        raise HTTPException(status_code=400, detail="Batch ID mismatch")

    from app.services.imports import commit_batch
    
    result = await commit_batch(
        session=db,
        batch_id=batch_id,
        user=current_user,
        column_mapping=req.column_mapping
    )
    
    return result

@router.delete("/{batch_id}", response_model=dict)
async def delete_import_batch(
    batch_id: uuid.UUID,
    db: AsyncSession = Depends(get_tenant_session),
    current_user: UserCtx = Depends(get_current_user)
):
    from app.services.imports import rollback_batch
    
    try:
        return await rollback_batch(
            session=db,
            batch_id=batch_id,
            user=current_user
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

