import pytest
import uuid
from datetime import date
from httpx import AsyncClient
from app.db.models import Transaction
from app.db.session import tenant_session
from app.core.money import q

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
                id=user_id, email="test@example.com", password_hash=get_password_hash("test"),
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
async def test_create_transaction(auth_client: AsyncClient):
    payload = {
        "type": "expense",
        "category": "software",
        "amount": "99.99",
        "currency": "USD",
        "occurred_on": "2026-07-01",
        "description": "GitHub Copilot"
    }
    resp = await auth_client.post("/api/v1/transactions/", json=payload)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "id" in data
    assert data["status"] == "created"
    
    # Check if it's in DB
    async with tenant_session(str(auth_client.company_id)) as db:
        tx = await db.get(Transaction, uuid.UUID(data["id"]))
        assert tx is not None
        assert tx.amount == q("99.99")

@pytest.mark.asyncio
async def test_list_and_get_transaction(auth_client: AsyncClient):
    # Create one first
    payload = {
        "type": "income",
        "category": "sales",
        "amount": "500",
        "currency": "USD",
        "occurred_on": "2026-07-02"
    }
    resp = await auth_client.post("/api/v1/transactions/", json=payload)
    tx_id = resp.json()["id"]
    
    # List
    list_resp = await auth_client.get("/api/v1/transactions/")
    assert list_resp.status_code == 200
    list_data = list_resp.json()
    assert list_data["total"] >= 1
    ids = [item["id"] for item in list_data["items"]]
    assert tx_id in ids
    
    # Get by ID
    get_resp = await auth_client.get(f"/api/v1/transactions/{tx_id}")
    assert get_resp.status_code == 200
    get_data = get_resp.json()
    assert get_data["id"] == tx_id
    assert get_data["category"] == "sales"

@pytest.mark.asyncio
async def test_update_transaction(auth_client: AsyncClient):
    payload = {
        "type": "expense",
        "category": "office",
        "amount": "10",
        "currency": "USD",
        "occurred_on": "2026-07-03"
    }
    resp = await auth_client.post("/api/v1/transactions/", json=payload)
    tx_id = resp.json()["id"]
    
    # Update
    update_payload = {"category": "hardware", "description": "Mouse"}
    upd_resp = await auth_client.patch(f"/api/v1/transactions/{tx_id}", json=update_payload)
    assert upd_resp.status_code == 200
    
    get_resp = await auth_client.get(f"/api/v1/transactions/{tx_id}")
    get_data = get_resp.json()
    assert get_data["category"] == "hardware"
    assert get_data["description"] == "Mouse"

@pytest.mark.asyncio
async def test_delete_transaction(auth_client: AsyncClient):
    payload = {
        "type": "expense",
        "category": "misc",
        "amount": "5",
        "currency": "USD",
        "occurred_on": "2026-07-04"
    }
    resp = await auth_client.post("/api/v1/transactions/", json=payload)
    tx_id = resp.json()["id"]
    
    # Delete
    del_resp = await auth_client.delete(f"/api/v1/transactions/{tx_id}")
    assert del_resp.status_code == 200
    
    # Verify not found
    get_resp = await auth_client.get(f"/api/v1/transactions/{tx_id}")
    assert get_resp.status_code == 404
