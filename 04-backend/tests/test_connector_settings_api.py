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
    
from tests.test_connectors_api import db_session
from app.db.models.connectors import ConnectorConfig

@pytest.mark.asyncio
async def test_patch_connector_settings_semantics(client_a, db_session):
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

    import uuid
    # Verify initial settings
    stmt = select(ConnectorConfig).where(ConnectorConfig.id == uuid.UUID(c_id))
    config = (await db_session.execute(stmt)).scalars().first()
    assert config.settings == {"access_mode": "cloud_managed"}

    # Patch with valid - replaces
    res_patch = await client_a.patch(
        f"{settings.API_V1_STR}/connectors/{c_id}",
        json={"settings": {"access_mode": "legacy"}}
    )
    assert res_patch.status_code == 200, res_patch.text
    await db_session.refresh(config)
    assert config.settings == {"access_mode": "legacy"}
    
    # Patch with {} clears settings
    res_patch_clear = await client_a.patch(
        f"{settings.API_V1_STR}/connectors/{c_id}",
        json={"settings": {}}
    )
    assert res_patch_clear.status_code == 200, res_patch_clear.text
    await db_session.refresh(config)
    assert config.settings == {}
    
    # Patch with null (missing) -> no-op
    res_patch_null = await client_a.patch(
        f"{settings.API_V1_STR}/connectors/{c_id}",
        json={"sync_interval_minutes": 120} # settings omitted
    )
    assert res_patch_null.status_code == 200, res_patch_null.text
    await db_session.refresh(config)
    assert config.settings == {}
    
    res_patch_explicit_null = await client_a.patch(
        f"{settings.API_V1_STR}/connectors/{c_id}",
        json={"settings": None}
    )
    assert res_patch_explicit_null.status_code == 200, res_patch_explicit_null.text
    await db_session.refresh(config)
    assert config.settings == {}

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

    # Client B tries to read it
    res_get_b = await client_b.get(
        f"{settings.API_V1_STR}/connectors/{c_id}"
    )
    assert res_get_b.status_code == 405

    # Client B lists connectors, should not see A's
    res_list_b = await client_b.get(
        f"{settings.API_V1_STR}/connectors/"
    )
    assert res_list_b.status_code == 200
    assert not any(c["id"] == c_id for c in res_list_b.json())


@pytest.mark.asyncio
async def test_connector_settings_patch_validate_true(client_a, monkeypatch):
    # Mock connector class
    class MockGoogleAdsConnector:
        call_count = 0
        def __init__(self, config, secret):
            self.config = config
            self.secret = secret
        async def test_connection(self):
            MockGoogleAdsConnector.call_count += 1
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
    assert MockGoogleAdsConnector.call_count == 1

    # Mock connector class for second call to expect access_mode = legacy
    class MockGoogleAdsConnectorPreserved:
        call_count = 0
        def __init__(self, config, secret):
            self.config = config
            self.secret = secret
        async def test_connection(self):
            MockGoogleAdsConnectorPreserved.call_count += 1
            assert self.config.settings == {"access_mode": "legacy"}
            return True

    monkeypatch.setattr("app.api.v1.connectors.get_connector_class", lambda x: MockGoogleAdsConnectorPreserved)

    # Patch with validate=true and ONLY secret, settings should be preserved
    res_patch_secret_only = await client_a.patch(
        f"{settings.API_V1_STR}/connectors/{c_id}?validate=true",
        json={"secret": "newer_secret"}
    )
    assert res_patch_secret_only.status_code == 200, res_patch_secret_only.text
    assert MockGoogleAdsConnectorPreserved.call_count == 1


@pytest.mark.asyncio
async def test_connector_settings_audit(client_a, db_session):
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

    import uuid
    stmt = select(AuditLog).where(
        AuditLog.entity_id == uuid.UUID(c_id),
        AuditLog.action == "connector.settings_updated"
    ).order_by(AuditLog.created_at.desc())
    audit_res = await db_session.execute(stmt)
    log = audit_res.scalars().first()

    assert log is not None
    assert "changed_settings_keys" in log.diff
    assert log.diff["changed_settings_keys"]["new"] == ["lookback_days"]
    assert "settings" not in log.diff
    assert "secret" not in log.diff
    assert "encrypted_secret" not in log.diff

    def extract_values(d):
        vals = []
        if isinstance(d, dict):
            for v in d.values():
                vals.extend(extract_values(v))
        elif isinstance(d, list):
            for v in d:
                vals.extend(extract_values(v))
        else:
            vals.append(d)
        return vals
        
    all_vals = extract_values(log.diff)
    assert 7 not in all_vals
    assert 14 not in all_vals
    assert "7" not in all_vals
    assert "14" not in all_vals
    assert "my-secret" not in all_vals
