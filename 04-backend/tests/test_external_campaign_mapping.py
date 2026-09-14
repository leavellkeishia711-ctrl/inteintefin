import pytest
from httpx import AsyncClient
from app.db.models.campaigns import ExternalCampaignMapping
from sqlalchemy import select
import uuid

from app.db.session import async_session_maker
from app.db.models.campaigns import CampaignRun
from datetime import datetime, timezone

async def create_dummy_run(client):
    me = await client.get("/api/v1/auth/me")
    company_id = uuid.UUID(me.json()["company_id"])
    user_id = uuid.UUID(me.json()["id"])
    run_id = uuid.uuid4()
    async with async_session_maker() as session:
        run = CampaignRun(
            id=run_id,
            company_id=company_id,
            buyer_id=user_id,
            started_at=datetime.now(timezone.utc)
        )
        session.add(run)
        await session.commit()
    return str(run_id)



@pytest.mark.asyncio
async def test_create_mapping_success(client_a: AsyncClient):
    run_a_id = await create_dummy_run(client_a)
    payload = {
        "platform": "meta",
        "external_id": "test_ext_1",
        "campaign_run_id": run_a_id
    }
    response = await client_a.post("/api/v1/external-campaign-mappings/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["platform"] == "meta"
    assert data["external_id"] == "test_ext_1"
    assert data["campaign_run_id"] == run_a_id
    
@pytest.mark.asyncio
async def test_create_duplicate_returns_409(client_a: AsyncClient):
    run_a_id = await create_dummy_run(client_a)
    payload = {
        "platform": "google_ads",
        "external_id": "duplicate_ext",
        "campaign_run_id": run_a_id
    }
    response1 = await client_a.post("/api/v1/external-campaign-mappings/", json=payload)
    assert response1.status_code == 201
    
    response2 = await client_a.post("/api/v1/external-campaign-mappings/", json=payload)
    assert response2.status_code == 409
    
@pytest.mark.asyncio
async def test_soft_delete_mapping(client_a: AsyncClient):
    run_a_id = await create_dummy_run(client_a)
    payload = {
        "platform": "tiktok_ads",
        "external_id": "delete_ext",
        "campaign_run_id": run_a_id
    }
    create_res = await client_a.post("/api/v1/external-campaign-mappings/", json=payload)
    mapping_id = create_res.json()["id"]
    
    del_res = await client_a.delete(f"/api/v1/external-campaign-mappings/{mapping_id}")
    assert del_res.status_code == 204
    
    get_res = await client_a.get(f"/api/v1/external-campaign-mappings/")
    assert get_res.status_code == 200
    assert not any(m["id"] == mapping_id for m in get_res.json())

@pytest.mark.asyncio
async def test_get_mappings_filtered(client_a: AsyncClient):
    run_a_id = await create_dummy_run(client_a)
    for ext_id in ["f1", "f2"]:
        await client_a.post("/api/v1/external-campaign-mappings/", json={
            "platform": "meta", "external_id": ext_id, "campaign_run_id": run_a_id
        })
    await client_a.post("/api/v1/external-campaign-mappings/", json={
        "platform": "google_ads", "external_id": "f3", "campaign_run_id": run_a_id
    })
    
    res = await client_a.get("/api/v1/external-campaign-mappings/?platform=meta")
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 2
    assert all(d["platform"] == "meta" for d in data)

@pytest.mark.asyncio
async def test_list_isolates_by_company(client_a: AsyncClient, client_b: AsyncClient):
    run_a_id = await create_dummy_run(client_a)
    run_b_id = await create_dummy_run(client_b)
    res_a = await client_a.post("/api/v1/external-campaign-mappings/", json={
        "platform": "binom", "external_id": "iso_a", "campaign_run_id": run_a_id
    })
    assert res_a.status_code == 201
    
    res_b = await client_b.post("/api/v1/external-campaign-mappings/", json={
        "platform": "binom", "external_id": "iso_b", "campaign_run_id": run_b_id
    })
    assert res_b.status_code == 201
    
    get_a = await client_a.get("/api/v1/external-campaign-mappings/")
    ids_a = [m["external_id"] for m in get_a.json()]
    assert "iso_a" in ids_a
    assert "iso_b" not in ids_a
    
    get_b = await client_b.get("/api/v1/external-campaign-mappings/")
    ids_b = [m["external_id"] for m in get_b.json()]
    assert "iso_b" in ids_b
    assert "iso_a" not in ids_b
