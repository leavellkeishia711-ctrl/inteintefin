import pytest
from httpx import AsyncClient
import uuid

pytestmark = pytest.mark.asyncio

async def test_ad_account_crud(async_client: AsyncClient, owner_token: str):
    headers = {"Authorization": f"Bearer {owner_token}"}
    
    # Create
    create_payload = {
        "platform": "facebook",
        "external_account_id": f"act_{uuid.uuid4()}",
        "name": "Test FB Account",
        "status": "active"
    }
    resp = await async_client.post("/api/v1/ad-accounts/", headers=headers, json=create_payload)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["name"] == "Test FB Account"
    assert data["platform"] == "facebook"
    acc_id = data["id"]
    
    # Read
    resp = await async_client.get(f"/api/v1/ad-accounts/{acc_id}", headers=headers)
    assert resp.status_code == 200
    
    # Update
    resp = await async_client.patch(f"/api/v1/ad-accounts/{acc_id}", headers=headers, json={"status": "paused"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "paused"
