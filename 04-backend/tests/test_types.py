import pytest
from httpx import AsyncClient
from app.db.models import Transaction
from datetime import date
from decimal import Decimal
import uuid
import pytest_asyncio

@pytest_asyncio.fixture
async def auth_client(app):
    import httpx
    from app.db.session import system_session
    from app.db.models import Company, User
    from app.core.security import get_password_hash, create_access_token
    
    company_id = uuid.uuid4()
    user_id = uuid.uuid4()
    
    async with system_session() as db:
        async with db.begin():
            company = Company(id=company_id, name="Test Co", base_currency="USD")
            db.add(company)
            user = User(
                id=user_id, email="test_types@example.com", password_hash=get_password_hash("test"),
                name="Test", role="owner", company_id=company_id
            )
            db.add(user)
    
    token = create_access_token(subject=str(user_id), company_id=str(company_id), role="owner")
    
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        client.headers.update({"Authorization": f"Bearer {token}"})
        # Attach IDs for use in tests
        client.company_id = company_id
        client.user_id = user_id
        yield client

@pytest.mark.asyncio
async def test_openapi_schema_money(auth_client: AsyncClient):
    resp = await auth_client.get("/api/v1/openapi.json")
    assert resp.status_code == 200
    schema = resp.json()
    
    # Check that PnLResult revenue is string
    components = schema.get("components", {}).get("schemas", {})
    pnl_result = components.get("PnLResult")
    assert pnl_result is not None, "PnLResult schema not found"
    
    revenue_prop = pnl_result["properties"]["revenue"]
    assert revenue_prop.get("type") == "string", f"Expected string, got {revenue_prop}"
    assert revenue_prop.get("format") == "decimal"

@pytest.mark.asyncio
async def test_pnl_returns_string(auth_client: AsyncClient):
    from app.db.session import tenant_session
    
    # Insert a transaction
    async with tenant_session(str(auth_client.company_id)) as db_session:
        tx = Transaction(
            company_id=auth_client.company_id,
            type="income",
            category="sales",
            amount=Decimal("1234.56"),
            currency="USD",
            fx_rate_to_base=Decimal("1.0"),
            occurred_on=date(2026, 1, 1),
            source="manual",
            created_by=auth_client.user_id
        )
        db_session.add(tx)
        await db_session.commit()
    
    resp = await auth_client.get("/api/v1/reports/pnl?start_date=2026-01-01&end_date=2026-01-31")
    assert resp.status_code == 200
    data = resp.json()
    
    assert data["revenue"] == "1234.56"
    assert type(data["revenue"]) is str
