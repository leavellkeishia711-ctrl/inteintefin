import pytest
from httpx import AsyncClient, ASGITransport
from datetime import date
from decimal import Decimal
import uuid

import pytest_asyncio
from app.db.session import tenant_session
from app.core.money import q

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
async def test_ad_account_crud(auth_client: AsyncClient):
    import asyncio
    # Create
    resp = await auth_client.post("/api/v1/ad-accounts/", json={
        "platform": "Facebook",
        "name": "Test Act 1",
        "external_account_id": "act_12345",
        "status": "active"
    })
    await asyncio.sleep(0.01)

    assert resp.status_code == 200
    account = resp.json()
    assert account["platform"] == "Facebook"
    assert account["id"] is not None
    
    # Get
    resp = await auth_client.get(f"/api/v1/ad-accounts/{account['id']}")
    await asyncio.sleep(0.01)
    assert resp.status_code == 200
    assert resp.json()["id"] == account["id"]
    
    # Update
    resp = await auth_client.patch(f"/api/v1/ad-accounts/{account['id']}", json={
        "status": "banned"
    })
    await asyncio.sleep(0.01)
    assert resp.status_code == 200
    assert resp.json()["status"] == "banned"

@pytest.mark.asyncio
async def test_campaign_run_stat_upsert(auth_client: AsyncClient):
    # Create CampaignRun first
    resp = await auth_client.post("/api/v1/campaign-runs/", json={
        "buyer_id": str(auth_client.user_id),
        "started_at": "2024-01-01T00:00:00Z"
    })
    assert resp.status_code == 200
    run = resp.json()
    
    # Upsert Stat (Insert)
    stat_date = "2024-01-01"
    payload = {
        "campaign_run_id": run["id"],
        "stat_date": stat_date,
        "spend": "100.00",
        "revenue": "200.00",
        "currency": "USD",
        "fx_rate_to_base": "1.00000000",
        "source": "api",
        "external_id": "stat_1"
    }
    resp = await auth_client.post("/api/v1/campaign-run-stats/upsert", json=payload)
    assert resp.status_code == 200
    stat = resp.json()
    assert stat["spend"] == "100.00"
    
    # Upsert Stat (Update - same date/run)
    payload["spend"] = "150.00"
    resp = await auth_client.post("/api/v1/campaign-run-stats/upsert", json=payload)
    assert resp.status_code == 200
    stat2 = resp.json()
    assert stat2["id"] == stat["id"]  # Same ID because it's an update
    assert stat2["spend"] == "150.00"

