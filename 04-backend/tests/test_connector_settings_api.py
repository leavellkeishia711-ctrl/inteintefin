import pytest
from app.core.config import settings
from unittest.mock import patch
from sqlalchemy import select
from app.db.models import AuditLog

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
    assert res.status_code == 201, res.text
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
    assert res.status_code == 422, res.text
    
@pytest.mark.asyncio
async def test_patch_connector_settings_semantics(client_a, db):
    # Create first
    res = await client_a.post(
        f"{settings.API_V1_STR}/connectors/",
        json={
            "connector_name": "google_ads",
            "secret": "my-secret",
            "settings": {"access_mode": "cloud_managed"}
        }
    )
    assert res.status_code == 201, res.text
    c_id = res.json()["id"]

    # Patch with valid - replaces
    res_patch = await client_a.patch(
        f"{settings.API_V1_STR}/connectors/{c_id}",
        json={"settings": {"access_mode": "legacy"}}
    )
    assert res_patch.status_code == 200, res_patch.text
    
    # Patch with {} clears settings
    res_patch_clear = await client_a.patch(
        f"{settings.API_V1_STR}/connectors/{c_id}",
        json={"settings": {}}
    )
    assert res_patch_clear.status_code == 200, res_patch_clear.text
    
    # Patch with null (missing) -> no-op
    res_patch_null = await client_a.patch(
        f"{settings.API_V1_STR}/connectors/{c_id}",
        json={"sync_interval_minutes": 120} # settings omitted
    )
    assert res_patch_null.status_code == 200, res_patch_null.text

    # Patch with invalid
    res_patch_invalid = await client_a.patch(
        f"{settings.API_V1_STR}/connectors/{c_id}",
        json={"settings": {"access_mode": "invalid"}}
    )
    assert res_patch_invalid.status_code == 422, res_patch_invalid.text


@pytest.mark.asyncio
async def test_connector_settings_tenant_isolation(client_a, client_b):
    # Client A creates connector
    res = await client_a.post(
        f"{settings.API_V1_STR}/connectors/",
        json={
            "connector_name": "google_ads",
            "secret": "my-secret",
            "settings": {"access_mode": "cloud_managed"}
        }
    )
    assert res.status_code == 201, res.text
    c_id = res.json()["id"]

    # Client B tries to patch it
    res_b = await client_b.patch(
        f"{settings.API_V1_STR}/connectors/{c_id}",
        json={"settings": {"access_mode": "legacy"}}
    )
    assert res_b.status_code == 404, res_b.text


@pytest.mark.asyncio
async def test_connector_settings_patch_validate_true(client_a, monkeypatch):
    # Mock connector class
    class MockGoogleAdsConnector:
        def __init__(self, config, secret):
            self.config = config
            self.secret = secret
        async def test_connection(self):
            # Verify the dummy config received the *new* settings correctly
            assert self.config.settings == {"access_mode": "legacy"}
            return True

    monkeypatch.setattr("app.api.v1.connectors.get_connector_class", lambda x: MockGoogleAdsConnector)

    res = await client_a.post(
        f"{settings.API_V1_STR}/connectors/",
        json={
            "connector_name": "google_ads",
            "secret": "my-secret",
            "settings": {"access_mode": "cloud_managed"}
        }
    )
    assert res.status_code == 201, res.text
    c_id = res.json()["id"]

    # Patch with validate=true
    res_patch = await client_a.patch(
        f"{settings.API_V1_STR}/connectors/{c_id}?validate=true",
        json={"secret": "new_secret", "settings": {"access_mode": "legacy"}}
    )
    assert res_patch.status_code == 200, res_patch.text

    # Mock connector class for second call to expect access_mode = legacy
    class MockGoogleAdsConnectorPreserved:
        def __init__(self, config, secret):
            self.config = config
            self.secret = secret
        async def test_connection(self):
            assert self.config.settings == {"access_mode": "legacy"}
            return True

    monkeypatch.setattr("app.api.v1.connectors.get_connector_class", lambda x: MockGoogleAdsConnectorPreserved)

    # Patch with validate=true and ONLY secret, settings should be preserved
    res_patch_secret_only = await client_a.patch(
        f"{settings.API_V1_STR}/connectors/{c_id}?validate=true",
        json={"secret": "newer_secret"}
    )
    assert res_patch_secret_only.status_code == 200, res_patch_secret_only.text


@pytest.mark.asyncio
async def test_connector_settings_audit(client_a, db):
    # Create connector
    res = await client_a.post(
        f"{settings.API_V1_STR}/connectors/",
        json={
            "connector_name": "meta",
            "secret": "my-secret",
            "settings": {"lookback_days": 7}
        }
    )
    assert res.status_code == 201, res.text
    c_id = res.json()["id"]

    # Patch settings
    res_patch = await client_a.patch(
        f"{settings.API_V1_STR}/connectors/{c_id}",
        json={"settings": {"lookback_days": 14}}
    )
    assert res_patch.status_code == 200, res_patch.text

    # Read AuditLog directly
    stmt = select(AuditLog).where(
        AuditLog.entity_id == c_id,
        AuditLog.action == "connector.settings_updated"
    ).order_by(AuditLog.created_at.desc())
    audit_res = await db.execute(stmt)
    log = audit_res.scalars().first()

    assert log is not None
    assert "changed_settings_keys" in log.diff["new"]
    assert log.diff["new"]["changed_settings_keys"] == ["lookback_days"]
    assert "settings" not in log.diff["new"]
    assert "settings" not in log.diff["old"] if log.diff.get("old") else True
