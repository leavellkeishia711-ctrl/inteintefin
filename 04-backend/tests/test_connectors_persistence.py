import pytest
from app.db.session import tenant_session
from app.db.models.connectors import ConnectorConfig
from sqlalchemy import select

@pytest.mark.asyncio
async def test_api_persistence_create(client_a):
    resp = await client_a.post("/api/v1/connectors/", json={
        "connector_name": "keitaro",
        "secret": "my-secret-key-123",
        "sync_interval_minutes": 60
    })
    assert resp.status_code == 201
    data = resp.json()
    conn_id = data["id"]
    
    # Read directly from DB in a new connection
    from jose import jwt
    from app.core.config import settings
    # decode the client token to find company_id
    token = client_a.headers["Authorization"].split(" ")[1]
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    company_id = payload.get("company_id")
    
    async with tenant_session(company_id) as db:
        async with db.begin():
            stmt = select(ConnectorConfig).where(ConnectorConfig.id == conn_id)
            res = await db.execute(stmt)
            config = res.scalars().first()
            assert config is not None
            assert config.connector_name == "keitaro"
            assert config.sync_interval_minutes == 60

@pytest.mark.asyncio
async def test_api_persistence_patch_status(client_a):
    resp = await client_a.post("/api/v1/connectors/", json={
        "connector_name": "keitaro-patch",
        "secret": "my-secret",
        "sync_interval_minutes": 60
    })
    assert resp.status_code == 201
    conn_id = resp.json()["id"]

    resp2 = await client_a.patch(f"/api/v1/connectors/{conn_id}", json={
        "status": "paused",
        "sync_interval_minutes": 120
    })
    assert resp2.status_code == 200

    token = client_a.headers["Authorization"].split(" ")[1]
    from jose import jwt
    from app.core.config import settings
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    company_id = payload.get("company_id")

    async with tenant_session(company_id) as db:
        async with db.begin():
            stmt = select(ConnectorConfig).where(ConnectorConfig.id == conn_id)
            res = await db.execute(stmt)
            config = res.scalars().first()
            assert config.status == "paused"
            assert config.sync_interval_minutes == 120

@pytest.mark.asyncio
async def test_api_persistence_soft_delete(client_a):
    resp = await client_a.post("/api/v1/connectors/", json={
        "connector_name": "keitaro-del",
        "secret": "my-secret",
        "sync_interval_minutes": 60
    })
    assert resp.status_code == 201
    conn_id = resp.json()["id"]

    resp2 = await client_a.delete(f"/api/v1/connectors/{conn_id}")
    assert resp2.status_code == 204

    token = client_a.headers["Authorization"].split(" ")[1]
    from jose import jwt
    from app.core.config import settings
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    company_id = payload.get("company_id")

    # DB verify
    async with tenant_session(company_id) as db:
        async with db.begin():
            stmt = select(ConnectorConfig).where(ConnectorConfig.id == conn_id)
            res = await db.execute(stmt)
            config = res.scalars().first()
            assert config is not None
            assert config.deleted_at is not None
            assert config.status == "paused"
