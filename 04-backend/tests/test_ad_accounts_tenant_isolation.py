import pytest
from httpx import AsyncClient
import uuid
from app.db.session import system_session
from app.db.models.campaigns import AdAccount

pytestmark = pytest.mark.asyncio

async def test_tenant_isolation(client_a: AsyncClient, company_b_fixtures):
    # Insert ad account directly for company B
    comp_b_id = uuid.UUID(company_b_fixtures.ids["company_id"])
    async with system_session() as db:
        db.add(AdAccount(
            company_id=comp_b_id,
            platform="google",
            external_account_id="G123",
            name="Other Corp Google",
            status="active"
        ))
        await db.commit()
    
    # Fetch with client_a (company A)
    resp = await client_a.get("/api/v1/ad-accounts/")
    assert resp.status_code == 200
    
    # Should not see other corp's google account
    data = resp.json()
    for acc in data:
        assert not (acc.get("platform") == "google" and acc.get("external_account_id") == "G123")
