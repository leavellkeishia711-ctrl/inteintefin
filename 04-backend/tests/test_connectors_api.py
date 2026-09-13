import pytest
from httpx import AsyncClient
from app.db.models.connectors import ConnectorConfig
from sqlalchemy import select
import json

@pytest.mark.asyncio
async def test_rotate_secret_revives_unauthorized_connector(client_a: AsyncClient, system_session):
    # Create via API to get valid company_id
    response = await client_a.post(
        "/api/v1/connectors/",
        json={"connector_name": "meta", "secret": "enc1", "sync_interval_minutes": 60}
    )
    assert response.status_code == 201
    config_id = response.json()["id"]
    
    # Manually make it unauthorized in DB
    res = await system_session.execute(select(ConnectorConfig).where(ConnectorConfig.id == config_id))
    db_config = res.scalars().first()
    db_config.status = "unauthorized"
    db_config.retry_count = 5
    db_config.next_sync_at = None
    await system_session.commit()

    response = await client_a.patch(
        f"/api/v1/connectors/{config_id}?validate=false",
        json={"secret": "new_secret"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "active"
    
    # Check DB
    res = await system_session.execute(select(ConnectorConfig).where(ConnectorConfig.id == config_id))
    db_config = res.scalars().first()
    assert db_config.status == "active"
    assert db_config.retry_count == 0
    assert db_config.next_sync_at is not None

@pytest.mark.asyncio
async def test_rotate_secret_never_leaks(client_a: AsyncClient, system_session, caplog):
    response = await client_a.post(
        "/api/v1/connectors/",
        json={"connector_name": "meta", "secret": "old_secret", "sync_interval_minutes": 60}
    )
    assert response.status_code == 201
    config_id = response.json()["id"]

    secret_val = "SUPER_SECRET_VALUE_123"
    response = await client_a.patch(
        f"/api/v1/connectors/{config_id}?validate=false",
        json={"secret": secret_val}
    )
    assert response.status_code == 200
    
    # Check audit log via DB
    from app.db.models import AuditLog
    res = await system_session.execute(select(AuditLog).where(AuditLog.entity_id == config_id))
    logs = res.scalars().all()
    assert len(logs) > 0
    
    for log in logs:
        diff_str = json.dumps(log.diff) if log.diff else ""
        assert secret_val not in diff_str
        
    for record in caplog.records:
        assert secret_val not in record.message

@pytest.mark.asyncio
async def test_rotate_with_validate_false_on_unauthorized(client_a: AsyncClient, system_session, monkeypatch):
    response = await client_a.post(
        "/api/v1/connectors/",
        json={"connector_name": "meta", "secret": "old", "sync_interval_minutes": 60}
    )
    assert response.status_code == 201
    config_id = response.json()["id"]
    
    res = await system_session.execute(select(ConnectorConfig).where(ConnectorConfig.id == config_id))
    config = res.scalars().first()
    old_enc = config.encrypted_secret

    # mock connector test_connection to raise UnauthorizedError
    from app.connectors.meta_ads import MetaAdsConnector
    from app.connectors.base import UnauthorizedError
    
    async def mock_test_connection(*args, **kwargs):
        raise UnauthorizedError("Invalid")
    
    monkeypatch.setattr(MetaAdsConnector, "test_connection", mock_test_connection)

    response = await client_a.patch(
        f"/api/v1/connectors/{config_id}?validate=true",
        json={"secret": "bad_secret"}
    )
    assert response.status_code == 400
    
    # check db unchanged
    await system_session.refresh(config)
    assert config.encrypted_secret == old_enc

@pytest.mark.asyncio
async def test_soft_deleted_connector_can_be_recreated(client_a: AsyncClient):
    # create
    response = await client_a.post(
        "/api/v1/connectors/",
        json={"connector_name": "binom", "secret": "s1"}
    )
    assert response.status_code == 201
    conn_id = response.json()["id"]
    
    # delete
    response = await client_a.delete(
        f"/api/v1/connectors/{conn_id}"
    )
    assert response.status_code == 204
    
    # create again
    response = await client_a.post(
        "/api/v1/connectors/",
        json={"connector_name": "binom", "secret": "s2"}
    )
    assert response.status_code == 201 # should succeed now
    
    # create third time (should fail duplicate)
    response = await client_a.post(
        "/api/v1/connectors/",
        json={"connector_name": "binom", "secret": "s3"}
    )
    assert response.status_code == 400

@pytest.mark.asyncio
async def test_create_unknown_connector_returns_422(client_a: AsyncClient):
    response = await client_a.post(
        "/api/v1/connectors/",
        json={"connector_name": "nonexistent", "secret": "s1"}
    )
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_manual_sync_endpoint(client_a: AsyncClient, monkeypatch):
    response = await client_a.post(
        "/api/v1/connectors/",
        json={"connector_name": "meta", "secret": "old", "sync_interval_minutes": 60}
    )
    assert response.status_code == 201
    config_id = response.json()["id"]

    class MockTask:
        id = "mock-id-123"

    def mock_delay(*args, **kwargs):
        return MockTask()
        
    from app.workers.tasks import manual_sync_connector_task
    monkeypatch.setattr(manual_sync_connector_task, "delay", mock_delay)
    
    response = await client_a.post(
        f"/api/v1/connectors/{config_id}/sync"
    )
    assert response.status_code == 202
    assert response.json()["task_id"] == "mock-id-123"
    
    # second call should be rate limited (429)
    response = await client_a.post(
        f"/api/v1/connectors/{config_id}/sync"
    )
    assert response.status_code == 429
