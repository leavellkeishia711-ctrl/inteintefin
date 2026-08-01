import pytest
from app.workers.tasks import tenant_task_session
from sqlalchemy import text
from app.db.session import tenant_engine
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
import sqlalchemy

@pytest.mark.asyncio
async def test_tenant_task_session_sets_context():
    company_a_id = str(uuid.uuid4())
    company_b_id = str(uuid.uuid4())
    
    # 1. Start a task for company A
    async with tenant_task_session(company_a_id) as db:
        # Check that the context is set to company A
        res = await db.execute(text("SHOW app.company_id"))
        current_cid = res.scalar()
        assert current_cid == company_a_id, f"Expected {company_a_id}, got {current_cid}"
        
        # Try to insert something for company B - should fail RLS WITH CHECK
        try:
            await db.execute(
                text("INSERT INTO users (id, company_id, name, email, password_hash, role) VALUES (gen_random_uuid(), :cid, 'test', 'test@test.com', 'hash', 'admin')"),
                {"cid": company_b_id}
            )
            assert False, "Cross-tenant INSERT bypassed RLS in celery task session!"
        except sqlalchemy.exc.ProgrammingError as e:
            assert hasattr(e.orig, "sqlstate") and e.orig.sqlstate == "42501"
        except sqlalchemy.exc.InternalError as e:
            assert hasattr(e.orig, "sqlstate") and e.orig.sqlstate == "42501"

@pytest.mark.asyncio
async def test_tenant_task_session_cleans_up():
    company_a_id = str(uuid.uuid4())
    
    # Run the block
    async with tenant_task_session(company_a_id) as db:
        pass
        
    # Afterwards, verify that if we open a fresh session from the engine, it does not have the config.
    async with AsyncSession(tenant_engine) as db:
        try:
            res = await db.execute(text("SHOW app.company_id"))
            current_cid = res.scalar()
            # If it's not set, PostgreSQL might throw an error "unrecognized configuration parameter"
            # Or it might be empty if they reset it globally.
            assert current_cid == "" or current_cid is None, "Context leaked across sessions!"
        except sqlalchemy.exc.ProgrammingError as e:
            # "unrecognized configuration parameter" is expected if not set
            assert "unrecognized configuration parameter" in str(e) or "42704" in str(getattr(e.orig, "sqlstate", ""))
