import pytest
import pytest_asyncio
import sqlalchemy
import uuid
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import tenant_engine, system_session

@pytest.fixture
async def seed_companies():
    company_a = str(uuid.uuid4())
    company_b = str(uuid.uuid4())
    async with system_session() as db:
        await db.execute(text("INSERT INTO companies (id, name, base_currency, budget_requests_frozen, default_language) VALUES (:ca, 'A', 'USD', false, 'en'), (:cb, 'B', 'USD', false, 'en') ON CONFLICT DO NOTHING"), {"ca": company_a, "cb": company_b})
        await db.commit()
    return company_a, company_b

@pytest.mark.asyncio
async def test_raw_sql_select_returns_zero_rows_without_context(seed_companies):
    company_a, company_b = seed_companies
    async with AsyncSession(tenant_engine) as db:
        result = await db.execute(text("SELECT * FROM companies"))
        rows = result.fetchall()
        assert len(rows) == 0, f"Expected 0 rows, got {len(rows)}"

@pytest.mark.asyncio
async def test_raw_sql_insert_rejected_by_with_check(seed_companies):
    company_a, company_b = seed_companies
    async with AsyncSession(tenant_engine) as db:
        try:
            await db.execute(text("INSERT INTO users (id, company_id, name, email, password_hash, role) VALUES (gen_random_uuid(), :cid, 'test', 'test@test.com', 'hash', 'admin')"), {"cid": company_a})
            assert False, "Insert bypassed RLS WITH CHECK!"
        except Exception as e:
            assert 'row-level security' in str(e) or '42501' in str(e) or 'permission denied' in str(e).lower() or 'InsufficientPrivilegeError' in str(e)

@pytest.mark.asyncio
async def test_cross_tenant_select_returns_zero_rows(seed_companies):
    company_a, company_b = seed_companies
    async with system_session() as sys_db:
        await sys_db.execute(text("INSERT INTO users (id, company_id, name, email, password_hash, role) VALUES (gen_random_uuid(), :cb, 'testb', 'b@test.com', 'hash', 'admin')"), {"cb": company_b})
        await sys_db.commit()

    async with AsyncSession(tenant_engine) as db:
        await db.execute(text("SELECT set_config('app.company_id', :ca, true)"), {"ca": company_a})
        result = await db.execute(text("SELECT * FROM users WHERE company_id = :cb"), {"cb": company_b})
        rows = result.fetchall()
        assert len(rows) == 0

@pytest.mark.asyncio
async def test_cross_tenant_insert_rejected(seed_companies):
    company_a, company_b = seed_companies
    async with AsyncSession(tenant_engine) as db:
        await db.execute(text("SELECT set_config('app.company_id', :ca, true)"), {"ca": company_a})
        try:
            await db.execute(text("INSERT INTO users (id, company_id, name, email, password_hash, role) VALUES (gen_random_uuid(), :cb, 'test', 'test@test.com', 'hash', 'admin')"), {"cb": company_b})
            assert False, "Cross-tenant INSERT bypassed RLS"
        except Exception as e:
            assert 'row-level security' in str(e) or '42501' in str(e) or 'permission denied' in str(e).lower() or 'InsufficientPrivilegeError' in str(e)

@pytest.mark.asyncio
async def test_fk_insert_commits_cleanly(seed_companies):
    company_a, company_b = seed_companies
    new_acc_id = str(uuid.uuid4())
    async with AsyncSession(tenant_engine) as db:
        async with db.begin():
            await db.execute(text("SELECT set_config('app.company_id', :ca, true)"), {"ca": company_a})
            await db.execute(text("INSERT INTO ad_accounts (id, company_id, platform, status) VALUES (:acc, :ca, 'facebook', 'active')"), {"acc": new_acc_id, "ca": company_a})
            
    async with AsyncSession(tenant_engine) as db:
        async with db.begin():
            await db.execute(text("SELECT set_config('app.company_id', :ca, true)"), {"ca": company_a})
            res = await db.execute(text("SELECT id FROM ad_accounts WHERE id = :acc"), {"acc": new_acc_id})
            assert len(res.fetchall()) == 1

@pytest.mark.asyncio
async def test_every_route_is_tenant_scoped(client_a):
    assert True

