import pytest
import uuid
import io
from httpx import AsyncClient
from sqlalchemy import select
from app.db.models.finance import ImportBatch, ImportRow, Transaction
from app.db.session import system_session

@pytest.mark.asyncio
async def test_csv_import_e2e(client_a: AsyncClient):
    # 1. Upload CSV
    csv_content = """Date,Amount,Currency,Category,Type,Description,Ref
2026-01-01,100.50,USD,ad_spend,expense,FB Ads,REF-001
2026-01-02,200.00,EUR,salary,expense,Dev,REF-002
2026-01-03,invalid,USD,ad_spend,expense,Bad row,REF-003
"""
    files = {'file': ('test.csv', io.BytesIO(csv_content.encode('utf-8')), 'text/csv')}
    upload_res = await client_a.post("/api/v1/imports/upload", files=files)
    assert upload_res.status_code == 200, upload_res.text
    data = upload_res.json()
    batch_id = data["batch_id"]
    
    assert data["row_count"] == 3
    assert "Date" in data["columns"]
    
    async with system_session() as db_session:
        # 2. Check DB state
        batch = await db_session.get(ImportBatch, uuid.UUID(batch_id))
        assert batch.status == "pending"
        
    # 3. Commit batch
    mapping = {
        "occurred_on": "Date",
        "amount": "Amount",
        "currency": "Currency",
        "category": "Category",
        "type": "Type",
        "description": "Description",
        "external_id": "Ref"
    }
    commit_res = await client_a.post(f"/api/v1/imports/{batch_id}/commit", json={
        "batch_id": batch_id,
        "column_mapping": mapping
    })
    
    assert commit_res.status_code == 200, commit_res.text
    c_data = commit_res.json()
    assert c_data["imported"] == 2
    assert c_data["duplicates"] == 0
    assert c_data["errors"] == 1
    
    async with system_session() as db_session:
        # 4. Check DB again
        batch = await db_session.get(ImportBatch, uuid.UUID(batch_id))
        assert batch.status == "completed_with_errors"
        assert batch.error_count == 1
        
        stmt = select(Transaction).where(Transaction.import_batch_id == batch.id)
        result = await db_session.execute(stmt)
        txs = result.scalars().all()
        assert len(txs) == 2
        
    # Check idempotent commit (re-commit)
    # The API throws error if status is not pending or processing
    commit_res_2 = await client_a.post(f"/api/v1/imports/{batch_id}/commit", json={
        "batch_id": batch_id,
        "column_mapping": mapping
    })
    assert commit_res_2.status_code == 409
    
    # 5. Rollback
    del_res = await client_a.delete(f"/api/v1/imports/{batch_id}")
    assert del_res.status_code == 200
    
    async with system_session() as db_session:
        batch = await db_session.get(ImportBatch, uuid.UUID(batch_id))
        assert batch.status == "rolled_back"
        
        # Ensure they are soft deleted
        stmt2 = select(Transaction).where(Transaction.import_batch_id == batch.id)
        result2 = await db_session.execute(stmt2)
        txs2 = result2.scalars().all()
        for tx in txs2:
            assert tx.deleted_at is not None
