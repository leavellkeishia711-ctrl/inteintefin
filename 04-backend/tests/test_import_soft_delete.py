import uuid
import pytest
from decimal import Decimal
from datetime import datetime, timezone
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import Transaction, Company

pytestmark = pytest.mark.asyncio

from app.db.session import system_session

async def test_import_idempotency_and_soft_delete():
    async with system_session() as db_session:
        # Setup test company
        company_id = uuid.uuid4()
        company_id_2 = uuid.uuid4()
        db_session.add(Company(id=company_id, name="Test Company A"))
        db_session.add(Company(id=company_id_2, name="Test Company B"))
        await db_session.flush()

        class DummyUserCtx:
            company_id = str(company_id)
            user_id = str(uuid.uuid4())
            role = "owner"
            email = "test@example.com"
            
        user = DummyUserCtx()
        
        # 1. First import: creates active row
        ext_id = f"ext-{uuid.uuid4()}"
        
        # Mocking commit_import_batch is not ideal, let's insert directly via ORM index to test DB constraint
        from sqlalchemy.dialects.postgresql import insert
        
        stmt = insert(Transaction).values(
            company_id=company_id,
            source="test_source",
            external_id=ext_id,
            occurred_on=datetime.now(timezone.utc),
            type="expense",
            category="Ads",
            amount=Decimal("100.00"),
            currency="USD",
            fx_rate_to_base=Decimal("1.0"),
            description="First",
            created_by=uuid.uuid4()
        ).on_conflict_do_nothing(
            index_elements=["company_id", "source", "external_id"],
            index_where=sa.text("external_id IS NOT NULL AND deleted_at IS NULL")
        ).returning(Transaction.id)
        
        res1 = await db_session.execute(stmt)
        tx1_id = res1.scalar()
        assert tx1_id is not None
        await db_session.flush()

        # 2. Idempotent import: should do nothing (return None)
        stmt2 = insert(Transaction).values(
            company_id=company_id,
            source="test_source",
            external_id=ext_id,
            occurred_on=datetime.now(timezone.utc),
            type="expense",
            category="Ads",
            amount=Decimal("200.00"),
            currency="USD",
            fx_rate_to_base=Decimal("1.0"),
            description="Duplicate",
            created_by=uuid.uuid4()
        ).on_conflict_do_nothing(
            index_elements=["company_id", "source", "external_id"],
            index_where=sa.text("external_id IS NOT NULL AND deleted_at IS NULL")
        ).returning(Transaction.id)
        
        res2 = await db_session.execute(stmt2)
        tx2_id = res2.scalar()
        assert tx2_id is None # Conflict ignored

        # 3. Soft delete the original row
        await db_session.execute(
            sa.update(Transaction).where(Transaction.id == tx1_id).values(deleted_at=datetime.now(timezone.utc))
        )
        await db_session.flush()

        # 4. Import again: should create a new active row
        res3 = await db_session.execute(stmt2)
        tx3_id = res3.scalar()
        assert tx3_id is not None
        assert tx3_id != tx1_id # Created a new row!
        
        # Verify DB has one soft-deleted and one active row for this external_id
        rows = (await db_session.execute(sa.select(Transaction).where(Transaction.external_id == ext_id))).scalars().all()
        assert len(rows) == 2
        active = [r for r in rows if r.deleted_at is None]
        assert len(active) == 1
        assert active[0].id == tx3_id

        # 5. Different company: same external_id does not conflict
        stmt_other_company = insert(Transaction).values(
            company_id=company_id_2,
            source="test_source",
            external_id=ext_id,
            occurred_on=datetime.now(timezone.utc),
            type="expense",
            category="Ads",
            amount=Decimal("100.00"),
            currency="USD",
            fx_rate_to_base=Decimal("1.0"),
            description="Other Company",
            created_by=uuid.uuid4()
        ).on_conflict_do_nothing(
            index_elements=["company_id", "source", "external_id"],
            index_where=sa.text("external_id IS NOT NULL AND deleted_at IS NULL")
        ).returning(Transaction.id)
        
        res_other = await db_session.execute(stmt_other_company)
        tx_other_id = res_other.scalar()
        assert tx_other_id is not None
