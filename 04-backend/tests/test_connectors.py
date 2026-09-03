import pytest
from httpx import AsyncClient
from app.db.models.connectors import ConnectorConfig
from app.connectors.credentials import encrypt_secret, decrypt_secret
from sqlalchemy import select
import uuid

@pytest.mark.asyncio
async def test_credentials_encryption():
    secret = "my_super_secret"
    encrypted = encrypt_secret(secret)
    assert encrypted != secret
    assert decrypt_secret(encrypted) == secret

@pytest.mark.asyncio
async def test_connector_api_create(client: AsyncClient, token_headers_owner):
    res = await client.post("/api/v1/connectors/", headers=token_headers_owner, json={
        "connector_name": "keitaro",
        "secret": "my_secret",
        "sync_interval_minutes": 60
    })
    assert res.status_code == 200
    data = res.json()
    assert "secret" not in data
    assert "encrypted_secret" not in data
    assert data["connector_name"] == "keitaro"
    assert data["status"] == "active"

@pytest.mark.asyncio
async def test_connector_api_tenant_isolation(client: AsyncClient, token_headers_admin2, db_session):
    res = await client.get("/api/v1/connectors/", headers=token_headers_admin2)
    assert res.status_code == 200
    assert len(res.json()) == 0
