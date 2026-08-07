import pytest
import pytest_asyncio
import asyncio
import sys

# psycopg requires WindowsSelectorEventLoopPolicy on Windows
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"

@pytest.fixture
def app():
    from app.main import app as main_app
    return main_app

@pytest_asyncio.fixture(scope="session", autouse=True)
async def dispose_engine():
    yield
    from app.db.session import engine, tenant_engine
    await engine.dispose()
    await tenant_engine.dispose()

import pytest_asyncio

@pytest_asyncio.fixture
async def client_a(app):
    print("client_a: fixture started")
    import httpx
    import uuid
    from app.db.session import system_session, tenant_session
    from app.db.models import Company, User
    from app.core.security import get_password_hash, create_access_token
    
    company_a_id = uuid.uuid4()
    user_a_id = uuid.uuid4()
    
    # Pre-compute hash to prevent Supavisor connection idle timeout
    pw_hash = get_password_hash("test")
    
    print("client_a: starting db operations")
    async with system_session() as db:
        async with db.begin():
            print("client_a: inside system_session")
            company = Company(id=company_a_id, name="Company A", base_currency="USD")
            db.add(company)
            user = User(
                id=user_a_id, email="a@example.com", password_hash="hash123",
                name="A", role="owner", company_id=company_a_id
            )
            db.add(user)
    
    token = create_access_token(subject=str(user_a_id), company_id=str(company_a_id), role="owner")
    
    # We must use httpx.AsyncClient because httpx in 0.28+ is strict about it
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        client.headers.update({"Authorization": f"Bearer {token}"})
        yield client

@pytest_asyncio.fixture
async def client_b(app, company_b_fixtures):
    import httpx
    from app.core.security import create_access_token
    token = create_access_token(
        subject=company_b_fixtures.ids["user_id"], 
        company_id=company_b_fixtures.ids["company_id"], 
        role="owner"
    )
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        client.headers.update({"Authorization": f"Bearer {token}"})
        yield client

class CompanyBFixtures:
    def __init__(self, ids: dict):
        self.ids = ids

@pytest_asyncio.fixture
async def company_b_fixtures():
    import uuid
    from app.db.session import system_session
    from app.db.models import Company, User, Transaction
    
    company_b_id = uuid.uuid4()
    user_b_id = uuid.uuid4()
    tx_b_id = uuid.uuid4()
    
    async with system_session() as db:
        async with db.begin():
            company = Company(id=company_b_id, name="Company B", base_currency="USD")
            db.add(company)
            user = User(
                id=user_b_id, email="b@example.com", password_hash="hash",
                name="B", role="owner", company_id=company_b_id
            )
            db.add(user)
            await db.flush()  # user must exist before Transaction.created_by references it
            
            from app.core.money import q
            from datetime import date
            tx = Transaction(
                id=tx_b_id, company_id=company_b_id, type="expense", category="software",
                amount=q(100), currency="USD", fx_rate_to_base=q(1), occurred_on=date.today(),
                source="manual", created_by=user_b_id
            )
            db.add(tx)
        
    return CompanyBFixtures({
        "id": str(tx_b_id), # generic resource id
        "company_id": str(company_b_id),
        "user_id": str(user_b_id),
        "transaction_id": str(tx_b_id)
    })
