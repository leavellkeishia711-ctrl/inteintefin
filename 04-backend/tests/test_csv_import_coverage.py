import pytest
import uuid
import io
from httpx import AsyncClient
from sqlalchemy import select, delete
import sqlalchemy as sa
from app.db.models.finance import ImportBatch, ImportRow, Transaction, FxRate
from app.db.session import system_session
from datetime import date
from decimal import Decimal

@pytest.mark.asyncio
async def test_csv_import_fx_rate(client_a: AsyncClient):
    # Setup FX rate
    async with system_session() as db_session:
        async with db_session.begin():
            await db_session.execute(delete(FxRate).where(FxRate.source == "manual", FxRate.rate_date == date(2026, 1, 2)))
            fx = FxRate(
                rate_date=date(2026, 1, 2),
                from_currency="EUR",
                to_currency="USD",
                rate=Decimal("1.1000"),
                source="manual"
            )
            db_session.add(fx)
        
    csv_content = """Date,Amount,Currency,Category,Type,Description,Ref
2026-01-02,200.00,EUR,salary,expense,Dev,REF-EUR
"""
    files = {'file': ('test_fx.csv', io.BytesIO(csv_content.encode('utf-8')), 'text/csv')}
    upload_res = await client_a.post("/api/v1/imports/upload", files=files)
    assert upload_res.status_code == 200, upload_res.text
    batch_id = upload_res.json()["batch_id"]
    
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
    assert c_data["imported"] == 1
    assert c_data["errors"] == 0
    
    async with system_session() as db_session:
        stmt = select(Transaction).where(Transaction.import_batch_id == uuid.UUID(batch_id))
        tx = (await db_session.execute(stmt)).scalar_one()
        assert tx.currency == "EUR"
        assert tx.fx_rate_to_base == Decimal("1.1000")

    async with system_session() as db_session:
        async with db_session.begin():
            await db_session.execute(delete(FxRate).where(FxRate.source == "manual", FxRate.rate_date == date(2026, 1, 2)))

@pytest.mark.asyncio
async def test_csv_import_limits(client_a: AsyncClient):
    # Over 5MB limit
    large_content = b"a" * (5 * 1024 * 1024 + 10)
    files = {'file': ('large.csv', io.BytesIO(large_content), 'text/csv')}
    upload_res = await client_a.post("/api/v1/imports/upload", files=files)
    assert upload_res.status_code == 413, upload_res.text
    
    # Over 5000 rows
    headers = "Date,Amount,Currency,Category,Type,Description,Ref\n"
    row = "2026-01-01,100.00,USD,ad_spend,expense,Dev,REF\n"
    too_many_rows_content = headers + row * 5001
    files2 = {'file': ('rows.csv', io.BytesIO(too_many_rows_content.encode('utf-8')), 'text/csv')}
    upload_res2 = await client_a.post("/api/v1/imports/upload", files=files2)
    assert upload_res2.status_code == 400, upload_res2.text
    assert "limit" in upload_res2.text.lower() or "exceeded" in upload_res2.text.lower()

@pytest.mark.asyncio
async def test_csv_import_tenant_isolation(client_a: AsyncClient, client_b: AsyncClient):
    csv_content = """Date,Amount,Currency,Category,Type,Description,Ref\n2026-01-01,100.50,USD,ad_spend,expense,FB Ads,REF-001\n"""
    files = {'file': ('test.csv', io.BytesIO(csv_content.encode('utf-8')), 'text/csv')}
    upload_res = await client_a.post("/api/v1/imports/upload", files=files)
    assert upload_res.status_code == 200, upload_res.text
    batch_id = upload_res.json()["batch_id"]
    
    mapping = {
        "occurred_on": "Date",
        "amount": "Amount",
        "currency": "Currency",
        "category": "Category",
        "type": "Type",
        "description": "Description",
        "external_id": "Ref"
    }
    
    # Client B tries to commit Client A's batch
    commit_res = await client_b.post(f"/api/v1/imports/{batch_id}/commit", json={
        "batch_id": batch_id,
        "column_mapping": mapping
    })
    assert commit_res.status_code == 400, commit_res.text
    assert "not found" in commit_res.text.lower()
    
    # Client B tries to delete Client A's batch
    del_res = await client_b.delete(f"/api/v1/imports/{batch_id}")
    assert del_res.status_code == 400, del_res.text
    assert "not found" in del_res.text.lower()

@pytest.mark.asyncio
async def test_csv_import_fx_rate_triangulation(client_a: AsyncClient):
    import io
    async with system_session() as db_session:
        async with db_session.begin():
            await db_session.execute(delete(FxRate).where(FxRate.source == "ecb", FxRate.rate_date == date(2026, 1, 1)))
            db_session.add(FxRate(
                rate_date=date(2026, 1, 1),
                from_currency="EUR",
                to_currency="USD",
                rate=Decimal("1.1000"),
                source="ecb"
            ))
            db_session.add(FxRate(
                rate_date=date(2026, 1, 1),
                from_currency="EUR",
                to_currency="GBP",
                rate=Decimal("0.8500"),
                source="ecb"
            ))
        
    csv_content = """Date,Amount,Currency,Category,Type,Description,Ref\n2026-01-01,100.00,GBP,ad_spend,expense,FB Ads,REF-TRIA-01\n"""
    files = {'file': ('test.csv', io.BytesIO(csv_content.encode('utf-8')), 'text/csv')}
    res_upload = await client_a.post("/api/v1/imports/upload", files=files)
    assert res_upload.status_code == 200, res_upload.text
    batch_id = res_upload.json()["batch_id"]

    mapping = {
        "Date": "transaction_date",
        "Amount": "amount",
        "Currency": "currency",
        "Category": "category",
        "Type": "transaction_type",
        "Description": "description",
        "Ref": "external_id"
    }

    res_commit = await client_a.post(f"/api/v1/imports/{batch_id}/commit", json={"batch_id": batch_id, "column_mapping": mapping})
    assert res_commit.status_code == 200, res_commit.text

    async with system_session() as db_session:
        stmt = select(Transaction).where(Transaction.external_id == "REF-TRIA-01")
        txn = (await db_session.execute(stmt)).scalars().first()
        assert txn is not None
        assert txn.currency == "GBP"
        assert txn.amount == Decimal("100.0000")
        assert txn.amount_base == Decimal("129.4118")

    async with system_session() as db_session:
        async with db_session.begin():
            await db_session.execute(delete(FxRate).where(FxRate.source == "ecb", FxRate.rate_date == date(2026, 1, 1)))
