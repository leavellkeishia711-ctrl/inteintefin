import uuid
import pytest
from decimal import Decimal
from datetime import datetime, timezone
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert
from app.db.models import Transaction, Company, User
from app.db.session import system_session
from app.core.money import q

pytestmark = pytest.mark.asyncio

async def test_transaction_partial_unique_index_allows_reimport_after_soft_delete(company_b_fixtures):
    """
    DB integration test proving the partial unique index behavior for soft deletes.
    NOTE: This does NOT test the production commit_batch() flow. The production service 
    app/services/imports.py currently has `rows = []` and acts as a stub, so it cannot 
    be tested end-to-end here. This tests ONLY PostgreSQL index behavior.
    """
    tenant_b_company = company_b_fixtures.ids["company_id"]
    tenant_b_user = company_b_fixtures.ids["user_id"]

    tenant_a_company = str(uuid.uuid4())
    tenant_a_user = str(uuid.uuid4())

    async with system_session() as db_session:
        # Setup valid Company and User for Tenant A
        company = Company(id=tenant_a_company, name="Tenant A", base_currency="USD")
        db_session.add(company)
        user = User(
            id=tenant_a_user, email=f"{tenant_a_user}@example.com", password_hash="hash",
            name="A", role="owner", company_id=tenant_a_company
        )
        db_session.add(user)
        await db_session.flush()

        ext_id = f"ext-{uuid.uuid4()}"
        
        # Helper to create exact production ON CONFLICT upsert statement
        def make_upsert_stmt(company_id, user_id, ext_id_val, amount_val):
            return insert(Transaction).values(
                company_id=company_id,
                source="csv",
                external_id=ext_id_val,
                occurred_on=datetime.now(timezone.utc),
                type="expense",
                category="ad_spend",  # Valid CheckConstraint value
                amount=q(amount_val),
                currency="USD",
                fx_rate_to_base=q("1.0"),
                description="Test",
                created_by=user_id
            ).on_conflict_do_nothing(
                index_elements=["company_id", "source", "external_id"],
                index_where=sa.text("external_id IS NOT NULL AND deleted_at IS NULL")
            ).returning(Transaction.id)

        # a. вставить Transaction для (company_id, source, external_id) и подтвердить одну активную строку;
        stmt1 = make_upsert_stmt(tenant_a_company, tenant_a_user, ext_id, "100.00")
        res1 = await db_session.execute(stmt1)
        tx1_id = res1.scalar()
        assert tx1_id is not None
        await db_session.flush()

        # b. вставить такой же активный ключ повторно с ON CONFLICT DO NOTHING и подтвердить, что вторая строка не создаётся;
        stmt2 = make_upsert_stmt(tenant_a_company, tenant_a_user, ext_id, "200.00")
        res2 = await db_session.execute(stmt2)
        tx2_id = res2.scalar()
        assert tx2_id is None # Conflict ignored, nothing returned

        # c. поставить первой строке deleted_at;
        await db_session.execute(
            sa.update(Transaction).where(Transaction.id == tx1_id).values(deleted_at=datetime.now(timezone.utc))
        )
        await db_session.flush()

        # d. вставить тот же ключ снова и подтвердить, что новая активная строка создаётся, а старая остаётся soft-deleted;
        res3 = await db_session.execute(stmt2)
        tx3_id = res3.scalar()
        assert tx3_id is not None
        assert tx3_id != tx1_id

        # e. убедиться, что итог для tenant A: одна активная и одна soft-deleted строка;
        rows_a = (await db_session.execute(
            sa.select(Transaction).where(Transaction.company_id == tenant_a_company, Transaction.external_id == ext_id)
        )).scalars().all()
        assert len(rows_a) == 2
        active_a = [r for r in rows_a if r.deleted_at is None]
        assert len(active_a) == 1
        assert active_a[0].id == tx3_id

        # f. вставить тот же (source, external_id) для tenant B с валидными Company/User и убедиться, что конфликт отсутствует.
        stmt_b = make_upsert_stmt(tenant_b_company, tenant_b_user, ext_id, "300.00")
        res_b = await db_session.execute(stmt_b)
        tx_b_id = res_b.scalar()
        assert tx_b_id is not None
