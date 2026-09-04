import pytest
from httpx import AsyncClient
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.campaigns import AdAccount

pytestmark = pytest.mark.asyncio

async def test_tenant_isolation(async_client: AsyncClient, owner_token: str, second_company: dict, db_session: AsyncSession):
    # Insert ad account directly for second company
    db_session.add(AdAccount(
        company_id=uuid.UUID(second_company["id"]),
        platform="google",
        external_account_id="G123",
        name="Other Corp Google",
        status="active"
    ))
    await db_session.commit()
    
    # Fetch with owner_token (first company)
    headers = {"Authorization": f"Bearer {owner_token}"}
    resp = await async_client.get("/api/v1/ad-accounts/", headers=headers)
    assert resp.status_code == 200
    
    # Should not see other corp's google account
    data = resp.json()
    for acc in data:
        assert acc["platform"] != "google" or acc["external_account_id"] != "G123"
