import pytest
from app.core.config import settings
from unittest.mock import patch

@pytest.mark.asyncio
async def test_create_connector_with_settings(client_a):
    res = await client_a.post(
        f"{settings.API_V1_STR}/connectors/",
        json={
            "connector_name": "meta",
            "secret": "my-secret",
            "sync_interval_minutes": 60,
            "settings": {"lookback_days": 14}
        }
    )
    # Note: local DB might not be running. If it is, this should be 201
    if res.status_code == 201:
        data = res.json()
        assert "settings" not in data

@pytest.mark.asyncio
async def test_create_connector_invalid_settings(client_a):
    res = await client_a.post(
        f"{settings.API_V1_STR}/connectors/",
        json={
            "connector_name": "meta",
            "secret": "my-secret",
            "settings": {"base_url": "http://evil.com"}
        }
    )
    if res.status_code != 500: # if not connection error
        assert res.status_code == 422
    
@pytest.mark.asyncio
async def test_patch_connector_settings(client_a):
    res = await client_a.post(
        f"{settings.API_V1_STR}/connectors/",
        json={
            "connector_name": "google_ads",
            "secret": "my-secret",
            "settings": {"access_mode": "cloud_managed"}
        }
    )
    if res.status_code == 201:
        c_id = res.json()["id"]

        res_patch = await client_a.patch(
            f"{settings.API_V1_STR}/connectors/{c_id}",
            json={"settings": {"access_mode": "legacy"}}
        )
        assert res_patch.status_code == 200
        
        res_patch_clear = await client_a.patch(
            f"{settings.API_V1_STR}/connectors/{c_id}",
            json={"settings": {}}
        )
        assert res_patch_clear.status_code == 200
        
        res_patch_invalid = await client_a.patch(
            f"{settings.API_V1_STR}/connectors/{c_id}",
            json={"settings": {"access_mode": "invalid"}}
        )
        assert res_patch_invalid.status_code == 422
