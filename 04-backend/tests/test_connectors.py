import pytest
from httpx import AsyncClient, Response, Request
from datetime import datetime, timezone, timedelta, date
from decimal import Decimal

from app.db.models.connectors import ConnectorConfig
from app.db.models.campaigns import CampaignRunStat, CampaignRun
from app.db.models.finance import FxRate
from app.db.models.companies import Company
from app.connectors.credentials import encrypt_secret, decrypt_secret
from app.connectors.keitaro import KeitaroConnector, UnauthorizedError, ConnectorError
from sqlalchemy import select, and_
import uuid

def test_credentials_encryption():
    secret = "my_super_secret_keitaro_key"
    encrypted = encrypt_secret(secret)
    assert encrypted != secret
    assert decrypt_secret(encrypted) == secret

    with pytest.raises(ValueError):
        decrypt_secret("invalid_cipher")

@pytest.mark.asyncio
async def test_api_create_connector(client: AsyncClient, token_headers_owner):
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
async def test_api_tenant_isolation(client: AsyncClient, token_headers_owner, token_headers_admin2, db_session):
    res = await client.get("/api/v1/connectors/", headers=token_headers_admin2)
    assert res.status_code == 200
    assert len(res.json()) == 0

@pytest.mark.asyncio
async def test_keitaro_normalize():
    connector = KeitaroConnector(config=None, decrypted_api_key="mock")
    
    raw = [
        {"campaign_id": "123", "date": "2024-01-01", "spend": 10.5, "revenue": 15},
        {"campaign_id": "123", "date": "2024-01-01", "spend": "20.1", "revenue": "30"}, # Dup, should override
        {"campaign_id": "999", "date": "invalid-date", "spend": 5}, # Invalid date
        {"campaign_id": "456", "date": "2024-01-02", "spend": -5, "revenue": 0}, # Negative money
    ]
    
    normalized = connector.normalize(raw)
    
    assert len(normalized) == 1
    
    rec = normalized[0]
    assert rec.external_id == "123"
    assert rec.stat_date == date(2024, 1, 1)
    assert rec.spend == Decimal("20.1")
    assert rec.revenue == Decimal("30.0")

from unittest.mock import patch, AsyncMock

@pytest.mark.asyncio
async def test_keitaro_fetch_401():
    connector = KeitaroConnector(config=None, decrypted_api_key="mock")
    
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = Response(401, request=Request("GET", "https://api.keitaro.io/v1/report"))
        
        with pytest.raises(UnauthorizedError):
            await connector.fetch()
            
        assert mock_get.call_count == 1 # No retry on 401

@pytest.mark.asyncio
async def test_keitaro_fetch_429():
    connector = KeitaroConnector(config=None, decrypted_api_key="mock")
    
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = Response(429, request=Request("GET", "https://api.keitaro.io/v1/report"))
        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            with pytest.raises(ConnectorError):
                await connector.fetch()
                
            assert mock_get.call_count == 3 # Should retry
            assert mock_sleep.call_count == 2
