import pytest
from httpx import AsyncClient
import uuid

pytestmark = pytest.mark.asyncio

async def test_ad_account_crud(client_a: AsyncClient):
    # Create
    create_payload = {
        "platform": "facebook",
        "external_account_id": f"act_{uuid.uuid4()}",
        "name": "Test FB Account",
        "status": "active"
    }
    resp = await client_a.post("/api/v1/ad-accounts/", json=create_payload)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["name"] == "Test FB Account"
    assert data["platform"] == "facebook"
    acc_id = data["id"]
    
    # Read
    resp = await client_a.get(f"/api/v1/ad-accounts/{acc_id}")
    assert resp.status_code == 200
    
    # Update
    resp = await client_a.patch(f"/api/v1/ad-accounts/{acc_id}", json={"status": "suspended"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "suspended"
