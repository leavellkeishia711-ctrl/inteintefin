import pytest
from httpx import AsyncClient
from app.db.models.connectors import ConnectorConfig
from app.db.models import Company
from app.db.models import User
from app.core.security import create_access_token
from sqlalchemy import select, update
import uuid
import json

@pytest.mark.asyncio
async def test_rotate_secret_revives_unauthorized_connector(async_client: AsyncClient, system_session, auth_headers):
    # Get user
    res = await system_session.execute(select(User))
    user = res.scalars().first()
    
    # Create unauthorized config
    config = ConnectorConfig(
        company_id=user.company_id,
        connector_name="meta",
        encrypted_secret="enc1",
        status="unauthorized",
        next_sync_at=None,
        retry_count=5
    )
    system_session.add(config)
    await system_session.commit()

    response = await async_client.patch(
        f"/api/v1/connectors/{config.id}?validate=false",
        headers=auth_headers,
        json={"secret": "new_secret"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "active"
    
    # Check DB
    res = await system_session.execute(select(ConnectorConfig).where(ConnectorConfig.id == config.id))
    db_config = res.scalars().first()
    assert db_config.status == "active"
    assert db_config.retry_count == 0
    assert db_config.next_sync_at is not None

@pytest.mark.asyncio
async def test_rotate_secret_never_leaks(async_client: AsyncClient, system_session, auth_headers, caplog):
    res = await system_session.execute(select(User))
    user = res.scalars().first()
    
    config = ConnectorConfig(
        company_id=user.company_id,
        connector_name="meta",
        encrypted_secret="enc1",
        status="active"
    )
    system_session.add(config)
    await system_session.commit()

    secret_val = "SUPER_SECRET_VALUE_123"
    response = await async_client.patch(
        f"/api/v1/connectors/{config.id}?validate=false",
        headers=auth_headers,
        json={"secret": secret_val}
    )
    assert response.status_code == 200
    
    # Check audit log via DB
    from app.db.models import AuditLog
    res = await system_session.execute(select(AuditLog).where(AuditLog.entity_id == config.id))
    logs = res.scalars().all()
    assert len(logs) > 0
    
    for log in logs:
        diff_str = json.dumps(log.diff) if log.diff else ""
        assert secret_val not in diff_str
        
    for record in caplog.records:
        assert secret_val not in record.message

@pytest.mark.asyncio
async def test_rotate_with_validate_false_on_unauthorized(async_client: AsyncClient, system_session, auth_headers, monkeypatch):
    res = await system_session.execute(select(User))
    user = res.scalars().first()
    
    config = ConnectorConfig(
        company_id=user.company_id,
        connector_name="meta",
        encrypted_secret="enc1",
        status="active"
    )
    system_session.add(config)
    await system_session.commit()

    # mock connector test_connection to raise UnauthorizedError
    from app.connectors.meta_ads import MetaAdsConnector
    from app.connectors.base import UnauthorizedError
    
    async def mock_test_connection(*args, **kwargs):
        raise UnauthorizedError("Invalid")
    
    monkeypatch.setattr(MetaAdsConnector, "test_connection", mock_test_connection)

    response = await async_client.patch(
        f"/api/v1/connectors/{config.id}?validate=true",
        headers=auth_headers,
        json={"secret": "bad_secret"}
    )
    assert response.status_code == 400
    
    # check db unchanged
    await system_session.refresh(config)
    assert config.encrypted_secret == "enc1"

@pytest.mark.asyncio
async def test_soft_deleted_connector_can_be_recreated(async_client: AsyncClient, system_session, auth_headers):
    # create
    response = await async_client.post(
        "/api/v1/connectors/",
        headers=auth_headers,
        json={"connector_name": "binom", "secret": "s1"}
    )
    assert response.status_code == 201
    conn_id = response.json()["id"]
    
    # delete
    response = await async_client.delete(
        f"/api/v1/connectors/{conn_id}",
        headers=auth_headers
    )
    assert response.status_code == 204
    
    # create again
    response = await async_client.post(
        "/api/v1/connectors/",
        headers=auth_headers,
        json={"connector_name": "binom", "secret": "s2"}
    )
    assert response.status_code == 201 # should succeed now
    
    # create third time (should fail duplicate)
    response = await async_client.post(
        "/api/v1/connectors/",
        headers=auth_headers,
        json={"connector_name": "binom", "secret": "s3"}
    )
    assert response.status_code == 400

@pytest.mark.asyncio
async def test_create_unknown_connector_returns_422(async_client: AsyncClient, auth_headers):
    response = await async_client.post(
        "/api/v1/connectors/",
        headers=auth_headers,
        json={"connector_name": "nonexistent", "secret": "s1"}
    )
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_manual_sync_endpoint(async_client: AsyncClient, system_session, auth_headers, monkeypatch):
    res = await system_session.execute(select(User))
    user = res.scalars().first()
    
    config = ConnectorConfig(
        company_id=user.company_id,
        connector_name="meta",
        encrypted_secret="enc1",
        status="active"
    )
    system_session.add(config)
    await system_session.commit()

    class MockTask:
        id = "mock-id-123"

    def mock_delay(*args, **kwargs):
        return MockTask()
        
    from app.workers.tasks import manual_sync_connector_task
    monkeypatch.setattr(manual_sync_connector_task, "delay", mock_delay)
    
    response = await async_client.post(
        f"/api/v1/connectors/{config.id}/sync",
        headers=auth_headers
    )
    assert response.status_code == 202
    assert response.json()["task_id"] == "mock-id-123"
    
    # second call should be rate limited (429)
    response = await async_client.post(
        f"/api/v1/connectors/{config.id}/sync",
        headers=auth_headers
    )
    assert response.status_code == 429
