from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any
from app.core.deps import get_tenant_session
from app.core.deps import get_current_user
from app.db.models import User, ImportBatch
import csv
import io
import uuid
from pydantic import BaseModel

router = APIRouter()

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
    current_user: User = Depends(get_current_user)
):
    """
    Step 1: Upload CSV, create ImportBatch, insert ImportRows.
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")
        
    content = await file.read()
    text = content.decode('utf-8')
    reader = csv.DictReader(io.StringIO(text))
    
    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail="CSV is empty or missing headers")
        
    rows = list(reader)
    
    batch = ImportBatch(
        company_id=current_user.company_id,
        filename=file.filename,
        row_count=len(rows),
        status='pending',
        created_by=current_user.id
    )
    db.add(batch)
    await db.commit()
    
    # Store rows in S3/MinIO later, as per design

    
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
    current_user: User = Depends(get_current_user)
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
        user=current_user
    )
    
    return result

@router.delete("/{batch_id}", response_model=dict)
async def delete_import_batch(
    batch_id: uuid.UUID,
    db: AsyncSession = Depends(get_tenant_session),
    current_user: User = Depends(get_current_user)
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

