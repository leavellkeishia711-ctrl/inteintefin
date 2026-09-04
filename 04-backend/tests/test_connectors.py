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
async def test_api_create_connector(client_a: AsyncClient):
    res = await client_a.post("/api/v1/connectors/", json={
        "connector_name": "keitaro",
        "secret": "my_secret",
        "sync_interval_minutes": 60
    })
    assert res.status_code == 201
    data = res.json()
    assert "secret" not in data
    assert "encrypted_secret" not in data
    assert data["connector_name"] == "keitaro"
    assert data["status"] == "active"

@pytest.mark.asyncio
async def test_api_tenant_isolation(client_a: AsyncClient, client_b: AsyncClient):
    await client_a.post("/api/v1/connectors/", json={
        "connector_name": "keitaro",
        "secret": "my_secret2",
        "sync_interval_minutes": 60
    })
    res = await client_b.get("/api/v1/connectors/")
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

@pytest.mark.asyncio
async def test_keitaro_fetch_500():
    connector = KeitaroConnector(config=None, decrypted_api_key="mock")
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        from httpx import Response, Request
        mock_get.return_value = Response(500, request=Request("GET", "https://api.keitaro.io/v1/report"))
        with patch("asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(ConnectorError):
                await connector.fetch()
            assert mock_get.call_count == 3

@pytest.mark.asyncio
async def test_keitaro_fetch_timeout():
    connector = KeitaroConnector(config=None, decrypted_api_key="mock")
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        import httpx
        mock_get.side_effect = httpx.TimeoutException("Timeout")
        with patch("asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(ConnectorError):
                await connector.fetch()
            assert mock_get.call_count == 3

@pytest.mark.asyncio
async def test_keitaro_malformed_json():
    connector = KeitaroConnector(config=None, decrypted_api_key="mock")
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        from httpx import Response, Request
        mock_get.return_value = Response(200, content=b"invalid json", request=Request("GET", "https://api.keitaro.io/v1/report"))
        with pytest.raises(ConnectorError):
            await connector.fetch()

def test_keitaro_normalize_utc():
    connector = KeitaroConnector(config=None, decrypted_api_key="mock")
    raw = [{"campaign_id": "1", "date": "2024-01-01", "spend": 10, "revenue": 10}]
    normalized = connector.normalize(raw)
    assert normalized[0].stat_date == date(2024, 1, 1)

def test_keitaro_normalize_missing_fields():
    connector = KeitaroConnector(config=None, decrypted_api_key="mock")
    raw = [{"campaign_id": "1"}]
    # Should skip
    normalized = connector.normalize(raw)
    assert len(normalized) == 0

@pytest.mark.asyncio
async def test_keitaro_fetch_403():
    connector = KeitaroConnector(config=None, decrypted_api_key="mock")
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        from httpx import Response, Request
        mock_get.return_value = Response(403, request=Request("GET", "https://api.keitaro.io/v1/report"))
        with pytest.raises(UnauthorizedError):
            await connector.fetch()
        assert mock_get.call_count == 1 # No retry on 403

def test_keitaro_normalize_bad_money():
    connector = KeitaroConnector(config=None, decrypted_api_key="mock")
    raw = [{"campaign_id": "1", "date": "2024-01-01", "spend": "bad_money", "revenue": "10"}]
    # Should skip
    normalized = connector.normalize(raw)
    assert len(normalized) == 0

